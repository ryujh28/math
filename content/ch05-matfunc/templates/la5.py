"""5장 행렬함수와 이차형식 — 생성기."""
import itertools
import random
import sympy as sp
from texkit import tex, mat, tup, join_terms
from checks import same, opt, step, vstep, decoy, vdecoy, x, y, t

UNIMOD = [sp.Matrix(m) for m in ([[1, 1], [0, 1]], [[2, 1], [1, 1]], [[1, 2], [1, 3]], [[1, -1], [1, 0]],
                                  [[1, 0], [1, 1]], [[1, 1], [1, 2]], [[2, 1], [3, 2]])]
LABELS = {"pd": r"\text{양의 정부호}", "nd": r"\text{음의 정부호}", "indef": r"\text{부정부호}", "psd": r"\text{양의 준정부호}", "nsd": r"\text{음의 준정부호}"}


def _qtex(a, b, c):
    return join_terms([(a, "x^{2}"), (b, "xy"), (c, "y^{2}")])


def _classify(M):
    ev = [sp.nsimplify(e) for e in M.eigenvals()]
    if all(e > 0 for e in ev):
        return "pd"
    if all(e < 0 for e in ev):
        return "nd"
    if all(e >= 0 for e in ev):
        return "psd"
    if all(e <= 0 for e in ev):
        return "nsd"
    return "indef"


def qform_matrix():
    out = []
    for a, b, c in itertools.product([1, 2, 3, -1, 5], [-4, -2, 2, 4, 6, 3], [1, 2, -3, 4]):
        q = a * x**2 + b * x * y + c * y**2
        M = sp.Matrix([[a, sp.Rational(b, 2)], [sp.Rational(b, 2), c]])
        v = sp.Matrix([x, y])
        ok = lambda X, q=q, v=v: X == X.T and same(sp.expand((v.T * X * v)[0]), q)
        cands = [(sp.Matrix([[a, b], [b, c]]), "missing_factor"), (sp.Matrix([[a, b], [0, c]]), "algebra"),
                 (sp.Matrix([[a, -sp.Rational(b, 2)], [-sp.Rational(b, 2), c]]), "sign"), (sp.Matrix([[c, sp.Rational(b, 2)], [sp.Rational(b, 2), a]]), "algebra")]
        out.append({"params": {"abc": [a, b, c]}, "tier": 1, "prompt": rf"q(x, y) = {_qtex(a, b, c)} = \mathbf{{x}}^{{T}}A\,\mathbf{{x}},\quad A = \;?",
                    "answer": opt(mat(M), lambda X=M, ok=ok: ok(X)),
                    "wrong": [opt(mat(X), lambda X=X, ok=ok: ok(X), er) for X, er in cands]})
    return out


def definiteness():
    out = []
    for a, b, c in itertools.product([-3, -1, 1, 2, 4], [-4, -2, 0, 2, 4], [-3, -1, 1, 2, 4]):
        M = sp.Matrix([[a, sp.Rational(b, 2)], [sp.Rational(b, 2), c]])
        truth = _classify(M)
        ok = lambda lab, truth=truth: lab == truth
        out.append({"params": {"abc": [a, b, c]}, "tier": 2, "prompt": rf"q(x, y) = {_qtex(a, b, c)}\ \text{{은?}}",
                    "answer": opt(LABELS[truth], lambda l=truth, ok=ok: ok(l)),
                    "wrong": [opt(LABELS[l], lambda l=l, ok=ok: ok(l), "theorem_condition") for l in LABELS if l != truth]})
    return out


def exp_diag():
    out = []
    for a, b in itertools.permutations([-3, -2, -1, 1, 2, 3], 2):
        A = sp.diag(a, b)
        truth = (A * t).exp()
        ea, eb = sp.exp(a * t), sp.exp(b * t)
        cands = [(sp.diag(sp.exp(-a * t), sp.exp(-b * t)), "sign"), (sp.diag(1 + a * t, 1 + b * t), "algebra"),
                 (sp.Matrix([[ea, 1], [1, eb]]), "algebra"), (sp.diag(sp.exp(a) * t, sp.exp(b) * t), "algebra")]
        out.append({"params": {"a": a, "b": b}, "tier": 1, "prompt": rf"A = {mat(A)}\qquad e^{{At}} = \;?",
                    "answer": opt(mat(sp.diag(ea, eb)), lambda X=sp.diag(ea, eb), tr=truth: same(X, tr)),
                    "wrong": [opt(mat(X), lambda X=X, tr=truth: same(X, tr), er) for X, er in cands]})
    return out


