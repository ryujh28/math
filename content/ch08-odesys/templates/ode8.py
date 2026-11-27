"""8장 고계 및 연립 ODE — 생성기.

참값은 SymPy의 고수준 연산(roots, eigenvals, jacobian, dsolve)으로 따로 구하고,
화면 TeX는 손으로 조립한다. 스칼라 ODE의 독립변수는 x, 연립계는 t.
"""
import itertools
import random
import sympy as sp
from texkit import tex, join_terms, sum_tex, poly_tex, mat, tup
from checks import same, opt, step, vstep, decoy, vdecoy, is_family_solution, independent, x, r, t

CS = sp.symbols("C1:5")
DER = {0: "y", 1: r"y^{\prime}", 2: r"y^{\prime\prime}", 3: r"y^{\prime\prime\prime}", 4: r"y^{(4)}"}
X_, Y_ = sp.symbols("X Y")          # 연립계 상태변수 (화면에는 x, y)


# ---------------------------------------------------------------- 공통
def _poly_from_roots(roots):
    """roots: [(값, 중복도)] (복소수는 켤레 둘 다) → 실계수 다항식 (r에 대해, 최고차 계수 1)."""
    p = sp.Integer(1)
    for v, m in roots:
        p *= (r - v) ** m
    return sp.expand(p)


def _ode_tex(cp, rhs=0):
    """특성다항식 cp(r) → y''' − 6y'' + … = rhs."""
    P = sp.Poly(cp, r)
    parts = [(c, DER[k]) for (k,), c in sorted(P.terms(), key=lambda q: -q[0][0])]
    return f"{join_terms(parts)} = {tex(rhs)}"


def _L(cp):
    P = sp.Poly(cp, r)
    return lambda g, P=P: sum(c * sp.diff(g, x, k) for (k,), c in P.terms())


def _basis(spec):
    """spec: [('re', a, m) | ('cx', α, β, m)] → 기저 함수 목록."""
    out = []
    for sp_ in spec:
        if sp_[0] == "re":
            _, a, m = sp_
            out += [x**k * sp.exp(a * x) for k in range(m)]
        else:
            _, al, be, m = sp_
            for k in range(m):
                out += [x**k * sp.exp(al * x) * sp.cos(be * x), x**k * sp.exp(al * x) * sp.sin(be * x)]
    return out


def _roots_of(spec):
    out = []
    for sp_ in spec:
        if sp_[0] == "re":
            out.append((sp_[1], sp_[2]))
        else:
            _, al, be, m = sp_
            out += [(al + be * sp.I, m), (al - be * sp.I, m)]
    return out


def _gen_tex(basis):
    return " + ".join(f"C_{i + 1}{tex(f)}" if tex(f) != "1" else f"C_{i + 1}" for i, f in enumerate(basis))


def _basis_ok(cp, n):
    L = _L(cp)
    return lambda b, L=L, n=n: len(b) == n and all(same(sp.simplify(L(f)), 0) for f in b) and independent(list(b))


def _roots_tex(spec):
    parts = []
    for sp_ in spec:
        if sp_[0] == "re":
            _, a, m = sp_
            parts.append(f"{tex(a)}" + ({1: "", 2: r"\ (\text{중근})", 3: r"\ (\text{삼중근})"}[m]))
        else:
            _, al, be, m = sp_
            parts.append(rf"{tex(al) + ' ' if al else ''}\pm {tex(be) if be != 1 else ''}i" + (r"\ (\text{중근})" if m == 2 else ""))
    return r"r = " + r",\ ".join(parts)


def _rootset(spec):
    return sorted([(sp.re(v), sp.im(v), m) for v, m in _roots_of(spec)], key=lambda q: (float(q[0]), float(q[1]), q[2]))


def _rootset_ok(spec_true):
    truth = _rootset(spec_true)
    return lambda spec: _rootset(spec) == truth


def _neg_spec(spec):
    return [("re", -s_[1], s_[2]) if s_[0] == "re" else ("cx", -s_[1], s_[2], s_[3]) for s_ in spec]


# 근 구조 가족 (3계 · 4계)
def _specs():
    fam = {"real": [], "rep": [], "triple": [], "cplx": [], "quart": []}
    for a, b, c in itertools.combinations([-3, -2, -1, 0, 1, 2, 3], 3):
        if max(abs(a), abs(b), abs(c)) <= 3 and (a, b, c) != (-3, 0, 3):
            fam["real"].append([("re", a, 1), ("re", b, 1), ("re", c, 1)])
    for a, b in itertools.permutations([-2, -1, 0, 1, 2], 2):
        fam["rep"].append([("re", a, 2), ("re", b, 1)])
    for a in [-2, -1, 1, 2, 3, -3]:
        fam["triple"].append([("re", a, 3)])
    for c, al, be in itertools.product([-2, -1, 0, 1, 2], [0, -1, 1], [1, 2]):
        fam["cplx"].append([("re", c, 1), ("cx", al, be, 1)])
    for k in [1, 2, 3]:
        fam["quart"].append([("re", k, 1), ("re", -k, 1), ("cx", 0, k, 1)])      # r⁴ − k⁴
        fam["quart"].append([("cx", 0, k, 2)])                                    # (r² + k²)²
        fam["quart"].append([("re", 0, 2), ("cx", 0, k, 1)])                      # r²(r² + k²)
        fam["quart"].append([("re", 0, 2), ("re", k, 1), ("re", -k, 1)])          # r²(r² − k²)
    return fam


WHY = {
    "char_sign": r"$y^{(k)}$를 $r^k$로 바꿉니다. 계수의 부호를 그대로 옮겨야 합니다.",
    "root_sign": r"특성방정식의 근의 부호가 틀렸습니다. 인수 $(r - a)$의 근은 $a$입니다.",
    "rep": r"$m$중근 $a$에는 $e^{ax}, xe^{ax}, \dots, x^{m-1}e^{ax}$가 대응합니다. 같은 함수를 두 번 쓰면 독립인 해가 모자랍니다.",
    "cplx": r"복소근 $\alpha \pm \beta i$에는 $e^{\alpha x}\cos\beta x$, $e^{\alpha x}\sin\beta x$가 대응합니다.",
    "basis_sign": r"근 $r$에 대응하는 해는 $e^{rx}$입니다. 지수의 부호가 바뀌었습니다.",
    "consts": r"초기조건을 일반해와 그 도함수에 넣어 상수에 대한 연립방정식을 풀어야 합니다.",
    "final": r"상수를 대입한 결과가 초기조건이나 방정식을 만족하지 않습니다.",
}


