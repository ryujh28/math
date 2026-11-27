"""7장 2계 선형 ODE — 생성기. 참 해는 SymPy dsolve로 따로 구한다."""
import itertools
import sympy as sp
from texkit import tex, join_terms, sum_tex, poly_tex
from checks import (same, opt, step, vstep, decoy, vdecoy, is_family_solution, independent, fit_constants,
                    x, r, C1, C2)

f = sp.Function("f")
P2, P1 = r"y^{\prime\prime}", r"y^{\prime}"
A_, B_ = sp.symbols("A B")


def _L(p, q):
    return lambda g, p=p, q=q: sp.diff(g, x, 2) + p * sp.diff(g, x) + q * g


def _ode_tex(p, q, R=0):
    return f"{join_terms([(1, P2), (p, P1), (q, 'y')])} = {tex(R)}"


def _dsolve2(p, q, R, y0, v0):
    sol = sp.dsolve(sp.Eq(f(x).diff(x, 2) + p * f(x).diff(x) + q * f(x), R), f(x), ics={f(0): y0, f(x).diff(x).subs(x, 0): v0})
    return sp.simplify(sol.rhs)


def _basis_ok(p, q):
    """기저 (b1, b2)가 동차방정식의 일차독립 해인지."""
    L = _L(p, q)
    return lambda b, L=L: is_family_solution(C1 * b[0] + C2 * b[1], L, [C1, C2]) and independent(list(b))


def _cases():
    """(p, q, 종류, 기저, 근 표시)"""
    out = []
    for r1, r2 in itertools.combinations([-4, -3, -2, -1, 1, 2, 3], 2):
        out.append((-(r1 + r2), r1 * r2, "real", (sp.exp(r1 * x), sp.exp(r2 * x)), (r1, r2)))
    for rr in [-3, -2, -1, 1, 2]:
        out.append((-2 * rr, rr * rr, "rep", (sp.exp(rr * x), x * sp.exp(rr * x)), (rr,)))
    for al, be in itertools.product([-2, -1, 0, 1], [1, 2, 3]):
        out.append((-2 * al, al * al + be * be, "cplx", (sp.exp(al * x) * sp.cos(be * x), sp.exp(al * x) * sp.sin(be * x)), (al, be)))
    return out


def _gen_tex(kind, roots):
    if kind == "real":
        a, b = roots
        return f"C_1{tex(sp.exp(a * x))} + C_2{tex(sp.exp(b * x))}"
    if kind == "rep":
        (a,) = roots
        return rf"\left(C_1 + C_2x\right){tex(sp.exp(a * x))}"
    al, be = roots
    inner = rf"C_1\cos {tex(be * x)} + C_2\sin {tex(be * x)}"
    return inner if al == 0 else rf"{tex(sp.exp(al * x))}\left({inner}\right)"


def _wrong_bases(kind, roots):
    if kind == "real":
        a, b = roots
        return [((sp.exp(-a * x), sp.exp(-b * x)), "sign", ("real", (-a, -b))),
                ((sp.exp(a * x), x * sp.exp(a * x)), "wrong_pair", ("rep", (a,))),
                ] + ([((sp.cos(abs(a) * x), sp.sin(abs(b) * x)), "wrong_pair", None)] if a and b else [])
    if kind == "rep":
        (a,) = roots
        return [((sp.exp(a * x), sp.exp(-a * x)), "wrong_pair", ("real", (a, -a))),
                ((sp.exp(-a * x), x * sp.exp(-a * x)), "sign", ("rep", (-a,))),
                ((sp.exp(a * x), x**2 * sp.exp(a * x)), "algebra", None)]
    al, be = roots
    out = ([((sp.exp(be * x) * sp.cos(abs(al) * x), sp.exp(be * x) * sp.sin(abs(al) * x)), "algebra", ("cplx", (be, abs(al))))] if al else []) + \
          [((sp.exp(al * x), sp.exp(be * x)), "wrong_pair", ("real", (al, be)))]
    if al != 0:
        out.append(((sp.exp(-al * x) * sp.cos(be * x), sp.exp(-al * x) * sp.sin(be * x)), "sign", ("cplx", (-al, be))))
    else:
        out.append(((sp.exp(be * x), sp.exp(-be * x)), "sign", ("real", (be, -be))))
    return out


def _btex(b, spec):
    if spec is None:
        return f"C_1{tex(b[0])} + C_2{tex(b[1])}"
    kind, roots = spec
    if kind == "real" and roots[0] == roots[1]:
        return f"C_1{tex(b[0])} + C_2{tex(b[1])}"
    return _gen_tex(kind, roots)


# ---------------------------------------------------------------- 사실 원자
def general_form():
    out = []
    for p, q, kind, basis, roots in _cases():
        ok = _basis_ok(p, q)
        wr = _wrong_bases(kind, roots)
        out.append({"params": {"p": p, "q": q}, "tier": 1 if kind == "real" else 2,
                    "prompt": rf"{_ode_tex(p, q)}\ \text{{의 일반해}}",
                    "answer": opt("y = " + _gen_tex(kind, roots), lambda b=basis, ok=ok: ok(b)),
                    "wrong": [opt("y = " + _btex(b, spec), lambda b=b, ok=ok: ok(b), e) for b, e, spec in wr]})
    return out


def _trial_ok(p, q, R, unknowns):
    L = _L(p, q)
    return lambda form, L=L, R=R, u=unknowns: fit_constants(sp.expand(L(form)), R, [s_ for s_ in u if form.has(s_)])


def trial_form():
    out = []
    for p, q, kind, basis, roots in _cases():
        if kind != "real":
            continue
        r1, r2 = roots
        for a in [-2, -1, 1, 2, 3]:
            R = 3 * sp.exp(a * x)
            res = a in roots
            right = A_ * x * sp.exp(a * x) if res else A_ * sp.exp(a * x)
            cands = [(A_ * sp.exp(a * x) if res else A_ * x * sp.exp(a * x), "theorem_condition"),
                     (A_ * sp.exp(-a * x), "sign"), (A_ * x**2 * sp.exp(a * x), "algebra"), (A_ + B_ * x, "wrong_pair")]
            ok = _trial_ok(p, q, R, [A_, B_])
            out.append({"params": {"p": p, "q": q, "R": f"exp{a}"}, "tier": 3 if res else 2,
                        "prompt": rf"{_ode_tex(p, q, R)}\ \text{{의 특수해 꼴}}\ y_p = \;?",
                        "answer": opt(tex(right), lambda g=right, ok=ok: ok(g)),
                        "wrong": [opt(tex(g), lambda g=g, ok=ok: ok(g), e) for g, e in cands]})
        for b in [1, 2, 3]:
            if p == 0:
                continue
            R = 2 * sp.cos(b * x)
            right = A_ * sp.cos(b * x) + B_ * sp.sin(b * x)
            cands = [(A_ * sp.cos(b * x), "missing_factor"), (A_ * sp.sin(b * x), "wrong_pair"),
                     (A_ * sp.exp(b * x), "wrong_pair"), (A_ * x * sp.cos(b * x), "algebra")]
            ok = _trial_ok(p, q, R, [A_, B_])
            out.append({"params": {"p": p, "q": q, "R": f"cos{b}"}, "tier": 2,
                        "prompt": rf"{_ode_tex(p, q, R)}\ \text{{의 특수해 꼴}}\ y_p = \;?",
                        "answer": opt(tex(right), lambda g=right, ok=ok: ok(g)),
                        "wrong": [opt(tex(g), lambda g=g, ok=ok: ok(g), e) for g, e in cands]})
    return out


