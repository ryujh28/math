"""10장 새 풀이 뼈대 (M3.6): 합성곱으로 풀기 · 연립 ODE · 적분방정식.

판정 함수(ok)는 SymPy로 따로 계산한 참값과 비교한다. 빌드는 정답 단계는 참, 오답 블록은 거짓인지 확인한다.
"""
import itertools
import sympy as sp
from texkit import tex, join_terms, sum_tex
from checks import same, step, decoy
from lapkit import F as frac

t, s = sp.symbols("t s")
tau = sp.Symbol("tau", positive=True)
X, Yv = sp.symbols("X Y")

WHY = {
    "cv_H": r"$H(s)$는 입력을 뺀 방정식의 역수입니다. $s^2 + \omega^2$의 부호를 바꾸면 쌍곡함수가 됩니다.",
    "cv_h": r"$\dfrac{1}{s^2 + \omega^2}$의 역변환은 $\dfrac{1}{\omega}\sin\omega t$입니다. $\dfrac{1}{\omega}$이 빠졌습니다.",
    "cv_int": r"합성곱은 $\int_0^t h(t - \tau)f(\tau)\,d\tau$입니다. $h$의 인수가 $t - \tau$여야 합니다.",
    "cv_res": r"적분 계산이 틀렸습니다. 결과를 방정식에 넣어 확인해 보세요.",
    "sy_ic": r"$\mathcal{L}\{x^{\prime}\} = sX - x(0)$입니다. 초기값의 부호가 틀렸습니다.",
    "sy_cr": r"Cramer 공식의 분자는 해당 열을 우변으로 바꾼 행렬식입니다. 분자를 잘못 만들었습니다.",
    "sy_pf": r"부분분수 계수의 부호가 틀렸습니다. 통분하면 원래 분자와 달라집니다.",
    "sy_exp": r"$\dfrac{1}{s - r} \leftrightarrow e^{rt}$: 지수의 부호는 극점과 같습니다.",
    "vo_K": r"합성곱 $\int_0^t k(t - \tau)y(\tau)\,d\tau$의 변환은 $K(s)Y(s)$입니다.",
    "vo_solve": r"$Y = F + \lambda KY$를 $Y$로 정리하면 $Y = \dfrac{F}{1 - \lambda K}$입니다. 부호가 틀렸습니다.",
    "vo_pf": r"부분분수 계수의 부호가 틀렸습니다.",
    "vo_back": r"역변환이 틀렸습니다. 지수의 부호와 계수를 확인하세요.",
}


U = sp.Symbol("U")


def shifted_tex(h):
    """h(t − τ)의 TeX: e^{-(t - τ)}, \\sin (t - τ) 꼴."""
    tx = tex(h.subs(t, U))
    tx = tx.replace("- U", "-(t - \\tau)").replace("U", "(t - \\tau)")
    return tx


def LT(e):
    return sp.simplify(sp.laplace_transform(e, t, s, noconds=True))


def ILT(e):
    out = 0
    for term in sp.Add.make_args(sp.apart(sp.together(e), s)):
        out += sp.inverse_laplace_transform(term, s, t).subs(sp.Heaviside(t), 1)
    return sp.expand(out)


