"""9장 문제별 해설."""
import sympy as sp
from exkit import tex, m, dm, x
from ser9 import _families, _coeffs, _sing_kind, _roots_desc, _indicial, _taylor_truth, _taylor_cases, FORMS, _case_of, r_

KIND_TXT = {"reg": "정칙특이점", "irr": "비정칙특이점"}


def shift(P, it):
    d, mm = int(P["d"]), int(P["m"])
    p = mm - d
    return [f"{m('k = n + ' + tex(p) if p > 0 else 'k = n - ' + tex(-p))}로 놓으면 {m('n = k ' + ('- ' + tex(p) if p > 0 else '+ ' + tex(-p)))}",
            f"계수의 {m('n')}도 {m('k ' + ('- ' + tex(p) if p > 0 else '+ ' + tex(-p)))}로, 시작은 {m('n = ' + str(d))} → {m('k = ' + str(d + p))}"], []


def _fam(it):
    fam, key = it["params"]["family"], it["params"]["key"]
    for F in _families():
        if F["fam"] == fam and str(F["key"]) == key:
            return F
    return None


def recur(P, it):
    F = _fam(it)
    if F is None:
        return []
    a = _coeffs(F["rec"])
    return [f"대입하고 지수를 맞추면 {m(F['start'] + r'\left[' + F['br_tex'] + r'\right]x^n = 0')}",
            f"대괄호 {m('= 0')}을 {m('a_{n+2}')}에 대해 풀면 {m(F['rec_tex'])}",
            f"확인: {m('a_2 = ' + tex(sp.expand(a[2])) + r',\ a_3 = ' + tex(sp.expand(a[3])))}"], []


def sing(P, it):
    e0, e1 = int(P["e0"]), int(P["e1"])
    qa, ra = P["q"], P["r"]
    Pp = x**e0 * (x - 1) ** e1
    pts = [0] + ([1] if e1 else [])
    lines = [f"{m('p = ' + tex(sp.factor(sp.cancel(qa / Pp))) + r',\ q = ' + tex(sp.factor(sp.cancel(ra / Pp))))}"]
    for p0 in pts:
        k = _sing_kind(Pp, qa, ra, p0)
        lines.append(f"{m('x = ' + str(p0))}: {m(('x' if p0 == 0 else '(x - ' + str(p0) + ')') + 'p = ' + tex(sp.factor(sp.cancel((x - p0) * qa / Pp))))}, {m(('x^{2}' if p0 == 0 else '(x - ' + str(p0) + ')^{2}') + 'q = ' + tex(sp.factor(sp.cancel((x - p0) ** 2 * ra / Pp))))} → {KIND_TXT[k]}")
    return lines, []


def indicial(P, it):
    D, P0, Q0 = P["D"], P["P0"], P["Q0"]
    rs = _roots_desc(P0, Q0)
    return [("" if D == 1 else f"{m(tex(D) + 'x^{2}')}로 나누면 ") + f"{m('p_0 = ' + tex(P0) + r',\ q_0 = ' + tex(Q0))}",
            f"{m('r(r - 1) + p_0r + q_0 = ' + tex(_indicial(P0, Q0)) + ' = 0')} → {m('r = ' + r',\ '.join(tex(v) for v in rs))}"], \
        [(sp.expand(_indicial(P0, Q0)).subs(r_, rs[0]), 0), (sp.expand(_indicial(P0, Q0)).subs(r_, rs[1]), 0)]


def radius(P, it):
    a, b, x0 = P["a"], P["b"], P["x0"]
    R = sp.sqrt((x0 - a) ** 2 + b)
    return [f"특이점: {m(tex(sp.expand((x - a) ** 2 + b)) + ' = 0')} → {m('x = ' + tex(a) + r' \pm ' + (tex(sp.sqrt(b)) if b != 1 else '') + 'i')}",
            f"{m('x_0 = ' + tex(x0))}까지의 거리 {m(r'\sqrt{(' + tex(x0 - a) + ')^{2} + ' + tex(b) + '} = ' + tex(R))}"], []


def second(P, it):
    r1, r2 = P["r1"], P["r2"]
    cs = it["params"]["family"]
    txt = {"nonint": "차가 정수가 아니다 → 둘째 해도 Frobenius 급수", "equal": "중근 → 반드시 로그 항", "intdiff": "차가 정수 → 로그 항이 붙을 수도(계수 C)"}[cs]
    return [f"{m('r_1 - r_2 = ' + tex(r1 - r2))}: {txt}"], []


def taylor(P, it):
    ode, ics = it["params"]["ode"], [sp.sympify(v) for v in it["params"]["ics"]]
    for fam, order, f, ics_, ode_ in _taylor_cases():
        if ode_ == ode and [sp.Integer(v) for v in ics_] == ics:
            c = _taylor_truth(order, f, ics_)
            return [f"{m(r'y^{(k)}(0)')}를 차례로: " + m(r",\ ".join(f"{['y', r'y^{\prime}', r'y^{\prime\prime}', r'y^{\prime\prime\prime}'][k]}(0) = {tex(c[k])}" for k in range(4))),
                    f"{m('x^{3}')}의 계수 {m(r'= \frac{y^{(3)}(0)}{3!} = ' + tex(c[3] / 6))}"], []
    return []


def named(P, it):
    nm = it["params"]["family"]
    key = {"legendre": r"(1 - x^2)y'' - 2xy'", "cheb": r"(1 - x^2)y'' - xy'", "hermite": r"y'' - 2xy'", "laguerre": r"xy'' + (1 - x)y'",
           "bessel": r"x^2y'' + xy' + (x^2 - \nu^2)y", "airy": r"y'' = xy"}[nm]
    return [f"알아보는 열쇠: {m(key.replace(chr(39) * 2, r'^{\prime\prime}').replace(chr(39), r'^{\prime}'))}"], []


EXPLAIN = {"ser.shift": shift, "ser.recur": recur, "ser.sing": sing, "ser.indicial": indicial, "ser.radius": radius,
           "ser.second": second, "ser.taylor": taylor, "ser.named": named}
