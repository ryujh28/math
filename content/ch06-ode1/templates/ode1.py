"""6장 1계 ODE — 생성기. 참 해는 SymPy dsolve로 따로 구한다."""
import itertools
import sympy as sp
from texkit import tex, join_terms, sum_tex
from checks import same, opt, step, vstep, decoy, vdecoy, relation_holds, is_family_solution, x, y, C

f = sp.Function("f")
P1 = r"y^{\prime}"
SMALL = [sp.Rational(5, 100), sp.Rational(11, 100), sp.Rational(17, 100), sp.Rational(23, 100)]


def _dsolve(lhs_minus_rhs, y0, x0=0):
    """lhs_minus_rhs(f(x)) = 0, f(x0) = y0 를 dsolve로 푼다."""
    sol = sp.dsolve(sp.Eq(lhs_minus_rhs(f(x)), 0), f(x), ics={f(x0): y0})
    if isinstance(sol, list):
        sol = sol[0]
    return sp.simplify(sol.rhs)


def _ptex(p):
    p = sp.sympify(p)
    if p == 1:
        return "+ "
    if p == -1:
        return "- "
    if p.could_extract_minus_sign():
        return "- " + tex(-p)
    return "+ " + tex(p)


# ---------------------------------------------------------------- 사실 원자
def integrating_factor():
    out = []
    cases = []
    for a in [1, 2, 3, -1, -2, sp.Rational(1, 2)]:
        cases.append((a, sp.exp(a * x), [(sp.exp(-a * x), "sign"), (a * x, "missing_factor"), (sp.exp(a), "algebra")]))
    for a in [1, 2, 3, -1, -2]:
        cases.append((a / x, x**a, [(x**(-a), "sign"), (a * sp.log(x), "missing_factor"), (sp.exp(a / x), "algebra")]))
    for a in [1, 2, -1, 3]:
        cases.append((2 * a * x, sp.exp(a * x**2), [(sp.exp(-a * x**2), "sign"), (sp.exp(2 * a * x), "algebra"), (a * x**2, "missing_factor")]))
    cases.append((sp.cos(x), sp.exp(sp.sin(x)), [(sp.exp(-sp.sin(x)), "sign"), (sp.exp(sp.cos(x)), "algebra"), (sp.sin(x), "missing_factor")]))
    for p, mu, wr in cases:
        ok = lambda m, p=p: not same(m, 0) and same(sp.diff(m, x), p * m)   # μ′ = pμ
        out.append({"params": {"p": str(p)}, "tier": 1,
                    "prompt": rf"{P1} {_ptex(p)}y = q(x)\ \text{{의 적분인자}}\ \mu(x) = \;?",
                    "answer": opt(tex(mu), lambda m=mu, ok=ok: ok(m)),
                    "wrong": [opt(tex(m), lambda m=m, ok=ok: ok(m), e) for m, e in wr]})
    return out


def separable_general():
    out = []
    for a, n in itertools.product([1, 2, 3, -1, -2, -3], [0, 1, 2]):
        rhs = a * x**n
        expo = a * x ** (n + 1) / (n + 1)
        resid = lambda g, rhs=rhs: sp.diff(g, x) - rhs * g
        ok = lambda g, resid=resid: is_family_solution(g, resid, [C]) and not same(sp.diff(g, C), 0)
        ans = C * sp.exp(expo)
        cands = [(C * sp.exp(a * x**n), "algebra"), (C * sp.exp(a * x ** (n + 1)), "missing_factor"),
                 (C * sp.exp(-expo), "sign"), (C + sp.exp(expo), "algebra")]
        lhs = join_terms([(a, "x" if n == 1 else ("" if n == 0 else f"x^{{{n}}}"))]) if n else tex(a)
        out.append({"params": {"a": a, "n": n}, "tier": 1, "prompt": rf"{P1} = {lhs}y\ \text{{의 일반해}}",
                    "answer": opt("y = " + tex(ans), lambda g=ans, ok=ok: ok(g)),
                    "wrong": [opt("y = " + tex(g), lambda g=g, ok=ok: ok(g), e) for g, e in cands]})
    return out