# ---------------------------------------------------------------- 원자 1: 고계 동차 일반해
def high_general():
    """3계·4계 상수계수 동차 ODE의 일반해 (특성방정식을 인수분해해야 한다)."""
    out = []
    fam = _specs()
    rng = random.Random(81)
    for k, lst in fam.items():
        rng.shuffle(lst)
        for spec in lst[:9]:
            cp = _poly_from_roots(_roots_of(spec))
            if any(not c.is_integer for c in sp.Poly(cp, r).coeffs()):
                continue
            n = sp.degree(cp, r)
            basis = _basis(spec)
            okb = _basis_ok(cp, n)
            wrongs = [(_basis(_neg_spec(spec)), "sign")]
            if any(s_[0] == "re" and s_[2] > 1 for s_ in spec):
                wb = []
                for s_ in spec:
                    if s_[0] == "re":
                        wb += [sp.exp(s_[1] * x * (j + 1)) for j in range(s_[2])] if s_[2] > 1 else [sp.exp(s_[1] * x)]
                    else:
                        wb += _basis([s_])
                wrongs.append((wb, "algebra"))
            if any(s_[0] == "cx" for s_ in spec):
                wb = []
                for s_ in spec:
                    if s_[0] == "cx":
                        _, al, be, m = s_
                        wb += [x**j * f_ for j in range(m) for f_ in (sp.exp((al + be) * x), sp.exp((al - be) * x))]
                    else:
                        wb += _basis([s_])
                wrongs.append((wb, "wrong_pair"))
            sh = [("re", s_[1] + 1, s_[2]) if s_[0] == "re" else ("cx", s_[1], s_[2] + 1, s_[3]) for s_ in spec]
            wrongs.append((_basis(sh), "algebra"))
            if len(wrongs) < 4:
                wrongs.append((basis[:-1] + [x * basis[-1]], "algebra"))
            out.append({"params": {"spec": str(spec), "cp": str(cp), "family": k}, "tier": {"real": 1, "rep": 2, "triple": 2, "cplx": 2, "quart": 3}[k],
                        "pace": "compute",
                        "prompt": rf"{_ode_tex(cp)}\ \text{{의 일반해}}",
                        "answer": opt("y = " + _gen_tex(basis), lambda b=basis, ok=okb: ok(b)),
                        "wrong": [opt("y = " + _gen_tex(b), lambda b=b, ok=okb: ok(b), e) for b, e in wrongs]})
    return out


# ---------------------------------------------------------------- 원자 2: 중근에 대응하는 해
def repeated_root():
    """특성근 a가 m중근일 때 대응하는 m개의 해."""
    out = []
    for a, m in itertools.product([-3, -2, -1, 1, 2, 3, 4], [2, 3, 4]):
        cp = (r - a) ** m
        L = _L(sp.expand(cp))
        ok = lambda fs, L=L, m=m: len(fs) == m and all(same(sp.simplify(L(f)), 0) for f in fs) and independent(list(fs))
        right = [x**k * sp.exp(a * x) for k in range(m)]
        wr = [([sp.exp((k + 1) * a * x) for k in range(m)], "algebra"),
              ([x**k * sp.exp(-a * x) for k in range(m)], "sign"),
              ([x**(k + 1) * sp.exp(a * x) for k in range(m)], "algebra"),
              ([sp.exp(a * x)] + [x**k for k in range(1, m)], "missing_factor")]
        out.append({"params": {"a": a, "m": m}, "tier": 1 if m == 2 else 2,
                    "prompt": rf"\text{{특성근}}\ r = {tex(a)}\ \text{{가}}\ {m}\text{{중근일 때 대응하는 해}}",
                    "answer": opt(r",\ ".join(tex(f) for f in right), lambda fs=right, ok=ok: ok(fs)),
                    "wrong": [opt(r",\ ".join(tex(f) for f in fs), lambda fs=fs, ok=ok: ok(fs), e) for fs, e in wr]})
    return out


# ---------------------------------------------------------------- 원자 3: 3×3 Wronskian
def _wr(fs):
    return sp.simplify(sp.Matrix([[sp.diff(f, x, k) for f in fs] for k in range(3)]).det())


def wronskian3():
    out = []
    sets = []
    for a, b, c in itertools.combinations([-2, -1, 0, 1, 2, 3], 3):
        sets.append(("exp", [sp.exp(a * x), sp.exp(b * x), sp.exp(c * x)]))
    for a in [-2, -1, 1, 2, 3]:
        sets.append(("rep", [sp.exp(a * x), x * sp.exp(a * x), x**2 * sp.exp(a * x)]))
    for k in [1, 2, 3, 4]:
        sets.append(("trig", [sp.Integer(1), sp.cos(k * x), sp.sin(k * x)]))
    sets.append(("poly", [sp.Integer(1), x, x**2]))
    for a in [1, 2, -1]:
        sets.append(("mix", [sp.Integer(1), x, sp.exp(a * x)]))
    for fam, fs in sets:
        W = _wr(fs)
        if W == 0:
            continue
        cand = [(-W, "sign"), (sp.simplify(W / 2) if fam in ("poly", "rep") else sp.simplify(W * 2), "missing_factor")]
        if W.has(sp.exp):
            cand.append((sp.simplify(W.subs(x, 0)), "missing_factor"))
            cand.append((sp.simplify(W * sp.exp(x)), "algebra"))
        else:
            cand.append((W + 1, "algebra"))
            cand.append((sp.simplify(W * x), "algebra"))
        ok = lambda e, fs=fs: same(e, _wr(fs))
        out.append({"params": {"fs": str(fs), "family": fam}, "tier": 1 if fam in ("poly", "exp") else 2, "pace": "compute",
                    "prompt": rf"W\left({r',\ '.join(tex(f) for f in fs)}\right) = \;?",
                    "answer": opt(tex(W), lambda e=W, ok=ok: ok(e)),
                    "wrong": [opt(tex(e), lambda e=e, ok=ok: ok(e), er) for e, er in cand]})
    return out


# ---------------------------------------------------------------- 원자 4: 동반행렬 (고계 → 1계 연립)
def companion():
    out = []
    for a, b, c in itertools.product([0, 1, -2, 3], [2, -1, 4], [1, -3, 5]):
        cp = r**3 + a * r**2 + b * r + c
        A = sp.Matrix([[0, 1, 0], [0, 0, 1], [-c, -b, -a]])
        ok = lambda M, cp=cp: sp.Matrix(M).shape == (3, 3) and same(sp.expand((r * sp.eye(3) - sp.Matrix(M)).det()), cp) and sp.Matrix(M)[0, :] == sp.Matrix([[0, 1, 0]]) and sp.Matrix(M)[1, :] == sp.Matrix([[0, 0, 1]])
        wr = [(sp.Matrix([[0, 1, 0], [0, 0, 1], [c, b, a]]), "sign"),
              (sp.Matrix([[0, 1, 0], [0, 0, 1], [-a, -b, -c]]), "algebra"),
              (A.T, "algebra"),
              (sp.Matrix([[0, 1, 0], [0, 0, 1], [a, b, c]]), "sign")]
        out.append({"params": {"a": a, "b": b, "c": c}, "tier": 1,
                    "prompt": rf"{_ode_tex(cp)},\ \mathbf{{u}} = (y,\ y^{{\prime}},\ y^{{\prime\prime}})\ \text{{일 때}}\ \mathbf{{u}}^{{\prime}} = A\mathbf{{u}}\text{{의}}\ A",
                    "answer": opt(mat(A), lambda M=A, ok=ok: ok(M)),
                    "wrong": [opt(mat(M), lambda M=M, ok=ok: ok(M), e) for M, e in wr if M != A]})
    return out


# ---------------------------------------------------------------- 평형점 분류
LABEL = {"saddle": r"\text{안장점 (불안정)}", "snode": r"\text{안정 마디}", "unode": r"\text{불안정 마디}",
         "sspiral": r"\text{안정 나선}", "uspiral": r"\text{불안정 나선}", "center": r"\text{중심}",
         "sdeg": r"\text{안정 퇴화 마디}", "udeg": r"\text{불안정 퇴화 마디}"}


def classify(A):
    ev = sp.Matrix(A).eigenvals()
    vals = [k for k, m in ev.items() for _ in range(m)]
    if any(v == 0 for v in vals):
        return None
    if all(sp.im(v) == 0 for v in vals):
        a, b = sorted([sp.re(v) for v in vals])
        if a * b < 0:
            return "saddle"
        if a == b:
            return "sdeg" if a < 0 else "udeg"
        return "snode" if a < 0 else "unode"
    re_ = sp.re(vals[0])
    return "center" if re_ == 0 else ("sspiral" if re_ < 0 else "uspiral")