def exp_jordan():
    out = []
    for a, c in itertools.product([-4, -3, -2, -1, 1, 2, 3, 4], [1, 2, -1]):
        A = sp.Matrix([[a, c], [0, a]])
        e = sp.exp(a * t)
        truth = sp.Matrix([[e, c * t * e], [0, e]])
        assert same(truth.diff(t), A * truth) and same(truth.subs(t, 0), sp.eye(2))
        ans = truth
        cands = [(sp.Matrix([[e, 0], [0, e]]), "missing_factor"), (sp.Matrix([[e, c * e], [0, e]]), "algebra"),
                 (sp.Matrix([[e, c * sp.exp(t)], [0, e]]), "algebra"), (sp.Matrix([[e, -c * t * e], [0, e]]), "sign"),
                 (sp.Matrix([[e, t * e], [0, e]]), "missing_factor")]
        out.append({"params": {"a": a, "c": c}, "tier": 2, "prompt": rf"A = {mat(A)}\qquad e^{{At}} = \;?",
                    "answer": opt(mat(ans), lambda X=ans, tr=truth: same(X, tr)),
                    "wrong": [opt(mat(X), lambda X=X, tr=truth: same(X, tr), er) for X, er in cands]})
    return out


# ---------------------------------------------------------------- 풀이 뼈대
WHY = {
    "order": r"$e^{At} = Pe^{Dt}P^{-1}$입니다. $P^{-1}e^{Dt}P$는 다른 행렬입니다.",
    "edt": r"$e^{Dt}$는 대각성분 $\lambda_i$에 대해 $e^{\lambda_i t}$입니다. 부호가 틀렸습니다.",
    "vec": r"고유벡터가 아닙니다: $(A - \lambda I)\mathbf{v} \ne \mathbf{0}$.",
    "half": r"$xy$ 계수 $b$는 반으로 나눠 두 비대각 자리에 들어갑니다.",
    "eig": r"이차형식 행렬의 고유값을 잘못 구했습니다.",
    "type": r"고유값의 부호로 판정합니다: 모두 양수면 양의 정부호, 부호가 섞이면 부정부호.",
}


def exp_At():
    out = []
    rng = random.Random(11)
    seen = set()
    for _ in range(2000):
        P = rng.choice(UNIMOD)
        d1, d2 = rng.sample([-3, -2, -1, 1, 2], 2)
        A = P * sp.diag(d1, d2) * P.inv()
        if tuple(A) in seen or A.is_diagonal() or max(abs(e) for e in A) > 8:
            continue
        seen.add(tuple(A))
        truth = (A * t).exp()                                  # 독립 계산
        eD = sp.diag(sp.exp(d1 * t), sp.exp(d2 * t))
        res = (P * eD * P.inv()).applyfunc(sp.expand)      # 성분을 지수의 합으로 (인수분해된 꼴은 읽기 어렵다)
        ok_vec = lambda P_, d_, A=A: P_.det() != 0 and all(same(A * P_[:, j], d_[j] * P_[:, j]) for j in range(2))
        steps = [
            step(rf"\lambda = {tex(d1)},\ {tex(d2)},\quad P = {mat(P)}", lambda P_=P, d_=(d1, d2), f=ok_vec: f(P_, d_)),
            vstep(rf"e^{{Dt}} = {mat(eD)}", eD, (sp.diag(d1, d2) * t).exp()),
            step(rf"e^{{At}} = P\,e^{{Dt}}P^{{-1}}", lambda: True),
            vstep(rf"e^{{At}} = {mat(res)}", res, truth),
        ]
        bad_res = (P.inv() * eD * P).applyfunc(sp.expand)
        bad_eD = sp.diag(sp.exp(-d1 * t), sp.exp(-d2 * t))
        Pb = sp.Matrix([[P[0, 1], P[0, 0]], [P[1, 0], P[1, 1]]])
        decoys = [
            vdecoy(3, rf"e^{{At}} = {mat(bad_res)}", bad_res, truth, "algebra", WHY["order"]),
            vdecoy(1, rf"e^{{Dt}} = {mat(bad_eD)}", bad_eD, (sp.diag(d1, d2) * t).exp(), "sign", WHY["edt"]),
            decoy(0, rf"\lambda = {tex(d1)},\ {tex(d2)},\quad P = {mat(Pb)}", lambda P_=Pb, d_=(d1, d2), f=ok_vec: f(P_, d_), "algebra", WHY["vec"]),
        ]
        out.append({"params": {"A": list(A)}, "tier": 2, "problem": rf"A = {mat(A)}\ \text{{일 때}}\ e^{{At}}",
                    "steps": steps, "decoys": decoys,
                    "verify": lambda X=res, A=A: None if same(sp.diff(X, t), A * X) and same(X.subs(t, 0), sp.eye(2)) else "X′ ≠ AX 또는 X(0) ≠ I"})
        if len(out) >= 40:
            break
    return out