def wronskian():
    out = []
    for a, b in itertools.permutations([-2, -1, 1, 2, 3], 2):
        f1, f2 = sp.exp(a * x), sp.exp(b * x)
        truth = sp.simplify(sp.wronskian([f1, f2], x))
        e = sp.exp((a + b) * x)
        cands = [((a - b) * e, "sign"), ((a + b) * e, "algebra"), (e, "missing_factor"), (a * b * e, "algebra")]
        out.append({"params": {"a": a, "b": b}, "tier": 2, "prompt": rf"W\!\left({tex(f1)},\ {tex(f2)}\right) = \;?",
                    "answer": opt(tex((b - a) * e), lambda v=(b - a) * e, tr=truth: same(v, tr)),
                    "wrong": [opt(tex(v), lambda v=v, tr=truth: same(v, tr), er) for v, er in cands]})
    return out


# ---------------------------------------------------------------- 풀이 뼈대
WHY = {
    "char_sign": r"$y^{\prime}$의 계수 $p$는 특성방정식에서 $r$의 계수로 그대로 갑니다: $r^2 + pr + q = 0$.",
    "roots": r"특성방정식의 근을 잘못 구했습니다.",
    "family": r"근의 종류에 맞는 해의 꼴이 아닙니다.",
    "rep": r"중근이면 두 번째 해에 $x$가 곱해집니다: $(C_1 + C_2x)e^{rx}$.",
    "consts": r"초기조건을 일반해와 그 도함수에 대입해야 합니다. $y^{\prime}(0)$을 그대로 $C_2$로 쓰면 안 됩니다.",
    "final": r"상수를 넣어 정리할 때 부호가 틀렸습니다.",
    "trial": r"강제항이 동차해와 겹치면(공명) $x$를 곱해야 하고, $\cos$ 강제항에는 $\sin$ 항도 필요합니다.",
    "coef": r"계수를 잘못 구했습니다. $y_p$를 방정식에 대입해 보세요.",
    "yp_sign": r"특수해의 부호가 틀렸습니다.",
    "indicial": r"$x^r$을 대입하면 $x^2y^{\prime\prime} \to r(r-1)x^r$입니다. $r^2$으로 쓰면 $-r$ 항이 빠집니다.",
    "euler_fam": r"Euler–Cauchy 방정식의 해는 $e^{rx}$가 아니라 $x^r$ 꼴입니다.",
}


def _roots_tex(kind, roots):
    if kind == "real":
        return f"r = {tex(roots[0])},\\ {tex(roots[1])}"
    if kind == "rep":
        return f"r = {tex(roots[0])}\\ (\\text{{중근}})"
    al, be = roots
    return f"r = {tex(al) if al else ''}{' ' if al else ''}\\pm {tex(be) if be != 1 else ''}i".replace("  ", " ")


def const_coeff():
    out = []
    for p, q, kind, basis, roots in _cases():
        for y0, v0 in [(1, 0), (0, 1), (2, -1), (1, 2), (-1, 3)]:
            ytrue = _dsolve2(p, q, 0, y0, v0)
            fam = C1 * basis[0] + C2 * basis[1]
            sol = sp.solve([fam.subs(x, 0) - y0, sp.diff(fam, x).subs(x, 0) - v0], [C1, C2])
            c1v, c2v = sol[C1], sol[C2]
            final = sp.expand(fam.subs({C1: c1v, C2: c2v}))
            okb = _basis_ok(p, q)
            cp = r**2 + p * r + q
            rset = set(sp.roots(sp.Poly(cp, r)).keys())
            steps = [
                vstep(rf"{poly_tex(cp, r)} = 0", cp, r**2 + p * r + q),
                step(_roots_tex(kind, roots), lambda k=kind, rt=roots, rs=rset: same(set(_root_vals(k, rt)), rs)),
                step(f"y = {_gen_tex(kind, roots)}", lambda b=basis, ok=okb: ok(b)),
                step(rf"C_1 = {tex(c1v)},\ C_2 = {tex(c2v)}", lambda fm=fam, a=c1v, b=c2v, yt=ytrue: same(fm.subs({C1: a, C2: b}), yt)),
                vstep(f"y = {sum_tex(final)}", final, ytrue),
            ]
            bad_cp = r**2 - p * r + q
            decoys = []
            if p != 0:
                decoys.append(vdecoy(0, rf"{poly_tex(bad_cp, r)} = 0", bad_cp, r**2 + p * r + q, "sign", WHY["char_sign"]))
            for b, er, spec in _wrong_bases(kind, roots)[:2]:
                decoys.append(decoy(2, f"y = {_btex(b, spec)}", lambda b=b, ok=okb: ok(b), er, WHY["rep"] if kind == "rep" else WHY["family"]))
            decoys.append(decoy(3, rf"C_1 = {tex(y0)},\ C_2 = {tex(v0)}", lambda fm=fam, a=y0, b=v0, yt=ytrue: same(fm.subs({C1: a, C2: b}), yt),
                                "initial_condition", WHY["consts"]))
            badf = final.subs(x, -x)
            decoys.append(vdecoy(4, f"y = {sum_tex(sp.expand(badf))}", badf, ytrue, "sign", WHY["final"]))
            tier = {"real": 2, "rep": 3, "cplx": 3}[kind]
            out.append({"params": {"p": p, "q": q, "y0": y0, "v0": v0, "family": kind}, "tier": tier,
                        "problem": rf"{_ode_tex(p, q)},\quad y(0) = {tex(y0)},\ {P1}(0) = {tex(v0)}",
                        "steps": steps, "decoys": decoys,
                        "verify": lambda yt=ytrue, L=_L(p, q), y0=y0, v0=v0: None if same(L(yt), 0) and same(yt.subs(x, 0), y0) and same(sp.diff(yt, x).subs(x, 0), v0) else "dsolve 해 확인 실패"})
    # 일반해만 (초기값 없음): 특성방정식 → 근 → 일반해. 근의 종류를 고르게 섞는다.
    for p, q, kind, basis, roots in _cases():
        okb = _basis_ok(p, q)
        cp = r**2 + p * r + q
        rset = set(sp.roots(sp.Poly(cp, r)).keys())
        steps = [
            vstep(rf"{poly_tex(cp, r)} = 0", cp, r**2 + p * r + q),
            step(_roots_tex(kind, roots), lambda k=kind, rt=roots, rs=rset: same(set(_root_vals(k, rt)), rs)),
            step(f"y = {_gen_tex(kind, roots)}", lambda b=basis, ok=okb: ok(b)),
        ]
        decoys = []
        if p != 0:
            bad_cp = r**2 - p * r + q
            decoys.append(vdecoy(0, rf"{poly_tex(bad_cp, r)} = 0", bad_cp, r**2 + p * r + q, "sign", WHY["char_sign"]))
        for b, er, spec in _wrong_bases(kind, roots)[:2]:
            decoys.append(decoy(2, f"y = {_btex(b, spec)}", lambda b=b, ok=okb: ok(b), er, WHY["rep"] if kind == "rep" else WHY["family"]))
        out.append({"params": {"p": p, "q": q, "family": "gen_" + kind}, "tier": 1,
                    "problem": rf"{_ode_tex(p, q)}\ \text{{의 일반해}}", "steps": steps, "decoys": decoys,
                    "verify": lambda b=basis, ok=okb: None if ok(b) else "기저 확인 실패"})
    return out