NEAR = {"saddle": ["unode", "snode", "center"], "snode": ["unode", "sspiral", "saddle"], "unode": ["snode", "uspiral", "saddle"],
        "sspiral": ["uspiral", "snode", "center"], "uspiral": ["sspiral", "unode", "center"], "center": ["sspiral", "uspiral", "saddle"],
        "sdeg": ["udeg", "snode", "sspiral"], "udeg": ["sdeg", "unode", "uspiral"]}


def _mats2(rng, n=4000, lim=4):
    seen, out = set(), []
    for _ in range(n):
        A = sp.Matrix(2, 2, [rng.randint(-lim, lim) for _ in range(4)])
        if tuple(A) in seen or A.det() == 0:
            continue
        seen.add(tuple(A))
        cl = classify(A)
        if cl is None:
            continue
        ev = list(A.eigenvals().keys())
        nice = all(sp.re(v).is_rational and (sp.im(v) == 0 or sp.im(v).is_rational) for v in ev)
        out.append((A, cl, nice))
    return out


def phase_type():
    """고유값(1단계) 또는 행렬(2단계)로 평형점 분류."""
    out = []
    evs = [((-2, -1), "snode"), ((1, 3), "unode"), ((-1, 2), "saddle"), ((-3, 1), "saddle"), ((-4, -2), "snode"), ((2, 5), "unode")]
    evs += [((-1 + 2 * sp.I, -1 - 2 * sp.I), "sspiral"), ((1 + sp.I, 1 - sp.I), "uspiral"), ((3 * sp.I, -3 * sp.I), "center"),
            ((2 * sp.I, -2 * sp.I), "center"), ((-2 + sp.I, -2 - sp.I), "sspiral"), ((2 + 3 * sp.I, 2 - 3 * sp.I), "uspiral"),
            ((-3, -3), "sdeg"), ((2, 2), "udeg")]
    for ev, cl in evs:
        D = sp.Matrix([[sp.re(ev[0]), -sp.im(ev[0])], [sp.im(ev[0]), sp.re(ev[0])]]) if sp.im(ev[0]) else sp.Matrix([[ev[0], 1 if ev[0] == ev[1] else 0], [0, ev[1]]])
        ok = lambda l, D=D: l == classify(D)
        out.append({"params": {"ev": [str(e) for e in ev], "family": "eig"}, "tier": 1,
                    "prompt": rf"\mathbf{{x}}^{{\prime}} = A\mathbf{{x}},\ \lambda = {tex(ev[0])},\ {tex(ev[1])}\ \text{{일 때 원점은}}",
                    "answer": opt(LABEL[cl], lambda l=cl, ok=ok: ok(l)),
                    "wrong": [opt(LABEL[w], lambda l=w, ok=ok: ok(l), "theorem_condition") for w in NEAR[cl]]})
    rng = random.Random(83)
    cnt = {}
    for A, cl, nice in _mats2(rng):
        if cnt.get(cl, 0) >= 4:
            continue
        cnt[cl] = cnt.get(cl, 0) + 1
        ok = lambda l, A=A: l == classify(A)
        out.append({"params": {"A": list(A), "family": "mat"}, "tier": 2, "pace": "compute",
                    "prompt": rf"\mathbf{{x}}^{{\prime}} = {mat(A)}\mathbf{{x}}\ \text{{의 원점은}}",
                    "answer": opt(LABEL[cl], lambda l=cl, ok=ok: ok(l)),
                    "wrong": [opt(LABEL[w], lambda l=w, ok=ok: ok(l), "theorem_condition") for w in NEAR[cl]]})
    return out


# ---------------------------------------------------------------- 원자 6: 점근 안정이 되는 매개변수 범위
k_ = sp.Symbol("k")


def _stable(A):
    return all(sp.re(v) < 0 for v in sp.Matrix(A).eigenvals())


def _region_ok(Ak, rel, c):
    """'k < c' 또는 'k > c'가 점근 안정 영역과 같은지 (표본 k에서 비교)."""
    pts = [c + d for d in (-sp.Rational(7, 2), -1, -sp.Rational(1, 3), sp.Rational(1, 3), 1, sp.Rational(7, 2))]
    for kv in pts:
        want = _stable(Ak.subs(k_, kv))
        got = (kv < c) if rel == "<" else (kv > c)
        if bool(want) != bool(got):
            return False
    return True


def stability_range():
    out = []
    for a, b, d in itertools.product([1, 2, -1, 3], [-1, -2, 2, -3], [-2, -3, -1, -4]):
        Ak = sp.Matrix([[k_, a], [b, d]])
        tr, det = Ak.trace(), Ak.det()
        # 점근 안정 ⟺ tr < 0, det > 0
        k_tr = sp.solve(sp.Eq(tr, 0), k_)[0]
        k_det = sp.solve(sp.Eq(det, 0), k_)[0]
        # det = d k − ab : d < 0 이므로 det > 0 ⟺ k < ab/d
        c = min(k_tr, k_det)
        if not _region_ok(Ak, "<", c) or c == k_tr == k_det:
            continue
        other = max(k_tr, k_det)
        cand = [(">", c, "sign"), ("<", other, "theorem_condition"), ("<", -c, "sign") if -c not in (c, other) else (">", other, "sign"), (">", other, "theorem_condition")]
        seen = {("<", c)}
        wr = []
        for rel, v, e in cand:
            if (rel, v) in seen:
                continue
            seen.add((rel, v))
            wr.append(opt(f"k {rel} {tex(v)}", lambda rel=rel, v=v, Ak=Ak: _region_ok(Ak, rel, v), e))
        out.append({"params": {"a": a, "b": b, "d": d}, "tier": 2, "pace": "compute",
                    "prompt": rf"\mathbf{{x}}^{{\prime}} = {mat(Ak)}\mathbf{{x}}\ \text{{의 원점이 점근 안정인}}\ k",
                    "answer": opt(f"k < {tex(c)}", lambda v=c, Ak=Ak: _region_ok(Ak, "<", v)),
                    "wrong": wr})
    return out


# ---------------------------------------------------------------- 비선형계 (평형점 · Jacobian)
def _systems():
    """(가족, f, g, 변수 표시, 매개변수) — f, g는 X_, Y_의 식."""
    out = []
    for a, b, c, d in itertools.product([1, 2, 3], [1, 2], [1, 2, 3], [1, 2]):
        out.append(("lv", X_ * (a - b * Y_), Y_ * (-c + d * X_), {"a": a, "b": b, "c": c, "d": d}))
    for p, q, al, be in itertools.product([2, 3, 4], [2, 3, 4], [1, sp.Rational(1, 2)], [1, sp.Rational(1, 2)]):
        out.append(("comp", X_ * (p - X_ - al * Y_), Y_ * (q - be * X_ - Y_), {"p": p, "q": q, "al": al, "be": be}))
    for k, cc in itertools.product([1, 2, 4, 9], [0, 1, 2]):
        out.append(("pend", Y_, -k * sp.sin(X_) - cc * Y_, {"k": k, "c": cc}))
    for a, cc in itertools.product([1, 2, 4], [0, 1, 3]):
        out.append(("duff", Y_, a * X_ - X_**3 - cc * Y_, {"a": a, "c": cc}))
    return out


