"""8장 문제별 해설."""
import ast
import sympy as sp
from exkit import tex, m, dm, x, r
from texkit import mat, poly_tex
lam = sp.Symbol('lambda')
from ode8 import _poly_from_roots, _roots_of, _basis, _wr, classify, LABEL, X_, Y_, _J, _systems, _equilibria, k_

t = sp.Symbol("t")


def _spec(P):
    return ast.literal_eval(str(P["spec"]))


def highgen(P, it):
    spec = _spec(P)
    cp = _poly_from_roots(_roots_of(spec))
    fac = sp.factor(cp)
    lines = [f"{m('y = e^{rx}')}를 넣으면 특성방정식 {m(tex(cp) + ' = 0')}",
             f"인수분해: {m(tex(fac) + ' = 0')}"]
    for s_ in spec:
        if s_[0] == "re" and s_[2] == 1:
            lines.append(f"{m('r = ' + tex(s_[1]))} → {m(tex(sp.exp(s_[1] * x)))}")
        elif s_[0] == "re":
            lines.append(f"{m('r = ' + tex(s_[1]))} ({s_[2]}중근) → " + m(r',\ '.join(tex(x**k * sp.exp(s_[1] * x)) for k in range(s_[2]))))
        else:
            _, al, be, mm = s_
            lines.append(f"{m('r = ' + tex(al + be * sp.I) + ',\\ ' + tex(al - be * sp.I))}" + (" (중근)" if mm == 2 else "") + " → "
                         + m(r',\ '.join(tex(f) for f in _basis([s_]))))
    return lines, [(sp.expand(fac), cp)]


def repsol(P, it):
    a, mm = P["a"], P["m"]
    return [f"{m(r'(D - a)(e^{ax}g) = e^{ax}g^{\prime}')}이므로 {m(r'(D - a)^{m}(e^{ax}g) = e^{ax}g^{(m)}')}",
            f"{m('g = x^{k}')}이고 {m('k < ' + tex(mm))}이면 {m('g^{(' + tex(mm) + ')} = 0')} → "
            + m(r',\ '.join(tex(x**k * sp.exp(a * x)) for k in range(int(mm)))) + " 모두 해"], \
        [(_dam(x**(int(mm) - 1) * sp.exp(a * x), a, int(mm)), 0)]


def _dam(f, a, mm):
    """(D − a)^m f"""
    for _ in range(mm):
        f = sp.diff(f, x) - a * f
    return sp.simplify(f)


def wronsk3(P, it):
    fs = sp.sympify(str(P["fs"]), locals={"x": x})
    M = sp.Matrix([[sp.diff(f, x, k) for f in fs] for k in range(3)])
    W = sp.simplify(M.det())
    return [f"{m('W = ' + r'\begin{vmatrix}' + r' \\ '.join(' & '.join(tex(e) for e in M.row(i)) for i in range(3)) + r'\end{vmatrix}')}",
            f"전개하면 {m('W = ' + tex(W))}"], [(W, _wr(list(fs)))]


def companion(P, it):
    a, b, c = P["a"], P["b"], P["c"]
    return [f"{m(r'u_1 = y,\ u_2 = y^{\prime},\ u_3 = y^{\prime\prime}')} → {m(r'u_1^{\prime} = u_2,\ u_2^{\prime} = u_3')}",
            f"방정식을 {m(r'y^{\prime\prime\prime}')}에 대해 풀면 {m(r'u_3^{\prime} = ' + tex(-c * sp.Symbol('u_1') - b * sp.Symbol('u_2') - a * sp.Symbol('u_3')))}: 마지막 행은 계수의 부호를 바꿔 {m('(-c, -b, -a)')} 순서."], []