def _root_vals(kind, roots):
    if kind == "real":
        return list(roots)
    if kind == "rep":
        return [roots[0]]
    al, be = roots
    return [al + be * sp.I, al - be * sp.I]


C_ = sp.Symbol("C")


def _fit(L, R, form):
    """시행 꼴 form의 미정계수를 맞춘 특수해 (안 맞으면 None)."""
    unk = sorted(form.free_symbols - {x}, key=lambda z: z.name)
    pts = [sp.Rational(k, 7) for k in (1, 2, 3, 5, 6, 9)][: len(unk) + 2]
    co = sp.solve([sp.expand(L(form) - R).subs(x, pt) for pt in pts], unk, dict=True)
    if not co:
        return None, None
    yp = sp.simplify(form.subs(co[0]))
    return (yp, co[0]) if same(L(yp), R) else (None, None)


def _forcings(p, q, kind, roots):
    """(가족, 강제항 R, 맞는 시행 꼴, 틀린 시행 꼴, 단계). 가족마다 구조가 다르다."""
    out = []
    rv = set(_root_vals(kind, roots))
    a_ok = [a for a in (1, 2, -1, -2, 3) if a not in rv]
    if a_ok:
        a = a_ok[(p + q) % len(a_ok)]
        out.append(("exp", 4 * sp.exp(a * x), A_ * sp.exp(a * x), A_ * x * sp.exp(a * x), 1))
    out.append(("poly1", q * x + p + 2 * q, A_ * x + B_, A_ * x, 1))   # y_p = x + 2: 상수항이 꼭 필요
    out.append(("poly2", 2 * q * x**2 if q else 2 * x**2, A_ * x**2 + B_ * x + C_, A_ * x**2, 2))
    if kind == "real" and q != 0 and 0 not in rv and a_ok:
        a = a_ok[0]
        out.append(("sum", 3 * sp.exp(a * x) + q, A_ * sp.exp(a * x) + B_, A_ * sp.exp(a * x), 2))
    for bb in (1, 2, 3):
        if kind == "cplx" and roots == (0, bb):
            continue
        fn = sp.cos if (p + bb) % 2 == 0 else sp.sin
        R = 5 * fn(bb * x)
        bad = A_ * fn(bb * x) if p != 0 else A_ * (sp.sin if fn is sp.cos else sp.cos)(bb * x)
        out.append(("trig", R, A_ * sp.cos(bb * x) + B_ * sp.sin(bb * x), bad, 2))
        break
    if kind == "real":
        r1 = roots[0] if roots[0] != 0 else roots[1]
        out.append(("res", 3 * sp.exp(r1 * x), A_ * x * sp.exp(r1 * x), A_ * sp.exp(r1 * x), 3))
    if kind == "rep":
        rr = roots[0]
        out.append(("res2", 2 * sp.exp(rr * x), A_ * x**2 * sp.exp(rr * x), A_ * x * sp.exp(rr * x), 3))
    if kind == "cplx" and roots[0] == 0:
        be = roots[1]
        out.append(("trigres", 4 * sp.cos(be * x), x * (A_ * sp.cos(be * x) + B_ * sp.sin(be * x)),
                    A_ * sp.cos(be * x) + B_ * sp.sin(be * x), 3))
    if kind == "cplx" and roots[0] != 0:
        be = roots[1]
        b2 = 1 if be != 1 else 2
        a2 = roots[0] - 1      # 지수가 동차해의 실수부와 같으면 cos만으로도 맞아 버리므로 비켜 둔다
        R = 2 * sp.exp(a2 * x) * sp.cos(b2 * x)
        out.append(("expcos", R, sp.exp(a2 * x) * (A_ * sp.cos(b2 * x) + B_ * sp.sin(b2 * x)),
                    A_ * sp.exp(a2 * x) * sp.cos(b2 * x), 3))
    return out