def principal_axes(As=(1, 2, 3, 5, -1, -3), Bs=(-4, -2, 2, 4, 6), Cs=(1, 2, 3, 5, -2)):
    out = []
    for a, b, c in itertools.product(As, Bs, Cs):
        M = sp.Matrix([[a, sp.Rational(b, 2)], [sp.Rational(b, 2), c]])
        ev = sorted(M.eigenvals().keys(), key=lambda e: float(e))
        if len(ev) != 2 or any(not e.is_rational for e in ev):
            continue
        l1, l2 = ev
        truth_cls = _classify(M)
        q = a * x**2 + b * x * y + c * y**2
        v = sp.Matrix([x, y])
        ok_M = lambda X, q=q, v=v: X == X.T and same(sp.expand((v.T * X * v)[0]), q)
        eigs = set(M.eigenvals().keys())
        X_, Y_ = sp.symbols("X Y")
        steps = [
            step(rf"A = {mat(M)}", lambda X=M, f=ok_M: f(X)),
            step(rf"\lambda_1 = {tex(l1)},\ \lambda_2 = {tex(l2)}", lambda v=(l1, l2), e=eigs: same(set(v), e)),
            step(rf"q = {join_terms([(l1, 'X^{2}'), (l2, 'Y^{2}')])}\ \ (\text{{주축 좌표}})", lambda v=(l1, l2), e=eigs: same(set(v), e)),
            step(rf"\Rightarrow\ {LABELS[truth_cls]}", lambda l=truth_cls, M=M: l == _classify(M)),
        ]
        Mb = sp.Matrix([[a, b], [b, c]])
        evb = sorted(Mb.eigenvals().keys(), key=lambda e: float(sp.N(e)))
        wrong_cls = [l for l in ("pd", "indef", "nd") if l != truth_cls][0]
        decoys = [
            decoy(0, rf"A = {mat(Mb)}", lambda X=Mb, f=ok_M: f(X), "missing_factor", WHY["half"]),
            decoy(1, rf"\lambda_1 = {tex(-l2)},\ \lambda_2 = {tex(-l1)}", lambda v=(-l2, -l1), e=eigs: same(set(v), e), "sign", WHY["eig"]),
            decoy(3, rf"\Rightarrow\ {LABELS[wrong_cls]}", lambda l=wrong_cls, M=M: l == _classify(M), "theorem_condition", WHY["type"]),
        ]
        out.append({"params": {"abc": [a, b, c]}, "tier": 2, "problem": rf"q(x, y) = {_qtex(a, b, c)}\ \text{{의 주축 변환}}",
                    "steps": steps, "decoys": decoys})
    return out


# ---------------------------------------------------------------- M3.6 2단계: 가족 추가 · 새 뼈대
WHY.update({
    "rot": r"$A = aI + bJ$ ($J$는 90° 회전)이면 $e^{At} = e^{at}(\cos bt\,I + \sin bt\,J)$입니다. $\sin$ 자리의 부호가 바뀌었습니다.",
    "jor": r"$A = \lambda I + N$, $N^2 = 0$이면 $e^{At} = e^{\lambda t}(I + Nt)$입니다. $Nt$ 항을 빠뜨리면 미분방정식을 만족하지 않습니다.",
    "nil": r"$N = A - \lambda I$이고 $N^{2} = 0$이라 급수가 두 항에서 끊깁니다.",
    "zero": r"고유값 0의 $e^{0 \cdot t} = 1$입니다. 0이 아닙니다.",
    "sys_ev": r"고유값은 $\det(A - \lambda I) = 0$의 근입니다. 부호가 틀렸습니다.",
    "sys_exp": r"각 해는 $e^{\lambda_i t}\mathbf{v}_i$입니다. 고유값과 고유벡터의 짝이 맞지 않으면 $\mathbf{x}' = A\mathbf{x}$를 만족하지 않습니다.",
    "sys_c": r"$\mathbf{x}(0) = c_1\mathbf{v}_1 + c_2\mathbf{v}_2$를 풀어야 합니다. 상수를 다시 구해 보세요.",
    "sys_swap": r"$c_1$과 $c_2$를 바꿔 넣었습니다. 초기조건이 맞지 않습니다.",
    "sys_cplx": r"$\mathbf{v} = \mathbf{p} + i\mathbf{q}$이면 실수해는 $e^{at}(\mathbf{p}\cos bt - \mathbf{q}\sin bt)$와 $e^{at}(\mathbf{p}\sin bt + \mathbf{q}\cos bt)$입니다. 부호가 틀렸습니다.",
    "sys_gen": r"고유벡터가 하나뿐이면 둘째 해는 $e^{\lambda t}(t\mathbf{v} + \mathbf{w})$, $(A - \lambda I)\mathbf{w} = \mathbf{v}$입니다. $\mathbf{w}$를 빠뜨렸습니다.",
    "cls": r"고유값의 부호로 판정합니다: 모두 양수면 양의 정부호, 하나가 0이면 준정부호, 부호가 섞이면 부정부호입니다.",
})