def phase(P, it):
    fam = it["params"]["family"]
    if fam == "eig":
        ev = [sp.sympify(str(e)) for e in P["ev"]]
    else:
        A = sp.Matrix(2, 2, P["A"])
        ev = [k for k, mm in A.eigenvals().items() for _ in range(mm)]
    if all(sp.im(v) == 0 for v in ev):
        a_, b_ = sorted(sp.re(v) for v in ev)
        why = "부호가 다른 실근 → 안장점" if a_ * b_ < 0 else ("같은 실근(중근) → 퇴화 마디" if a_ == b_ else "부호가 같은 실근 → 마디") + (", 음수라 안정" if a_ < 0 else ", 양수라 불안정")
    else:
        re_ = sp.re(ev[0])
        why = "순허수 → 중심" if re_ == 0 else f"복소근, 실수부 {m(tex(re_))} → " + ("안정 나선" if re_ < 0 else "불안정 나선")
    lines = []
    if fam != "eig":
        lines.append(f"{m(poly_tex(lam**2 - A.trace() * lam + A.det(), lam) + ' = 0')} → {m(r'\lambda = ' + r',\ '.join(tex(v) for v in ev))}")
    lines.append(why)
    return lines, []


def stabk(P, it):
    a, b, d = P["a"], P["b"], P["d"]
    A = sp.Matrix([[k_, a], [b, d]])
    tr, det = A.trace(), A.det()
    k1 = sp.solve(tr, k_)[0]
    k2 = sp.solve(det, k_)[0]
    c = min(k1, k2)
    return [f"점근 안정 ⟺ {m(r'\operatorname{tr}A < 0')}이고 {m(r'\det A > 0')}",
            f"{m(r'\operatorname{tr}A = ' + tex(tr) + ' < 0')} → {m('k < ' + tex(k1))}",
            f"{m(r'\det A = ' + tex(sp.expand(det)) + ' > 0')} → {m('k < ' + tex(k2))}",
            f"둘 다 → {m('k < ' + tex(c))}"], [(c, min(k1, k2))]


def _find(P, it):
    fam = it["params"]["family"]          # revive가 'comp' 같은 문자열을 SymPy 함수로 바꾸므로 원문을 쓴다
    for f_, f, g, PP in _systems():
        if f_ == fam and all(sp.nsimplify(PP[k]) == sp.nsimplify(P[k]) for k in PP):
            return f, g
    return None, None


def equil(P, it):
    f, g = _find(P, it)
    if f is None:
        return []
    sub = {X_: sp.Symbol("x"), Y_: sp.Symbol("y")}
    eqs = [e for e in _equilibria(f, g, it["params"]["family"]) if all(v.is_real for v in e)]
    return [f"{m(tex(sp.factor(f).subs(sub)) + ' = 0')}이고 {m(tex(sp.factor(g).subs(sub)) + ' = 0')}",
            "각 인수가 0인 경우를 짝지으면 " + m(r",\ ".join(f"({tex(a)},\\ {tex(b)})" for a, b in eqs))], \
        [(f.subs({X_: e[0], Y_: e[1]}), 0) for e in eqs] + [(g.subs({X_: e[0], Y_: e[1]}), 0) for e in eqs]


def jac(P, it):
    f, g = _find(P, it)
    if f is None:
        return []
    sub = {X_: sp.Symbol("x"), Y_: sp.Symbol("y")}
    pt = [sp.sympify(str(v)) for v in P["pt"]]
    J = _J(f, g)
    Je = J.subs({X_: pt[0], Y_: pt[1]})
    return [f"{m(r'J = \begin{pmatrix}f_x & f_y \\ g_x & g_y\end{pmatrix} = ' + mat(J.subs(sub)))}",
            f"{m('(' + tex(pt[0]) + ',\\ ' + tex(pt[1]) + ')')} 대입 → {m(mat(Je))}"], [(Je, _J(f, g).subs({X_: pt[0], Y_: pt[1]}))]


EXPLAIN = {"ode8.highgen": highgen, "ode8.repsol": repsol, "ode8.wronsk3": wronsk3, "ode8.companion": companion,
           "ode8.phase": phase, "ode8.stabk": stabk, "ode8.equil": equil, "ode8.jac": jac}
