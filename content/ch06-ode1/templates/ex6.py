"""6장 문제별 해설."""
import sympy as sp
from exkit import tex, m, dm, p, x, y

C = sp.Symbol("C")
_c = lambda e: "" if e == 1 else tex(e)  # noqa: E731


def mu(P, it):
    pp = P["p"]
    ip = sp.integrate(pp, x)
    mu_ = sp.simplify(sp.exp(ip))
    return [f"{m(r'\mu = e^{\int p\,dx}')}, {m('p = ' + tex(pp))}",
            f"{m(r'\int p\,dx = ' + tex(ip))} → {m(r'\mu = e^{' + tex(ip) + '}' + ('' if tex(mu_) == tex(sp.exp(ip)) else ' = ' + tex(mu_)))}",
            f"검산: {m(r"\mu' = p\mu")} 이면 {m(r"(\mu y)' = \mu(y' + py)")}"], [(sp.diff(mu_, x), pp * mu_)]


def sepgen(P, it):
    a, n = P["a"], P["n"]
    rhs = a * x**n
    I = sp.integrate(rhs, x)
    return [f"변수분리: {m(r'\frac{dy}{y} = ' + tex(rhs) + r'\,dx')}",
            f"양변 적분: {m(r'\ln|y| = ' + tex(I) + ' + c')}", f"{m('y = Ce^{' + tex(I) + '}')}"], \
        [(sp.diff(C * sp.exp(I), x), rhs * C * sp.exp(I))]


def exactk(P, it):
    a, b = P["a"], P["b"]
    k = sp.Symbol("k")
    Mxy = a * x**2 * y + b * y
    N = k * x**3 + b * x
    My, Nx = sp.diff(Mxy, y), sp.diff(N, x)
    kv = sp.solve(sp.Eq(My, Nx), k)[0]
    return [f"완전 조건 {m('M_y = N_x')}", f"{m('M_y = ' + tex(My))}, {m('N_x = ' + tex(Nx))}",
            f"{m('x^{2}')} 계수를 맞추면 {m('3k = ' + tex(a))} → {m('k = ' + tex(kv))}"], [(sp.simplify(My - Nx.subs(k, kv)), 0)]


def linformula(P, it):
    a, q = P["a"], P["q"]
    mu_ = sp.exp(a * x)
    I = sp.simplify(sp.integrate(mu_ * q, x))
    yp = sp.simplify(I / mu_)
    sol = yp + C * sp.exp(-a * x)
    return [f"{m(r'\mu = e^{' + tex(a * x) + '}')}, {m(r'y = \frac{1}{\mu}\left(\int \mu q\,dx + C\right)')}",
            f"{m(r'\int ' + tex(mu_) + r'\cdot ' + p(q) + r'\,dx = ' + tex(I))}",
            f"{m('y = ' + tex(sol))}"], [(sp.simplify(sp.diff(sol, x) + a * sol - q), 0)]


def exactcond(P, it):
    F = P["F"]
    Mx, Ny = sp.diff(F, x), sp.diff(F, y)
    return [f"완전 ⟺ {m(r'M_y = N_x')} (어떤 {m('F')}가 있어 {m('M = F_x')}, {m('N = F_y')})",
            f"정답 보기: {m('M_y = ' + tex(sp.diff(Mx, y)))}, {m('N_x = ' + tex(sp.diff(Ny, x)))} → 같다. 실제로 {m('F = ' + tex(F))}",
            "다른 보기는 둘이 다르다."], [(sp.diff(Mx, y), sp.diff(Ny, x))]


def bernoulli(P, it):
    n = sp.nsimplify(P["n"])
    k = 1 - n
    if "의 방정식은" in it["prompt"]:
        pp, q = P["p"], P["q"]
        return [f"{m('v = y^{' + tex(k) + '}')}이면 {m(r"v' = " + tex(k) + r"y^{" + tex(-n) + r"}y'")}. 원식을 {m('y^{' + tex(n) + '}')}로 나누고 {m(tex(k))}를 곱하면",
                dm(r"v' " + ("- " + _c(-k * pp) if (k * pp).could_extract_minus_sign() else "+ " + _c(k * pp)) + r"v = " + tex(sp.expand(k * q))),
                f"곧 {m(r"v' + (1 - n)pv = (1 - n)q")}: 양변 모두 {m('1 - n')}배."], []
    return [f"Bernoulli {m(r"y' + py = qy^{n}")}는 {m('v = y^{1 - n}')}로 선형이 된다.",
            f"{m('n = ' + tex(n))} → {m('v = y^{' + tex(k) + '}')}"], []


def existence(P, it):
    f = P["f"]
    pt = P["pt"]
    fy = sp.diff(f, y)
    return [f"Picard: {m('f')}와 {m(r'\partial f/\partial y')}가 초기점 근처에서 연속이면 해가 존재하고 유일하다.",
            f"{m(r'\partial f/\partial y = ' + tex(fy))}",
            f"{m('(' + tex(pt[0]) + ',\\ ' + tex(pt[1]) + ')')}에서 이 값이 정의되지 않는다(또는 {m('f')}가 정의되지 않는다) → 유일성 보장 안 됨. 다른 보기의 점에서는 둘 다 연속."], []


EXPLAIN = {"ode.mu": mu, "ode.sepgen": sepgen, "ode.exactk": exactk, "ode.linformula": linformula, "ode.exactcond": exactcond,
           "ode.bernoulli": bernoulli, "ode.existence": existence}
