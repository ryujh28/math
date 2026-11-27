"""2장 행렬과 선형변환 — 생성기."""
import itertools
import random
import sympy as sp
from texkit import tex, mat, vmat, aug, tup, join_terms
from checks import same, opt, step, vstep, decoy, vdecoy


def _mats(n, k, lo=-3, hi=4, seed=0, cond=None):
    rng = random.Random(seed)
    out, seen = [], set()
    tries = 0
    while len(out) < k and tries < 20000:
        tries += 1
        M = sp.Matrix(n, n, [rng.randint(lo, hi) for _ in range(n * n)])
        key = tuple(M)
        if key in seen or (cond and not cond(M)):
            continue
        seen.add(key)
        out.append(M)
    return out


def _o(val, truth):
    return lambda v=val, tr=truth: same(v, tr)


# ---------------------------------------------------------------- 사실 원자
def det2():
    out = []
    for A in _mats(2, 30, seed=1):
        a, b, c, d = A
        truth = A.det()
        cand = [(a * d + b * c, "sign"), (b * c - a * d, "sign"), (a * b - c * d, "algebra"), (a * c - b * d, "algebra"),
                (a * d, "missing_factor"), (truth + 1, "algebra"), (truth - 1, "algebra")]
        out.append({"params": {"A": list(A)}, "tier": 1, "prompt": rf"\det{mat(A)} = \;?",
                    "answer": opt(tex(truth), _o(truth, truth)),
                    "wrong": [opt(tex(v), _o(v, truth), e) for v, e in cand]})
    return out


def inv2():
    out = []
    for A in _mats(2, 30, -3, 4, seed=2, cond=lambda M: M.det() in (1, -1, 2, -2, 3) and M * M != sp.eye(2)):  # A² = I면 답이 문제와 같다
        a, b, c, d = A
        D = A.det()
        inv = sp.Matrix([[d, -b], [-c, a]]) / D
        ok = lambda X, A=A: same(sp.Matrix(X) * A, sp.eye(2))  # X A = I
        cand = [(sp.Matrix([[d, -b], [-c, a]]), "missing_factor"), (sp.Matrix([[d, b], [c, a]]) / D, "sign"),
                (sp.Matrix([[a, -b], [-c, d]]) / D, "algebra"), (sp.Matrix([[d, -c], [-b, a]]) / D, "algebra")]
        out.append({"params": {"A": list(A)}, "tier": 2 if abs(D) > 1 else 1, "prompt": rf"{mat(A)}^{{-1}} = \;?",
                    "answer": opt(mat(inv), lambda X=inv, ok=ok: ok(X)),
                    "wrong": [opt(mat(X), lambda X=X, ok=ok: ok(X), e) for X, e in cand]})
    return out


def matmul2():
    out = []
    As, Bs = _mats(2, 30, -2, 3, seed=3), _mats(2, 30, -2, 3, seed=4)
    for A, Bm in zip(As, Bs):
        truth = A * Bm
        cand = [(Bm * A, "algebra"), (A.multiply_elementwise(Bm), "wrong_pair"), (A.T * Bm, "algebra"), (A * Bm.T, "algebra")]
        out.append({"params": {"A": list(A), "B": list(Bm)}, "tier": 1, "prompt": rf"{mat(A)}{mat(Bm)} = \;?",
                    "answer": opt(mat(truth), _o(truth, truth)),
                    "wrong": [opt(mat(X), _o(X, truth), e) for X, e in cand]})
    return out


def rank3():
    out = []
    rng = random.Random(5)
    for target in (1, 2, 3):
        made = 0
        while made < 8:
            U = sp.Matrix(3, target, [rng.randint(-2, 2) for _ in range(3 * target)])
            V = sp.Matrix(target, 3, [rng.randint(-2, 2) for _ in range(3 * target)])
            A = U * V
            if A.rank() != target or max(abs(e) for e in A) > 9:
                continue
            made += 1
            truth = A.rank()
            out.append({"params": {"A": list(A)}, "tier": 2, "prompt": rf"\operatorname{{rank}}{mat(A)} = \;?",
                        "answer": opt(tex(truth), _o(truth, truth)),
                        "wrong": [opt(tex(v), _o(v, truth), "algebra") for v in (0, 1, 2, 3) if v != truth]})
    return out