FAMILY_CAP = {"exp": 10, "poly1": 8, "poly2": 10, "sum": 8, "trig": 10, "res": 8, "res2": 5, "trigres": 3, "expcos": 8}
WHY_TRIAL = {
    "exp": r"강제항 $e^{ax}$가 동차해와 겹치지 않으면 $Ae^{ax}$면 충분합니다. $x$를 곱하는 것은 공명일 때뿐입니다.",
    "poly1": r"일차식 강제항에는 상수항까지 갖춘 $Ax + B$를 씁니다. 상수항이 빠지면 $qy$와 $py^{\prime}$에서 나오는 항을 맞출 수 없습니다.",
    "poly2": r"이차식 강제항에는 $Ax^2 + Bx + C$를 씁니다. 미분하면 낮은 차수 항이 생기므로 모든 차수가 필요합니다.",
    "sum": r"강제항이 두 항의 합이면 각 항에 맞는 꼴을 더합니다(중첩). 상수 강제항에는 상수 $B$가 필요합니다.",
    "trig": r"$\cos$나 $\sin$ 강제항에는 $A\cos bx + B\sin bx$를 씁니다. 미분하면 $\cos$와 $\sin$이 서로 바뀌기 때문입니다.",
    "res": r"강제항 $e^{rx}$가 동차해와 겹치면(공명) $Ae^{rx}$는 대입하면 0이 됩니다. $x$를 곱해 $Axe^{rx}$로 씁니다.",
    "res2": r"$e^{rx}$가 중근의 동차해 $e^{rx}$, $xe^{rx}$와 모두 겹치므로 $x^2$을 곱해 $Ax^2e^{rx}$로 씁니다.",
    "trigres": r"$\cos\beta x$가 동차해와 겹치므로(공명) $x(A\cos\beta x + B\sin\beta x)$로 씁니다.",
    "expcos": r"$e^{ax}\cos bx$ 강제항에는 $e^{ax}(A\cos bx + B\sin bx)$를 씁니다. $\sin$ 항이 빠지면 계수를 맞출 수 없습니다.",
}


def undetermined():
    """미정계수법. 동차해 종류(실근·중근·복소근)와 강제항 가족(지수·다항식·합·삼각·공명)을 섞어 구조가 다른 문제를 만든다."""
    out, count = [], {}
    for p, q, kind, basis, roots in _cases():
        if q == 0:
            continue
        L = _L(p, q)
        okb = _basis_ok(p, q)
        for fam, R, form, bad_form, tier in _forcings(p, q, kind, roots):
            if count.get(fam, 0) >= FAMILY_CAP[fam]:
                continue
            yp, co = _fit(L, R, form)
            if yp is None or yp == 0:
                continue
            unk = sorted(co, key=lambda z: z.name)
            okt = _trial_ok(p, q, R, [A_, B_, C_])
            full = C1 * basis[0] + C2 * basis[1] + yp
            ok_full = lambda g, L=L, R=R, b=basis: is_family_solution(g, lambda h, L=L, R=R: L(h) - R, [C1, C2]) and independent(list(b))
            co_tex = ",\\ ".join(f"{tex(k)} = {tex(co[k])}" for k in unk)
            gen = _gen_tex(kind, roots)
            steps = [
                step(f"y_h = {gen}", lambda b=basis, ok=okb: ok(b)),
                step(f"y_p = {tex(form)}", lambda g=form, ok=okt: ok(g)),
                step(co_tex, lambda g=yp, L=L, R=R: same(L(g), R)),
                step(f"y = {gen} + {sum_tex(yp)}".replace("+ -", "- "), lambda g=full, ok=ok_full: ok(g)),
            ]
            bad_co = ",\\ ".join(f"{tex(k)} = {tex(-co[k])}" for k in unk)
            decoys = []
            wb = _wrong_bases(kind, roots)
            if wb:
                b_, er, spec = wb[0]
                decoys.append(decoy(0, f"y_h = {_btex(b_, spec)}", lambda b=b_, ok=okb: ok(b), er, WHY["rep"] if kind == "rep" else WHY["family"]))
            decoys += [
                decoy(1, f"y_p = {tex(bad_form)}", lambda g=bad_form, ok=okt: ok(g), "theorem_condition", WHY_TRIAL[fam]),
                decoy(2, bad_co, lambda g=-yp, L=L, R=R: same(L(g), R), "sign", WHY["coef"]),
                decoy(3, f"y = {gen} + {sum_tex(-yp)}".replace("+ -", "- "),
                      lambda g=C1 * basis[0] + C2 * basis[1] - yp, ok=ok_full: ok(g), "sign", WHY["yp_sign"]),
            ]
            count[fam] = count.get(fam, 0) + 1
            out.append({"params": {"p": p, "q": q, "R": str(R), "family": fam}, "tier": tier,
                        "problem": rf"{_ode_tex(p, q, R)}\ \text{{의 일반해}}", "steps": steps, "decoys": decoys})
    return out


def _ind_tex(a, b, var="r"):
    """r(r - 1) + ar + b = 0 의 TeX."""
    return f"{var}({var} - 1)" + "".join(f" {'+' if c > 0 else '-'} {abs(c) if (abs(c) != 1 or u == '') else ''}{u}" for c, u in [(a, var), (b, "")] if c != 0) + " = 0"


def _euler_problem(a, b, ics=None):
    lhs = rf"x^{{2}}{P2}" + "".join(f" {'+' if c > 0 else '-'} {abs(c) if abs(c) != 1 else ''}{t}" for c, t in [(a, "x" + P1), (b, "y")] if c != 0)
    if ics is None:
        return lhs + r" = 0\ (x > 0)\ \text{의 일반해}"
    return lhs + rf" = 0,\quad y(1) = {tex(ics[0])},\ {P1}(1) = {tex(ics[1])}"


WHY.update({
    "euler_rep": r"지표방정식이 중근 $r$을 가지면 두 번째 해는 $x\,x^r$이 아니라 $x^r\ln x$입니다.",
    "euler_cplx": r"$r = \alpha \pm \beta i$이면 $x^{\alpha}\cos(\beta\ln x)$, $x^{\alpha}\sin(\beta\ln x)$입니다. $\ln x$가 빠지면 해가 아닙니다.",
})


