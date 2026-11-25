"""4장 문제별 해설."""
import sympy as sp
from exkit import tex, mat, tup, sq, M, V, prod, m, dm, p


def ata(P, it):
    A = M(P["A"], 3, 2)
    G = A.T * A
    c1, c2 = A[:, 0], A[:, 1]
    return [f"{m('A^{T}A')}의 원소는 열끼리의 내적: {m(r'\mathbf{a}_1 = ' + tup(c1))}, {m(r'\mathbf{a}_2 = ' + tup(c2))}",
            f"{m(r'\mathbf{a}_1\cdot\mathbf{a}_1 = ' + tex(c1.dot(c1)))}, {m(r'\mathbf{a}_1\cdot\mathbf{a}_2 = ' + tex(c1.dot(c2)))}, {m(r'\mathbf{a}_2\cdot\mathbf{a}_2 = ' + tex(c2.dot(c2)))}",
            dm("A^{T}A = " + mat(G))], [(G, A.T * A)]


def sv(P, it):
    A = sq(P["A"])
    G = A.T * A
    ev = sorted(G.eigenvals().keys(), reverse=True)
    svs = [sp.sqrt(e) for e in ev]
    return [f"특이값 = {m('A^{T}A')}의 고유값의 제곱근. {m('A^{T}A = ' + mat(G))}",
            f"고유값 {m(r',\ '.join(tex(e) for e in ev))} → {m(r'\sigma = ' + r',\ '.join(tex(q) for q in svs))}"], \
        [(sorted(svs, key=float), sorted(A.singular_values(), key=float))]


def svd(P, it):
    s1, s2 = P["s"]
    q = int(P["q"])
    rule = r"U, V\text{가 직교라 길이·부피를 바꾸지 않으므로, 크기에 관한 양은 }\Sigma\text{에서 바로 읽는다.}"
    out = [
        (r"\|A\|_2 = \sigma_{\max} = " + tex(s1)),
        (r"|\det A| = |\det U|\,\sigma_1\sigma_2\,|\det V| = " + prod(s1, s2) + " = " + tex(s1 * s2)),
        (r"\|A\|_F^{2} = \sigma_1^{2} + \sigma_2^{2} = " + tex(s1**2) + " + " + tex(s2**2) + " = " + tex(s1**2 + s2**2)),
        (r"A^{T}A = V\Sigma^{2}V^{T}\ \Rightarrow\ \text{고유값 } \sigma_1^{2}, \sigma_2^{2} = " + tex(s1**2) + r",\ " + tex(s2**2)),
    ][q]
    return [f"{m(rule)}", f"{m(out)}"], []


def normaleq(P, it):
    A, b = M(P["A"], 3, 2), V(P["b"])
    G, Ab = A.T * A, A.T * b
    if "정규방정식" in it["prompt"]:
        return [f"{m(r'\|A\mathbf{x} - \mathbf{b}\|')}를 최소로 하는 {m(r'\hat{\mathbf{x}}')}는 {m(r'A^{T}A\hat{\mathbf{x}} = A^{T}\mathbf{b}')}를 만족한다.",
                f"{m('A^{T}A = ' + mat(G))}, {m(r'A^{T}\mathbf{b} = ' + mat(Ab))}"], [(G, A.T * A)]
    xh = G.inv() * Ab
    return [f"정규방정식 {m(r'A^{T}A\hat{\mathbf{x}} = A^{T}\mathbf{b}')}: {m(mat(G) + r'\hat{\mathbf{x}} = ' + mat(Ab))}",
            f"풀면 {m(r'\hat{\mathbf{x}} = ' + tup(xh))}",
            f"검산: 잔차 {m(r'A\hat{\mathbf{x}} - \mathbf{b} = ' + tup(A * xh - b))}가 {m('A')}의 열과 직교 ({m(r'A^{T}(A\hat{\mathbf{x}} - \mathbf{b}) = \mathbf{0}')})"], \
        [(A.T * (A * xh - b), sp.zeros(2, 1))]


def projmat(P, it):
    a = V(P["a"])
    n2 = a.dot(a)
    Pm = a * a.T / n2
    return [f"열이 하나면 {m(r'P = \frac{\mathbf{a}\mathbf{a}^{T}}{\mathbf{a}^{T}\mathbf{a}}')}. {m(r'\mathbf{a}^{T}\mathbf{a} = ' + tex(n2))}",
            dm(r"P = \frac{1}{" + tex(n2) + "}" + mat(a * a.T) + " = " + mat(Pm)), f"검산: {m('P^{2} = P')}"], [(Pm * Pm, Pm)]


def qr(P, it):
    A, Q = sq(P["A"]), sq(P["Q"])
    R = Q.T * A
    return [f"{m('Q^{T}Q = I')}이므로 {m('A = QR')}의 양변에 {m('Q^{T}')}를 곱하면 {m('R = Q^{T}A')}",
            dm("R = " + mat(Q.T) + mat(A) + " = " + mat(R)), "위삼각인지 확인 (왼쪽 아래가 $0$)."], [(Q * R, A), (R[1, 0], 0)]


def orthmat(P, it):
    Q = sq(P["Q"])
    return [f"직교행렬은 {m('Q^{T}Q = I')}, 곧 {m('Q^{-1} = Q^{T}')}. 행과 열을 바꾸기만 하면 된다.",
            dm("Q^{-1} = Q^{T} = " + mat(Q.T))], [(Q.T * Q, sp.eye(Q.rows))]


EXPLAIN = {"la.ata": ata, "la.sv": sv, "la.svd": svd, "la.normaleq": normaleq, "la.projmat": projmat, "la.qr": qr, "la.orthmat": orthmat}