def _sys_tex(f, g, fam=None, P=None):
    """교과서 꼴로: x' = x(a − by), y' = y(−c + dx) 등."""
    if fam == "lv":
        return rf"x^{{\prime}} = x\left({join_terms([(P['a'], ''), (-P['b'], 'y')])}\right),\ y^{{\prime}} = y\left({join_terms([(P['d'], 'x'), (-P['c'], '')])}\right)"
    if fam == "comp":
        return rf"x^{{\prime}} = x\left({join_terms([(P['p'], ''), (-1, 'x'), (-P['al'], 'y')])}\right),\ y^{{\prime}} = y\left({join_terms([(P['q'], ''), (-P['be'], 'x'), (-1, 'y')])}\right)"
    if fam == "pend":
        return rf"x^{{\prime}} = y,\ y^{{\prime}} = {join_terms([(-P['k'], r'\sin x'), (-P['c'], 'y')])}"
    if fam == "duff":
        return rf"x^{{\prime}} = y,\ y^{{\prime}} = {join_terms([(P['a'], 'x'), (-1, 'x^{3}'), (-P['c'], 'y')])}"
    sub = {X_: sp.Symbol("x"), Y_: sp.Symbol("y")}
    return rf"x^{{\prime}} = {tex(f.subs(sub))},\ y^{{\prime}} = {tex(g.subs(sub))}"


def _equilibria(f, g, fam):
    if fam == "pend":
        return [(sp.Integer(0), sp.Integer(0)), (sp.pi, sp.Integer(0))]
    sol = sp.solve([f, g], [X_, Y_], dict=True)
    if any(X_ not in s_ or Y_ not in s_ for s_ in sol):
        return None                      # 평형점이 곡선을 이루는 퇴화 사례
    return [(s_[X_], s_[Y_]) for s_ in sol]


def equilibria():
    out = []
    rng = random.Random(85)
    for fam, f, g, P in _systems():
        if fam == "pend":
            continue
        eq = _equilibria(f, g, fam)
        if eq is None:
            continue
        eq = [e for e in eq if all(v.is_real for v in e)]
        ok = lambda pts, f=f, g=g, n=len(eq): len(set(pts)) == n and all(same(f.subs({X_: a, Y_: b}), 0) and same(g.subs({X_: a, Y_: b}), 0) for a, b in pts)
        eqs = sorted(eq, key=lambda q: (float(q[0]), float(q[1])))
        txt = lambda pts: r",\ ".join(tup(p) for p in pts)
        wr = []
        nz = [e for e in eqs if e != (0, 0)]
        wr.append((eqs[:1] + [(b, a) for a, b in nz], "algebra"))
        wr.append(([e for e in eqs if e != (0, 0)] or [(1, 1)], "missing_factor"))
        wr.append((eqs[:1] + [(-a, -b) for a, b in nz], "sign"))
        wr.append(([(0, 0)] + [(sp.Rational(1, 1) / a if a else 0, b) for a, b in nz], "algebra"))
        wr = [(p_, e_) for p_, e_ in wr if len(set(p_)) == len(p_)]
        out.append({"params": {**P, "family": fam}, "tier": 1 if fam == "lv" else 2,
                    "prompt": rf"{_sys_tex(f, g, fam, P)}\ \text{{의 평형점 전부}}",
                    "answer": opt(txt(eqs), lambda pts=eqs, ok=ok: ok(pts)),
                    "wrong": [opt(txt(p), lambda pts=p, ok=ok: ok(pts), e) for p, e in wr]})
    rng.shuffle(out)
    return out[:40]


def _J(f, g):
    return sp.Matrix([[sp.diff(f, X_), sp.diff(f, Y_)], [sp.diff(g, X_), sp.diff(g, Y_)]])


def jacobian_at():
    out = []
    for fam, f, g, P in _systems():
        J = _J(f, g)
        eqs = _equilibria(f, g, fam)
        if eqs is None:
            continue
        eqs = [e for e in eqs if all(v.is_real for v in e)]
        e = [q for q in eqs if q != (0, 0)][-1] if fam != "pend" else (0, 0)
        Je = J.subs({X_: e[0], Y_: e[1]})
        o = [q for q in eqs if q != e][0]
        ok = lambda M, Je=Je: same(sp.Matrix(M), Je)
        wr = [(Je.T, "algebra"), (J.subs({X_: o[0], Y_: o[1]}), "wrong_pair"), (-Je, "sign"),
              (sp.Matrix([[Je[0, 0], -Je[0, 1]], [Je[1, 0], -Je[1, 1]]]), "sign")]
        out.append({"params": {**P, "family": fam, "pt": [str(v) for v in e]}, "tier": 2, "pace": "compute",
                    "prompt": rf"{_sys_tex(f, g, fam, P)}\ \text{{의 평형점}}\ {tup(e)}\ \text{{에서 Jacobian}}",
                    "answer": opt(mat(Je), lambda M=Je, ok=ok: ok(M)),
                    "wrong": [opt(mat(M), lambda M=M, ok=ok: ok(M), er) for M, er in wr]})
    rng = random.Random(87)
    rng.shuffle(out)
    return out[:40]


# ================================================================ 풀이 뼈대
WHY.update({
    "elim_y": r"첫 식 $x^{\prime} = ax + by$에서 $y = \dfrac{x^{\prime} - ax}{b}$입니다. $ax$의 부호를 바꾸면 안 됩니다.",
    "elim_ode": r"소거하면 $x^{\prime\prime} - (\operatorname{tr}A)x^{\prime} + (\det A)x = 0$입니다. 계수는 $\operatorname{tr}A$와 $\det A$입니다.",
    "elim_ygen": r"$y$는 새로 상수를 붙이지 않고 $x$의 일반해에서 $y = \dfrac{x^{\prime} - ax}{b}$로 구합니다.",
    "swap": r"두 상수를 바꿔 넣었습니다. 초기조건이 맞지 않습니다.",
    "tr": r"$\operatorname{tr}A$는 대각성분의 합, $\det A = ad - bc$입니다.",
    "disc": r"판별식은 $\Delta = (\operatorname{tr}A)^2 - 4\det A$입니다. 부호로 실근·복소근이 갈립니다.",
    "ev": r"고유값은 $\lambda = \dfrac{\operatorname{tr}A \pm \sqrt{\Delta}}{2}$입니다.",
    "stab": r"실수부가 모두 음수면 안정, 하나라도 양수면 불안정입니다. 실근의 부호가 다르면 안장점입니다.",
    "kind": r"고유값이 실수면 마디나 안장점, 복소수면 나선, 순허수면 중심입니다.",
    "jac_T": r"Jacobian의 $(i, j)$ 성분은 $i$번째 식을 $j$번째 변수로 미분한 것입니다. 행과 열을 바꿨습니다.",
    "jac_pt": r"선형화는 묻는 평형점에서 Jacobian을 계산해야 합니다. 다른 평형점의 값입니다.",
    "eq": r"평형점에서는 두 식이 모두 0입니다. 이 점은 그렇지 않습니다.",
    "xstar": r"평형점은 $A\mathbf{x}^* + \mathbf{b} = \mathbf{0}$, 즉 $\mathbf{x}^* = -A^{-1}\mathbf{b}$입니다. 부호가 틀렸습니다.",
    "u0": r"편차 $\mathbf{u} = \mathbf{x} - \mathbf{x}^*$의 초기값은 $\mathbf{x}(0) - \mathbf{x}^*$입니다.",
    "back": r"마지막에 $\mathbf{x} = \mathbf{x}^* + \mathbf{u}$로 평형점을 더해야 합니다.",
})


def _ic_tex(vals):
    return r",\ ".join(f"{DER[k].replace('y', 'y', 1)}(0) = {tex(v)}" for k, v in enumerate(vals))


