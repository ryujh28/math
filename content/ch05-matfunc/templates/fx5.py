"""5장 공식 원자의 구체적 적용 문제."""
import itertools
import random
import numpy as np
import sympy as sp
from texkit import tex, mat
from checks import same, opt, t


def _case(prompt, ans_tex, ans_ok, wrong, tier=None, params=None):
    c = {"params": params or {}, "prompt": prompt, "answer": opt(ans_tex, ans_ok),
         "wrong": [opt(tx, ok, e) for tx, ok, e in wrong]}
    if tier is not None:
        c["tier"] = tier
    return c


def _ok_mat(X, tr):
    return lambda X=X, tr=tr: same(sp.Matrix(X), tr)


def _nice(M):
    """sinh·cosh 대신 지수함수로, 항별로 펼쳐서."""
    return sp.Matrix(M).applyfunc(lambda e: sp.expand(sp.simplify(e).rewrite(sp.exp)))


def _ok_exp(X, A):
    """X(t) = e^{At} ⟺ X′ = AX, X(0) = I (행렬지수 계산과 독립적인 판정)."""
    return lambda X=X, A=A: same(sp.Matrix(X).diff(t), A * sp.Matrix(X)) and same(sp.Matrix(X).subs(t, 0), sp.eye(A.rows))


def _expm(A):
    """2×2 위삼각 또는 회전 생성자의 e^{At} 닫힌 꼴."""
    a, c, d, b = A
    if d == 0:
        if a == b:
            return sp.Matrix([[sp.exp(a * t), c * t * sp.exp(a * t)], [0, sp.exp(a * t)]])
        return sp.Matrix([[sp.exp(a * t), c * (sp.exp(a * t) - sp.exp(b * t)) / (a - b)], [0, sp.exp(b * t)]])
    w = c
    return sp.Matrix([[sp.cos(abs(w) * t), sp.sign(w) * sp.sin(abs(w) * t)], [-sp.sign(w) * sp.sin(abs(w) * t), sp.cos(abs(w) * t)]])


PS = [sp.Matrix([[1, 1], [0, 1]]), sp.Matrix([[1, 0], [1, 1]]), sp.Matrix([[1, 1], [1, 2]]), sp.Matrix([[2, 1], [1, 1]]),
      sp.Matrix([[1, -1], [0, 1]]), sp.Matrix([[1, 2], [0, 1]])]


def expdiagform():
    out = []
    for P, (l1, l2) in itertools.product(PS, [(1, -1), (2, 0), (-1, -2), (1, 3)]):
        D = sp.diag(l1, l2)
        A = P * D * P.inv()
        truth = _nice(P * sp.diag(sp.exp(l1 * t), sp.exp(l2 * t)) * P.inv())
        cand = [(sp.diag(sp.exp(l1 * t), sp.exp(l2 * t)), "missing_factor"),
                (_nice(P.inv() * sp.diag(sp.exp(l1 * t), sp.exp(l2 * t)) * P), "algebra"),
                (_nice(P * sp.diag(sp.exp(-l1 * t), sp.exp(-l2 * t)) * P.inv()), "sign"),
                (_nice(P * sp.diag(sp.exp(l2 * t), sp.exp(l1 * t)) * P.inv()), "wrong_pair")]
        out.append(_case(rf"P = {mat(P)},\ D = {mat(D)},\ A = PDP^{{-1}}\text{{일 때 }} e^{{At}} = \;?", mat(truth),
                         _ok_exp(truth, A), [(mat(X), _ok_exp(X, A), e) for X, e in cand],
                         tier=2, params={"P": list(P), "d": [l1, l2]}))
    return out


def expderiv():
    """e^{At}가 주어지면 A = (d/dt e^{At})|_{t=0}."""
    out = []
    rng = random.Random(51)
    seen = set()
    while len(out) < 20:
        kind = 0 if rng.random() < 0.7 else 1
        if kind == 0:
            a, b, c = rng.choice([-2, -1, 1, 2, 3]), rng.choice([-2, -1, 1, 2]), rng.choice([-1, 1, 2, -3])
            A = sp.Matrix([[a, c], [0, b]]) if a != b else sp.Matrix([[a, c], [0, a]])
        else:
            w = rng.choice([1, 2, 3])
            k = rng.choice([1, -1])
            A = sp.Matrix([[0, k * w], [-k * w, 0]])
        if tuple(A) in seen:
            continue
        seen.add(tuple(A))
        E = _expm(A) if A[1, 0] != 0 else _nice(_expm(A))
        assert _ok_exp(E, A)()
        cand = [(sp.eye(2), "initial_condition"), (-A, "sign"), (A.T, "algebra"), (A + sp.eye(2), "algebra")]
        out.append(_case(rf"e^{{At}} = {mat(E)}\text{{일 때 }} A = \;?", mat(A), _ok_mat(A, A),
                         [(mat(X), _ok_mat(X, A), e) for X, e in cand if X != A],
                         tier=2, params={"A": list(A)}))
    return out


def _pair_tex(A, B):
    return rf"A = {mat(A)},\ B = {mat(B)}"


def expcommute():
    """e^{A+B} = e^A e^B가 보장되는 쌍 (AB = BA)."""
    out = []
    rng = random.Random(52)
    seen = set()

    def rnd():
        return sp.Matrix(2, 2, [rng.randint(-2, 2) for _ in range(4)])

    while len(out) < 20:
        A = rnd()
        if A.is_diagonal() or tuple(A) in seen:
            continue
        seen.add(tuple(A))
        p, q = rng.choice([1, 2, -1, 3]), rng.choice([0, 1, -2, 2])
        B = p * A + q * sp.eye(2)  # A의 다항식 → 교환
        if B == A:
            continue
        bad = []
        while len(bad) < 3:
            Bb = rnd()
            if A * Bb != Bb * A:
                bad.append(Bb)
        ok = lambda A, B: A * B == B * A
        out.append(_case(r"e^{A+B} = e^{A}e^{B}\text{가 보장되는 것은?}", _pair_tex(A, B), lambda A=A, B=B, ok=ok: ok(A, B),
                         [(_pair_tex(A, X), lambda A=A, X=X, ok=ok: ok(A, X), "theorem_condition") for X in bad],
                         params={"A": list(A), "B": list(B)}))
    return out


def _minors_pos(M):
    return all(M[:k, :k].det() > 0 for k in range(1, M.rows + 1))


def _sym(n, rng):
    M = sp.zeros(n, n)
    for i in range(n):
        for j in range(i, n):
            v = rng.randint(-3, 4) if i != j else rng.randint(-2, 5)
            M[i, j] = M[j, i] = v
    return M


def sylvester():
    out = []
    rng = random.Random(53)
    for n, k in ((2, 12), (3, 12)):
        made = 0
        while made < k:
            good = _sym(n, rng)
            if not _minors_pos(good):
                continue
            bad = []
            while len(bad) < 3:
                M = _sym(n, rng)
                if not _minors_pos(M) and M[0, 0] > 0:  # 첫 원소는 양수라 한눈에 안 보이게
                    bad.append(M)
            ok = lambda M: bool(min(np.linalg.eigvalsh(np.array(M.tolist(), dtype=float))) > 1e-9)
            out.append(_case(r"\text{양의 정부호인 대칭행렬은?}", mat(good), lambda M=good, ok=ok: ok(M),
                             [(mat(M), lambda M=M, ok=ok: ok(M), "theorem_condition") for M in bad],
                             tier=1 if n == 2 else 2, params={"A": list(good)}))
            made += 1
    return out