# ---------------------------------------------------------------- 합성곱으로 풀기
def conv_solve():
    """정지 상태의 계에 입력 f(t): Y = H(s)F(s) → h(t) → y = (h * f)(t).
    가족: 1계 y' + ay · 진동자 y'' + ω²y · 과감쇠 y'' + 3y' + 2y."""
    out = []
    specs = []
    for a in [1, 2, 3]:
        for fname, ft in [("1", sp.Integer(1)), ("t", t), ("t2", t**2), ("exp", sp.exp(-(a + 1) * t)), ("sin", sp.sin(t)), ("cos", sp.cos(t))]:
            specs.append(("first", [a], sp.exp(-a * t), ft, 1 if fname in ("1", "t") else 2,
                          (1 / (s - a), sp.exp(a * t), rf"\frac{{1}}{{s - {a}}}", tex(sp.exp(a * t)))))
    for w in [1, 2, 3]:
        for fname, ft in [("1", sp.Integer(1)), ("t", t), ("t2", t**2), ("exp", sp.exp(-t)), ("sin", sp.sin((w + 1) * t)), ("cos", sp.cos((w + 1) * t))]:
            specs.append(("osc", [0, w * w], sp.sin(w * t) / w, ft, 2 if fname in ("1", "t") else 3,
                          (1 / (s**2 - w * w), sp.sinh(w * t) / w, rf"\frac{{1}}{{s^{{2}} - {w * w}}}", tex(sp.sinh(w * t) / w))))
    for fname, ft in [("1", sp.Integer(1)), ("t", t), ("exp", sp.exp(-3 * t)), ("exp2", sp.exp(t))]:
        specs.append(("over", [3, 2], sp.exp(-t) - sp.exp(-2 * t), ft, 3,
                      (1 / (s**2 - 3 * s + 2), sp.exp(2 * t) - sp.exp(t), r"\frac{1}{s^{2} - 3s + 2}", tex(sp.exp(2 * t) - sp.exp(t)))))
    for fam, co, h, ft, tier, (Hb, hb, Hbt, hbt) in specs:
        order = len(co)
        den = s + co[0] if order == 1 else s**2 + co[0] * s + co[1]
        H = 1 / den
        if not same(LT(h), H):
            continue
        Fs = LT(ft)
        y = sp.simplify(sp.integrate(h.subs(t, t - tau) * ft.subs(t, tau), (tau, 0, t)))
        y = sp.expand(y)
        Lop = (lambda g, a=co[0]: sp.diff(g, t) + a * g) if order == 1 else (lambda g, p=co[0], q=co[1]: sp.diff(g, t, 2) + p * sp.diff(g, t) + q * g)
        if not same(Lop(y), ft) or not same(y.subs(t, 0), 0):
            continue
        lhs = join_terms([(1, r"y^{\prime}"), (co[0], "y")]) if order == 1 else join_terms([(1, r"y^{\prime\prime}"), (co[0], r"y^{\prime}"), (co[1], "y")])
        ics = "y(0) = 0" if order == 1 else r"y(0) = y^{\prime}(0) = 0"
        prob = rf"{lhs} = {tex(ft)},\quad {ics}\ \text{{를 합성곱으로}}"
        Ht = frac(H)
        integrand = sp.simplify(h.subs(t, t - tau) * ft.subs(t, tau))
        ht = shifted_tex(h)
        if len(sp.Add.make_args(h)) > 1:
            ht = rf"\left({ht}\right)"
        itx = ht if ft == 1 else rf"{ht}\,{tex(ft.subs(t, tau)) if len(sp.Add.make_args(ft)) == 1 else rf'\left({tex(ft.subs(t, tau))}\right)'}"
        steps = [
            step(rf"Y = H(s)F(s),\ H(s) = {Ht}", lambda H=H, y=y, Fs=Fs: same(LT(y), H * Fs)),
            step(rf"h(t) = {tex(h)}", lambda h=h, H=H: same(LT(h), H)),
            step(rf"y = \int_0^t {itx}\,d\tau", lambda I=integrand, y=y: same(sp.integrate(I, (tau, 0, t)), y)),
            step(rf"y = {sum_tex(y)}", lambda y=y, Lop=Lop, ft=ft: same(Lop(y), ft) and same(y.subs(t, 0), 0)),
        ]
        bad_int = sp.simplify(h.subs(t, tau) * ft.subs(t, tau))
        decoys = [
            decoy(0, rf"Y = H(s)F(s),\ H(s) = {Hbt}", lambda Hb=Hb, H=H: same(Hb, H), "sign", WHY["cv_H"]),
            decoy(2, rf"y = \int_0^t {tex(bad_int)}\,d\tau", lambda I=bad_int, y=y: same(sp.integrate(I, (tau, 0, t)), y), "algebra", WHY["cv_int"]),
            decoy(3, rf"y = {sum_tex(-y)}", lambda y=-y, Lop=Lop, ft=ft: same(Lop(y), ft), "sign", WHY["cv_res"]),
        ]
        if fam == "osc" and co[1] != 1:
            w = sp.sqrt(co[1])
            decoys.append(decoy(1, rf"h(t) = {tex(sp.sin(w * t))}", lambda h=sp.sin(w * t), H=H: same(LT(h), H), "missing_factor", WHY["cv_h"]))
        out.append({"params": {"family": fam, "co": co, "f": str(ft)}, "tier": tier, "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda y=y, Lop=Lop, ft=ft: None if same(Lop(y), ft) else "해 확인 실패"})
    return out


# ---------------------------------------------------------------- 연립 ODE
def system_solve():
    """x' = ax + by + f₁, y' = cx + dy + f₂를 Laplace로. 가족: 서로 다른 실근 · 회전(복소근, 감쇠 없음) · 삼각(한 식이 따로 풀림) · 상수 입력."""
    out = []
    specs = []
    for A, fam, tier in [([[1, 2], [2, 1]], "real", 2), ([[2, 1], [1, 2]], "real", 2), ([[-2, 1], [1, -2]], "real", 2), ([[0, 1], [2, 1]], "real", 2),
                         ([[-3, 1], [2, -2]], "real", 2), ([[0, 1], [-1, 0]], "rot", 2), ([[0, 2], [-2, 0]], "rot", 2), ([[0, -1], [4, 0]], "rot", 3),
                         ([[-1, 1], [0, -2]], "tri", 1), ([[1, 2], [0, -1]], "tri", 1), ([[-2, 0], [1, -1]], "tri", 1), ([[2, 1], [0, 1]], "tri", 1)]:
        for x0, y0 in [(1, 0), (0, 1), (1, 1), (2, -1)]:
            specs.append((fam, A, (0, 0), (x0, y0), tier))
    for A, f in [([[-1, 0], [1, -2]], (1, 0)), ([[-2, 1], [0, -1]], (0, 2)), ([[-1, 1], [0, -2]], (2, 0)), ([[-3, 1], [2, -2]], (4, 0))]:
        for x0, y0 in [(0, 0), (1, 0)]:
            specs.append(("forced", A, f, (x0, y0), 3))
    for fam, A, (f1, f2), (x0, y0), tier in specs:
        (a, b), (c, d) = A
        F1, F2 = (sp.Integer(f1) / s if f1 else 0), (sp.Integer(f2) / s if f2 else 0)
        sol = sp.solve([s * X - x0 - a * X - b * Yv - F1, s * Yv - y0 - c * X - d * Yv - F2], [X, Yv], dict=True)[0]
        Xs, Ys = sp.factor(sol[X]), sp.factor(sol[Yv])
        xt, yt = ILT(Xs), ILT(Ys)
        ok_sys = lambda xt, yt, a=a, b=b, c=c, d=d, f1=f1, f2=f2, x0=x0, y0=y0: (
            same(sp.diff(xt, t), a * xt + b * yt + f1) and same(sp.diff(yt, t), c * xt + d * yt + f2) and same(xt.subs(t, 0), x0) and same(yt.subs(t, 0), y0))
        if not ok_sys(xt, yt) or xt == 0 or yt == 0:
            continue
        rhs1 = join_terms([(a, "x"), (b, "y"), (f1, "")]) or "0"
        rhs2 = join_terms([(c, "x"), (d, "y"), (f2, "")]) or "0"
        prob = rf"x^{{\prime}} = {rhs1},\ y^{{\prime}} = {rhs2},\quad x(0) = {x0},\ y(0) = {y0}"
        e1 = join_terms([(1, "sX"), (-x0, "")]) + " = " + (join_terms([(a, "X"), (b, "Y")]) + (f" + {frac(F1)}" if f1 else "") or "0")
        e2 = join_terms([(1, "sY"), (-y0, "")]) + " = " + (join_terms([(c, "X"), (d, "Y")]) + (f" + {frac(F2)}" if f2 else "") or "0")
        e1b = join_terms([(1, "sX"), (x0, "")]) + " = " + (join_terms([(a, "X"), (b, "Y")]) + (f" + {frac(F1)}" if f1 else "") or "0")
        e2b = join_terms([(1, "sY"), (y0, "")]) + " = " + (join_terms([(c, "X"), (d, "Y")]) + (f" + {frac(F2)}" if f2 else "") or "0")
        chk_eq = lambda xs, ys, x0_, y0_, a=a, b=b, c=c, d=d, F1=F1, F2=F2, Xs=Xs, Ys=Ys: same(s * Xs - x0_ - a * Xs - b * Ys - F1, 0) and same(s * Ys - y0_ - c * Xs - d * Ys - F2, 0)
        pfx = sp.apart(Xs, s)
        steps = [
            step(rf"{e1},\ \ {e2}", lambda chk=chk_eq, x0=x0, y0=y0: chk(None, None, x0, y0)),
            step(rf"X = {frac(Xs)},\ Y = {frac(Ys)}", lambda Xs=Xs, Ys=Ys, xt=xt, yt=yt: same(LT(xt), Xs) and same(LT(yt), Ys)),
            step(rf"X = {sum_tex(pfx)}", lambda pf=pfx, Xs=Xs: same(pf, Xs)),
            step(rf"x(t) = {sum_tex(xt)},\ y(t) = {sum_tex(yt)}", lambda xt=xt, yt=yt, ok=ok_sys: ok(xt, yt)),
        ]
        if sum_tex(pfx).replace(" ", "") == frac(Xs).replace(" ", ""):
            steps.pop(2)
        decoys = []
        if x0 or y0:
            decoys.append(decoy(0, rf"{e1b},\ \ {e2b}", lambda chk=chk_eq, x0=x0, y0=y0: chk(None, None, -x0, -y0), "sign", WHY["sy_ic"]))
        bX = sp.factor(sp.solve([s * X - x0 - d * X - b * Yv - F1, s * Yv - y0 - c * X - a * Yv - F2], [X, Yv], dict=True)[0][X])
        if not same(bX, Xs):
            decoys.append(decoy(1, rf"X = {frac(bX)},\ Y = {frac(Ys)}", lambda bX=bX, Xs=Xs: same(bX, Xs), "algebra", WHY["sy_cr"]))
        terms = sp.Add.make_args(pfx)
        if len(terms) >= 2 and len(steps) == 4:
            bad = pfx - 2 * terms[-1]
            decoys.append(decoy(2, rf"X = {sum_tex(bad)}", lambda b=bad, Xs=Xs: same(b, Xs), "sign", WHY["sy_pf"]))
        flip = lambda g: g.replace(sp.exp, lambda q: sp.exp(-q))
        if xt.has(sp.exp) and not same(flip(xt), xt):
            decoys.append(decoy(len(steps) - 1, rf"x(t) = {sum_tex(flip(xt))},\ y(t) = {sum_tex(flip(yt))}", lambda xt=flip(xt), yt=flip(yt), ok=ok_sys: ok(xt, yt), "sign", WHY["sy_exp"]))
        elif fam == "rot":
            sw = lambda g: g.subs({sp.sin: None}) if False else g.replace(sp.sin, lambda q: sp.Function("SWAP")(q)).replace(sp.cos, sp.sin).replace(sp.Function("SWAP"), sp.cos)
            decoys.append(decoy(len(steps) - 1, rf"x(t) = {sum_tex(sw(xt))},\ y(t) = {sum_tex(sw(yt))}", lambda xt=sw(xt), yt=sw(yt), ok=ok_sys: ok(xt, yt), "wrong_pair", r"$\dfrac{s}{s^2 + \omega^2} \leftrightarrow \cos\omega t$, $\dfrac{\omega}{s^2 + \omega^2} \leftrightarrow \sin\omega t$입니다. 둘을 바꿨습니다."))
        out.append({"params": {"family": fam, "A": A, "f": [f1, f2], "ics": [x0, y0]}, "tier": tier, "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda xt=xt, yt=yt, ok=ok_sys: None if ok(xt, yt) else "해 확인 실패"})
    return out


# ---------------------------------------------------------------- 적분방정식
def volterra_solve():
    """y(t) = f(t) + λ∫₀ᵗ k(t − τ)y(τ)dτ. 합성곱 정리로 Y = F + λKY.
    가족: k = 1 · k = e^{-(t-τ)} · k = t − τ · k = sin(t − τ)."""
    out = []
    specs = []
    for lam, (fname, ft) in itertools.product([1, -1, 2, 3], [("1", sp.Integer(1)), ("t", t), ("exp", sp.exp(-t))]):
        specs.append(("k1", sp.Integer(1), lam, ft, 1))
    for lam, (fname, ft) in itertools.product([1, 2, -2], [("1", sp.Integer(1)), ("t", t), ("exp", sp.exp(t))]):
        specs.append(("kexp", sp.exp(-t), lam, ft, 2))
    for lam, (fname, ft) in itertools.product([1, -1, 4, -4], [("1", sp.Integer(1)), ("t", t)]):
        specs.append(("klin", t, lam, ft, 3))
    for lam, (fname, ft) in itertools.product([1, -1], [("1", sp.Integer(1)), ("t", t), ("sin", sp.sin(t))]):
        specs.append(("ksin", sp.sin(t), lam, ft, 3))
    for fam, k, lam, ft, tier in specs:
        Fs, Ks = LT(ft), LT(k)
        Ys = sp.factor(sp.cancel(Fs / (1 - lam * Ks)))
        yt = ILT(Ys)
        resid = lambda y, k=k, lam=lam, ft=ft: sp.simplify(y - ft - lam * sp.integrate(k.subs(t, t - tau) * y.subs(t, tau), (tau, 0, t)))
        if not same(resid(yt), 0):
            continue
        kt = shifted_tex(k)
        if k == t:
            kt = r"(t - \tau)"
        integ = r"\int_0^t y(\tau)\,d\tau" if k == 1 else rf"\int_0^t {kt}\,y(\tau)\,d\tau"
        coef = "" if lam == 1 else ("-" if lam == -1 else tex(lam))
        sign = "+" if lam > 0 else "-"
        coef = "" if abs(lam) == 1 else tex(abs(lam))
        prob = rf"y(t) = {tex(ft)} {sign} {coef}{integ}"
        pf = sp.apart(Ys, s)
        steps = [
            step(rf"Y = {frac(Fs)} {sign} {coef}{frac(Ks)}\,Y", lambda Fs=Fs, Ks=Ks, lam=lam, Ys=Ys: same(Ys - Fs - lam * Ks * Ys, 0)),
            step(rf"Y = {frac(Ys)}", lambda Ys=Ys, yt=yt: same(LT(yt), Ys)),
            step(rf"Y = {sum_tex(pf)}", lambda pf=pf, Ys=Ys: same(pf, Ys)),
            step(rf"y = {sum_tex(yt)}", lambda yt=yt, r=resid: same(r(yt), 0)),
        ]
        if sum_tex(pf).replace(" ", "") == frac(Ys).replace(" ", ""):
            steps.pop(2)
        Yb = sp.factor(sp.cancel(Fs / (1 + lam * Ks)))
        decoys = [
            decoy(0, rf"Y = {frac(Fs)} {sign} {coef}{tex(k)}\,Y" if k != 1 else rf"Y = {frac(Fs)} {sign} {coef}Y", lambda: False, "wrong_pair", WHY["vo_K"]),
            decoy(1, rf"Y = {frac(Yb)}", lambda Yb=Yb, Ys=Ys: same(Yb, Ys), "sign", WHY["vo_solve"]),
        ]
        flip = lambda g: g.replace(sp.exp, lambda q: sp.exp(-q))
        if yt.has(sp.exp) and not same(flip(yt), yt):
            decoys.append(decoy(len(steps) - 1, rf"y = {sum_tex(flip(yt))}", lambda y=flip(yt), r=resid: same(r(y), 0), "sign", WHY["vo_back"]))
        terms = sp.Add.make_args(pf)
        if len(terms) >= 2 and len(steps) == 4:
            bad = pf - 2 * terms[-1]
            decoys.append(decoy(2, rf"Y = {sum_tex(bad)}", lambda b=bad, Ys=Ys: same(b, Ys), "sign", WHY["vo_pf"]))
        out.append({"params": {"family": fam, "lam": lam, "f": str(ft)}, "tier": tier, "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda yt=yt, r=resid: None if same(r(yt), 0) else "해 확인 실패"})
    return out