def euler_cauchy():
    """Euler–Cauchy x²y'' + axy' + by = 0. 가족: 서로 다른 실근 · 중근(x^r ln x) · 복소근(x^α cos(β ln x)) · 일반해만."""
    out = []
    lnx = sp.log(x)
    kinds = []
    xp = lambda k: "x" if k == 1 else f"x^{{{k}}}"         # 음의 지수도 x^{-2}로 (1/x² 대신)
    for r1, r2 in itertools.combinations([-3, -2, -1, 1, 2, 3], 2):
        kinds.append(("real", 1 - (r1 + r2), r1 * r2, (x**r1, x**r2), f"r = {tex(r1)},\\ {tex(r2)}",
                      f"C_1{xp(r1)} + C_2{xp(r2)}", [((sp.exp(r1 * x), sp.exp(r2 * x)), f"C_1{tex(sp.exp(r1 * x))} + C_2{tex(sp.exp(r2 * x))}", "wrong_pair", "euler_fam")]))
    for rr in [-2, -1, 1, 2, 3]:
        kinds.append(("rep", 1 - 2 * rr, rr * rr, (x**rr, x**rr * lnx), f"r = {tex(rr)}\\ (\\text{{중근}})",
                      rf"\left(C_1 + C_2\ln x\right){xp(rr)}",
                      [((x**rr, x**(rr + 1)), rf"\left(C_1 + C_2x\right){xp(rr)}", "wrong_pair", "euler_rep"),
                       ((sp.exp(rr * x), x * sp.exp(rr * x)), rf"\left(C_1 + C_2x\right){tex(sp.exp(rr * x))}", "wrong_pair", "euler_fam")]))
    for al, be in [(0, 1), (0, 2), (1, 1), (-1, 1), (1, 2), (-1, 2), (2, 1)]:
        pre = xp(al) if al else ""
        inner = rf"C_1\cos({tex(be)}\ln x) + C_2\sin({tex(be)}\ln x)".replace(r"(1\ln x)", r"(\ln x)")
        bad_inner = rf"C_1\cos {tex(be * x)} + C_2\sin {tex(be * x)}"
        kinds.append(("cplx", 1 - 2 * al, al * al + be * be, (x**al * sp.cos(be * lnx), x**al * sp.sin(be * lnx)),
                      _roots_tex("cplx", (al, be)),
                      (rf"{pre}\left({inner}\right)" if al else inner),
                      [((x**al * sp.cos(be * x), x**al * sp.sin(be * x)), (rf"{pre}\left({bad_inner}\right)" if al else bad_inner), "wrong_pair", "euler_cplx")]))
    for kind, a, b, basis, roots_tx, gen_tx, wrongs in kinds:
        Lx = lambda g, a=a, b=b: x**2 * sp.diff(g, x, 2) + a * x * sp.diff(g, x) + b * g
        okb = lambda bb, Lx=Lx: is_family_solution(C1 * bb[0] + C2 * bb[1], Lx, [C1, C2]) and independent(list(bb))
        ind = r * (r - 1) + a * r + b
        rts = set(sp.roots(sp.Poly(sp.expand(ind), r)).keys())
        bad_ind = r**2 + a * r + b
        ind_tx = _ind_tex(a, b)
        bad_tx = "r^{2}" + "".join(f" {'+' if c > 0 else '-'} {abs(c) if (abs(c) != 1 or t_ == '') else ''}{t_}" for c, t_ in [(a, "r"), (b, "")] if c != 0) + " = 0"
        head = [
            vstep(ind_tx, ind, sp.expand(ind)),
            step(roots_tx, lambda rts=rts, kind=kind, basis=basis: len(rts) >= 1),
            step(f"y = {gen_tx}", lambda bb=basis, ok=okb: ok(bb)),
        ]
        head_dec = [decoy(0, bad_tx, lambda e=bad_ind, ind=ind: same(sp.expand(e), sp.expand(ind)), "algebra", WHY["indicial"])]
        for bb, tx, er, w in wrongs:
            head_dec.append(decoy(2, f"y = {tx}", lambda bb=bb, ok=okb: ok(bb), er, WHY[w]))
        # 일반해만
        out.append({"params": {"a": a, "b": b, "family": "gen_" + kind}, "tier": 1, "problem": _euler_problem(a, b),
                    "steps": list(head), "decoys": list(head_dec),
                    "verify": lambda bb=basis, ok=okb: None if ok(bb) else "기저 확인 실패"})
        for y0, v0 in [(1, 0), (2, 1), (0, 1), (1, -1)]:
            fam = C1 * basis[0] + C2 * basis[1]
            cs = sp.solve([fam.subs(x, 1) - y0, sp.diff(fam, x).subs(x, 1) - v0], [C1, C2])
            if not cs:
                continue
            final = sp.expand(fam.subs(cs))
            if final == 0:
                continue
            steps = list(head) + [
                step(rf"C_1 = {tex(cs[C1])},\ C_2 = {tex(cs[C2])}", lambda fm=fam, c=cs, Lx=Lx, y0=y0, v0=v0: same(Lx(fm.subs(c)), 0) and same(fm.subs(c).subs(x, 1), y0) and same(sp.diff(fm.subs(c), x).subs(x, 1), v0)),
                step(f"y = {sum_tex(final)}", lambda g=final, Lx=Lx, y0=y0, v0=v0: same(Lx(g), 0) and same(g.subs(x, 1), y0) and same(sp.diff(g, x).subs(x, 1), v0)),
            ]
            decoys = list(head_dec) + [
                decoy(3, rf"C_1 = {tex(y0)},\ C_2 = {tex(v0)}", lambda fm=fam, a_=y0, b_=v0, Lx=Lx, y0=y0, v0=v0: same(sp.diff(fm.subs({C1: a_, C2: b_}), x).subs(x, 1), v0) and same(fm.subs({C1: a_, C2: b_}).subs(x, 1), y0),
                      "initial_condition", WHY["consts"]),
            ]
            out.append({"params": {"a": a, "b": b, "y0": y0, "v0": v0, "family": kind}, "tier": 2 if kind == "real" else 3,
                        "problem": _euler_problem(a, b, (y0, v0)), "steps": steps, "decoys": decoys,
                        "verify": lambda g=final, Lx=Lx: None if same(Lx(g), 0) else "해 확인 실패"})
    return out


# ---------------------------------------------------------------- 새 풀이 뼈대 (M3.6)
SMALLX = [sp.Rational(7, 100), sp.Rational(13, 100), sp.Rational(19, 100), sp.Rational(29, 100)]

WHY.update({
    "vp_w": r"$W = y_1y_2^{\prime} - y_1^{\prime}y_2$입니다. 순서를 바꾸면 부호가 뒤집힙니다.",
    "vp_sign": r"$u_1^{\prime} = -\dfrac{y_2g}{W}$입니다. 앞의 $-$를 빠뜨렸습니다.",
    "vp_swap": r"$y_p = u_1y_1 + u_2y_2$입니다. $u_1$은 $y_1$에, $u_2$는 $y_2$에 곱합니다.",
    "vp_int": r"$u^{\prime}$을 적분해야 $u$가 됩니다. 적분이 틀렸습니다.",
    "red_sign": r"$v^{\prime} = \dfrac{e^{-\int p\,dx}}{y_1^2}$입니다. 지수의 부호가 바뀌었습니다.",
    "red_sq": r"분모는 $y_1$이 아니라 $y_1^2$입니다.",
    "red_back": r"$v$를 구한 뒤 $y_2 = v\,y_1$로 $y_1$을 곱해야 합니다.",
    "red_std": r"표준형 $y^{\prime\prime} + p(x)y^{\prime} + q(x)y = 0$을 만들려면 $y^{\prime\prime}$의 계수로 나눠야 합니다.",
    "fo_eq": r"감쇠력은 속도에 반대 방향이라 방정식에서 $+cy^{\prime}$입니다. 부호를 그대로 옮깁니다.",
    "fo_class": r"$c^2 - 4mk$의 부호로 판정합니다: 음수면 저감쇠(진동), 양수면 과감쇠, 0이면 임계감쇠.",
    "fo_res": r"$\omega$가 고유진동수와 같으면 공명입니다. $A\cos\omega t + B\sin\omega t$는 동차해라서 $t$를 곱해야 합니다.",
    "fo_coef": r"미정계수를 잘못 풀었습니다. 대입해서 $\cos$, $\sin$ 계수를 각각 맞춰 보세요.",
})


