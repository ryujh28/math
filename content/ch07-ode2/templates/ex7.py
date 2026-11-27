"""7장 문제별 해설."""
import sympy as sp
from exkit import tex, m, dm, p, x, r
from fx7 import VP

C1, C2 = sp.symbols("C_1 C_2")


def _roots(pp, q):
    return sp.roots(sp.Poly(r**2 + pp * r + q, r))


def form(P, it):
    pp, q = P["p"], P["q"]
    rt = _roots(pp, q)
    ch = sp.Poly(r**2 + pp * r + q, r).as_expr()
    ks = list(rt)
    if len(ks) == 2 and all(k.is_real for k in ks):
        rule = r"\text{서로 다른 실근 } r_1, r_2 \Rightarrow y = C_1e^{r_1x} + C_2e^{r_2x}"
    elif len(ks) == 1:
        rule = r"\text{중근 } r \Rightarrow y = (C_1 + C_2x)e^{rx}"
    else:
        rule = r"\text{복소근 } \alpha \pm i\beta \Rightarrow y = e^{\alpha x}(C_1\cos\beta x + C_2\sin\beta x)"
    return [f"특성방정식 {m(tex(ch) + ' = 0')} → {m('r = ' + r',\ '.join(tex(k) for k in ks))}", f"{m(rule)}"], []


def trial(P, it):
    pp, q, R = P["p"], P["q"], str(P["R"])
    rt = _roots(pp, q)
    if R.startswith("exp"):
        a = sp.Integer(R[3:])
        res = a in rt
        lines = [f"강제항 {m('3e^{' + tex(a * x) + '}')} → 기본 꼴 {m('Ae^{' + tex(a * x) + '}')}",
                 f"특성근 {m(r',\ '.join(tex(k) for k in rt))}"]
        lines.append(f"특성근에 {m(tex(a))} 포함 → 기본 꼴이 동차해와 겹친다(공명). {m('x')}를 곱해 {m('Axe^{' + tex(a * x) + '}')}"
                     if res else f"특성근에 {m(tex(a))} 없음 → 기본 꼴 그대로 {m('Ae^{' + tex(a * x) + '}')}")
        return lines, []
    b = sp.Integer(R[3:])
    return [f"강제항 {m(r'2\cos ' + tex(b * x))} → 미분하면 {m(r'\sin')}이 섞이므로 두 항이 다 필요하다",
            f"{m(r'y_p = A\cos ' + tex(b * x) + r' + B\sin ' + tex(b * x))} (특성근에 {m(r'\pm ' + (tex(b) if b != 1 else '') + 'i')} 없음 → 공명 없음)"], []


def wronskian(P, it):
    a, b = P["a"], P["b"]
    f1, f2 = sp.exp(a * x), sp.exp(b * x)
    W = sp.simplify(f1 * sp.diff(f2, x) - sp.diff(f1, x) * f2)
    return [f"{m(r"W = y_1y_2' - y_1'y_2")}",
            dm(r"W = " + tex(f1) + r"\cdot " + p(sp.diff(f2, x)) + " - " + p(sp.diff(f1, x)) + r"\cdot " + tex(f2)
               + " = (" + tex(b) + " - " + p(a) + ")e^{" + tex((a + b) * x) + "} = " + tex(W))], [(W, sp.wronskian([f1, f2], x))]


def eulerform(P, it):
    a, b = P["a"], P["b"]
    ch = sp.expand(r * (r - 1) + a * r + b)
    lines = [f"{m('y = x^{r}')}: {m(r"x^{2}y'' = r(r - 1)x^{r}")}, {m(r"xy' = rx^{r}")}",
             f"{m('r(r - 1) + ' + p(a) + 'r + ' + p(b) + ' = ' + tex(sp.Poly(ch, r).as_expr()) + ' = 0')}"]
    if "일반해" in it["prompt"]:
        rt = sorted(sp.solve(ch, r))
        lines.append(f"{m(tex(sp.factor(ch)) + ' = 0')} → {m('r = ' + r',\ '.join(tex(k) for k in rt))} → {m('y = C_1x^{' + tex(rt[0]) + '} + C_2x^{' + tex(rt[1]) + '}')}")
    return lines, []


def reduction(P, it):
    if "m" in P:
        mm = P["m"]
        if "x^{2}" in it["prompt"]:
            return [f"Euler–Cauchy 특성방정식이 중근 {m('r = ' + tex(mm))}을 가진다.",
                    f"이때 두 번째 해는 {m(r'\ln x')}가 곱해진 {m('x^{' + tex(mm) + r'}\ln x')} ({m(r"v' = e^{-\int p\,dx}/y_1^{2}")}을 계산하면 {m(r"v' = 1/x")}, {m(r'v = \ln x')})."], []
        return [f"특성방정식이 중근 {m('r = ' + tex(mm))}을 가진다 ({m('(r - ' + p(mm) + ')^{2} = 0')}).",
                f"{m('y_2 = vy_1')}로 놓으면 {m(r"v'' = 0")}, {m('v = x')} → {m('y_2 = xe^{' + tex(mm * x) + '}')}"], []
    return [f"{m('y_2 = vy_1')}로 놓으면 {m(r"v' = \frac{e^{-\int p\,dx}}{y_1^{2}}")} ({m('p')}는 {m(r"y''")} 계수를 1로 만든 뒤의 {m(r"y'")} 계수).",
            "이를 적분해 $v$를 얻고 $y_2 = vy_1$. 정답 보기를 방정식에 넣으면 $0$이 되고 $y_1$과 비례하지 않는다."], []


def superpos(P, it):
    r1, r2 = P["r"]
    return [f"비동차 해 = 동차해 전체 + 특수해 하나: {m('y = C_1y_1 + C_2y_2 + y_p')}",
            f"동차 부분은 특성근 {m(tex(r1) + r',\ ' + tex(r2))}에서 {m('C_1e^{' + tex(r1 * x) + '} + C_2e^{' + tex(r2 * x) + '}')}",
            "상수 하나만 있거나 $y_p$가 빠진 것은 일반해가 아니다."], []


def varparam(P, it):
    et = str(P["eq"])
    _, y1, y2, R = next(v for v in VP if v[0] == et)
    W = sp.simplify(y1 * sp.diff(y2, x) - y2 * sp.diff(y1, x))
    u1p, u2p = sp.simplify(-y2 * R / W), sp.simplify(y1 * R / W)
    q = str(P["q"])
    lines = [f"{m(r"W = y_1y_2' - y_1'y_2 = " + tex(W))}"]
    if q == "W":
        return lines, []
    lines.append(f"{m(r"u_1' = -\frac{y_2R}{W} = " + tex(u1p))}, {m(r"u_2' = \frac{y_1R}{W} = " + tex(u2p))}")
    if q == "u1":
        return lines, []
    u1, u2 = sp.integrate(u1p, x), sp.integrate(u2p, x)
    lines.append(f"적분: {m('u_1 = ' + tex(u1))}, {m('u_2 = ' + tex(u2))}")
    lines.append(f"{m('y_p = u_1y_1 + u_2y_2 = ' + tex(sp.simplify(u1 * y1 + u2 * y2)))}")
    return lines, [(sp.diff(u1, x), u1p)]


EXPLAIN = {"ode2.form": form, "ode2.trial": trial, "ode2.wronskian": wronskian, "ode2.eulerform": eulerform,
           "ode2.reduction": reduction, "ode2.superpos": superpos, "ode2.varparam": varparam}
