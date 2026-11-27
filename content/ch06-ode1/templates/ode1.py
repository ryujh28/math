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
    for a in [1, 2, 3, 4, -1, -2, -3, sp.Rational(1, 2), sp.Rational(-1, 2)]:
        cases.append((a, sp.exp(a * x), [(sp.exp(-a * x), "sign"), (a * x, "missing_factor"), (sp.exp(a), "algebra")]))
    for a in [1, 2, 3, 4, -1, -2, -3]:
        cases.append((a / x, x**a, [(x**(-a), "sign"), (a * sp.log(x), "missing_factor"), (sp.exp(a / x), "algebra")]))
    for a in [1, 2, -1, 3, -2]:
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
    for a, n in itertools.product([1, 2, 3, 4, -1, -2, -3, -4], [0, 1, 2]):
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
    "sep_third": r"$\int x^2\,dx = \dfrac{x^3}{3}$입니다. $\dfrac{1}{3}$이 빠졌습니다.",
    "sep_atan": r"$\int \dfrac{dy}{1 + y^2} = \arctan y$입니다. $\ln(1 + y^2)$은 $\dfrac{2y}{1 + y^2}$를 적분한 것입니다.",
    "sep_exp": r"$\int e^{y}\,dy = e^{y}$입니다. 부호를 바꿀 이유가 없습니다.",
    "sep_const": r"상수 $k$를 $x$로 적분하면 $kx$입니다. $kx$를 한 번 더 적분했습니다.",
    "ex_trig": r"$\int y\cos x\,dx = y\sin x$입니다. $\cos$의 적분은 $+\sin$입니다.",
    "ex_exp": r"$\int ye^{x}\,dx = ye^{x}$입니다. $e^x$를 적분해도 $x$가 곱해지지 않습니다.",
    "ex_int": r"$\int M\,dx$는 $x$에 대해서만 적분합니다. $2cxy$를 $x$로 적분하면 $cx^2y$입니다.",
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
    # 가족 더: y' = k(1 + y²) → arctan, y' = kx²y → x³/3, y' = e^{x - y} → ln(eˣ + C), y' = ky (지수 성장·감쇠)
    for k, y0 in itertools.product([1, 2, -1, 3], [0, 1, -1]):
        fams.append(dict(f=sp.Integer(k), g=1 + y**2, H=sp.atan(y), F=k * x, rhs=k * (1 + y**2), y0=y0, pts=SMALL,
                         badH=(sp.log(1 + y**2), "algebra", "sep_atan"), tier=3, key=("tan", k, y0)))
    for k, y0 in itertools.product([1, 3, -3, 6], [1, 2, 3]):
        fams.append(dict(f=k * x**2, g=y, H=sp.log(y), F=k * x**3 / 3, rhs=k * x**2 * y, y0=y0, pts=None,
                         badF=(k * x**3, "missing_factor", "sep_third"), tier=2, key=("x2y", k, y0)))
    for y0 in [0, 1, 2, -1]:
        fams.append(dict(f=sp.exp(x), g=sp.exp(-y), H=sp.exp(y), F=sp.exp(x), rhs=sp.exp(x - y), y0=y0, pts=SMALL,
                         badH=(-sp.exp(-y), "sign", "sep_exp"), tier=3, key=("exy", y0)))
    for k, y0 in itertools.product([2, 3, -1, -2], [1, 2, -3]):
        fams.append(dict(f=sp.Integer(k), g=y, H=sp.log(y), F=k * x, rhs=k * y, y0=y0, pts=None,
                         badF=(k * x**2 / 2, "algebra", "sep_const"), tier=1, key=("ky", k, y0)))
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
        out.append({"params": {"fam": str(fm["key"]), "family": fm["key"][0]}, "tier": fm["tier"], "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda yt=ytrue, rhs=fm["rhs"], y0=y0, p=pts: None if same(sp.diff(yt, x), rhs.subs(y, yt), p) and same(yt.subs(x, 0), y0) else "해 확인 실패"})
    return out


def exact():
    """완전미분방정식. 가족: 다항식 · 삼각(y cos x) · 지수(y eˣ) · 3차 다항식(x³y², 초기값은 x = 1)."""
    out = []
    specs = []
    for c, a, b, y0 in itertools.product([1, 2, -1, 3], [1, 2, -3, 0], [1, 2, -1], [1, 2, -1]):
        specs.append(("poly", 2 * c * x * y + a, c * x**2 + 2 * b * y, c * x**2 * y + a * x, b * y**2,
                      c * x * y + a * x, 2 * b * y, (0, y0), 1, ("ex_int", "algebra")))
    for a, b, y0 in itertools.product([1, 2, -1], [1, 3], [1, 2, -1]):
        specs.append(("trig", y * sp.cos(x) + 2 * a * x, sp.sin(x) + 3 * b * y**2, y * sp.sin(x) + a * x**2, b * y**3,
                      -y * sp.sin(x) + a * x**2, 3 * b * y**2, (0, y0), 3, ("ex_trig", "sign")))
    for a, b, y0 in itertools.product([1, 2, -1], [1, 2, -1], [1, 2, -1]):
        specs.append(("exp", y * sp.exp(x) + a, sp.exp(x) + 2 * b * y, y * sp.exp(x) + a * x, b * y**2,
                      x * y * sp.exp(x) + a * x, 2 * b * y, (0, y0), 2, ("ex_exp", "algebra")))
    for c, b, y0 in itertools.product([1, 2, -1], [1, 2, -2], [1, 2, -1]):
        specs.append(("cubic", 3 * c * x**2 * y**2, 2 * c * x**3 * y + b, c * x**3 * y**2, b * y,
                      3 * c * x**3 * y**2, sp.Integer(b), (1, y0), 3, ("ex_int", "algebra")))
    for fam, M, N, Fp, h, Fpb, hb, (x0, y0), tier, (wi, ei) in specs:
        Ffull = Fp + h
        K = Ffull.subs({x: x0, y: y0})
        My = sp.diff(M, y)
        prob = rf"\left({sum_tex(M)}\right)dx + \left({sum_tex(N)}\right)dy = 0,\quad y({tex(x0)}) = {tex(y0)}"
        steps = [
            step(rf"M_y = N_x = {tex(My)}", lambda M=M, N=N, v=My: same(sp.diff(M, y), v) and same(sp.diff(N, x), v)),
            step(rf"F = \int M\,dx = {sum_tex(Fp)} + h(y)", lambda Fp=Fp, M=M: same(sp.diff(Fp, x), M)),
            step(rf"F_y = N \Rightarrow h(y) = {tex(h)}", lambda F=Ffull, N=N: same(sp.diff(F, y), N)),
            vstep(rf"{sum_tex(Ffull)} = {tex(K)}", K, Ffull.subs({x: x0, y: y0})),
        ]
        Fbh = Fp + hb
        decoys = [
            decoy(1, rf"F = \int M\,dx = {sum_tex(Fpb)} + h(y)", lambda Fp=Fpb, M=M: same(sp.diff(Fp, x), M), ei, WHY[wi]),
            decoy(2, rf"F_y = N \Rightarrow h(y) = {tex(hb)}", lambda F=Fbh, N=N: same(sp.diff(F, y), N), "algebra", WHY["ex_h"]),
            vdecoy(3, rf"{sum_tex(Ffull)} = {tex(-K)}", -K, Ffull.subs({x: x0, y: y0}), "initial_condition", WHY["ex_c"]),
            decoy(0, rf"M_y = {tex(My)},\ N_x = {tex(sp.diff(N, x) / 2)}", lambda N=N, v=sp.diff(N, x) / 2: same(sp.diff(N, x), v), "algebra", WHY["ex_my"]),
        ]
        out.append({"params": {"family": fam, "M": str(M), "N": str(N), "y0": y0}, "tier": tier, "problem": prob,
                    "steps": steps, "decoys": decoys,
                    "verify": lambda M=M, N=N, F=Ffull: None if same(sp.diff(F, x), M) and same(sp.diff(F, y), N) else "퍼텐셜 확인 실패"})
    return out


# ---------------------------------------------------------------- 새 풀이 뼈대 (M3.6)
v = sp.Symbol("v")
XP = [sp.Rational(6, 5), sp.Rational(3, 2), sp.Rational(9, 5), sp.Rational(11, 5)]   # x > 1 쪽 표본점 (ln x, 1/x가 안전)

WHY.update({
    "bern_v": r"$v = y^{1-n}$입니다. 지수를 $n - 1$로 쓰면 $v$의 식이 선형이 되지 않습니다.",
    "bern_rhs": r"$v^{\prime} = (1 - n)y^{-n}y^{\prime}$이므로 우변에도 $(1 - n)$이 곱해집니다.",
    "bern_back": r"$v = y^{1-n}$이므로 $y = v^{1/(1-n)}$입니다. 거듭제곱을 거꾸로 했습니다.",
    "bern_c": r"$C$는 $v(0) = y_0^{\,1-n}$에서 정합니다. $y_0$를 그대로 넣으면 안 됩니다.",
    "if_recip": r"$\mu = e^{\int g\,dx}$입니다. $e^{-\int g\,dx}$로 쓰면 역수가 됩니다.",
    "if_ratio": r"$\dfrac{M_y - N_x}{N}$의 부호가 바뀌었습니다. 순서는 $M_y - N_x$입니다.",
    "if_c": r"초기조건 $(1, y_0)$를 $F$에 대입해 상수를 정합니다.",
    "if_h": r"$\int \mu M\,dx$만 쓰고 $h(y)$를 빠뜨렸습니다. $F_y = \mu N$으로 $h$를 정해야 합니다.",
    "hom_x": r"$y = vx$이면 $y^{\prime} = v + xv^{\prime}$입니다. $xv^{\prime}$의 $x$를 빠뜨렸습니다.",
    "hom_int": r"$v$에 대한 적분이 틀렸습니다. 양변을 미분해서 확인해 보세요.",
    "hom_c": r"$x = 1$이면 $\ln x = 0$이므로 $C$는 $v(1) = y_0$를 넣은 값입니다.",
    "hom_back": r"$v = \dfrac{y}{x}$이므로 마지막에 $x$를 곱해 $y = vx$로 되돌려야 합니다.",
})


def bernoulli_solve():
    """Bernoulli y' + Py = Qyⁿ 풀이: v = y^{1-n}로 선형화 → 적분인자 → 되돌리기. 가족: n = 2, 3, -1, 1/2."""
    out = []
    specs = []
    for P, Q, y0 in itertools.product([1, 2, -1, 3], [1, 2, -2], [1, 2, sp.Rational(1, 2)]):
        specs.append((2, P, Q, y0, 1))
    for P, Q, y0 in itertools.product([1, 2, 3], [1, 2], [1, 2]):
        specs.append((3, P, Q, y0, 2))
    for P, Q, y0 in itertools.product([1, 2, -1], [1, 2, 3], [1, 2, 3]):
        specs.append((-1, P, Q, y0, 2))
    for P, Q, y0 in itertools.product([2, 4, -2], [2, 4], [1, 4]):
        specs.append((sp.Rational(1, 2), P, Q, y0, 3))
    for n, P, Q, y0, tier in specs:
        k = 1 - sp.sympify(n)
        v0 = sp.Integer(y0) ** k if not isinstance(y0, sp.Rational) else y0 ** k
        Cv = sp.simplify(v0 - sp.Rational(Q, P))
        if Cv == 0:
            continue
        vsol = sp.Rational(Q, P) + Cv * sp.exp(-k * P * x)
        ytrue = sp.simplify(vsol ** (1 / k))
        res = lambda g, P=P, Q=Q, n=n: sp.diff(g, x) + P * g - Q * g**n
        if not same(res(ytrue), 0, SMALL) or not same(ytrue.subs(x, 0), y0):
            continue
        prob = rf"{join_terms([(1, P1), (P, 'y')])} = {tex(Q * y**n)},\quad y(0) = {tex(y0)}"
        steps = [
            step(rf"v = {tex(y**k)}", lambda k=k, n=n: same(k, 1 - n)),
            step(rf"v^{{\prime}} {_ptex(k * P)}v = {tex(k * Q)}", lambda yt=ytrue, k=k, P=P, Q=Q: same(sp.diff(yt**k, x) + k * P * yt**k, k * Q, SMALL)),
            step(rf"v = {tex(sp.Rational(Q, P))} + C{tex(sp.exp(-k * P * x))}", lambda rel=v - sp.Rational(Q, P) - C * sp.exp(-k * P * x), yt=ytrue, k=k: fit_c(rel.subs(v, yt**k))),
            vstep(rf"C = {tex(Cv)}", Cv, sp.simplify((ytrue**k).subs(x, 0) - sp.Rational(Q, P))),
            vstep(rf"y = {rf'\left({sum_tex(vsol)}\right)^{{2}}' if 1 / k == 2 else tex(ytrue)}", ytrue, ytrue, SMALL),
        ]
        decoys = [
            decoy(0, rf"v = {tex(y**(-k))}", lambda k=k, n=n: same(-k, 1 - n), "sign", WHY["bern_v"]),
            decoy(1, rf"v^{{\prime}} {_ptex(k * P)}v = {tex(Q)}", lambda yt=ytrue, k=k, P=P, Q=Q: same(sp.diff(yt**k, x) + k * P * yt**k, Q, SMALL), "missing_factor", WHY["bern_rhs"]),
        ]
        if sp.simplify(sp.Integer(y0) - sp.Rational(Q, P) - Cv) != 0:
            Cb = sp.simplify(y0 - sp.Rational(Q, P))
            decoys.append(vdecoy(3, rf"C = {tex(Cb)}", Cb, sp.simplify((ytrue**k).subs(x, 0) - sp.Rational(Q, P)), "initial_condition", WHY["bern_c"]))
        yb = sp.simplify(vsol ** k)
        if not same(yb, ytrue, SMALL):
            decoys.append(vdecoy(4, rf"y = {tex(yb)}", yb, ytrue, "algebra", WHY["bern_back"], SMALL))
        out.append({"params": {"n": str(n), "P": P, "Q": Q, "y0": str(y0), "family": f"n={n}"}, "tier": tier, "problem": prob,
                    "steps": steps, "decoys": decoys,
                    "verify": lambda yt=ytrue, res=res, y0=y0: None if same(res(yt), 0, SMALL) and same(yt.subs(x, 0), y0) else "해 확인 실패"})
    return out


def fit_c(e):
    """e(x; C) = 0 이 되는 상수 C가 있는지 (C는 하나)."""
    from checks import fit_constants
    return fit_constants(e, sp.Integer(0), [C], x, SMALL)


def integrating_factor_solve():
    """완전하지 않은 M dx + N dy = 0에 적분인자 μ를 곱해 완전하게 만들어 푼다.
    가족: μ = x · μ = x² · μ = eˣ · μ = 1/x² (모두 x만의 함수) · μ = y (y만의 함수)."""
    out = []
    specs = []
    for a, b, c in itertools.product([1, 2], [1, -1, 2], [0, 1]):
        F = a * x**2 * y + b * x**3 + c * x**2 * y**2
        specs.append(("mu_x", x, F, b * x**3 + a * x**2 * y + c * x**2 * y**2, 2))
    for a, b in itertools.product([1, 2, -1], [1, 2, -1]):
        F = a * x**3 * y + b * x**3 * y**2
        specs.append(("mu_x2", x**2, F, None, 3))
    for a, b, c in itertools.product([1, 2, -1], [1, 2], [0, 1]):
        F = sp.exp(x) * (a * y + b * y**2) + c * x
        specs.append(("mu_exp", sp.exp(x), F, None, 2))
    for b in [1, 2, -1, 3]:
        F = y / x + b * x
        specs.append(("mu_inv2", x**-2, F, None, 3))
    for a, b in itertools.product([1, 2, 3], [1, -1, 2]):
        F = a * x * y**2 + b * y**3
        specs.append(("mu_y", y, F, None, 3))
    for fam, mu, F, _, tier in specs:
        M, N = sp.expand(sp.diff(F, x) / mu), sp.expand(sp.diff(F, y) / mu)
        if not (M.is_polynomial(x, y) and N.is_polynomial(x, y)):
            continue
        My, Nx = sp.diff(M, y), sp.diff(N, x)
        if sp.simplify(My - Nx) == 0:
            continue
        byx = fam != "mu_y"
        g = sp.simplify((My - Nx) / N) if byx else sp.simplify((Nx - My) / M)
        var = x if byx else y
        if g.has(y if byx else x):
            continue
        for y0 in [1, 2, -1]:
            K = F.subs({x: 1, y: y0})
            Fp = sp.integrate(sp.expand(mu * M), x)
            h = sp.simplify(F - Fp)
            par = lambda e: rf"\left({sum_tex(e)}\right)" if len(sp.Add.make_args(e)) > 1 else tex(e) + r"\,"
            prob = rf"{par(M)}dx + {par(N)}dy = 0,\quad y(1) = {tex(y0)}"
            ratio_tx = (r"\frac{M_y - N_x}{N} = " if byx else r"\frac{N_x - M_y}{M} = ") + tex(g)
            steps = [
                step(rf"M_y = {tex(My)},\ N_x = {tex(Nx)}\ (\text{{완전 아님}})", lambda M=M, N=N, a=My, b=Nx: same(sp.diff(M, y), a) and same(sp.diff(N, x), b) and not same(a, b)),
                step(ratio_tx + rf" \Rightarrow \mu = {tex(mu)}", lambda mu=mu, M=M, N=N, g=g, var=var: same(sp.diff(mu, var) / mu, g) and same(sp.diff(mu * M, y), sp.diff(mu * N, x))),
                step(rf"F = \int \mu M\,dx = {sum_tex(Fp)} + h(y)" if h != 0 else rf"F = \int \mu M\,dx = {sum_tex(Fp)}",
                     lambda Fp=Fp, mu=mu, M=M: same(sp.diff(Fp, x), mu * M)),
                step(rf"{sum_tex(F)} = {tex(K)}", lambda F=F, mu=mu, M=M, N=N, K=K, y0=y0: same(sp.diff(F, x), mu * M) and same(sp.diff(F, y), mu * N) and same(F.subs({x: 1, y: y0}), K)),
            ]
            if h != 0:
                steps.insert(3, step(rf"F_y = \mu N \Rightarrow h(y) = {tex(h)}", lambda F=F, mu=mu, N=N: same(sp.diff(F, y), mu * N)))
            mub = 1 / mu
            decoys = [
                decoy(1, ratio_tx + rf" \Rightarrow \mu = {tex(mub)}", lambda mu=mub, M=M, N=N: same(sp.diff(mu * M, y), sp.diff(mu * N, x)), "sign", WHY["if_recip"]),
                decoy(len(steps) - 1, rf"{sum_tex(F)} = {tex(-K)}", lambda F=F, K=-K, y0=y0: same(F.subs({x: 1, y: y0}), K), "initial_condition", WHY["if_c"]),
            ]
            if h != 0:
                decoys.append(decoy(len(steps) - 1, rf"{sum_tex(Fp)} = {tex(Fp.subs({x: 1, y: y0}))}", lambda Fp=Fp, mu=mu, N=N: same(sp.diff(Fp, y), mu * N), "missing_factor", WHY["if_h"]))
            if g != 0:
                bad_ratio = (r"\frac{M_y - N_x}{N} = " if byx else r"\frac{N_x - M_y}{M} = ") + tex(-g)
                decoys.append(decoy(1, bad_ratio + rf" \Rightarrow \mu = {tex(mub)}", lambda: False, "sign", WHY["if_ratio"]))
            out.append({"params": {"family": fam, "F": str(F), "y0": y0}, "tier": tier, "problem": prob, "steps": steps, "decoys": decoys,
                        "verify": lambda F=F, mu=mu, M=M, N=N: None if same(sp.diff(F, x), mu * M) and same(sp.diff(F, y), mu * N) else "퍼텐셜 확인 실패"})
    return out


def homogeneous_sub():
    """동차형 y' = f(y/x): y = vx로 치환해 변수분리. 가족: f = v + a · v + kv² · v + k/v · v + ke^{-v}."""
    out = []
    lnx = sp.log(x)
    specs = []
    for a, y0 in itertools.product([1, 2, -1, 3], [0, 1, 2, -1]):
        specs.append(("lin", v + a, sp.Integer(a), v, a * lnx, y0, 1))      # x v' = a,  v = a ln x + C
    for k, y0 in itertools.product([1, 2, -1], [1, 2, -1, sp.Rational(1, 2)]):
        specs.append(("sq", v + k * v**2, k * v**2, -1 / v, k * lnx, y0, 2))
    for k, y0 in itertools.product([1, 2, 3], [2, 3, 4]):
        specs.append(("inv", v + k / v, k / v, v**2 / 2, k * lnx, y0, 2))
    for k, y0 in itertools.product([1, 2], [1, 2, 3]):
        specs.append(("expv", v + k * sp.exp(-v), k * sp.exp(-v), sp.exp(v), k * lnx, y0, 3))
    for fam, fv, g, H, R, y0, tier in specs:
        C0 = sp.simplify(H.subs(v, y0))
        sols = sp.solve(sp.Eq(H, R + C0), v)
        vt = None
        for cand in sols:
            if same(cand.subs(x, 1), y0) and same(x * sp.diff(cand, x), g.subs(v, cand), XP):
                vt = cand
                break
        if vt is None:
            continue
        yt = sp.simplify(x * vt)
        rhs = fv.subs(v, y / x)
        res = lambda h, rhs=rhs: sp.diff(h, x) - rhs.subs(y, h)
        if not same(res(yt), 0, XP):
            continue
        prob = rf"{P1} = {tex(sp.expand(rhs))},\quad y(1) = {tex(y0)}\ (x > 0)"
        Hb = {"lin": v / 2, "sq": 1 / v, "inv": v**2, "expv": -sp.exp(-v)}[fam]
        steps = [
            step(r"y = vx,\ y^{\prime} = v + xv^{\prime}", lambda: True),
            step(rf"xv^{{\prime}} = {tex(g)}", lambda vt=vt, g=g: same(x * sp.diff(vt, x), g.subs(v, vt), XP)),
            step(rf"{tex(H)} = {tex(R)} + C", lambda rel=H - R - C, vt=vt: fit_constants_x(rel.subs(v, vt))),
            vstep(rf"C = {tex(C0)}", C0, sp.simplify(H.subs(v, vt) - R).subs(x, 1)),
            vstep(rf"y = {tex(yt)}", yt, yt, XP),
        ]
        decoys = [
            decoy(1, rf"v^{{\prime}} = {tex(g)}", lambda vt=vt, g=g: same(sp.diff(vt, x), g.subs(v, vt), XP), "missing_factor", WHY["hom_x"]),
            decoy(2, rf"{tex(Hb)} = {tex(R)} + C", lambda rel=Hb - R - C, vt=vt: fit_constants_x(rel.subs(v, vt)), "algebra", WHY["hom_int"]),
            vdecoy(4, rf"y = {tex(vt)}", vt, yt, "missing_factor", WHY["hom_back"], XP),
        ]
        if not same(C0, y0):
            decoys.append(vdecoy(3, rf"C = {tex(y0)}", y0, sp.simplify(H.subs(v, vt) - R).subs(x, 1), "initial_condition", WHY["hom_c"]))
        out.append({"params": {"family": fam, "f": str(fv), "y0": str(y0)}, "tier": tier, "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda yt=yt, res=res, y0=y0: None if same(res(yt), 0, XP) and same(yt.subs(x, 1), y0) else "해 확인 실패"})
    return out


def fit_constants_x(e):
    from checks import fit_constants
    return fit_constants(e, sp.Integer(0), [C], x, XP)