_J = sp.Matrix([[0, -1], [1, 0]])


def _shift(l):
    """A − λI를 부호에 맞게: λ = −2이면 A + 2I."""
    return rf"A + {tex(-l)}I" if l < 0 else rf"A - {tex(l)}I"


def _with_family(items, fam, k):
    for c in items:
        c["params"]["family"] = fam
    return items[:k]


def exp_families():
    """e^{At}. 가족: 서로 다른 실수 고유값(기존) · 고유값 0 포함 · 회전형 aI + bJ · 조르당형 λI + N."""
    out = _with_family(exp_At(), "distinct", 26)
    rng = random.Random(21)
    seen = set()
    # 고유값 0
    zero = []
    for P in UNIMOD:
        for k in (-3, -2, -1, 1, 2, 3):
            A = P * sp.diag(0, k) * P.inv()
            if tuple(A) in seen or A.is_diagonal() or max(abs(e) for e in A) > 8:
                continue
            seen.add(tuple(A))
            truth = (A * t).exp()
            eD = sp.diag(1, sp.exp(k * t))
            res = (P * eD * P.inv()).applyfunc(sp.expand)
            ok_vec = lambda P_, d_, A=A: P_.det() != 0 and all(same(A * P_[:, j], d_[j] * P_[:, j]) for j in range(2))
            bad0 = sp.diag(0, sp.exp(k * t))
            steps = [
                step(rf"\lambda = 0,\ {tex(k)},\quad P = {mat(P)}", lambda P_=P, d_=(0, k), f=ok_vec: f(P_, d_)),
                vstep(rf"e^{{Dt}} = {mat(eD)}", eD, (sp.diag(0, k) * t).exp()),
                step(rf"e^{{At}} = P\,e^{{Dt}}P^{{-1}}", lambda: True),
                vstep(rf"e^{{At}} = {mat(res)}", res, truth),
            ]
            decoys = [
                vdecoy(1, rf"e^{{Dt}} = {mat(bad0)}", bad0, (sp.diag(0, k) * t).exp(), "algebra", WHY["zero"]),
                vdecoy(3, rf"e^{{At}} = {mat((P.inv() * eD * P).applyfunc(sp.expand))}", (P.inv() * eD * P).applyfunc(sp.expand), truth, "algebra", WHY["order"]),
                vdecoy(3, rf"e^{{At}} = {mat((P * bad0 * P.inv()).applyfunc(sp.expand))}", (P * bad0 * P.inv()).applyfunc(sp.expand), truth, "algebra", WHY["zero"]),
            ]
            zero.append({"params": {"A": list(A), "family": "zero"}, "tier": 1, "problem": rf"A = {mat(A)}\ \text{{일 때}}\ e^{{At}}", "steps": steps, "decoys": decoys,
                         "verify": lambda X=res, A=A: None if same(sp.diff(X, t), A * X) and same(X.subs(t, 0), sp.eye(2)) else "X′ ≠ AX"})
    rng.shuffle(zero)
    out += zero[:14]
    # 회전형
    rot = []
    for a, b in itertools.product([0, -1, 1, -2, 2], [1, 2, 3, -1]):
        A = a * sp.eye(2) + b * _J
        res = (sp.exp(a * t) * (sp.cos(b * t) * sp.eye(2) + sp.sin(b * t) * _J)).applyfunc(sp.expand)
        truth = (A * t).exp().applyfunc(lambda e: sp.simplify(e.rewrite(sp.cos)))
        badr = (sp.exp(a * t) * (sp.cos(b * t) * sp.eye(2) - sp.sin(b * t) * _J)).applyfunc(sp.expand)
        badc = (sp.exp(a * t) * (sp.cosh(b * t) * sp.eye(2) + sp.sinh(b * t) * _J)).applyfunc(sp.expand)
        lam_tex = (f"{tex(a)} \\pm {tex(abs(b))}i" if a else f"\\pm {tex(abs(b))}i").replace("1i", "i") if abs(b) == 1 else (f"{tex(a)} \\pm {abs(b)}i" if a else f"\\pm {abs(b)}i")
        steps = [
            step(rf"\lambda = {lam_tex}", lambda A=A, a=a, b=b: same(set(A.eigenvals().keys()), {a + b * sp.I, a - b * sp.I})),
            step(rf"A = {tex(a)}I {'+' if b > 0 else '-'} {tex(abs(b)) if abs(b) != 1 else ''}J,\ J = {mat(_J)}", lambda A=A, a=a, b=b: same(a * sp.eye(2) + b * _J, A)),
            step(rf"e^{{At}} = e^{{{tex(a * t)}}}\left(\cos {tex(abs(b) * t)}\,I {'+' if b > 0 else '-'} \sin {tex(abs(b) * t)}\,J\right)", lambda: True),
            vstep(rf"e^{{At}} = {mat(res)}", res, truth),
        ]
        decoys = [
            vdecoy(3, rf"e^{{At}} = {mat(badr)}", badr, truth, "sign", WHY["rot"]),
            vdecoy(3, rf"e^{{At}} = {mat(badc)}", badc, truth, "wrong_pair", r"고유값이 복소수이면 삼각함수가 나옵니다. $\cosh$, $\sinh$는 실수 고유값 $\pm b$일 때입니다."),
            step(rf"\lambda = {tex(a)},\ {tex(b)}", lambda A=A, a=a, b=b: same(set(A.eigenvals().keys()), {a, b})) | {"pos": 0, "error": "algebra", "why": r"$A = aI + bJ$의 고유값은 $a \pm bi$입니다."},
        ]
        rot.append({"params": {"A": list(A), "family": "rot"}, "tier": 3, "problem": rf"A = {mat(A)}\ \text{{일 때}}\ e^{{At}}", "steps": steps, "decoys": decoys,
                    "verify": lambda X=res, A=A: None if same(sp.diff(X, t), A * X) and same(X.subs(t, 0), sp.eye(2)) else "X′ ≠ AX"})
    rng.shuffle(rot)
    out += rot[:14]
    # 조르당형
    jor = []
    Ns = [sp.Matrix([[0, 1], [0, 0]]), sp.Matrix([[0, 0], [1, 0]]), sp.Matrix([[1, -1], [1, -1]]), sp.Matrix([[2, -4], [1, -2]]), sp.Matrix([[-1, 1], [-1, 1]]), sp.Matrix([[3, 9], [-1, -3]]), sp.Matrix([[0, 2], [0, 0]])]
    for lmb, N in itertools.product([-2, -1, 1, 2, 3], Ns):
        A = lmb * sp.eye(2) + N
        res = (sp.exp(lmb * t) * (sp.eye(2) + N * t)).applyfunc(sp.expand)
        truth = (A * t).exp()
        badn = (sp.exp(lmb * t) * sp.eye(2)).applyfunc(sp.expand)
        badh = (sp.exp(lmb * t) * (sp.eye(2) + N * t ** 2 / 2)).applyfunc(sp.expand)
        steps = [
            step(rf"\lambda = {tex(lmb)}\ (\text{{중근}})", lambda A=A, l=lmb: A.eigenvals() == {l: 2}),
            step(rf"N = {_shift(lmb)} = {mat(N)},\ N^{{2}} = 0", lambda A=A, l=lmb, N=N: same(A - l * sp.eye(2), N) and N * N == sp.zeros(2)),
            step(rf"e^{{At}} = e^{{{tex(lmb * t)}}}(I + Nt)", lambda: True),
            vstep(rf"e^{{At}} = {mat(res)}", res, truth),
        ]
        decoys = [
            vdecoy(3, rf"e^{{At}} = {mat(badn)}", badn, truth, "missing_factor", WHY["jor"]),
            vdecoy(3, rf"e^{{At}} = {mat(badh)}", badh, truth, "algebra", WHY["nil"]),
            step(rf"N = {_shift(lmb)} = {mat(N.T)},\ N^{{2}} = 0", lambda A=A, l=lmb, N=N.T: same(A - l * sp.eye(2), N)) | {"pos": 1, "error": "algebra", "why": WHY["nil"]} if N != N.T else None,
        ]
        jor.append({"params": {"A": list(A), "family": "jordan"}, "tier": 3, "problem": rf"A = {mat(A)}\ \text{{일 때}}\ e^{{At}}", "steps": steps, "decoys": [d for d in decoys if d],
                    "verify": lambda X=res, A=A: None if same(sp.diff(X, t), A * X) and same(X.subs(t, 0), sp.eye(2)) else "X′ ≠ AX"})
    rng.shuffle(jor)
    out += jor[:14]
    return out


