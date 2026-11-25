"""4장 공식 원자의 구체적 적용 문제."""
import itertools
import random
import sympy as sp
from texkit import tex, mat, tup
from checks import same, opt


def _case(prompt, ans_tex, ans_ok, wrong, tier=None, params=None):
    c = {"params": params or {}, "prompt": prompt, "answer": opt(ans_tex, ans_ok),
         "wrong": [opt(tx, ok, e) for tx, ok, e in wrong]}
    if tier is not None:
        c["tier"] = tier
    return c


R = sp.Rational
# 유리수 원소의 회전·반사 (피타고라스 수)
TRIPLES = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (4, 3, 5)]


def _orth2():
    out = []
    for a, b, c in TRIPLES:
        ca, sa = R(a, c), R(b, c)
        out.append(sp.Matrix([[ca, -sa], [sa, ca]]))   # 회전
        out.append(sp.Matrix([[ca, sa], [sa, -ca]]))   # 반사
        out.append(sp.Matrix([[-ca, sa], [-sa, -ca]]))
    return out


def _perm3():
    out = []
    for p in itertools.permutations(range(3)):
        for sg in [(1, 1, 1), (1, -1, 1), (-1, 1, 1)]:
            M = sp.zeros(3, 3)
            for i, j in enumerate(p):
                M[i, j] = sg[i]
            if M != M.T:
                out.append(M)
    return out


def orthmat():
    out = []
    for Q in _orth2() + _perm3()[:10]:
        truth = Q.T
        cand = [(Q, "algebra"), (-Q, "sign"), (-Q.T, "sign"), (2 * Q.T, "normalization")]
        ok = lambda X, Q=Q: same(sp.Matrix(X) * Q, sp.eye(Q.rows))
        out.append(_case(rf"Q = {mat(Q)}\text{{일 때 }} Q^{{-1}} = \;?", mat(truth), lambda X=truth, ok=ok: ok(X),
                         [(mat(X), lambda X=X, ok=ok: ok(X), e) for X, e in cand], tier=1 if Q.rows == 2 else 2,
                         params={"Q": [str(q) for q in Q]}))
    return out


def projmat():
    """열 하나짜리 A = a: P = aaᵀ/(aᵀa)."""
    out = []
    vecs = [v for v in itertools.product(range(-2, 3), repeat=2) if any(v) and v[0] != 0 and v[1] != 0]
    vecs += [v for v in itertools.product(range(-1, 3), repeat=3) if sum(1 for q in v if q) >= 2][:14]
    for v in vecs:
        a = sp.Matrix(v)
        n2 = a.dot(a)
        P = a * a.T / n2
        cand = [(a * a.T, "normalization"), (sp.eye(a.rows) - P, "algebra"), (a * a.T / sp.sqrt(n2), "normalization"),
                (a * a.T / (2 * n2), "missing_factor")]
        cand = [(X, e) for X, e in cand if all(q.is_rational for q in X)]
        out.append(_case(rf"A = {mat(a)}\text{{의 열공간으로의 사영행렬 }} P = \;?", mat(P), lambda X=P, tr=P: same(X, tr),
                         [(mat(X), lambda X=X, tr=P: same(X, tr), e) for X, e in cand], tier=1 if a.rows == 2 else 2,
                         params={"a": list(v)}))
    return out