def high_ivp():
    """3계·4계 상수계수 초기값 문제. 가족: 서로 다른 실근 · 중근 · 삼중근 · 실근 + 복소근 · 4계."""
    out = []
    fam = _specs()
    rng = random.Random(91)
    for k, lst in fam.items():
        rng.shuffle(lst)
        made = 0
        for spec in lst:
            if made >= {"real": 16, "rep": 16, "triple": 12, "cplx": 16, "quart": 12}[k]:
                break
            cp = _poly_from_roots(_roots_of(spec))
            if any(not c.is_integer for c in sp.Poly(cp, r).coeffs()):
                continue
            n = sp.degree(cp, r)
            basis = _basis(spec)
            cs = [rng.choice([1, -1, 2, -2, 3]) for _ in range(n)]
            ytrue = sp.expand(sum(c * f for c, f in zip(cs, basis)))
            ics = [sp.diff(ytrue, x, j).subs(x, 0) for j in range(n)]
            if max(abs(v) for v in ics) > 30:
                continue
            fam_expr = sum(CS[i] * basis[i] for i in range(n))
            L = _L(cp)
            okb = _basis_ok(cp, n)
            ok_c = lambda cv, fe=fam_expr, ics=ics, n=n: all(same(sp.diff(fe, x, j).subs(x, 0).subs(dict(zip(CS, cv))), ics[j]) for j in range(n))
            ok_y = lambda Y, L=L, ics=ics, n=n: same(sp.simplify(L(Y)), 0) and all(same(sp.diff(Y, x, j).subs(x, 0), ics[j]) for j in range(n))
            ctex = lambda cv: r",\ ".join(f"C_{i + 1} = {tex(v)}" for i, v in enumerate(cv))
            bad_cp = sp.expand(cp.subs(r, -r) * (-1) ** n)
            steps = [
                vstep(rf"{poly_tex(cp, r)} = 0", cp, sp.expand(sum(c * r**k_ for (k_,), c in sp.Poly(cp, r).terms()))),
                step(_roots_tex(spec), lambda sp_=spec, ok=_rootset_ok(spec): ok(sp_)),
                step(f"y = {_gen_tex(basis)}", lambda b=basis, ok=okb: ok(b)),
                step(ctex(cs), lambda cv=cs, ok=ok_c: ok(cv)),
                step(f"y = {sum_tex(ytrue)}", lambda Y=ytrue, ok=ok_y: ok(Y)),
            ]
            decoys = []
            if not same(bad_cp, cp):
                decoys.append(vdecoy(0, rf"{poly_tex(bad_cp, r)} = 0", bad_cp, cp, "sign", WHY["char_sign"]))
            ns = _neg_spec(spec)
            if _rootset(ns) != _rootset(spec):
                decoys.append(step(_roots_tex(ns), lambda sp_=ns, ok=_rootset_ok(spec): ok(sp_)) | {"pos": 1, "error": "sign", "why": WHY["root_sign"]})
                decoys.append(decoy(2, f"y = {_gen_tex(_basis(ns))}", lambda b=_basis(ns), ok=okb: ok(b), "sign", WHY["basis_sign"]))
            if k in ("rep", "triple") or any(s_[0] == "cx" and s_[3] == 2 for s_ in spec) or (k == "quart" and spec[0] == ("re", 0, 2)):
                bad = []      # x를 곱해야 할 자리를 지수만 바꾼 함수로 (중근을 실근처럼)
                for s_ in spec:
                    if s_[0] == "re":
                        bad += [sp.exp(s_[1] * x)] * 1 + [sp.exp(s_[1] * x * (j + 2)) for j in range(s_[2] - 1)]
                    else:
                        bad += _basis([("cx", s_[1], s_[2], 1)]) + ([sp.exp(s_[1] * x) * sp.cos(2 * s_[2] * x), sp.exp(s_[1] * x) * sp.sin(2 * s_[2] * x)] if s_[3] == 2 else [])
                decoys.append(decoy(2, f"y = {_gen_tex(bad)}", lambda b=bad, ok=okb: ok(b), "algebra", WHY["rep"]))
            if k in ("cplx", "quart") and any(s_[0] == "cx" for s_ in spec):
                bad = []
                for s_ in spec:
                    bad += _basis([s_]) if s_[0] == "re" else [x**j * f_ for j in range(s_[3]) for f_ in (sp.exp((s_[1] + s_[2]) * x), sp.exp((s_[1] - s_[2]) * x))]
                decoys.append(decoy(2, f"y = {_gen_tex(bad)}", lambda b=bad, ok=okb: ok(b), "wrong_pair", WHY["cplx"]))
            alt = list(reversed(cs))
            if alt != cs:
                decoys.append(decoy(3, ctex(alt), lambda cv=alt, ok=ok_c: ok(cv), "initial_condition", WHY["consts"]))
            decoys.append(decoy(3, ctex(ics), lambda cv=ics, ok=ok_c: ok(cv), "initial_condition", WHY["consts"]) if list(ics) != cs else None)
            Yb = sp.expand(ytrue.subs(x, -x))
            decoys.append(decoy(4, f"y = {sum_tex(Yb)}", lambda Y=Yb, ok=ok_y: ok(Y), "sign", WHY["final"]))
            made += 1
            out.append({"params": {"cp": str(cp), "ics": [str(v) for v in ics], "family": k},
                        "tier": {"real": 1, "rep": 2, "triple": 2, "cplx": 3, "quart": 3}[k],
                        "problem": rf"{_ode_tex(cp)},\quad {_ic_tex(ics)}",
                        "steps": steps, "decoys": [d for d in decoys if d],
                        "verify": lambda Y=ytrue, L=L, ics=ics, n=n: None if same(sp.simplify(L(Y)), 0) and all(same(sp.diff(Y, x, j).subs(x, 0), ics[j]) for j in range(n)) else "해 확인 실패"})
    return out


# ---------------------------------------------------------------- 소거법
def _pair_ok(A):
    a, b, c, d = A

    def ok(X, Yv, consts=()):
        trials = [dict(zip(consts, v)) for v in ((2, -1), (sp.Rational(1, 3), 5))] if consts else [{}]
        for sub in trials:
            Xs, Ys = X.subs(sub), Yv.subs(sub)
            if not (same(sp.diff(Xs, t), a * Xs + b * Ys) and same(sp.diff(Ys, t), c * Xs + d * Ys)):
                return False
        return True
    return ok


def _tbasis(kind, roots):
    if kind == "real":
        return [sp.exp(roots[0] * t), sp.exp(roots[1] * t)]
    if kind == "rep":
        return [sp.exp(roots[0] * t), t * sp.exp(roots[0] * t)]
    al, be = roots
    return [sp.exp(al * t) * sp.cos(be * t), sp.exp(al * t) * sp.sin(be * t)]


def _kind_of(A):
    p, q = A.trace(), A.det()
    dsc = p * p - 4 * q
    if dsc > 0:
        sq = sp.sqrt(dsc)
        if not sq.is_rational:
            return None
        return "real", ((p - sq) / 2, (p + sq) / 2)
    if dsc == 0:
        return "rep", (p / 2,)
    sq = sp.sqrt(-dsc)
    if not sq.is_rational or (p / 2).q != 1 or (sq / 2).q != 1:
        return None
    return "cplx", (p / 2, sq / 2)


def _xt_roots_tex(kind, roots):
    if kind == "real":
        return rf"r = {tex(roots[0])},\ {tex(roots[1])}"
    if kind == "rep":
        return rf"r = {tex(roots[0])}\ (\text{{중근}})"
    al, be = roots
    return rf"r = {tex(al) + ' ' if al else ''}\pm {tex(be) if be != 1 else ''}i"


def _lin2(a, b, var1="x", var2="y"):
    return join_terms([(a, var1), (b, var2)])