def paxes_families():
    """주축 변환을 판정 결과로 가족 표시하고, 준정부호(고유값 0) 사례를 더한다."""
    items = principal_axes() + principal_axes((-1, -2, -3, -5, -6), (-8, -6, -4, 4, 6, 8), (-1, -2, -3, -5, -6)) \
        + principal_axes((1, 2, 4, 6, -2, -4, -6), (-8, -6, 6, 8), (-1, -2, -4, 3, 6))
    _u = set()
    items = [c for c in items if not (tuple(c["params"]["abc"]) in _u or _u.add(tuple(c["params"]["abc"])))]
    for a, b, c in itertools.product([1, 2, 4, 9, -1, -4], [-12, -6, -4, -2, 2, 4, 6, 12], [1, 2, 4, 9, -1, -4]):
        if b * b == 4 * a * c and a * c > 0:
            M = sp.Matrix([[a, sp.Rational(b, 2)], [sp.Rational(b, 2), c]])
            ev = sorted(M.eigenvals().keys(), key=lambda e: float(e))
            if len(ev) != 2 or any(not e.is_rational for e in ev):
                continue
            l1, l2 = ev
            cls = _classify(M)
            q = a * x**2 + b * x * y + c * y**2
            v = sp.Matrix([x, y])
            ok_M = lambda X, q=q, v=v: X == X.T and same(sp.expand((v.T * X * v)[0]), q)
            eigs = set(M.eigenvals().keys())
            steps = [
                step(rf"A = {mat(M)}", lambda X=M, f=ok_M: f(X)),
                step(rf"\lambda_1 = {tex(l1)},\ \lambda_2 = {tex(l2)}", lambda v=(l1, l2), e=eigs: same(set(v), e)),
                step(rf"q = {join_terms([(l1, 'X^{2}'), (l2, 'Y^{2}')])}\ \ (\text{{주축 좌표}})", lambda v=(l1, l2), e=eigs: same(set(v), e)),
                step(rf"\Rightarrow\ {LABELS[cls]}", lambda l=cls, M=M: l == _classify(M)),
            ]
            wrong = "pd" if cls == "psd" else "nd"   # nsd이면 nd가 그럴듯한 오답
            decoys = [
                decoy(0, rf"A = {mat(sp.Matrix([[a, b], [b, c]]))}", lambda X=sp.Matrix([[a, b], [b, c]]), f=ok_M: f(X), "missing_factor", WHY["half"]),
                decoy(3, rf"\Rightarrow\ {LABELS[wrong]}", lambda l=wrong, M=M: l == _classify(M), "theorem_condition", WHY["cls"]),
                decoy(3, rf"\Rightarrow\ {LABELS['indef']}", lambda M=M: "indef" == _classify(M), "theorem_condition", WHY["cls"]),
            ]
            items.append({"params": {"abc": [a, b, c]}, "tier": 3, "problem": rf"q(x, y) = {_qtex(a, b, c)}\ \text{{의 주축 변환}}", "steps": steps, "decoys": decoys})
    by = {}
    for c in items:
        cls = c["steps"][-1]["tex"]
        fam = next(k for k, v in LABELS.items() if v in cls)
        fam = {"nsd": "psd"}.get(fam, fam)   # 준정부호는 부호와 무관하게 한 가족
        c["params"]["family"] = fam
        c["tier"] = {"pd": 1, "nd": 2, "indef": 2, "psd": 3}[fam]
        by.setdefault(fam, []).append(c)
    rng = random.Random(5)
    out = []
    for fam, lst in by.items():
        rng.shuffle(lst)
        out += lst[:18]
    return out