def exact_k():
    out = []
    k = sp.Symbol("k")
    for a, b in itertools.product([1, 2, 3, 4, -2, 6], [1, 2, -1, 3]):
        M = a * x**2 * y + b * y
        N = k * x**3 + b * x
        kv = sp.Rational(a, 3)
        ok = lambda v, M=M, N=N: same(sp.diff(M, y), sp.diff(N.subs(k, v), x))
        cands = [(a, "missing_factor"), (3 * a, "algebra"), (-kv, "sign"), (kv + 1, "algebra")]
        prob = rf"\left({join_terms([(a, 'x^{2}y'), (b, 'y')])}\right)dx + \left(kx^{{3}} {'+' if b > 0 else '-'} {abs(b) if abs(b) != 1 else ''}x\right)dy = 0\ \text{{이 완전하려면}}\ k = \;?"
        out.append({"params": {"a": a, "b": b}, "tier": 2, "prompt": prob,
                    "answer": opt(tex(kv), lambda v=kv, ok=ok: ok(v)),
                    "wrong": [opt(tex(v), lambda v=v, ok=ok: ok(v), e) for v, e in cands]})
    return out


# ---------------------------------------------------------------- 풀이 뼈대
WHY = {
    "mu_sign": r"적분인자는 $\mu = e^{\int p\,dx}$입니다. 지수의 부호가 틀렸습니다.",
    "int": r"우변 적분 $\int \mu q\,dx$를 잘못 계산했습니다.",
    "ic": r"초기조건을 넣을 때 우변 적분값 $F(0)$을 빼지 않았습니다.",
    "sep_ic": r"$x = 0$, $y = y_0$를 대입해 $C$를 정해야 합니다. $C$는 $y_0$ 자체가 아닙니다.",
    "final": r"마지막에 $\mu$로 나눌 때 지수 부호가 틀렸습니다.",
    "sep": r"변수를 분리할 때 $g(y)$를 분모로 보내야 합니다.",
    "sep_int": r"적분 결과가 틀렸습니다. 양변을 미분해서 확인해 보세요.",
    "sep_half": r"$\int x\,dx = \dfrac{x^2}{2}$입니다. $\dfrac{1}{2}$이 빠졌습니다.",
    "ex_int": r"$\int M\,dx$는 $x$에 대해서만 적분합니다. $2cxy$를 $x$로 적분하면 $cx^2y$.",
    "ex_h": r"$h^{\prime}(y)$를 구한 뒤 $y$로 적분해야 $h(y)$가 됩니다.",
    "ex_c": r"초기조건 $(x_0, y_0)$를 $F$에 대입해 상수를 정합니다.",
    "ex_my": r"$M_y = \partial M/\partial y$, $N_x = \partial N/\partial x$ 계산이 틀렸습니다.",
}