def elimination():
    """x' = ax + by, y' = cx + dy 를 소거법으로. 가족: 서로 다른 실근 · 중근 · 복소근 · 근 하나가 0."""
    out = []
    rng = random.Random(93)
    C1_, C2_ = CS[0], CS[1]
    xp = sp.Symbol("xp")
    cnt = {}
    combos = list(itertools.product(range(-4, 5), repeat=4))
    rng.shuffle(combos)
    for a, b, c, d in combos:
        if b == 0 or c == 0:
            continue
        A = sp.Matrix([[a, b], [c, d]])
        kd = _kind_of(A)
        if kd is None:
            continue
        kind, roots = kd
        fam = "zero" if kind == "real" and 0 in roots else kind
        if fam == "real" and any(abs(v) > 4 for v in roots):
            continue
        want = {"real": 18, "rep": 14, "cplx": 16, "zero": 12}[fam]
        if cnt.get(fam, 0) >= want:
            continue
        x0, y0 = rng.choice([(1, 0), (0, 1), (1, 1), (2, -1), (1, -2), (3, 1)])
        basis = _tbasis(kind, roots)
        xg = C1_ * basis[0] + C2_ * basis[1]
        yg = sp.expand((sp.diff(xg, t) - a * xg) / b)
        sol = sp.solve([xg.subs(t, 0) - x0, yg.subs(t, 0) - y0], [C1_, C2_])
        cv = (sol[C1_], sol[C2_])
        if any(abs(v.q) > 6 for v in cv):
            continue
        X = sp.expand(xg.subs({C1_: cv[0], C2_: cv[1]}))
        Yv = sp.expand(yg.subs({C1_: cv[0], C2_: cv[1]}))
        okp = _pair_ok((a, b, c, d))
        cp = r**2 - A.trace() * r + A.det()
        ok_ode = lambda e, A=A: same(e, sp.expand((A - r * sp.eye(2)).det()))
        ok_xb = lambda bs, A=A: all(same(sp.diff(f, t, 2) - A.trace() * sp.diff(f, t) + A.det() * f, 0) for f in bs) and independent(list(bs), t)
        ys_true = sp.solve(xp - a * sp.Symbol("xs") - b * sp.Symbol("ys"), sp.Symbol("ys"))[0]
        yexpr = (xp - a * sp.Symbol("xs")) / b
        bexpr = (xp + a * sp.Symbol("xs")) / b
        ytx = lambda e: rf"y = {tex(sp.expand(e).subs({xp: sp.Symbol('PRIME'), sp.Symbol('xs'): sp.Symbol('x')})).replace('PRIME', r'x^{\prime}')}"
        steps = [
            step(ytx(yexpr), lambda e=yexpr, tr=ys_true: same(e, tr)),
            step(f"{join_terms([(1, r'x^{\prime\prime}'), (-A.trace(), r'x^{\prime}'), (A.det(), 'x')])} = 0",
                 lambda e=cp, ok=ok_ode: ok(e)),
            step(rf"{_xt_roots_tex(kind, roots)},\ x = {_gen_tex_t(basis)}", lambda bs=basis, ok=ok_xb: ok(bs)),
            step(rf"y = {_ctex(yg, (C1_, C2_))}", lambda X=xg, Y=yg, ok=okp, cs=(C1_, C2_): ok(X, Y, cs)),
            step(rf"x = {sum_tex(X)},\ y = {sum_tex(Yv)}", lambda X=X, Y=Yv, ok=okp, x0=x0, y0=y0: ok(X, Y) and same(X.subs(t, 0), x0) and same(Y.subs(t, 0), y0)),
        ]
        ybad = sp.expand((sp.diff(xg, t) + a * xg) / b)
        badcp = r**2 + A.trace() * r + A.det()
        decoys = [
            step(ytx(bexpr), lambda e=bexpr, tr=ys_true: same(e, tr)) | {"pos": 0, "error": "sign", "why": WHY["elim_y"]} if a != 0 else None,
            step(rf"y = {_ctex(ybad, (C1_, C2_))}", lambda X=xg, Y=ybad, ok=okp, cs=(C1_, C2_): ok(X, Y, cs)) | {"pos": 3, "error": "sign", "why": WHY["elim_y"]} if a != 0 else None,
            step(rf"y = C_3{tex(basis[0]) if basis[0] != 1 else ''} + C_4{tex(basis[1])}", lambda: False) | {"pos": 3, "error": "algebra", "why": WHY["elim_ygen"]},
        ]
        if A.trace() != 0:
            decoys.append(step(f"{join_terms([(1, r'x^{\prime\prime}'), (A.trace(), r'x^{\prime}'), (A.det(), 'x')])} = 0",
                               lambda e=badcp, ok=ok_ode: ok(e)) | {"pos": 1, "error": "sign", "why": WHY["elim_ode"]})
        if cv[0] != cv[1]:
            Xs = sp.expand(xg.subs({C1_: cv[1], C2_: cv[0]}))
            Ys = sp.expand(yg.subs({C1_: cv[1], C2_: cv[0]}))
            decoys.append(step(rf"x = {sum_tex(Xs)},\ y = {sum_tex(Ys)}", lambda X=Xs, Y=Ys, ok=okp, x0=x0, y0=y0: ok(X, Y) and same(X.subs(t, 0), x0) and same(Y.subs(t, 0), y0))
                          | {"pos": 4, "error": "initial_condition", "why": WHY["swap"]})
        cnt[fam] = cnt.get(fam, 0) + 1
        out.append({"params": {"A": [a, b, c, d], "x0": [x0, y0], "family": fam}, "tier": {"real": 1, "zero": 2, "rep": 3, "cplx": 3}[fam],
                    "problem": rf"x^{{\prime}} = {_lin2(a, b)},\ y^{{\prime}} = {_lin2(c, d)},\quad x(0) = {x0},\ y(0) = {y0}",
                    "steps": steps, "decoys": [q for q in decoys if q],
                    "verify": lambda X=X, Y=Yv, ok=okp, x0=x0, y0=y0: None if ok(X, Y) and same(X.subs(t, 0), x0) and same(Y.subs(t, 0), y0) else "해 아님"})
    return out


def _gen_tex_t(basis):
    return " + ".join(f"C_{i + 1}{tex(f)}" if f != 1 else f"C_{i + 1}" for i, f in enumerate(basis))


def _ctex(e, consts):
    """상수별로 묶어서: C_1(…) + C_2(…)."""
    parts = []
    for i, c in enumerate(consts):
        co = sp.factor(sp.expand(e).coeff(c))
        if co == 0:
            continue
        body = tex(co)
        if co == 1:
            parts.append((1, f"C_{i + 1}"))
        elif co == -1:
            parts.append((-1, f"C_{i + 1}"))
        elif sp.Add.make_args(sp.expand(co)).__len__() == 1:
            num = co.as_coeff_Mul()
            parts.append((num[0], f"C_{i + 1}" + (tex(num[1]) if num[1] != 1 else "")))
        else:
            parts.append((1, rf"C_{i + 1}\left({tex(sp.expand(co))}\right)"))
    return join_terms(parts)


def _sqp(p):
    return f"({tex(p)})^{{2}}" if p < 0 else f"{tex(p)}^{{2}}"


