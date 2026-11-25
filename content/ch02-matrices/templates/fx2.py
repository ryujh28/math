"""2장 공식 원자의 구체적 적용 문제."""
import itertools
import random
import sympy as sp
from texkit import tex, mat
from checks import same, opt


def _case(prompt, ans_tex, ans_ok, wrong, tier=None, params=None):
    c = {"params": params or {}, "prompt": prompt, "answer": opt(ans_tex, ans_ok),
         "wrong": [opt(tx, ok, e) for tx, ok, e in wrong]}
    if tier is not None:
        c["tier"] = tier
    return c


def _val(v, tr):
    return lambda v=v, tr=tr: same(v, tr)


def _mats(n, k, seed, lo=-2, hi=3, cond=None):
    rng = random.Random(seed)
    out, seen = [], set()
    while len(out) < k:
        M = sp.Matrix(n, n, [rng.randint(lo, hi) for _ in range(n * n)])
        if tuple(M) in seen or (cond and not cond(M)):
            continue
        seen.add(tuple(M))
        out.append(M)
    return out


# (TeX, A의 지수, B의 지수)
FORMS = [("AB", 1, 1), ("A^{2}B", 2, 1), ("AB^{-1}", 1, -1), ("A^{T}B", 1, 1),
         ("A^{-1}B^{2}", -1, 2), ("A^{3}", 3, 0), ("B^{T}A^{-1}", -1, 1)]


def detprod():
    out = []
    rng = random.Random(21)
    for (form, p, q), (a, b) in itertools.product(FORMS, [(2, 3), (-1, 4), (3, -2), (2, 5)]):
        a, b = sp.Integer(a), sp.Integer(b)
        truth = a ** p * b ** q
        cand = [(p * a + q * b, "algebra"), (a ** p + b ** q, "algebra"), (a ** (-p) * b ** (-q), "sign"),
                (a ** p * b ** (-q), "sign"), (a * b, "missing_factor"), (-truth, "sign"), (p * q * a * b, "algebra")]
        tier = 1 if form in ("AB", "A^{T}B", "A^{3}") else 2
        out.append(_case(rf"\det A = {a},\ \det B = {b}\text{{일 때 }} \det({form}) = \;?", tex(truth), _val(truth, truth),
                         [(tex(v), _val(v, truth), e) for v, e in cand], tier=tier, params={"form": form, "a": int(a), "b": int(b)}))
    rng.shuffle(out)
    return out


def detscale():
    out = []
    for n, k, d in itertools.product([2, 3, 4], [2, 3, -1, -2, sp.Rational(1, 2)], [3, -2, 5]):
        k, d = sp.nsimplify(k), sp.Integer(d)
        truth = k ** n * d
        cand = [(k * d, "missing_factor"), (k ** (n - 1) * d, "algebra"), (n * k * d, "algebra"), (k ** n + d, "algebra"),
                (-truth, "sign"), (k ** (n + 1) * d, "algebra")]
        kt = "-" if k == -1 else tex(k)
        prompt = rf"A \in \mathbb{{R}}^{{{n}\times{n}}},\ \det A = {d}\text{{일 때 }} \det({kt}A) = \;?"
        out.append(_case(prompt, tex(truth), _val(truth, truth), [(tex(v), _val(v, truth), e) for v, e in cand],
                         tier=1 if n == 2 else 2, params={"n": n, "k": str(k), "d": int(d)}))
    return out


def _singular(n, rng):
    while True:
        M = sp.Matrix(n, n, [rng.randint(-3, 3) for _ in range(n * n)])
        i, j = rng.sample(range(n), 2)
        c = rng.choice([-2, -1, 2, 3])
        if rng.random() < 0.5:
            M[j, :] = c * M[i, :]
        else:
            M[:, j] = c * M[:, i]
        if M.det() == 0 and any(M):
            return M


def invertible():
    out = []
    rng = random.Random(22)
    for n, k in ((2, 12), (3, 12)):
        for good in _mats(n, k, 23 + n, -3, 4, cond=lambda M: M.det() != 0):
            bad = [_singular(n, rng) for _ in range(3)]
            out.append(_case(r"\text{가역인 행렬은?}", mat(good), lambda M=good: M.det() != 0,
                             [(mat(M), lambda M=M: M.det() != 0, "theorem_condition") for M in bad],
                             tier=1 if n == 2 else 2, params={"A": list(good)}))
        for _ in range(6):  # 반대로 묻기
            bad = _singular(n, rng)
            goods = _mats(n, 3, rng.randint(0, 10 ** 6), -3, 4, cond=lambda M: M.det() != 0)
            out.append(_case(r"\text{가역이 아닌 행렬은?}", mat(bad), lambda M=bad: M.det() == 0,
                             [(mat(M), lambda M=M: M.det() == 0, "theorem_condition") for M in goods],
                             tier=1 if n == 2 else 2, params={"A": list(bad)}))
    return out


def _unimod(k, seed):
    return _mats(2, k, seed, -2, 3, cond=lambda M: M.det() in (1, -1))


def invprod():
    out = []
    As, Bs = _unimod(14, 24), _unimod(14, 25)
    for Ai, Bi in zip(As, Bs):
        if Ai * Bi == Bi * Ai:
            continue
        truth = Bi * Ai  # (AB)^{-1}
        ok = lambda X, AB=Ai.inv() * Bi.inv(): same(AB * sp.Matrix(X), sp.eye(2))
        cand = [(Ai * Bi, "algebra"), (Ai + Bi, "algebra"), (Ai.T * Bi.T, "algebra"), (Bi * Ai.T, "algebra")]
        out.append(_case(rf"A^{{-1}} = {mat(Ai)},\ B^{{-1}} = {mat(Bi)}\text{{일 때 }} (AB)^{{-1}} = \;?", mat(truth),
                         lambda X=truth, ok=ok: ok(X), [(mat(X), lambda X=X, ok=ok: ok(X), e) for X, e in cand],
                         tier=2, params={"Ai": list(Ai), "Bi": list(Bi)}))
    return out


def transprod():
    out = []
    rng = random.Random(26)
    shapes = [(2, 2, 2)] * 8 + [(2, 3, 2)] * 6 + [(3, 2, 2)] * 6
    for m, k, n in shapes:
        A = sp.Matrix(m, k, [rng.randint(-2, 3) for _ in range(m * k)])
        B = sp.Matrix(k, n, [rng.randint(-2, 3) for _ in range(k * n)])
        truth = (A * B).T
        cand = [(A * B, "algebra")]
        if A.T.cols == B.T.rows:
            cand.append((A.T * B.T, "algebra"))
        if B.cols == A.rows:
            cand.append((B * A, "algebra"))
        cand += [(truth.T, "algebra") if truth.shape != truth.T.shape else (-truth, "sign"), (B.T * A.T + sp.ones(*truth.shape), "algebra")]
        out.append(_case(rf"A = {mat(A)},\ B = {mat(B)}\text{{일 때 }} (AB)^{{T}} = \;?", mat(truth),
                         lambda X=truth, tr=truth: same(X, tr), [(mat(X), lambda X=X, tr=truth: same(X, tr), e) for X, e in cand],
                         tier=1 if (m, k, n) == (2, 2, 2) else 2, params={"A": list(A), "B": list(B)}))
    return out
