"""2장 문제별 해설."""
import sympy as sp
from exkit import tex, mat, sq, M, prod, m, dm, p
from fx2 import FORMS


def det2(P, it):
    A = sq(P["A"])
    a, b, c, d = A
    v = a * d - b * c
    return [f"{m('ad - bc')}: {m(prod(a, d) + ' - ' + prod(b, c) + ' = ' + tex(a * d) + ' - ' + p(b * c) + ' = ' + tex(v))}"], [(v, A.det())]


def inv2(P, it):
    A = sq(P["A"])
    a, b, c, d = A
    D = a * d - b * c
    adj = sp.Matrix([[d, -b], [-c, a]])
    inv = adj / D
    return [f"{m(r'\det A = ' + tex(D))}", f"{m('a')}와 {m('d')}는 자리를 바꾸고 {m('b')}, {m('c')}는 부호만 바꾼다:",
            dm(r"A^{-1} = " + (mat(adj) if D == 1 else "-" + mat(adj) + " = " + mat(inv) if D == -1 else r"\frac{1}{" + tex(D) + "}" + mat(adj) + " = " + mat(inv)))], [(inv, A.inv())]


def matmul(P, it):
    A, B = sq(P["A"]), sq(P["B"])
    C = A * B
    e = lambda i, j: prod(A[i, 0], B[0, j]) + " + " + prod(A[i, 1], B[1, j])
    return [f"{m('(AB)_{ij}')} = {m('A')}의 {m('i')}행 · {m('B')}의 {m('j')}열",
            f"예: {m('(AB)_{11} = ' + e(0, 0) + ' = ' + tex(C[0, 0]))}, {m('(AB)_{12} = ' + e(0, 1) + ' = ' + tex(C[0, 1]))}",
            dm("AB = " + mat(C))], [(C, A * B)]


def rank(P, it):
    A = sq(P["A"])
    R, piv = A.rref()
    return [f"행 소거로 기약행사다리꼴을 만들면 {m(mat(R))}", f"피벗이 {m(tex(len(piv)))}개 → {m(r'\operatorname{rank} A = ' + tex(len(piv)))}"], \
        [(len(piv), A.rank())]


def det3(P, it):
    A = sq(P["A"])
    minors = [A.minor_submatrix(0, j).det() for j in range(3)]
    terms = [A[0, j] * minors[j] * (-1) ** j for j in range(3)]
    expr = " ".join((("+ " if k else "") if (-1) ** k > 0 else "- ") + prod(A[0, k], minors[k]) for k in range(3))
    return ["1행을 따라 전개 (부호 $+,\\,-,\\,+$):",
            dm(expr + " = " + tex(sum(terms))),
            f"소행렬식: {m('M_{11} = ' + tex(minors[0]))}, {m('M_{12} = ' + tex(minors[1]))}, {m('M_{13} = ' + tex(minors[2]))}"], \
        [(sum(terms), A.det())]


def detprod(P, it):
    form = it["prompt"].split(r"\det(")[1].split(")")[0]
    _, a_, b_ = next(f for f in FORMS if f[0] == form)
    a, b = P["a"], P["b"]
    v = a ** a_ * b ** b_
    rules = r"\det(XY) = \det X\,\det Y,\ \det(X^{T}) = \det X,\ \det(X^{-1}) = \frac{1}{\det X}"
    parts = []
    if a_:
        parts.append(p(a) + (f"^{{{a_}}}" if a_ != 1 else ""))
    if b_:
        parts.append(p(b) + (f"^{{{b_}}}" if b_ != 1 else ""))
    return [f"{m(rules)}", f"{m(r'\det(' + form + ') = ' + r' \cdot '.join(parts) + ' = ' + tex(v))}"], []


def detscale(P, it):
    n, k, d = P["n"], P["k"], P["d"]
    v = k ** n * d
    return [f"{m('kA')}는 {m(tex(n))}개의 행 각각에 {m('k')}를 곱한 것이라 행렬식은 {m('k^{n}')}배: {m(r'\det(kA) = k^{n}\det A')}",
            f"{m(p(k) + '^{' + tex(n) + '}' + r' \cdot ' + p(d) + ' = ' + tex(v))}"], []


def invertible(P, it):
    A = sq(P["A"])
    d = A.det()
    ask_inv = "가역이 아닌" not in it["prompt"]
    return [f"정답 행렬의 행렬식: {m(r'\det' + mat(A) + ' = ' + tex(d))}",
            ("행렬식이 $0$이 아니면 가역" if ask_inv else "행렬식이 $0$이면 가역이 아님") +
            ". 나머지 보기는 " + ("한 행(또는 열)이 다른 행의 배수라 행렬식이 $0$." if ask_inv else "행렬식이 $0$이 아니다.")], []


def invprod(P, it):
    Ai, Bi = sq(P["Ai"]), sq(P["Bi"])
    R = Bi * Ai
    return [f"{m('(AB)^{-1} = B^{-1}A^{-1}')}: 순서가 뒤집힌다 ({m(r'(AB)(B^{-1}A^{-1}) = I')}).",
            dm("B^{-1}A^{-1} = " + mat(Bi) + mat(Ai) + " = " + mat(R))], [((Ai.inv() * Bi.inv()) * R, sp.eye(2))]


def transprod(P, it):
    a, b = P["A"], P["B"]
    shapes = {(4, 4): ((2, 2), (2, 2)), (6, 6): ((2, 3), (3, 2)), (6, 4): ((3, 2), (2, 2))}
    (ra, ca), (rb, cb) = shapes[(len(a), len(b))]
    A, B = M(a, ra, ca), M(b, rb, cb)
    C = A * B
    return [f"{m('(AB)^{T} = B^{T}A^{T}')}: 순서가 뒤집힌다. 먼저 곱하고 전치해도 같다.",
            dm("AB = " + mat(C) + r"\ \Rightarrow\ (AB)^{T} = " + mat(C.T))], [(B.T * A.T, C.T)]


EXPLAIN = {"la.det2": det2, "la.inv2": inv2, "la.matmul": matmul, "la.rank": rank, "la.det3": det3, "la.detprod": detprod,
           "la.detscale": detscale, "la.invertible": invertible, "la.invprod": invprod, "la.transprod": transprod}