# ---------------------------------------------------------------- 평형점 분류 (뼈대)
def phase_classify():
    """x' = Ax의 원점 분류: tr·det → 판별식 → 고유값 → 분류. 가족: 안장점 · 마디 · 나선 · 중심 · 퇴화 마디."""
    out = []
    rng = random.Random(95)
    famof = {"saddle": "saddle", "snode": "node", "unode": "node", "sspiral": "spiral", "uspiral": "spiral", "center": "center", "sdeg": "deg", "udeg": "deg"}
    cnt = {}
    for A, cl, nice in _mats2(rng, 20000, 5):
        if not nice:
            continue
        fam = famof[cl]
        if cnt.get(fam, 0) >= {"saddle": 14, "node": 16, "spiral": 16, "center": 12, "deg": 12}[fam]:
            continue
        p, q = A.trace(), A.det()
        dsc = p * p - 4 * q
        ev = sorted(A.eigenvals().keys(), key=lambda v: (float(sp.re(v)), float(sp.im(v))))
        evs = [k for k, m in A.eigenvals().items() for _ in range(m)]
        ok_ev = lambda vs, A=A: sorted([sp.nsimplify(v) for v in vs], key=lambda v: (float(sp.re(v)), float(sp.im(v)))) == sorted([k for k, m in A.eigenvals().items() for _ in range(m)], key=lambda v: (float(sp.re(v)), float(sp.im(v))))
        evtex = lambda vs: (rf"\lambda = {tex(vs[0])}\ (\text{{중근}})" if len(set(vs)) == 1 else rf"\lambda = {tex(vs[0])},\ {tex(vs[1])}")
        vs = sorted(evs, key=lambda v: (float(sp.re(v)), float(sp.im(v))))
        steps = [
            step(rf"\operatorname{{tr}}A = {tex(p)},\ \det A = {tex(q)}", lambda pq=(p, q), A=A: same(pq, (A.trace(), A.det()))),
            step(rf"\Delta = {_sqp(p)} - 4\cdot {tex(q) if q >= 0 else '(' + tex(q) + ')'} = {tex(dsc)}", lambda d=dsc, A=A: same(d, A.trace() ** 2 - 4 * A.det())),
            step(evtex(vs), lambda v=vs, ok=ok_ev: ok(v)),
            step(rf"\Rightarrow\ {LABEL[cl]}", lambda l=cl, A=A: l == classify(A)),
        ]
        bq = A[0, 0] * A[1, 1] + A[0, 1] * A[1, 0]
        decoys = [step(rf"\operatorname{{tr}}A = {tex(p)},\ \det A = {tex(bq)}", lambda pq=(p, bq), A=A: same(pq, (A.trace(), A.det()))) | {"pos": 0, "error": "sign", "why": WHY["tr"]} if bq != q else None,
                  step(evtex([-v for v in vs][::-1]), lambda v=[-v for v in vs], ok=ok_ev: ok(v)) | {"pos": 2, "error": "sign", "why": WHY["ev"]} if fam != "center" else None]
        if dsc != 0:
            decoys.append(step(rf"\Delta = {_sqp(p)} + 4\cdot {tex(q) if q >= 0 else '(' + tex(q) + ')'} = {tex(p * p + 4 * q)}", lambda d=p * p + 4 * q, A=A: same(d, A.trace() ** 2 - 4 * A.det())) | {"pos": 1, "error": "sign", "why": WHY["disc"]})
        for w in NEAR[cl][:2]:
            decoys.append(step(rf"\Rightarrow\ {LABEL[w]}", lambda l=w, A=A: l == classify(A)) | {"pos": 3, "error": "theorem_condition", "why": WHY["stab"] if w[0] != cl[0] or "saddle" in (w, cl) else WHY["kind"]})
        cnt[fam] = cnt.get(fam, 0) + 1
        out.append({"params": {"A": list(A), "family": fam}, "tier": {"saddle": 1, "node": 1, "spiral": 2, "center": 2, "deg": 3}[fam],
                    "problem": rf"\mathbf{{x}}^{{\prime}} = {mat(A)}\mathbf{{x}}\ \text{{의 원점 분류}}",
                    "steps": steps, "decoys": [d_ for d_ in decoys if d_]})
    return out


# ---------------------------------------------------------------- 선형화
def linearize():
    """비선형계의 평형점 분류: 평형점 → Jacobian → 평형점에서 값 → 고유값 → 분류.
    가족: 포식자–피식자 · 경쟁 · 진자 · Duffing."""
    out = []
    rng = random.Random(97)
    subs_xy = {X_: sp.Symbol("x"), Y_: sp.Symbol("y")}
    cnt = {}
    systems = _systems()
    rng.shuffle(systems)
    for fam, f, g, P in systems:
        eqs = _equilibria(f, g, fam)
        if eqs is None:
            continue
        eqs = [e for e in eqs if all(v.is_real for v in e)]
        J = _J(f, g)
        for e in eqs:
            Je = J.subs({X_: e[0], Y_: e[1]}).applyfunc(sp.simplify)
            cl = classify(Je)
            if cl is None:
                continue
            ev = [k for k, m in Je.eigenvals().items() for _ in range(m)]
            if not all(sp.re(v).is_rational and (sp.im(v) == 0 or (sp.im(v) ** 2).is_rational) for v in ev):
                continue
            if any(len(tex(v)) > 22 for v in ev):
                continue
            key = (fam, e == (0, 0))
            if cnt.get(fam, 0) >= {"lv": 16, "comp": 16, "pend": 14, "duff": 14}[fam] or cnt.get(key, 0) >= 9:
                continue
            others = [o for o in eqs if o != e]
            Jo = J.subs({X_: others[0][0], Y_: others[0][1]}).applyfunc(sp.simplify) if others else None
            vs = sorted(ev, key=lambda v: (float(sp.re(v)), float(sp.im(v))))
            ok_ev = lambda v, Je=Je: sorted(v, key=lambda q: (float(sp.re(q)), float(sp.im(q)))) == sorted([k for k, m in Je.eigenvals().items() for _ in range(m)], key=lambda q: (float(sp.re(q)), float(sp.im(q))))
            Jt = J.subs(subs_xy)
            steps = [
                step(rf"{tup(e)}:\ f = 0,\ g = 0", lambda e=e, f=f, g=g: same(f.subs({X_: e[0], Y_: e[1]}), 0) and same(g.subs({X_: e[0], Y_: e[1]}), 0)),
                step(rf"J = {mat(Jt)}", lambda M=J, f=f, g=g: same(M, _J(f, g))),
                step(rf"J{tup(e)} = {mat(Je)}", lambda M=Je, Je=Je: same(M, Je)),
                step(rf"\lambda = {tex(vs[0])},\ {tex(vs[1])}" if vs[0] != vs[1] else rf"\lambda = {tex(vs[0])}\ (\text{{중근}})", lambda v=vs, ok=ok_ev: ok(v)),
                step(rf"\Rightarrow\ {LABEL[cl]}" + (r"\ (\text{선형화})" if cl == "center" else ""), lambda l=cl, Je=Je: l == classify(Je)),
            ]
            decoys = [step(rf"J = {mat(Jt.T)}", lambda M=J.T, f=f, g=g: same(M, _J(f, g))) | {"pos": 1, "error": "algebra", "why": WHY["jac_T"]} if not same(J, J.T) else None]
            if Jo is not None and not same(Jo, Je):
                decoys.append(step(rf"J{tup(e)} = {mat(Jo)}", lambda M=Jo, Je=Je: same(M, Je)) | {"pos": 2, "error": "wrong_pair", "why": WHY["jac_pt"]})
            if cl != "center":
                decoys.append(step(rf"\lambda = {tex(-vs[1])},\ {tex(-vs[0])}" if vs[0] != vs[1] else rf"\lambda = {tex(-vs[0])}\ (\text{{중근}})", lambda v=[-q for q in vs], ok=ok_ev: ok(v)) | {"pos": 3, "error": "sign", "why": WHY["ev"]})
            for w in NEAR[cl][:2]:
                decoys.append(step(rf"\Rightarrow\ {LABEL[w]}", lambda l=w, Je=Je: l == classify(Je)) | {"pos": 4, "error": "theorem_condition", "why": WHY["stab"]})
            bad_e = (e[1], e[0])
            if bad_e != e and not (same(f.subs({X_: bad_e[0], Y_: bad_e[1]}), 0) and same(g.subs({X_: bad_e[0], Y_: bad_e[1]}), 0)):
                decoys.append(step(rf"{tup(bad_e)}:\ f = 0,\ g = 0", lambda e=bad_e, f=f, g=g: same(f.subs({X_: e[0], Y_: e[1]}), 0) and same(g.subs({X_: e[0], Y_: e[1]}), 0)) | {"pos": 0, "error": "algebra", "why": WHY["eq"]})
            cnt[fam] = cnt.get(fam, 0) + 1
            cnt[key] = cnt.get(key, 0) + 1
            out.append({"params": {**{k2: str(v2) for k2, v2 in P.items()}, "pt": [str(v) for v in e], "family": fam},
                        "tier": {"lv": 1, "comp": 2, "pend": 2, "duff": 3}[fam],
                        "problem": rf"{_sys_tex(f, g, fam, P)}\ \text{{의 평형점}}\ {tup(e)}\ \text{{를 선형화로 분류}}",
                        "steps": steps, "decoys": [d_ for d_ in decoys if d_]})
    return out