def linear():
    out = []
    for a, kind, k, b, y0 in itertools.product([1, 2, 3, -1], ["const", "exp", "lin"], [1, 2, 3, -2], [1, 2, -1], [0, 1, 2, -1]):
        if kind == "const" and b != 1:
            continue
        if kind == "lin" and b != 1:
            continue
        if kind == "exp" and a + b == 0:
            continue
        q = {"const": sp.Integer(k), "exp": k * sp.exp(b * x), "lin": k * x}[kind]
        mu = sp.exp(a * x)
        F = sp.simplify(sp.integrate(mu * q, x))
        ytrue = _dsolve(lambda g, a=a, q=q: g.diff(x) + a * g - q, y0)
        C0 = sp.simplify(mu.subs(x, 0) * y0 - F.subs(x, 0))
        final = sp.expand(sp.simplify((F + C0) / mu))
        prob = rf"{join_terms([(1, P1), (a, 'y')])} = {tex(q)},\quad y(0) = {tex(y0)}"
        steps = [
            step(rf"\mu = {tex(mu)}", lambda m=mu, a=a: same(sp.diff(m, x), a * m)),
            step(rf"\left({tex(mu)}\,y\right)^{{\prime}} = {tex(sp.expand(mu * q))}", lambda m=mu, yt=ytrue, q=q: same(sp.diff(m * yt, x), m * q)),
            step(rf"{tex(mu)}\,y = {tex(F)} + C", lambda rel=mu * y - F - C, yt=ytrue: relation_holds(rel, yt, [C])),
            vstep(rf"C = {tex(C0)}", C0, sp.simplify((mu * ytrue - F).subs(x, 0))),
            vstep(rf"y = {sum_tex(final)}", final, ytrue),
        ]
        bad_mu = sp.exp(-a * x)
        if kind == "exp":
            Fb = k * sp.exp((a + b) * x)
        elif kind == "lin":
            Fb = k * (x / sp.Integer(a) + sp.Rational(1, a**2)) * sp.exp(a * x)
        else:
            Fb = k * sp.exp(a * x)
        bad_final = sp.expand(sp.simplify((F + C0) * sp.exp(a * x)))
        decoys = [
            decoy(0, rf"\mu = {tex(bad_mu)}", lambda m=bad_mu, a=a: same(sp.diff(m, x), a * m), "sign", WHY["mu_sign"]),
            decoy(2, rf"{tex(mu)}\,y = {tex(sp.simplify(Fb))} + C", lambda rel=mu * y - Fb - C, yt=ytrue: relation_holds(rel, yt, [C]), "algebra", WHY["int"]),
            vdecoy(3, rf"C = {tex(y0)}", y0, sp.simplify((mu * ytrue - F).subs(x, 0)), "initial_condition", WHY["ic"]),
            vdecoy(4, rf"y = {sum_tex(bad_final)}", bad_final, ytrue, "sign", WHY["final"]),
        ]
        tier = {"const": 1, "exp": 2, "lin": 3}[kind]
        out.append({"params": {"a": a, "q": str(q), "y0": y0}, "tier": tier, "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda yt=ytrue, a=a, q=q, y0=y0: None if same(sp.diff(yt, x) + a * yt, q) and same(yt.subs(x, 0), y0) else "dsolve 해 확인 실패"})
    return out


def separable():
    out = []
    fams = []
    for k, y0 in itertools.product([1, 2, -1, -2], [1, 2, -1, sp.Rational(1, 2)]):
        fams.append(dict(f=k * x, g=y**2, H=-1 / y, F=k * x**2 / 2, rhs=k * x * y**2, y0=y0, pts=SMALL,
                         badH=(1 / y, "sign", "sep_int"), tier=2, key=("xy2", k, y0)))
    for y0 in [1, 2, 3, 4]:
        fams.append(dict(f=x, g=1 / y, H=y**2 / 2, F=x**2 / 2, rhs=x / y, y0=y0, pts=None,
                         badF=(x**2, "missing_factor", "sep_half"), tier=1, key=("x/y", y0)))
    for a, y0 in itertools.product([1, 2, -1, -2, 0], [1, 2, 3]):
        fams.append(dict(f=x + a, g=y, H=sp.log(y), F=x**2 / 2 + a * x, rhs=(x + a) * y, y0=y0, pts=None,
                         badF=(x**2 + a * x, "missing_factor", "sep_half"), tier=1, key=("lin", a, y0)))
    for y0 in [2, 3]:
        fams.append(dict(f=sp.exp(x), g=1 / y, H=y**2 / 2, F=sp.exp(x), rhs=sp.exp(x) / y, y0=y0, pts=None,
                         badH=(y**2, "missing_factor", "sep_int"), tier=2, key=("ex/y", y0)))
    for fm in fams:
        fx, g, H, F, y0, pts = fm["f"], fm["g"], fm["H"], fm["F"], fm["y0"], fm["pts"]
        ytrue = _dsolve(lambda h, rhs=fm["rhs"]: h.diff(x) - rhs.subs(y, h), y0)
        if isinstance(ytrue, sp.Piecewise):
            continue
        C0 = sp.simplify(H.subs(y, y0) - F.subs(x, 0))
        prob = rf"{P1} = {tex(fm['rhs'])},\quad y(0) = {tex(y0)}"
        h = sp.simplify(1 / g)
        steps = [
            step(rf"{tex(h)}\,dy = {tex(fx)}\,dx", lambda h=h, g=g, fx=fx, f0=fm["f"]: same(sp.simplify(h * g), 1) and same(fx, f0)),
            step(rf"{tex(H)} = {tex(F)} + C", lambda rel=H - F - C, yt=ytrue, p=pts: relation_holds(rel, yt, [C], pts=p)),
            vstep(rf"C = {tex(C0)}", C0, sp.simplify(H.subs(y, ytrue) - F).subs(x, 0)),
            vstep(rf"y = {tex(ytrue)}", ytrue, ytrue, pts),
        ]
        decoys = [
            decoy(0, rf"{tex(g)}\,dy = {tex(fx)}\,dx", lambda h=g, g=g: same(sp.simplify(h * g), 1), "algebra", WHY["sep"]),
            vdecoy(2, rf"C = {tex(y0)}", y0, sp.simplify(H.subs(y, ytrue) - F).subs(x, 0), "initial_condition", WHY["sep_ic"]),
        ]
        if "badH" in fm:
            Hb, er, w = fm["badH"]
            decoys.append(decoy(1, rf"{tex(Hb)} = {tex(F)} + C", lambda rel=Hb - F - C, yt=ytrue, p=pts: relation_holds(rel, yt, [C], pts=p), er, WHY[w]))
        if "badF" in fm:
            Fb, er, w = fm["badF"]
            decoys.append(decoy(1, rf"{tex(H)} = {tex(Fb)} + C", lambda rel=H - Fb - C, yt=ytrue, p=pts: relation_holds(rel, yt, [C], pts=p), er, WHY[w]))
        yb = ytrue.subs(x, -x) if not same(ytrue.subs(x, -x), ytrue, pts) else None
        if yb is not None:
            decoys.append(vdecoy(3, rf"y = {tex(yb)}", yb, ytrue, "sign", "적분 후 정리할 때 부호를 잘못 옮겼습니다.", pts))
        out.append({"params": {"fam": str(fm["key"])}, "tier": fm["tier"], "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda yt=ytrue, rhs=fm["rhs"], y0=y0, p=pts: None if same(sp.diff(yt, x), rhs.subs(y, yt), p) and same(yt.subs(x, 0), y0) else "해 확인 실패"})
    return out


def exact():
    out = []
    for c, a, b, y0 in itertools.product([1, 2, -1, 3], [1, 2, -3, 0], [1, 2, -1], [1, 2, -1]):
        M = 2 * c * x * y + a
        N = c * x**2 + 2 * b * y
        Fp = c * x**2 * y + a * x
        Ffull = Fp + b * y**2
        K = Ffull.subs({x: 0, y: y0})
        prob = rf"\left({join_terms([(2 * c, 'xy'), (a, '')])}\right)dx + \left({join_terms([(c, 'x^{2}'), (2 * b, 'y')])}\right)dy = 0,\quad y(0) = {tex(y0)}"
        steps = [
            step(rf"M_y = N_x = {tex(2 * c * x)}", lambda M=M, N=N, v=2 * c * x: same(sp.diff(M, y), v) and same(sp.diff(N, x), v)),
            step(rf"F = \int M\,dx = {tex(Fp)} + h(y)", lambda Fp=Fp, M=M: same(sp.diff(Fp, x), M)),
            step(rf"F_y = N \Rightarrow h(y) = {tex(b * y**2)}", lambda F=Ffull, N=N: same(sp.diff(F, y), N)),
            vstep(rf"{tex(Ffull)} = {tex(K)}", K, Ffull.subs({x: 0, y: y0})),
        ]
        Fpb = c * x * y + a * x
        Fbh = Fp + 2 * b * y
        decoys = [
            decoy(1, rf"F = \int M\,dx = {tex(Fpb)} + h(y)", lambda Fp=Fpb, M=M: same(sp.diff(Fp, x), M), "algebra", WHY["ex_int"]),
            decoy(2, rf"F_y = N \Rightarrow h(y) = {tex(2 * b * y)}", lambda F=Fbh, N=N: same(sp.diff(F, y), N), "algebra", WHY["ex_h"]),
            vdecoy(3, rf"{tex(Ffull)} = {tex(-K)}", -K, Ffull.subs({x: 0, y: y0}), "initial_condition", WHY["ex_c"]),
            decoy(0, rf"M_y = {tex(2 * c * x)},\ N_x = {tex(c * x)}", lambda N=N, v=c * x: same(sp.diff(N, x), v), "algebra", WHY["ex_my"]),
        ]
        out.append({"params": {"c": c, "a": a, "b": b, "y0": y0}, "tier": 2, "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda M=M, N=N, F=Ffull: None if same(sp.diff(F, x), M) and same(sp.diff(F, y), N) else "퍼텐셜 확인 실패"})
    return out
