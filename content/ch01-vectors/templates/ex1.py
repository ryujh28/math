"""1장 문제별 해설."""
import sympy as sp
from exkit import tex, tup, V, prod, m, dm, p


def dot(P, it):
    u, v = V(P["u"]), V(P["v"])
    terms = " + ".join(prod(a, b) for a, b in zip(u, v))
    val = sum(a * b for a, b in zip(u, v))
    return [f"성분끼리 곱해서 더한다: {m(terms)}", f"{m(r'\mathbf{u}\cdot\mathbf{v} = ' + tex(val))}"], [(val, u.dot(v))]


def norm(P, it):
    v = V(P["v"])
    ss = sum(c**2 for c in v)
    sq_ = " + ".join(p(c) + "^{2}" for c in v)
    return [f"성분 제곱의 합: {m(sq_ + ' = ' + tex(ss))}", f"그 제곱근: {m(r'\|\mathbf{v}\| = \sqrt{' + tex(ss) + '} = ' + tex(sp.sqrt(ss)))}"], \
        [(sp.sqrt(ss), v.norm())]


def orth(P, it):
    u, v = V(P["u"]), P["v"]  # v = [v0, v1], 셋째 성분이 k
    k = sp.Symbol("k")
    vv = sp.Matrix([v[0], v[1], k])
    d = sp.expand(u.dot(vv))
    sol = sp.solve(d, k)
    return [f"직교 ⟺ 내적이 $0$: {m(tex(d) + ' = 0')}", f"{m('k = ' + tex(sol[0]))}"], [(d.subs(k, sol[0]), 0)]


def proj(P, it):
    u, v = V(P["u"]), V(P["v"])
    uv, vv = u.dot(v), v.dot(v)
    pr = uv / vv * v
    return [f"{m(r'\mathbf{u}\cdot\mathbf{v} = ' + tex(uv))}, {m(r'\mathbf{v}\cdot\mathbf{v} = ' + tex(vv))}",
            dm(r"\operatorname{proj}_{\mathbf{v}}\mathbf{u} = \frac{" + tex(uv) + "}{" + tex(vv) + r"}\mathbf{v} = " + tup(pr))], \
        [(pr, (u.dot(v) / v.dot(v)) * v)]


def angle(P, it):
    u, v = V(P["u"]), V(P["v"])
    d, nu, nv = u.dot(v), u.norm(), v.norm()
    c = sp.radsimp(d / (nu * nv))
    return [f"{m(r'\mathbf{u}\cdot\mathbf{v} = ' + tex(d))}, {m(r'\|\mathbf{u}\| = ' + tex(nu))}, {m(r'\|\mathbf{v}\| = ' + tex(nv))}",
            dm(r"\cos\theta = \frac{" + tex(d) + "}{" + tex(nu) + r"\cdot " + tex(nv) + "} = " + tex(c))], [(c, d / (nu * nv))]


def cs(P, it):
    a, b = P["a"], P["b"]
    return [f"Cauchy–Schwarz: {m(r'|\mathbf{u}\cdot\mathbf{v}| \le \|\mathbf{u}\|\,\|\mathbf{v}\| = ' + tex(a) + r'\cdot ' + tex(b) + ' = ' + tex(a * b))}",
            f"그래서 {m(r'\mathbf{u}\cdot\mathbf{v}')}는 {m('[-' + tex(a * b) + ',\\ ' + tex(a * b) + ']')} 안에 있어야 한다. 이 구간에 든 보기가 답."], []


def triangle(P, it):
    a, b = P["a"], P["b"]
    lo, hi = abs(a - b), a + b
    return [f"삼각부등식과 그 역: {m(r'\big|\|\mathbf{u}\| - \|\mathbf{v}\|\big| \le \|\mathbf{u}+\mathbf{v}\| \le \|\mathbf{u}\| + \|\mathbf{v}\|')}",
            f"{m(tex(lo) + r' \le \|\mathbf{u}+\mathbf{v}\| \le ' + tex(hi))}. 이 구간에 든 보기가 답."], []


def gs(P, it):
    v1, v2 = V(P["v1"]), V(P["v2"])
    a, b = v2.dot(v1), v1.dot(v1)
    u2 = v2 - a / b * v1
    return [f"{m(r'\mathbf{v}_2\cdot\mathbf{u}_1 = ' + tex(a))}, {m(r'\mathbf{u}_1\cdot\mathbf{u}_1 = ' + tex(b))}",
            dm(r"\mathbf{u}_2 = \mathbf{v}_2 - \frac{" + tex(a) + "}{" + tex(b) + r"}\mathbf{u}_1 = " + tup(v2) + " - " + p(a / b) + tup(v1) + " = " + tup(u2)),
            f"검산: {m(r'\mathbf{u}_2\cdot\mathbf{u}_1 = ' + tex(u2.dot(v1)))}"], [(u2.dot(v1), 0)]


EXPLAIN = {"la.dot": dot, "la.norm": norm, "la.orth": orth, "la.proj": proj, "la.angle": angle, "la.cs": cs,
           "la.triangle": triangle, "la.gsformula": gs}