def det3():
    out = []
    for A in _mats(3, 30, -2, 3, seed=6):
        truth = A.det()
        m = [A.minor(0, j) for j in range(3)]
        allplus = A[0, 0] * m[0] + A[0, 1] * m[1] + A[0, 2] * m[2]
        diag = A[0, 0] * A[1, 1] * A[2, 2]
        cand = [(allplus, "sign"), (-truth, "sign"), (diag, "algebra"), (truth + 2, "algebra")]
        out.append({"params": {"A": list(A)}, "tier": 2, "prompt": rf"\det{mat(A)} = \;?",
                    "answer": opt(tex(truth), _o(truth, truth)),
                    "wrong": [opt(tex(v), _o(v, truth), e) for v, e in cand]})
    return out


# ---------------------------------------------------------------- 풀이 뼈대
WHY = {
    "el_sign": r"행 연산 $R_i - l\,R_1$에서 부호를 반대로 적용했습니다. 피벗 아래가 0이 되지 않거나 해가 달라집니다.",
    "el_arith": r"소거 중 산술 실수가 있습니다. 이 첨가행렬은 원래 방정식과 해가 다릅니다.",
    "back": r"뒤에서부터 대입할 때 계산이 틀렸습니다.",
    "order": r"해의 성분 순서가 뒤바뀌었습니다.",
    "cof_sign": r"여인수 전개의 부호는 $+,\,-,\,+$로 번갈아 바뀝니다.",
    "minor": r"소행렬식 하나를 잘못 계산했습니다.",
    "sum": r"마지막 합산이 틀렸습니다.",
}


def _solves(M, xs):
    """첨가행렬 M이 해 xs를 갖고, 그 해가 유일한지."""
    M = sp.Matrix(M)
    A, b = M[:, :-1], M[:, -1]
    return same(A * sp.Matrix(xs), b) and A.rank() == A.cols