def varparam_solve():
    """매개변수 변환법으로 특수해 구하기.
    가족: y'' + b²y = sec bx · csc bx · tan bx · sec² bx (교과서 꼴, 적분 결과를 손으로 정리) ·
          중근 y'' − 2ay' + a²y = eᵃˣ·h(x) (h = 1/xᵏ, 1/(1 + x²), ln x)."""
    out = []
    specs = []
    for b in [1, 2, 3, 4]:
        c, sn = sp.cos(b * x), sp.sin(b * x)
        bx = "x" if b == 1 else f"{b}x"
        k2 = sp.Rational(1, b * b)
        lsec = sp.log(1 / c + sn / c)
        L_SEC = rf"\ln\left|\sec {bx} + \tan {bx}\right|"
        fr = lambda q: "" if q == 1 else tex(q)
        specs.append(("sec", 0, b * b, (c, sn), 1 / c, rf"\sec {bx}",
                      (-sn / (b * c), sp.Rational(1, b), rf"-{fr(sp.Rational(1, b))}\tan {bx}", tex(sp.Rational(1, b))),
                      (k2 * sp.log(c), x / b, rf"{fr(k2)}\ln\left|\cos {bx}\right|", tex(x / b)),
                      (x / b * sn + k2 * c * sp.log(c), rf"{tex(x / b)}\sin {bx} + {fr(k2)}\cos {bx}\,\ln\left|\cos {bx}\right|"), 2 if b == 1 else 3))
        specs.append(("csc", 0, b * b, (c, sn), 1 / sn, rf"\csc {bx}",
                      (-sp.Rational(1, b) + 0 * x, c / (b * sn), tex(-sp.Rational(1, b)), rf"{fr(sp.Rational(1, b))}\cot {bx}"),
                      (-x / b, k2 * sp.log(sn), tex(-x / b), rf"{fr(k2)}\ln\left|\sin {bx}\right|"),
                      (-x / b * c + k2 * sn * sp.log(sn), rf"-{tex(x / b)}\cos {bx} + {fr(k2)}\sin {bx}\,\ln\left|\sin {bx}\right|"), 2 if b == 1 else 3))
        specs.append(("tan", 0, b * b, (c, sn), sn / c, rf"\tan {bx}",
                      (-sn * sn / (b * c), sn / b, rf"-{fr(sp.Rational(1, b))}\sin {bx}\tan {bx}", rf"{fr(sp.Rational(1, b))}\sin {bx}"),
                      (k2 * (sn - lsec), -k2 * c, (rf"{fr(k2)}\left(\sin {bx} - {L_SEC}\right)" if b != 1 else rf"\sin {bx} - {L_SEC}"), rf"-{fr(k2)}\cos {bx}"),
                      (-k2 * c * lsec, rf"-{fr(k2)}\cos {bx}\,{L_SEC}"), 3))
        specs.append(("sec2", 0, b * b, (c, sn), 1 / c**2, rf"\sec^{{2}} {bx}",
                      (-sn / (b * c**2), 1 / (b * c), rf"-{fr(sp.Rational(1, b))}\sec {bx}\tan {bx}", rf"{fr(sp.Rational(1, b))}\sec {bx}"),
                      (-k2 / c, k2 * lsec, rf"-{fr(k2)}\sec {bx}", rf"{fr(k2)}{L_SEC}"),
                      (-k2 + k2 * sn * lsec, rf"-{tex(k2)} + {fr(k2)}\sin {bx}\,{L_SEC}"), 3))
    for a in [1, 2, -1, 3, -2]:
        for hname, h in [("x1", 1 / x), ("x2", 1 / x**2), ("x3", 1 / x**3), ("atan", 1 / (1 + x**2)), ("ln", sp.log(x))]:
            ea = sp.exp(a * x)
            u1p, u2p = -x * h, h
            u1, u2 = sp.simplify(sp.integrate(u1p, x)), sp.simplify(sp.integrate(u2p, x))
            yp = sp.simplify(u1 * ea + u2 * x * ea)
            specs.append(("exp_" + hname, -2 * a, a * a, (ea, x * ea), ea * h, tex(ea * h),
                          (u1p, u2p, tex(u1p), tex(u2p)), (u1, u2, tex(u1), tex(u2)), (yp, tex(sp.factor(yp))), 2 if hname == "x1" else 3))
    for kind, p, q, (y1, y2), g, gtx, (u1p, u2p, u1pt, u2pt), (u1, u2, u1t, u2t), (yp, ypt), tier in specs:
        L = _L(p, q)
        W = sp.simplify(y1 * sp.diff(y2, x) - sp.diff(y1, x) * y2)
        if not same(L(yp), g, SMALLX):
            continue
        prob = rf"{_ode_tex(p, q).replace(' = 0', '')} = {gtx}\ \text{{의 특수해 (매개변수 변환법)}}"
        steps = [
            step(rf"y_1 = {tex(y1)},\ y_2 = {tex(y2)},\ W = {tex(W)}", lambda y1=y1, y2=y2, W=W, L=L: same(L(y1), 0, SMALLX) and same(L(y2), 0, SMALLX) and same(y1 * sp.diff(y2, x) - sp.diff(y1, x) * y2, W, SMALLX)),
            step(rf"u_1^{{\prime}} = {u1pt},\ u_2^{{\prime}} = {u2pt}", lambda a=u1p, b=u2p, y1=y1, y2=y2, g=g, W=W: same(a, -y2 * g / W, SMALLX) and same(b, y1 * g / W, SMALLX)),
            step(rf"u_1 = {u1t},\ u_2 = {u2t}", lambda u1=u1, u2=u2, a=u1p, b=u2p: same(sp.diff(u1, x), a, SMALLX) and same(sp.diff(u2, x), b, SMALLX)),
            step(rf"y_p = {ypt}", lambda yp=yp, L=L, g=g: same(L(yp), g, SMALLX)),
        ]
        neg = lambda tx: tx[1:] if tx.startswith("-") else "-" + tx
        decoys = [
            decoy(0, rf"y_1 = {tex(y1)},\ y_2 = {tex(y2)},\ W = {tex(-W)}", lambda W=-W, y1=y1, y2=y2: same(y1 * sp.diff(y2, x) - sp.diff(y1, x) * y2, W, SMALLX), "sign", WHY["vp_w"]),
            decoy(1, rf"u_1^{{\prime}} = {neg(u1pt)},\ u_2^{{\prime}} = {u2pt}", lambda a=-u1p, y2=y2, g=g, W=W: same(a, -y2 * g / W, SMALLX), "sign", WHY["vp_sign"]),
        ]
        bad = u1 * y2 + u2 * y1
        if not same(L(bad), g, SMALLX):
            decoys.append(decoy(3, rf"y_p = {tex(sp.simplify(bad))}", lambda b=bad, L=L, g=g: same(L(b), g, SMALLX), "algebra", WHY["vp_swap"]))
        out.append({"params": {"family": kind, "p": p, "q": q, "g": str(g)}, "tier": tier, "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda yp=yp, L=L, g=g: None if same(L(yp), g, SMALLX) else "특수해 확인 실패"})
    return out


def reduction_solve():
    """계수 낮추기: 해 y₁을 알 때 y₂ = v·y₁, v' = e^{-∫p}/y₁².
    가족: 상수계수 중근 · Euler 중근 · x²y'' − x(kx + 2)y' + (kx + 2)y = 0 (y₁ = x) · xy'' − (kx + 1)y' + ky = 0 (y₁ = eᵏˣ)."""
    out = []
    lnx = sp.log(x)
    specs = []
    for r_ in [1, 2, 3, -1, -2, -3, sp.Rational(1, 2), sp.Rational(-1, 2)]:
        specs.append(("const_rep", sp.Integer(1), -2 * r_, r_**2, sp.exp(r_ * x)))
    for r_ in [1, 2, 3, -1, -2, -3, sp.Rational(1, 2)]:
        specs.append(("euler_rep", x**2, (1 - 2 * r_) * x, r_**2, x**r_))
    for k in [1, 2, 3, -1, -2, -3, sp.Rational(1, 2)]:
        specs.append(("x_exp", x**2, -x * (k * x + 2), k * x + 2, x))
    for k in [1, 2, -1, -2, 3, sp.Rational(1, 2)]:
        specs.append(("exp_lin", x, -(k * x + 1), k, sp.exp(k * x)))
    for fam, a2, a1, a0, y1 in specs:
        if a1 == 0:
            continue          # p(x) = 0이면 e^{-∫p} = 1이라 단계가 비어 버린다
        Lg = lambda g, a2=a2, a1=a1, a0=a0: a2 * sp.diff(g, x, 2) + a1 * sp.diff(g, x) + a0 * g
        if not same(Lg(y1), 0, XPOS):
            continue
        p = sp.simplify(a1 / a2)
        E = sp.simplify(sp.exp(-sp.integrate(p, x)))
        vp = sp.simplify(E / y1**2)
        vv = sp.simplify(sp.integrate(vp, x))
        y2 = sp.simplify(vv * y1)
        if not (same(Lg(y2), 0, XPOS) and independent([y1, y2], x, XPOS)):
            continue
        prob = rf"{join_terms([(a2, P2), (a1, P1), (a0, 'y')]) if fam == 'const_rep' else _poly_lhs(a2, a1, a0)} = 0,\quad y_1 = {tex(y1)}\ \text{{일 때 }} y_2"
        steps = [
            step(rf"p(x) = {tex(sp.apart(p, x))}", lambda p=p, a1=a1, a2=a2: same(p, a1 / a2, XPOS)),
            step(rf"e^{{-\int p\,dx}} = {tex(E)}", lambda E=E, p=p: same(sp.diff(E, x), -p * E, XPOS)),
            step(rf"v^{{\prime}} = \frac{{e^{{-\int p\,dx}}}}{{y_1^{{2}}}} = {tex(vp)}", lambda vp=vp, E=E, y1=y1: same(vp, E / y1**2, XPOS)),
            step(rf"v = {tex(sp.factor(vv))}", lambda vv=vv, vp=vp: same(sp.diff(vv, x), vp, XPOS)),
            step(rf"y_2 = v\,y_1 = {tex(sp.factor(y2))}", lambda y2=y2, Lg=Lg, y1=y1: same(Lg(y2), 0, XPOS) and independent([y1, y2], x, XPOS)),
        ]
        Eb = sp.simplify(1 / E)
        decoys = [
            decoy(1, rf"e^{{-\int p\,dx}} = {tex(Eb)}", lambda E=Eb, p=p: same(sp.diff(E, x), -p * E, XPOS), "sign", WHY["red_sign"]),
            decoy(2, rf"v^{{\prime}} = \frac{{e^{{-\int p\,dx}}}}{{y_1}} = {tex(sp.simplify(E / y1))}", lambda vp=sp.simplify(E / y1), E=E, y1=y1: same(vp, E / y1**2, XPOS), "missing_factor", WHY["red_sq"]),
        ]
        if not (same(Lg(vv), 0, XPOS) and independent([y1, vv], x, XPOS)):
            decoys.append(decoy(4, rf"y_2 = {tex(vv)}", lambda g=vv, Lg=Lg, y1=y1: same(Lg(g), 0, XPOS) and independent([y1, g], x, XPOS), "missing_factor", WHY["red_back"]))
        if a2 != 1:
            decoys.append(decoy(0, rf"p(x) = {tex(a1)}", lambda p=a1, a1=a1, a2=a2: same(p, a1 / a2, XPOS), "algebra", WHY["red_std"]))
        out.append({"params": {"family": fam, "y1": str(y1), "a": [str(a2), str(a1), str(a0)]}, "tier": {"const_rep": 1, "euler_rep": 2}.get(fam, 3),
                    "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda y2=y2, Lg=Lg, y1=y1: None if same(Lg(y2), 0, XPOS) and independent([y1, y2], x, XPOS) else "y₂ 확인 실패"})
    return out


XPOS = [sp.Rational(6, 5), sp.Rational(3, 2), sp.Rational(9, 5), sp.Rational(11, 5)]


def _poly_lhs(a2, a1, a0):
    """x²y'' − x(kx + 2)y' + … 처럼 계수가 식인 좌변 TeX."""
    out = []
    for c, d in [(a2, P2), (a1, P1), (a0, "y")]:
        c = sp.factor(c)
        if c == 0:
            continue
        neg = c.could_extract_minus_sign()
        cc = -c if neg else c
        ct = "" if cc == 1 else (tex(cc) if (cc.is_Mul or cc.is_Pow or cc.is_Symbol or cc.is_number) else rf"\left({tex(cc)}\right)")
        out.append(("- " if neg else "+ ") + ct + d)
    s_ = " ".join(out)
    return s_[2:] if s_.startswith("+ ") else "-" + s_[2:]


def forced_oscillation():
    """강제 진동 my'' + cy' + ky = F₀cos ωt (용수철·RLC). 가족: 저감쇠 · 과감쇠 · 감쇠 없음(비공명) · 공명 · RLC 회로."""
    out = []
    specs = []
    for c, k, w in itertools.product([2, 4], [5, 10, 13, 17, 8], [1, 2]):
        if c * c < 4 * k and k != w * w:
            specs.append(("under", 1, c, k, 10, w, 2))
    for c, k, w in itertools.product([3, 5, 6], [2, 4, 6, 8], [1, 2]):
        if c * c > 4 * k:
            specs.append(("over", 1, c, k, 10, w, 2))
    for k, F0, w in [(4, 3, 1), (9, 8, 1), (9, 5, 2), (16, 7, 3), (1, 3, 2), (4, 12, 1), (25, 9, 4), (9, 16, 1), (16, 12, 2), (25, 24, 1)]:
        specs.append(("undamped", 1, 0, k, F0, w, 1))
    for k, F0 in [(1, 2), (4, 4), (9, 6), (16, 8), (4, 8), (1, 4), (9, 12), (25, 10)]:
        specs.append(("resonance", 1, 0, k, F0, sp.sqrt(k), 3))
    for R, invC, w in itertools.product([2, 4, 6], [5, 10, 13], [1, 2]):
        if R * R < 4 * invC and invC != w * w:
            specs.append(("rlc", 1, R, invC, 10, w, 3))
    T = sp.Symbol("t")
    for fam, m, c, k, F0, w, tier in specs:
        L = lambda g, m=m, c=c, k=k: m * sp.diff(g, T, 2) + c * sp.diff(g, T) + k * g
        R = F0 * sp.cos(w * T)
        res = fam == "resonance"
        form = T * (A_ * sp.cos(w * T) + B_ * sp.sin(w * T)) if res else A_ * sp.cos(w * T) + B_ * sp.sin(w * T)
        co = sp.solve([sp.expand(L(form) - R).subs(T, pt) for pt in (sp.Rational(1, 3), sp.Rational(2, 3), sp.Rational(5, 4))], [A_, B_], dict=True)
        if not co:
            continue
        co = co[0]
        yp = sp.expand(form.subs(co))
        if not same(L(yp), R):
            continue
        disc = c * c - 4 * m * k
        rts = sp.roots(sp.Poly(m * r**2 + c * r + k, r))
        if disc < 0:
            al, be = sp.Rational(-c, 2 * m), sp.sqrt(-disc) / (2 * m)
            roots_tx = rf"r = {tex(al)} \pm {tex(be) if be != 1 else ''}i" if al != 0 else rf"r = \pm {tex(be) if be != 1 else ''}i"
            yh = _gen_tex("cplx", (al, be)).replace("x", "t")
            cls = r"\text{저감쇠}" if c else r"\text{감쇠 없음}"
        else:
            r1, r2 = sorted(rts.keys())
            roots_tx = rf"r = {tex(r1)},\ {tex(r2)}"
            yh = f"C_1{tex(sp.exp(r1 * T))} + C_2{tex(sp.exp(r2 * T))}"
            cls = r"\text{과감쇠}" if disc > 0 else r"\text{임계감쇠}"
        var = "q" if fam == "rlc" else "y"
        eq_tx = join_terms([(m, var + r"^{\prime\prime}"), (c, var + r"^{\prime}"), (k, var)]) + f" = {tex(R)}"
        if fam == "rlc":
            prob = rf"Lq^{{\prime\prime}} + Rq^{{\prime}} + \tfrac{{1}}{{C}}q = E(t):\ L = 1,\ R = {c},\ C = {tex(sp.Rational(1, k))},\ E = {tex(R)}\ \text{{일 때 전하 }} q(t)\text{{의 일반해}}"
        else:
            prob = rf"my^{{\prime\prime}} + cy^{{\prime}} + ky = F(t):\ m = {m},\ c = {c},\ k = {k},\ F = {tex(R)}\ \text{{일 때 변위 }} y(t)\text{{의 일반해}}"
        co_tx = rf"{var}_p = {tex(form)},\ A = {tex(co[A_])},\ B = {tex(co[B_])}"
        steps = [
            step(eq_tx, lambda: True),
            step(rf"{roots_tx}\ ({cls})", lambda: True),
            step(co_tx, lambda yp=yp, L=L, R=R: same(L(yp), R)),
            step(rf"{var} = {yh} + {sum_tex(yp)}".replace("+ -", "- "), lambda yp=yp, L=L, R=R: same(L(yp), R)),
        ]
        steps[0]["ok"] = lambda: True
        decoys = []
        if c:
            decoys.append(decoy(0, join_terms([(m, var + r"^{\prime\prime}"), (-c, var + r"^{\prime}"), (k, var)]) + f" = {tex(R)}", lambda: False, "sign", WHY["fo_eq"]))
            other = r"\text{과감쇠}" if disc < 0 else r"\text{저감쇠}"
            decoys.append(decoy(1, rf"{roots_tx}\ ({other})", lambda: False, "theorem_condition", WHY["fo_class"]))
        bad = {A_: -co[A_], B_: co[B_]} if co[A_] != 0 else {A_: co[A_], B_: -co[B_]}
        badyp = sp.expand(form.subs(bad))
        decoys.append(decoy(2, rf"{var}_p = {tex(form)},\ A = {tex(bad[A_])},\ B = {tex(bad[B_])}", lambda b=badyp, L=L, R=R: same(L(b), R), "sign", WHY["fo_coef"]))
        if res:
            nf = A_ * sp.cos(w * T) + B_ * sp.sin(w * T)
            decoys.append(decoy(2, rf"{var}_p = {tex(nf)}\ (\text{{보통 꼴}})", lambda: False, "theorem_condition", WHY["fo_res"]))
        out.append({"params": {"family": fam, "m": m, "c": c, "k": k, "F0": F0, "w": str(w)}, "tier": tier, "problem": prob,
                    "steps": steps, "decoys": decoys,
                    "verify": lambda yp=yp, L=L, R=R: None if same(L(yp), R) else "특수해 확인 실패"})
    return out