def _vec_tex(v):
    return mat(sp.Matrix(v))


def _ok_basis(fs, A):
    return all(same(sp.diff(f, t), A * f) for f in fs) and sp.Matrix.hstack(*[f.subs(t, 0) for f in fs]).det() != 0


def _ok_final(X, A, x0):
    return same(sp.diff(X, t), A * X) and same(X.subs(t, 0), x0)


def ode_system():
    """x' = Ax, x(0) = x₀. 가족: 서로 다른 실수 고유값 · 고유값 0 · 복소 고유값(실수형) · 중근(고유벡터 하나)."""
    out = []
    rng = random.Random(61)
    c1, c2 = sp.symbols("c_1 c_2")
    seen = set()

    def make(A, x0, fam, tier, lam_tex, vec_tex, basis, bad_basis_list, extra_decoys=()):
        if (tuple(A), tuple(x0)) in seen:
            return None
        seen.add((tuple(A), tuple(x0)))
        M0 = sp.Matrix.hstack(*[f.subs(t, 0) for f in basis])
        cs = M0.solve(x0)
        if any(abs(ci.q) > 6 for ci in cs) or any(ci == 0 for ci in cs):
            return None
        X = (cs[0] * basis[0] + cs[1] * basis[1]).applyfunc(sp.expand)
        gen_tex = rf"\mathbf{{x}} = c_1{_btex(basis[0])} + c_2{_btex(basis[1])}"
        steps = [
            step(lam_tex[0], lam_tex[1]),
            step(vec_tex[0], vec_tex[1]),
            step(gen_tex, lambda fs=basis, A=A: _ok_basis(fs, A)),
            step(rf"c_1 = {tex(cs[0])},\ c_2 = {tex(cs[1])}", lambda cs=cs, M0=M0, x0=x0: same(M0 * sp.Matrix(cs), x0)),
            step(rf"\mathbf{{x}}(t) = {mat(X)}", lambda X=X, A=A, x0=x0: _ok_final(X, A, x0)),
        ]
        Xs = (cs[1] * basis[0] + cs[0] * basis[1]).applyfunc(sp.expand)
        decoys = [decoy(2, rf"\mathbf{{x}} = c_1{_btex(bb[0])} + c_2{_btex(bb[1])}", lambda fs=bb, A=A: _ok_basis(fs, A), err, why) for bb, err, why in bad_basis_list]
        if cs[0] != cs[1]:
            decoys.append(decoy(4, rf"\mathbf{{x}}(t) = {mat(Xs)}", lambda X=Xs, A=A, x0=x0: _ok_final(X, A, x0), "algebra", WHY["sys_swap"]))
        bc = (cs[0] + 1, cs[1])
        decoys.append(decoy(3, rf"c_1 = {tex(bc[0])},\ c_2 = {tex(bc[1])}", lambda cs=bc, M0=M0, x0=x0: same(M0 * sp.Matrix(cs), x0), "algebra", WHY["sys_c"]))
        decoys += list(extra_decoys)
        return {"params": {"A": list(A), "x0": list(x0), "family": fam}, "tier": tier,
                "problem": rf"\mathbf{{x}}' = {mat(A)}\mathbf{{x}},\ \mathbf{{x}}(0) = {mat(x0)}",
                "steps": steps, "decoys": decoys, "verify": lambda X=X, A=A, x0=x0: None if _ok_final(X, A, x0) else "해가 아님"}

    def real_case(P, d, fam, tier):
        A = P * sp.diag(*d) * P.inv()
        if A.is_diagonal() or max(abs(e) for e in A) > 8:
            return None
        v1, v2 = P[:, 0], P[:, 1]
        x0 = sp.Matrix([rng.randint(-3, 4), rng.randint(-3, 4)])
        basis = [sp.exp(d[0] * t) * v1, sp.exp(d[1] * t) * v2]
        ev = set(A.eigenvals().keys())
        lt = (rf"\lambda_1 = {tex(d[0])},\ \lambda_2 = {tex(d[1])}", lambda d=d, ev=ev: same(set(d), ev))
        vt = (rf"\mathbf{{v}}_1 = {mat(v1)},\ \mathbf{{v}}_2 = {mat(v2)}", lambda A=A, v1=v1, v2=v2, d=d: same(A * v1, d[0] * v1) and same(A * v2, d[1] * v2))
        bad = [([sp.exp(d[1] * t) * v1, sp.exp(d[0] * t) * v2], "wrong_pair", WHY["sys_exp"]),
               ([sp.exp(-d[0] * t) * v1, sp.exp(-d[1] * t) * v2], "sign", WHY["sys_ev"])]
        ex = [decoy(0, rf"\lambda_1 = {tex(-d[0])},\ \lambda_2 = {tex(-d[1])}", lambda d=(-d[0], -d[1]), ev=ev: same(set(d), ev), "sign", WHY["sys_ev"])]
        return make(A, x0, fam, tier, lt, vt, basis, bad, ex)

    real, zero, cplx, rep = [], [], [], []
    for _ in range(3000):
        P = rng.choice(UNIMOD)
        if len(real) < 18:
            c = real_case(P, tuple(rng.sample([-3, -2, -1, 1, 2, 3], 2)), "real", 2)
            if c: real.append(c)
        if len(zero) < 14:
            c = real_case(P, (0, rng.choice([-3, -2, -1, 1, 2])), "zero", 2)
            if c: zero.append(c)
        if len(cplx) < 16:
            a, b = rng.choice([0, -1, 1, -2]), rng.choice([1, 2, 3])
            A = P * (a * sp.eye(2) + b * _J) * P.inv()
            if max(abs(e) for e in A) <= 8 and all(e.q == 1 for e in A):
                ns = (A - (a + b * sp.I) * sp.eye(2)).nullspace()[0]
                ns = (ns / ns[next(i for i in range(2) if ns[i] != 0)]).applyfunc(sp.simplify)
                ns = (ns * sp.lcm([sp.fraction(sp.re(e))[1] for e in ns] + [sp.fraction(sp.im(e))[1] for e in ns])).applyfunc(sp.expand)
                p_, q_ = ns.applyfunc(sp.re), ns.applyfunc(sp.im)
                ea = sp.exp(a * t)
                b1 = ea * (p_ * sp.cos(b * t) - q_ * sp.sin(b * t))
                b2 = ea * (p_ * sp.sin(b * t) + q_ * sp.cos(b * t))
                x0 = sp.Matrix([rng.randint(-3, 4), rng.randint(-3, 4)])
                lt = (rf"\lambda = {tex(a + b * sp.I)},\ {tex(a - b * sp.I)}", lambda A=A, a=a, b=b: same(set(A.eigenvals().keys()), {a + b * sp.I, a - b * sp.I}))
                vt = (rf"\mathbf{{v}} = {mat(ns)} = {mat(p_)} + i{mat(q_)}", lambda A=A, v=ns, l=a + b * sp.I: same((A * v).applyfunc(sp.expand), (l * v).applyfunc(sp.expand)))
                bad = [([ea * (p_ * sp.cos(b * t) + q_ * sp.sin(b * t)), ea * (p_ * sp.sin(b * t) - q_ * sp.cos(b * t))], "sign", WHY["sys_cplx"]),
                       ([sp.exp(-a * t) * (p_ * sp.cos(b * t) - q_ * sp.sin(b * t)), sp.exp(-a * t) * (p_ * sp.sin(b * t) + q_ * sp.cos(b * t))], "sign", WHY["sys_ev"])] if a else \
                      [([ea * (p_ * sp.cos(b * t) + q_ * sp.sin(b * t)), ea * (p_ * sp.sin(b * t) - q_ * sp.cos(b * t))], "sign", WHY["sys_cplx"])]
                c = make(A, x0, "complex", 3, lt, vt, [b1, b2], bad)
                if c: cplx.append(c)
        if len(rep) < 16:
            lmb = rng.choice([-2, -1, 1, 2])
            J = sp.Matrix([[lmb, 1], [0, lmb]])
            A = P * J * P.inv()
            if max(abs(e) for e in A) <= 8:
                v, w = P[:, 0], P[:, 1]
                el = sp.exp(lmb * t)
                x0 = sp.Matrix([rng.randint(-3, 4), rng.randint(-3, 4)])
                lt = (rf"\lambda = {tex(lmb)}\ (\text{{중근}})", lambda A=A, l=lmb: A.eigenvals() == {l: 2})
                vt = (rf"\mathbf{{v}} = {mat(v)},\ ({_shift(lmb)})\mathbf{{w}} = \mathbf{{v}}:\ \mathbf{{w}} = {mat(w)}", lambda A=A, v=v, w=w, l=lmb: same(A * v, l * v) and same((A - l * sp.eye(2)) * w, v))
                bad = [([el * v, el * t * v], "missing_factor", WHY["sys_gen"]),
                       ([el * v, el * (t * w + v)], "wrong_pair", WHY["sys_gen"])]
                c = make(A, x0, "repeated", 3, lt, vt, [el * v, el * (t * v + w)], bad)
                if c: rep.append(c)
        if len(real) >= 18 and len(zero) >= 14 and len(cplx) >= 16 and len(rep) >= 16:
            break
    return real + zero + cplx + rep


def _btex(f):
    """e^{λt}(벡터) 또는 e^{at}(…) 꼴을 그대로 보이게: 지수 인수를 앞으로 뺀다."""
    f = sp.Matrix(f)
    exps = {a for e in f for a in sp.Add.make_args(sp.expand(e)) for a in [a] if a.has(sp.exp)}
    ex = [a for e in f for a in sp.Mul.make_args(sp.factor(e)) if isinstance(a, sp.exp)]
    if ex:
        E = ex[0]
        inner = (f / E).applyfunc(sp.expand)
        if not inner.has(sp.exp):
            return rf"e^{{{tex(E.args[0])}}}{mat(inner)}"
    return mat(f.applyfunc(sp.expand))