def gauss3():
    out = []
    rng = random.Random(11)
    tries = 0
    while len(out) < 70 and tries < 4000:
        tries += 1
        L = sp.Matrix([[1, 0, 0], [rng.randint(-2, 2), 1, 0], [rng.randint(-2, 2), rng.randint(-2, 2), 1]])
        U = sp.Matrix([[rng.choice([1, 2, -1]), rng.randint(-2, 2), rng.randint(-2, 2)],
                       [0, rng.choice([1, -1, 2]), rng.randint(-2, 2)],
                       [0, 0, rng.choice([1, -1, 2, 3])]])
        A = L * U
        if L[1, 0] == 0 and L[2, 0] == 0:
            continue
        xs = sp.Matrix([rng.randint(-3, 3) for _ in range(3)])
        b = A * xs
        if max(abs(e) for e in list(A) + list(b)) > 12:
            continue
        truth = A.LUsolve(b)  # 독립 계산
        M0 = A.row_join(b)
        # 1열 소거
        M1 = M0.copy()
        for i in (1, 2):
            M1[i, :] = M1[i, :] - (M0[i, 0] / M0[0, 0]) * M0[0, :]
        M2 = M1.copy()
        M2[2, :] = M2[2, :] - (M1[2, 1] / M1[1, 1]) * M1[1, :]
        x3 = M2[2, 3] / M2[2, 2]
        ok_aug = lambda M, tr=truth: _solves(M, tr)

        def upper1(M):
            return M[1, 0] == 0 and M[2, 0] == 0

        prob = rf"{aug(M0)}\ \text{{를 Gauss 소거로 풀기}}"
        steps = [
            step(rf"R_2, R_3\ \text{{에서 1열 소거:}}\ {aug(M1)}", lambda M=M1, f=ok_aug, up=upper1: f(M) and up(M)),
            step(rf"\text{{2열 소거:}}\ {aug(M2)}", lambda M=M2, f=ok_aug, up=upper1: f(M) and up(M) and M[2, 1] == 0),
            vstep(rf"x_3 = {tex(x3)}", x3, truth[2]),
            vstep(rf"(x_1, x_2, x_3) = {tup(xs)}", xs, truth),
        ]
        # 오답: 부호 반대로 적용한 1열 소거
        B1 = M0.copy()
        r = 1 if M0[1, 0] != 0 else 2
        B1[r, :] = M0[r, :] + (M0[r, 0] / M0[0, 0]) * M0[0, :]
        for i in (1, 2):
            if i != r:
                B1[i, :] = M1[i, :]
        B2 = M2.copy()
        B2[2, 3] = M2[2, 3] + 1
        bad_x = sp.Matrix([xs[2], xs[1], xs[0]])
        decoys = [
            decoy(0, rf"R_2, R_3\ \text{{에서 1열 소거:}}\ {aug(B1)}", lambda M=B1, f=ok_aug, up=upper1: f(M) and up(M), "sign", WHY["el_sign"]),
            decoy(1, rf"\text{{2열 소거:}}\ {aug(B2)}", lambda M=B2, f=ok_aug: f(M), "algebra", WHY["el_arith"]),
            vdecoy(2, rf"x_3 = {tex(x3 + 1)}", x3 + 1, truth[2], "algebra", WHY["back"]),
            vdecoy(3, rf"(x_1, x_2, x_3) = {tup(bad_x)}", bad_x, truth, "algebra", WHY["order"]),
        ]
        tier = 1 if all(e.q == 1 for e in list(M1) + list(M2)) else 2
        out.append({"params": {"A": list(A), "b": list(b)}, "tier": tier, "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda A=A, b=b, xs=xs: None if A * xs == b else "해가 방정식을 만족하지 않음"})
    return out


def cofactor3():
    out = []
    for A in _mats(3, 40, -3, 4, seed=21):
        D = A.det()
        a = [A[0, j] for j in range(3)]
        Ms = [A.minor_submatrix(0, j) for j in range(3)]
        m = [Mi.det() for Mi in Ms]
        expansion = join_terms([(a[0], vmat(Ms[0])), (-a[1], vmat(Ms[1])), (a[2], vmat(Ms[2]))])
        expansion_plus = join_terms([(a[0], vmat(Ms[0])), (a[1], vmat(Ms[1])), (a[2], vmat(Ms[2]))])
        ok_exp = lambda signs, A=A, a=a, Ms=Ms: same(sum(sg * a[j] * Ms[j].det() for j, sg in enumerate(signs)), A.det())
        pv = lambda v: f"\\left({tex(v)}\\right)" if v < 0 else tex(v)
        prod = f"{pv(a[0])}\\cdot {pv(m[0])} - {pv(a[1])}\\cdot {pv(m[1])} + {pv(a[2])}\\cdot {pv(m[2])}"
        steps = [
            step(rf"\det A = {expansion}", lambda f=ok_exp: f((1, -1, 1))),
            vstep(rf"M_{{11}} = {tex(m[0])},\ M_{{12}} = {tex(m[1])},\ M_{{13}} = {tex(m[2])}", m, [A.minor(0, j) for j in range(3)]),
            step(rf"\det A = {prod}", lambda: True),
            vstep(rf"\det A = {tex(D)}", D, A.det()),
        ]
        bad_m = [m[0], m[1] + 1, m[2]]
        decoys = [
            decoy(0, rf"\det A = {expansion_plus}", lambda f=ok_exp: f((1, 1, 1)), "sign", WHY["cof_sign"]),
            vdecoy(1, rf"M_{{11}} = {tex(bad_m[0])},\ M_{{12}} = {tex(bad_m[1])},\ M_{{13}} = {tex(bad_m[2])}", bad_m,
                   [A.minor(0, j) for j in range(3)], "algebra", WHY["minor"]),
            vdecoy(3, rf"\det A = {tex(D + 2)}", D + 2, A.det(), "algebra", WHY["sum"]),
            vdecoy(3, rf"\det A = {tex(-D)}", -D, A.det(), "sign", WHY["cof_sign"]),
        ]
        if 0 in a:
            continue
        out.append({"params": {"A": list(A)}, "tier": 1 if max(abs(e) for e in A) <= 3 else 2,
                    "problem": rf"\det{mat(A)}\ \text{{를 1행 여인수 전개로}}", "steps": steps, "decoys": decoys})
    return out
