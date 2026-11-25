"""3장 문제별 해설."""
import sympy as sp
from exkit import tex, mat, tup, sq, V, prod, m, dm, p

lam = sp.Symbol("lambda")


def _cp(A):
    return sp.expand((A - lam * sp.eye(A.rows)).det())


def charpoly(P, it):
    A = sq(P["A"])
    tr, D = A.trace(), A.det()
    poly = _cp(A)
    return [f"{m(r'\det(A - \lambda I) = \lambda^{2} - (\operatorname{tr}A)\lambda + \det A')}",
            f"{m(r'\operatorname{tr}A = ' + tex(tr))}, {m(r'\det A = ' + tex(D))}",
            dm(r"\det(A - \lambda I) = " + tex(sp.Poly(poly, lam).as_expr()))], [(poly, lam**2 - tr * lam + D)]


def eig2(P, it):
    A = sq(P["A"])
    poly = _cp(A)
    roots = sorted(sp.solve(poly, lam))
    fac = sp.factor(poly)
    return [f"특성다항식 {m(tex(sp.Poly(poly, lam).as_expr()) + ' = ' + tex(fac) + ' = 0')}",
            f"{m(r'\lambda = ' + r',\ '.join(tex(v) for v in roots))} (검산: 합 {m(tex(sum(roots)) + r' = \operatorname{tr}A')}, 곱 {m(tex(roots[0] * roots[1]) + r' = \det A')})"], \
        [(sum(roots), A.trace()), (roots[0] * roots[1], A.det())]


def eigvec(P, it):
    A, l = sq(P["A"]), P["lambda"]
    B = A - l * sp.eye(2)
    ns = B.nullspace()[0]
    den = sp.ilcm(*[sp.fraction(q)[1] for q in ns])
    ns = ns * den
    g = sp.gcd(list(ns))
    ns = ns / g if g else ns
    return [f"{m(r'(A - \lambda I)\mathbf{v} = \mathbf{0}')}을 푼다: {m(r'A - ' + p(l) + 'I = ' + mat(B))}",
            f"첫 행 {m(tex(B[0, 0]) + 'v_1 + ' + p(B[0, 1]) + 'v_2 = 0')} → {m(r'\mathbf{v} \propto ' + mat(ns))} (상수배는 모두 고유벡터)"], \
        [(A * ns, l * ns)]


def eigtri(P, it):
    A = sq(P["A"])
    d = [A[i, i] for i in range(3)]
    return [f"삼각행렬이면 {m(r'\det(A - \lambda I) = (a_{11} - \lambda)(a_{22} - \lambda)(a_{33} - \lambda)')}",
            f"그래서 고유값은 대각성분 {m(r',\ '.join(tex(v) for v in sorted(d)))}. 대각 밖 원소는 상관없다."], \
        [(sorted(d), sorted(sp.solve(_cp(A), lam)))]


def trdet(P, it):
    l1, l2 = P["l"]
    ask = str(P["ask"])
    if ask == "det":
        return [f"{m(r'\det A = \lambda_1\lambda_2')}", f"{m(prod(l1, l2) + ' = ' + tex(l1 * l2))}"], []
    return [f"{m(r'\operatorname{tr}A = \lambda_1 + \lambda_2')}", f"{m(tex(l1) + ' + ' + p(l2) + ' = ' + tex(l1 + l2))}"], []


def symeig(P, it):
    if "v" in P:
        v = V(P["v"])
        return [f"대칭행렬에서 다른 고유값의 고유벡터는 서로 직교한다.",
                f"{m(tup(v))}에 직교하는 벡터: {m(tup(sp.Matrix([-v[1], v[0]])))}와 그 상수배 (내적이 $0$인지 확인)."], []
    v1, v2 = V(P["v1"]), V(P["v2"])
    w = v1.cross(v2)
    return ["대칭행렬에서 다른 고유값의 고유벡터는 서로 직교한다. 세 번째는 앞의 둘 모두에 직교해야 한다.",
            f"외적으로 구한다: {m(tup(v1) + r' \times ' + tup(v2) + ' = ' + tup(w))} (상수배도 답)"], [(w.dot(v1), 0), (w.dot(v2), 0)]


def similar(P, it):
    A, Pm = sq(P["A"]), sq(P["P"])
    pr = it["prompt"]
    lines = [f"{m('B = P^{-1}AP')}이면 특성다항식이 같다: {m(r'\det(B - \lambda I) = \det(P^{-1}(A - \lambda I)P) = \det(A - \lambda I)')}"]
    if r"\det B" in pr:
        lines.append(f"그래서 {m(r'\det B = \det A = ' + tex(A.det()))}. {m('P')}는 계산할 필요가 없다.")
    elif r"\operatorname{tr} B" in pr:
        lines.append(f"그래서 {m(r'\operatorname{tr} B = \operatorname{tr} A = ' + tex(A.trace()))}. {m('P')}는 계산할 필요가 없다.")
    else:
        lines.append(dm(r"\det(B - \lambda I) = \det(A - \lambda I) = " + tex(sp.Poly(_cp(A), lam).as_expr())))
    B = Pm.inv() * A * Pm
    return lines, [(B.det(), A.det()), (B.trace(), A.trace())]


def eigpow(P, it):
    form = it["prompt"].split(r"\text{일 때 }")[1].split(r"\mathbf{v}")[0].strip()
    l = P["lam"]
    rules = {"A^{-1}": (lambda q: 1 / q, r"A\mathbf{v} = \lambda\mathbf{v}\ \Rightarrow\ \mathbf{v} = \lambda A^{-1}\mathbf{v}\ \Rightarrow\ A^{-1}\mathbf{v} = \tfrac{1}{\lambda}\mathbf{v}"),
             "A^{2}": (lambda q: q**2, r"A^{2}\mathbf{v} = A(\lambda\mathbf{v}) = \lambda^{2}\mathbf{v}"),
             "A^{3}": (lambda q: q**3, r"A^{k}\mathbf{v} = \lambda^{k}\mathbf{v}"),
             "A^{-2}": (lambda q: q**-2, r"A^{-1}\mathbf{v} = \lambda^{-1}\mathbf{v}\ \Rightarrow\ A^{-2}\mathbf{v} = \lambda^{-2}\mathbf{v}"),
             "(A + 2I)": (lambda q: q + 2, r"(A + cI)\mathbf{v} = (\lambda + c)\mathbf{v}"),
             "(A - 3I)": (lambda q: q - 3, r"(A + cI)\mathbf{v} = (\lambda + c)\mathbf{v}"),
             "(2A - I)^{-1}": (lambda q: 1 / (2 * q - 1), r"(2A - I)\mathbf{v} = (2\lambda - 1)\mathbf{v}\ \Rightarrow\ (2A - I)^{-1}\mathbf{v} = \tfrac{1}{2\lambda - 1}\mathbf{v}")}
    f, rule = rules[form]
    v = sp.nsimplify(f(l))
    return [f"{m(rule)}", f"{m(r'\lambda = ' + tex(l))}을 넣으면 {m(form + r'\mathbf{v} = ' + tex(v) + r'\mathbf{v}')}"], []


EXPLAIN = {"la.charpoly": charpoly, "la.eig2": eig2, "la.eigvec": eigvec, "la.eigtri": eigtri, "la.trdet": trdet,
           "la.symeig": symeig, "la.similar": similar, "la.eigpow": eigpow}
