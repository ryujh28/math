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
    pre = "" if al == 0 else tex(sp.exp(al * x))
    return rf"{pre}\left(C_1\cos {tex(be * x)} + C_2\sin {tex(be * x)}\right)"


def _wrong_bases(kind, roots):
    if kind == "real":
        a, b = roots
        return [((sp.exp(-a * x), sp.exp(-b * x)), "sign", ("real", (-a, -b))),
                ((sp.exp(a * x), x * sp.exp(a * x)), "wrong_pair", ("rep", (a,))),
                ((sp.cos(abs(a) * x), sp.sin(abs(b) * x)), "wrong_pair", None)]
    if kind == "rep":
        (a,) = roots
        return [((sp.exp(a * x), sp.exp(-a * x)), "wrong_pair", ("real", (a, -a))),
                ((sp.exp(-a * x), x * sp.exp(-a * x)), "sign", ("rep", (-a,))),
                ((sp.exp(a * x), x**2 * sp.exp(a * x)), "algebra", None)]
    al, be = roots
    out = [((sp.exp(be * x) * sp.cos(abs(al) * x), sp.exp(be * x) * sp.sin(abs(al) * x)), "algebra", ("cplx", (be, abs(al)))),
           ((sp.exp(al * x), sp.exp(be * x)), "wrong_pair", ("real", (al, be)))]
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
            tier = {"real": 1, "rep": 2, "cplx": 2}[kind]
            out.append({"params": {"p": p, "q": q, "y0": y0, "v0": v0}, "tier": tier,
                        "problem": rf"{_ode_tex(p, q)},\quad y(0) = {tex(y0)},\ {P1}(0) = {tex(v0)}",
                        "steps": steps, "decoys": decoys,
                        "verify": lambda yt=ytrue, L=_L(p, q), y0=y0, v0=v0: None if same(L(yt), 0) and same(yt.subs(x, 0), y0) and same(sp.diff(yt, x).subs(x, 0), v0) else "dsolve 해 확인 실패"})
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


def euler_cauchy():
    out = []
    for r1, r2 in itertools.combinations([-3, -2, -1, 1, 2, 3], 2):
        a, b = 1 - (r1 + r2), r1 * r2
        for y0, v0 in [(1, 0), (2, 1), (0, 1), (1, -1)]:
            sol = sp.dsolve(sp.Eq(x**2 * f(x).diff(x, 2) + a * x * f(x).diff(x) + b * f(x), 0), f(x),
                            ics={f(1): y0, f(x).diff(x).subs(x, 1): v0})
            ytrue = sp.simplify(sol.rhs)
            fam = C1 * x**r1 + C2 * x**r2
            cs = sp.solve([fam.subs(x, 1) - y0, sp.diff(fam, x).subs(x, 1) - v0], [C1, C2])
            final = sp.expand(fam.subs(cs))
            Lx = lambda g, a=a, b=b: x**2 * sp.diff(g, x, 2) + a * x * sp.diff(g, x) + b * g
            ind = r * (r - 1) + a * r + b
            okb = lambda bb, Lx=Lx: is_family_solution(C1 * bb[0] + C2 * bb[1], Lx, [C1, C2]) and independent(list(bb))
            steps = [
                vstep(rf"r(r - 1) {'+' if a >= 0 else '-'} {abs(a) if abs(a) != 1 else ''}r {'+' if b >= 0 else '-'} {abs(b)} = 0".replace(" + 0r", "").replace(" - 0r", ""),
                      ind, sp.expand(ind)),
                step(f"r = {tex(r1)},\\ {tex(r2)}", lambda rs={r1, r2}, ind=ind: same(rs, set(sp.roots(sp.Poly(sp.expand(ind), r)).keys()))),
                step(f"y = C_1x^{{{r1}}} + C_2x^{{{r2}}}", lambda bb=(x**r1, x**r2), ok=okb: ok(bb)),
                step(rf"C_1 = {tex(cs[C1])},\ C_2 = {tex(cs[C2])}", lambda fm=fam, c=cs, yt=ytrue: same(fm.subs(c), yt)),
                vstep(f"y = {sum_tex(final)}", final, ytrue),
            ]
            bad_ind = r**2 + a * r + b
            decoys = [
                step(f"y = C_1{tex(sp.exp(r1 * x))} + C_2{tex(sp.exp(r2 * x))}", lambda bb=(sp.exp(r1 * x), sp.exp(r2 * x)), ok=okb: ok(bb)),
            ]
            decoys = [
                decoy(0, rf"r^{{2}} {'+' if a >= 0 else '-'} {abs(a) if abs(a) != 1 else ''}r {'+' if b >= 0 else '-'} {abs(b)} = 0".replace(" + 0r", "").replace(" - 0r", ""),
                      lambda e=bad_ind, ind=ind: same(sp.expand(e), sp.expand(ind)), "algebra", WHY["indicial"]),
                decoy(2, f"y = C_1{tex(sp.exp(r1 * x))} + C_2{tex(sp.exp(r2 * x))}", lambda bb=(sp.exp(r1 * x), sp.exp(r2 * x)), ok=okb: ok(bb),
                      "wrong_pair", WHY["euler_fam"]),
                decoy(3, rf"C_1 = {tex(y0)},\ C_2 = {tex(v0)}", lambda fm=fam, a_=y0, b_=v0, yt=ytrue: same(fm.subs({C1: a_, C2: b_}), yt),
                      "initial_condition", WHY["consts"]),
            ]
            out.append({"params": {"r": [r1, r2], "y0": y0, "v0": v0}, "tier": 3,
                        "problem": rf"x^{{2}}{P2} {'+' if a >= 0 else '-'} {abs(a) if abs(a) != 1 else ''}x{P1} {'+' if b >= 0 else '-'} {abs(b)}y = 0,\quad y(1) = {tex(y0)},\ {P1}(1) = {tex(v0)}".replace(" + 0x" + P1, "").replace(" - 0x" + P1, ""),
                        "steps": steps, "decoys": decoys,
                        "verify": lambda yt=ytrue, Lx=Lx: None if same(Lx(yt), 0) else "해 확인 실패"})
    return out