# ---------------------------------------------------------------- 상수 강제항 x' = Ax + b
def forced_system():
    """x' = Ax + b, x(0) = x₀: 평형점 → 편차 u → u의 해 → x = x* + u.
    가족: 서로 다른 실근 · 복소근 · 중근(고유벡터 하나)."""
    out = []
    rng = random.Random(99)
    C1_, C2_ = CS[0], CS[1]
    cnt = {}
    combos = list(itertools.product(range(-4, 5), repeat=4))
    rng.shuffle(combos)
    for a, b, c, d in combos:
        A = sp.Matrix([[a, b], [c, d]])
        if A.det() == 0 or b == 0:
            continue
        kd = _kind_of(A)
        if kd is None:
            continue
        kind, roots = kd
        if kind == "real" and (0 in roots or any(abs(v) > 3 for v in roots)):
            continue
        if kind == "rep" and A.is_diagonal():
            continue
        if cnt.get(kind, 0) >= {"real": 18, "cplx": 16, "rep": 16}[kind]:
            continue
        xs = sp.Matrix([rng.choice([-2, -1, 1, 2, 3]), rng.choice([-2, -1, 1, 2])])
        bb = -A * xs
        if max(abs(v) for v in bb) > 12:
            continue
        x0 = xs + sp.Matrix([rng.choice([-2, -1, 1, 2]), rng.choice([-1, 1, 2, 0])])
        u0 = x0 - xs
        if u0 == sp.zeros(2, 1):
            continue
        # e^{At}를 근의 종류별 닫힌 꼴로 (맞는지는 아래 ok_u가 미분방정식으로 따로 확인)
        if kind == "real":
            l1, l2 = roots
            E = (sp.exp(l1 * t) * (A - l2 * sp.eye(2)) - sp.exp(l2 * t) * (A - l1 * sp.eye(2))) / (l1 - l2)
        elif kind == "rep":
            E = sp.exp(roots[0] * t) * (sp.eye(2) + (A - roots[0] * sp.eye(2)) * t)
        else:
            al, be = roots
            E = sp.exp(al * t) * (sp.cos(be * t) * sp.eye(2) + sp.sin(be * t) * (A - al * sp.eye(2)) / be)
        U = (E * u0).applyfunc(sp.expand)
        if any(len(tex(e)) > 40 for e in U):
            continue
        Xt = (xs + U).applyfunc(sp.expand)
        ok_x = lambda X, A=A, bb=bb, x0=x0: same(sp.diff(X, t), A * X + bb) and same(X.subs(t, 0), x0)
        ok_u = lambda Uv, A=A, u0=u0: same(sp.diff(Uv, t), A * Uv) and same(Uv.subs(t, 0), u0)
        steps = [
            step(rf"\mathbf{{x}}^* = -A^{{-1}}\mathbf{{b}} = {mat(xs)}", lambda v=xs, A=A, bb=bb: same(A * v + bb, sp.zeros(2, 1))),
            step(rf"\mathbf{{u}} = \mathbf{{x}} - \mathbf{{x}}^*:\ \mathbf{{u}}^{{\prime}} = A\mathbf{{u}},\ \mathbf{{u}}(0) = {mat(u0)}", lambda v=u0, x0=x0, xs=xs: same(v, x0 - xs)),
            step(rf"{_xt_roots_tex(kind, roots).replace('r =', r'\lambda =')}", lambda A=A, kd=kd: _kind_of(A) == kd),
            step(rf"\mathbf{{u}}(t) = {mat(U)}", lambda Uv=U, ok=ok_u: ok(Uv)),
            step(rf"\mathbf{{x}}(t) = \mathbf{{x}}^* + \mathbf{{u}} = {mat(Xt)}", lambda X=Xt, ok=ok_x: ok(X)),
        ]
        Xb = U.applyfunc(sp.expand)
        decoys = [
            step(rf"\mathbf{{x}}^* = -A^{{-1}}\mathbf{{b}} = {mat(-xs)}", lambda v=-xs, A=A, bb=bb: same(A * v + bb, sp.zeros(2, 1))) | {"pos": 0, "error": "sign", "why": WHY["xstar"]},
            step(rf"\mathbf{{u}} = \mathbf{{x}} - \mathbf{{x}}^*:\ \mathbf{{u}}^{{\prime}} = A\mathbf{{u}},\ \mathbf{{u}}(0) = {mat(x0)}", lambda v=x0, x0=x0, xs=xs: same(v, x0 - xs)) | {"pos": 1, "error": "initial_condition", "why": WHY["u0"]},
            step(rf"\mathbf{{x}}(t) = \mathbf{{x}}^* + \mathbf{{u}} = {mat(Xb)}", lambda X=Xb, ok=ok_x: ok(X)) | {"pos": 4, "error": "missing_factor", "why": WHY["back"]},
        ]
        if kind == "real":
            Ub = (sp.Matrix([[sp.exp(-roots[0] * t), 0], [0, sp.exp(-roots[1] * t)]]))
            P_ = sp.Matrix.hstack(*[(A - v * sp.eye(2)).nullspace()[0] for v in roots])
            Ub = (P_ * Ub * P_.inv() * u0).applyfunc(sp.expand)
            decoys.append(step(rf"\mathbf{{u}}(t) = {mat(Ub)}", lambda Uv=Ub, ok=ok_u: ok(Uv)) | {"pos": 3, "error": "sign", "why": r"$e^{\lambda t}$의 지수 부호가 바뀌었습니다. $\mathbf{u}^{\prime} = A\mathbf{u}$를 만족하지 않습니다."})
        cnt[kind] = cnt.get(kind, 0) + 1
        out.append({"params": {"A": [a, b, c, d], "b": list(bb), "x0": list(x0), "family": kind}, "tier": {"real": 1, "cplx": 2, "rep": 3}[kind],
                    "problem": rf"\mathbf{{x}}^{{\prime}} = {mat(A)}\mathbf{{x}} + {mat(bb)},\ \mathbf{{x}}(0) = {mat(x0)}",
                    "steps": steps, "decoys": decoys,
                    "verify": lambda X=Xt, ok=ok_x: None if ok(X) else "해 아님"})
    return out