def normaleq():
    """세 점 직선 맞춤 등: x̂ = (AᵀA)⁻¹Aᵀb."""
    out = []
    rng = random.Random(41)
    seen = set()
    while len(out) < 24:
        A = sp.Matrix(3, 2, [rng.randint(-2, 2) for _ in range(6)])
        b = sp.Matrix([rng.randint(-3, 3) for _ in range(3)])
        if A.rank() < 2 or (tuple(A), tuple(b)) in seen:
            continue
        M = A.T * A
        xh = M.inv() * A.T * b
        if max(q.q for q in xh) > 6 or (A * xh - b) == sp.zeros(3, 1):
            continue
        seen.add((tuple(A), tuple(b)))
        resid_ok = lambda X, A=A, b=b: same(A.T * (A * sp.Matrix(X) - b), sp.zeros(2, 1))
        cand = [(A[:2, :].inv() * b[:2, :] if A[:2, :].det() != 0 else -xh, "algebra"), (-xh, "sign"), (A.T * b, "missing_factor"),
                (xh + sp.Matrix([1, 0]), "algebra")]
        if len(out) % 2 == 0:
            out.append(_case(rf"A = {mat(A)},\ \mathbf{{b}} = {mat(b)}\text{{일 때 최소제곱해 }} \hat{{\mathbf{{x}}}} = \;?", tup(xh),
                             lambda X=xh, ok=resid_ok: ok(X), [(tup(X), lambda X=X, ok=resid_ok: ok(X), e) for X, e in cand],
                             tier=2, params={"A": list(A), "b": list(b)}))
        else:
            # 정규방정식 자체를 고르기
            def eq_tex(L, r):
                return mat(L) + r"\hat{\mathbf{x}} = " + mat(r)
            eq_ok = lambda L, r, M=M, Ab=A.T * b: same(L, M) and same(r, Ab)
            alts = [(M, -(A.T * b), "sign"), (A[:2, :], b[:2, :], "algebra"), (M, A.T * b + sp.Matrix([0, 1]), "algebra"),
                    (A[:2, :].T * A[:2, :], A[:2, :].T * b[:2, :], "algebra")]
            out.append(_case(rf"A = {mat(A)},\ \mathbf{{b}} = {mat(b)}\text{{의 정규방정식은?}}", eq_tex(M, A.T * b),
                             lambda L=M, r=A.T * b, ok=eq_ok: ok(L, r),
                             [(eq_tex(L, r), lambda L=L, r=r, ok=eq_ok: ok(L, r), e) for L, r, e in alts],
                             tier=1, params={"A": list(A), "b": list(b)}))
    return out


def qr():
    """Q가 주어지면 R = QᵀA."""
    out = []
    rng = random.Random(42)
    Qs = [Q for Q in _orth2() if Q.det() == 1]
    for Q in Qs:
        for _ in range(3):
            Rm = sp.Matrix([[rng.randint(1, 4) * Q[0, 0].q, rng.randint(-3, 3) * Q[0, 0].q], [0, rng.randint(1, 4) * Q[0, 0].q]])
            A = Q * Rm
            cand = [(Q * A, "algebra"), (Rm.T, "algebra"), (A * Q.T, "algebra"), (-Rm, "sign")]
            ok = lambda X, A=A, Q=Q: same(Q * sp.Matrix(X), A) and sp.Matrix(X)[1, 0] == 0
            out.append(_case(rf"A = {mat(A)},\ Q = {mat(Q)},\ A = QR\text{{일 때 }} R = \;?", mat(Rm), lambda X=Rm, ok=ok: ok(X),
                             [(mat(X), lambda X=X, ok=ok: ok(X), e) for X, e in cand], tier=2, params={"A": list(A), "Q": list(Q)}))
    return out


def svd():
    """A = UΣVᵀ에서 Σ로 읽는 양들."""
    out = []
    for s1, s2 in [(3, 2), (5, 1), (4, 3), (6, 2), (2, 1), (5, 3), (7, 4), (3, 1)]:
        s1, s2 = sp.Integer(s1), sp.Integer(s2)
        head = rf"A = U\Sigma V^{{T}},\ \Sigma = \begin{{pmatrix}} {s1} & 0 \\ 0 & {s2} \end{{pmatrix}},\ U, V\text{{는 직교}}\text{{일 때 }} "
        qs = [
            (r"\|A\|_2 = \;?", s1, [s1 ** 2, s1 + s2, s1 * s2, s2]),
            (r"|\det A| = \;?", s1 * s2, [s1 + s2, s1 ** 2 * s2 ** 2, s1, s1 ** 2 + s2 ** 2]),
            (r"\|A\|_F^{2} = \;?", s1 ** 2 + s2 ** 2, [s1 + s2, (s1 + s2) ** 2, s1 * s2, s1 ** 2]),
            (r"A^{T}A\text{의 고유값은?}", (s1 ** 2, s2 ** 2), [(s1, s2), (s1 ** 2, s1 * s2), (2 * s1, 2 * s2), (s1 + s2, s1 - s2)]),
        ]
        for i, (q, truth, wrong) in enumerate(qs):
            if isinstance(truth, tuple):
                fmt = lambda v: tex(v[0]) + r",\ " + tex(v[1])
                ok = lambda v, tr=truth: same(set(v), set(tr))
            else:
                fmt = tex
                ok = lambda v, tr=truth: same(v, tr)
            out.append(_case(head + q, fmt(truth), lambda v=truth, ok=ok: ok(v),
                             [(fmt(w), lambda v=w, ok=ok: ok(v), "missing_factor" if i != 3 else "normalization") for w in wrong],
                             tier=1 if i < 2 else 2, params={"s": [int(s1), int(s2)], "q": i}))
    return out
