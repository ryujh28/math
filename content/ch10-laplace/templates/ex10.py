"""10장 변환 정리 문제별 해설."""
import sympy as sp
from exkit import tex, m, dm, p, t, s
from texkit import join_terms
from fx10 import BASE, CONV

FT = {ft: f for ft, f in BASE}
LT = lambda f: sp.simplify(sp.laplace_transform(f, t, s, noconds=True))  # noqa: E731
F_ = lambda e: tex(sp.factor(sp.cancel(sp.together(e))))  # noqa: E731


def deriv1(P, it):
    if "y0" in P:
        y0 = P["y0"]
        return [f"{m(r"\mathcal{L}\{y'\} = sY - y(0)")}", f"{m('y(0) = ' + tex(y0))} → {m('sY - ' + p(y0))}"], []
    ft = str(P["f"])
    f = FT[ft]
    F, f0 = LT(f), f.subs(t, 0)
    return [f"{m(r"\mathcal{L}\{f'\} = sF(s) - f(0)")}",
            f"{m(r'F(s) = \mathcal{L}\{' + ft + r'\} = ' + tex(F))}, {m('f(0) = ' + tex(f0))}",
            f"{m(r's\cdot ' + p(F) + ' - ' + p(f0) + ' = ' + F_(s * F - f0))}"], [(s * F - f0, LT(sp.diff(f, t)))]


def deriv2(P, it):
    if "y0" in P:
        y0, v0 = P["y0"], P["v0"]
        return [f"{m(r"\mathcal{L}\{y''\} = s^{2}Y - sy(0) - y'(0)")}", f"{m('y(0) = ' + tex(y0))}, {m(r"y'(0) = " + tex(v0))}를 넣는다. 두 초기값 항 모두 빼기."], []
    ft = str(P["f"])
    f = FT[ft]
    F, f0, f1 = LT(f), f.subs(t, 0), sp.diff(f, t).subs(t, 0)
    val = s**2 * F - s * f0 - f1
    return [f"{m(r"\mathcal{L}\{f''\} = s^{2}F - sf(0) - f'(0)")}",
            f"{m('F = ' + tex(F))}, {m('f(0) = ' + tex(f0))}, {m(r"f'(0) = " + tex(f1))}",
            f"{m('= ' + F_(val))}"], [(val, LT(sp.diff(f, t, 2)))]


def sshift(P, it):
    ft, a = str(P["f"]), P["a"]
    f = FT[ft]
    F = LT(f)
    return [f"{m(r'\mathcal{L}\{e^{at}f(t)\} = F(s - a)')}: {m('s')}를 {m('s - ' + p(a))}로 바꾼다.",
            f"{m(r'\mathcal{L}\{' + ft + r'\} = ' + tex(F))} → {m(F_(F.subs(s, s - a)))}"], [(F.subs(s, s - a), LT(sp.exp(a * t) * f))]


def tshift(P, it):
    c = P["c"]
    if "trap" in P:
        return [f"{m(r'\mathcal{L}\{u(t - c)g(t - c)\} = e^{-cs}G(s)')}이려면 {m('t - c')}의 함수로 써야 한다.",
                f"{m('t = (t - ' + tex(c) + ') + ' + tex(c))} → {m(r'e^{-' + tex(c) + r's}\left(\frac{1}{s^{2}} + \frac{' + tex(c) + r'}{s}\right)')}"], []
    g = P["g"]
    G = LT(g)
    return [f"{m(r'\mathcal{L}\{u(t - c)g(t - c)\} = e^{-cs}G(s)')}, {m('c = ' + tex(c))}",
            f"{m(r'G(s) = \mathcal{L}\{' + tex(g) + r'\} = ' + tex(G))} → {m('e^{-' + tex(c) + 's}')}을 곱한다."], []


def conv(P, it):
    ft, gt = str(P["f"]), str(P["g"])
    f, g = next((a, c) for at, a, ct, c in CONV if at == ft and ct == gt)
    F, G = LT(f), LT(g)
    return [f"합성곱 정리: {m(r'\mathcal{L}\{f * g\} = F(s)G(s)')}",
            f"{m('F = ' + tex(F))}, {m('G = ' + tex(G))} → {m(F_(F * G))}"], []


def tmult(P, it):
    ft = str(P["f"])
    f = FT[ft]
    F = LT(f)
    return [f"{m(r'\mathcal{L}\{tf(t)\} = -F^{\prime}(s)')}",
            f"{m('F = ' + tex(F))}, {m(r"F'(s) = " + F_(sp.diff(F, s)))} → {m(F_(-sp.diff(F, s)))}"], [(-sp.diff(F, s), LT(t * f))]


def integral(P, it):
    ft = str(P["f"])
    f = FT[ft]
    F = LT(f)
    return [f"{m(r'\mathcal{L}\left\{\int_0^t f(\tau)\,d\tau\right\} = \frac{F(s)}{s}')}",
            f"{m('F = ' + tex(F))} → {m(F_(F / s))}"], []


def csqinv(P, it):
    al, be, A, B, mm = P["alpha"], P["beta"], P["A"], P["B"], P["m"]
    num = sp.expand(A * (s - al) + B * be)
    den = sp.expand((s - al) ** 2 + be**2)
    As, Bs = sp.Rational(A, mm), sp.Rational(B, mm)
    sh = tex(s - al)
    lines = []
    if mm != 1:
        lines.append(f"분모의 {m('s^{2}')} 계수 {m(tex(mm))}로 분자·분모를 나눈다.")
    sq = f"({sh})^{{2}} + {tex(be**2)}" if al else f"s^{{2}} + {tex(be**2)}"
    lines.append(f"완전제곱: {m(tex(den) + ' = ' + sq)}")
    if al and A and B:
        lines.append(f"분자를 {m(sh)} 꼴로 다시 쓴다: {m(tex(num) + ' = ' + join_terms([(A, '(' + sh + ')'), (B * be, '')]))}")
    f = sp.exp(al * t) * (As * sp.cos(be * t) + Bs * sp.sin(be * t))
    if B and be != 1:
        lines.append(f"사인 항은 분자에 {m(tex(be))}가 있어야 하므로 {m(tex(be))}로 나눠 맞춘다.")
    from fx10 import _damped_tex
    lines.append(f"따라서 {m('f(t) = ' + _damped_tex(al, As, Bs, be))}")
    return lines, [(LT(f), num / (mm * den))]


EXPLAIN = {"lap.csqinv": csqinv, "lap.deriv1": deriv1, "lap.deriv2": deriv2, "lap.sshift": sshift, "lap.tshift": tshift, "lap.conv": conv,
           "lap.tmult": tmult, "lap.integral": integral}
