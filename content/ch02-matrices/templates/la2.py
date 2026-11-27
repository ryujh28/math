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


# ---------------------------------------------------------------- M3.6 2단계: 가족 추가 · 새 뼈대
WHY.update({
    "swap": r"피벗 자리가 0이면 그 아래 0이 아닌 행과 먼저 바꿔야 합니다. 0으로는 나눌 수 없습니다.",
    "none": r"마지막 행이 $0 = c\ (c \neq 0)$이면 모순이라 해가 없습니다. 자유변수가 아닙니다.",
    "inf": r"마지막 행이 $0 = 0$이면 그 변수는 자유변수입니다. 해가 하나로 정해지지 않습니다.",
    "free": r"자유변수 $t$에 대한 해를 뒤에서부터 대입하다 틀렸습니다. 원래 식에 넣어 확인해 보세요.",
    "cof_row": r"0이 가장 많은 행(또는 열)을 골라 전개하면 계산할 소행렬식이 줄어듭니다. 부호는 $(-1)^{i+j}$입니다.",
    "tri": r"삼각행렬의 행렬식은 대각성분의 곱입니다.",
    "gj_op": r"행 연산을 첨가행렬 전체(오른쪽 $I$ 부분 포함)에 적용해야 합니다.",
    "gj_inv": r"$A^{-1}$는 왼쪽이 $I$가 된 뒤의 오른쪽 블록입니다. 계산이 틀리면 $AA^{-1} \neq I$입니다.",
    "cr_col": r"$A_i$는 $A$의 $i$번째 열을 $\mathbf{b}$로 바꾼 행렬입니다. 다른 열을 바꿨습니다.",
    "cr_div": r"Cramer 공식은 $x_i = \dfrac{\det A_i}{\det A}$입니다. 분자와 분모가 바뀌었습니다.",
    "cr_det": r"행렬식 계산이 틀렸습니다.",
})


def _rand_LU(rng):
    L = sp.Matrix([[1, 0, 0], [rng.randint(-2, 2), 1, 0], [rng.randint(-2, 2), rng.randint(-2, 2), 1]])
    U = sp.Matrix([[rng.choice([1, 2, -1]), rng.randint(-2, 2), rng.randint(-2, 2)],
                   [0, rng.choice([1, -1, 2]), rng.randint(-2, 2)], [0, 0, rng.choice([1, -1, 2, 3])]])
    return L, U


def _elim(M0):
    """1열·2열 소거 (피벗 0이면 아래 행과 교환). (M1, M2, swapped)"""
    M = M0.copy()
    swapped = False
    if M[0, 0] == 0:
        k = next(i for i in (1, 2) if M[i, 0] != 0)
        M.row_swap(0, k)
        swapped = True
    M1 = M.copy()
    for i in (1, 2):
        M1[i, :] = M1[i, :] - (M[i, 0] / M[0, 0]) * M[0, :]
    M2 = M1.copy()
    if M2[1, 1] == 0 and M2[2, 1] != 0:
        M2.row_swap(1, 2)
    if M2[1, 1] != 0:
        M2[2, :] = M2[2, :] - (M2[2, 1] / M2[1, 1]) * M2[1, :]
    return M1, M2, swapped


def gauss_families():
    """Gauss 소거. 가족: 해가 하나(기존) · 행 교환이 필요 · 해 없음 · 해가 무한히 많음(매개변수 해)."""
    out = []
    for c in gauss3():
        c["params"]["family"] = "unique"
        out.append(c)
    out = out[:30]
    rng = random.Random(31)
    tsym = sp.Symbol("t")
    made = {"swap": 0, "none": 0, "inf": 0}
    tries = 0
    while min(made.values()) < 18 and tries < 20000:
        tries += 1
        L, U = _rand_LU(rng)
        kind = rng.choice([k for k, v in made.items() if v < 18])
        if kind == "swap":
            A = L * U
            P = sp.Matrix([[0, 1, 0], [1, 0, 0], [0, 0, 1]])
            A = P * A                       # 첫 행 피벗을 0으로: (0이 아니면 다시)
            if A[0, 0] != 0:
                A[0, 0] = 0
            if A.det() == 0:
                continue
            xs = sp.Matrix([rng.randint(-3, 3) for _ in range(3)])
            b = A * xs
        else:
            U = U.copy()
            U[2, 2] = 0
            A = L * U
            if A.rank() != 2:
                continue
            xs = sp.Matrix([rng.randint(-3, 3) for _ in range(3)])
            b = A * xs
            if kind == "none":
                b = b + L * sp.Matrix([0, 0, rng.choice([1, 2, -1, 3])])
        if max(abs(e) for e in list(A) + list(b)) > 12:
            continue
        M0 = A.row_join(b)
        M1, M2, swapped = _elim(M0)
        if any(e.q > 4 for e in list(M1) + list(M2) if e.is_Rational):
            continue
        if kind == "swap" and not swapped:
            continue
        if kind != "swap" and (M2[2, 0] != 0 or M2[2, 1] != 0 or M2[2, 2] != 0 or M2[1, 1] == 0):
            continue
        ok_same_sol = lambda M, M0=M0: sp.Matrix(M).rref()[0] == M0.rref()[0]     # 행 동치 (같은 해집합)
        prob = rf"{aug(M0)}\ \text{{를 Gauss 소거로 풀기}}"
        head = rf"R_1 \leftrightarrow R_{{{2 if M0[1, 0] != 0 else 3}}},\ " if swapped else ""
        steps = [
            step(rf"{head}\text{{1열 소거:}}\ {aug(M1)}", lambda M=M1, f=ok_same_sol: f(M) and M[1, 0] == 0 and M[2, 0] == 0),
            step(rf"\text{{2열 소거:}}\ {aug(M2)}", lambda M=M2, f=ok_same_sol: f(M) and M[2, 0] == 0 and M[2, 1] == 0),
        ]
        decoys = []
        if kind == "swap":
            truth = A.LUsolve(b)
            x3 = M2[2, 3] / M2[2, 2]
            steps += [vstep(rf"x_3 = {tex(x3)}", x3, truth[2]), vstep(rf"(x_1, x_2, x_3) = {tup(xs)}", xs, truth)]
            B0 = M0.copy()
            Bd = B0.copy()
            decoys.append(vdecoy(2, rf"x_3 = {tex(x3 + 1)}", x3 + 1, truth[2], "algebra", WHY["back"]))
            if xs[0] != xs[2]:
                decoys.append(vdecoy(3, rf"(x_1, x_2, x_3) = {tup(sp.Matrix([xs[2], xs[1], xs[0]]))}", sp.Matrix([xs[2], xs[1], xs[0]]), truth, "algebra", WHY["order"]))
        elif kind == "none":
            c3 = M2[2, 3]
            steps += [step(rf"\text{{3행: }} 0 = {tex(c3)}\ (\text{{모순}})", lambda c=c3: c != 0),
                      step(r"\text{해 없음}", lambda A=A, b=b: A.rank() < A.row_join(b).rank())]
            decoys += [decoy(2, r"\text{3행: } 0 = 0\ (x_3\text{는 자유변수})", lambda c=c3: c == 0, "theorem_condition", WHY["none"]),
                       decoy(3, r"\text{해가 무한히 많음}", lambda A=A, b=b: A.rank() == A.row_join(b).rank(), "theorem_condition", WHY["none"])]
        else:
            sol = sp.solve(list(A * sp.Matrix(sp.symbols("x1 x2 x3")) - b), sp.symbols("x1 x2 x3"), dict=True)[0]
            x1s, x2s, x3s = sp.symbols("x1 x2 x3")
            free = x3s if x3s not in sol else (x2s if x2s not in sol else x1s)
            par = sp.Matrix([sp.expand(sol.get(v, v).subs(free, tsym)) for v in (x1s, x2s, x3s)])
            ok_par = lambda P_, A=A, b=b: same(A * P_.subs(tsym, 0), b) and same(A * P_.subs(tsym, 1), b) and not same(P_.subs(tsym, 0), P_.subs(tsym, 1))
            steps += [step(rf"\text{{3행: }} 0 = 0\ \Rightarrow\ x_{str(free)[1]} = t\ (\text{{자유변수}})", lambda c=M2[2, 3]: c == 0),
                      step(rf"(x_1, x_2, x_3) = {tup(par)}", lambda P_=par, f=ok_par: f(P_))]
            ks = [i for i in range(3) if par[i].has(tsym) and par[i] != tsym]
            if not ks:
                continue
            badp = par.copy()
            badp[ks[0]] = par[ks[0]].subs(tsym, -tsym)
            decoys += [decoy(2, r"\text{3행: } 0 = 0\ \Rightarrow\ \text{해 없음}", lambda: False, "theorem_condition", WHY["inf"]),
                       decoy(3, rf"(x_1, x_2, x_3) = {tup(badp)}", lambda P_=badp, f=ok_par: f(P_), "sign", WHY["free"])]
        B1 = M1.copy()
        B1[1, 3] = M1[1, 3] + 1
        decoys.append(decoy(0, rf"{head}\text{{1열 소거:}}\ {aug(B1)}", lambda M=B1, f=ok_same_sol: f(M), "algebra", WHY["el_arith"]))
        made[kind] += 1
        out.append({"params": {"A": list(A), "b": list(b), "family": kind}, "tier": {"swap": 2, "none": 2, "inf": 3}[kind],
                    "problem": prob, "steps": steps, "decoys": decoys})
    return out


def _sols(A, b):
    """검사용 해 몇 개 (해가 없으면 빈 목록)."""
    xs = sp.symbols("x1 x2 x3")
    sol = sp.solve(list(A * sp.Matrix(xs) - b), xs, dict=True)
    if not sol:
        return []
    sol = sol[0]
    out = []
    for val in (0, 1, -2):
        v = sp.Matrix([sol.get(xi, xi) for xi in xs]).subs({xi: val for xi in xs})
        out.append(v)
    return out


def cofactor_families():
    """여인수 전개. 가족: 1행 전개(기존) · 0이 많은 행·열 골라 전개 · 삼각행렬 · 1열 전개."""
    out = []
    for c in cofactor3():
        c["params"]["family"] = "row1"
        out.append(c)
    out = out[:24]
    rng = random.Random(41)
    seen = set()
    for kind, want in (("zero", 18), ("tri", 12), ("col1", 18)):
        made = 0
        while made < want:
            A = sp.Matrix(3, 3, [rng.randint(-3, 3) for _ in range(9)])
            if kind == "zero":
                i = rng.randint(0, 2)
                js = rng.sample([0, 1, 2], 2)
                for j in js:
                    A[i, j] = 0
                if A[i, 3 - sum(js)] == 0:
                    continue
                line, idx = "row", i
            elif kind == "tri":
                for (i, j) in ((1, 0), (2, 0), (2, 1)):
                    A[i, j] = 0
                if 0 in (A[0, 0], A[1, 1], A[2, 2]):
                    continue
                line, idx = "col", 0
            else:
                if 0 in (A[0, 0], A[1, 0], A[2, 0]):
                    continue
                line, idx = "col", 0
            if tuple(A) in seen or A.det() == 0:
                continue
            seen.add(tuple(A))
            D = A.det()
            pos = [(idx, j) for j in range(3)] if line == "row" else [(i, idx) for i in range(3)]
            terms = [(A[i, j], (-1) ** (i + j), A.minor_submatrix(i, j)) for i, j in pos]
            nz = [(a, sg, M) for a, sg, M in terms if a != 0]
            name = (rf"{idx + 1}\text{{행}}" if line == "row" else rf"{idx + 1}\text{{열}}")
            expansion = join_terms([(sg * a, vmat(M)) for a, sg, M in nz])
            ok_exp = lambda signs, nz=nz, A=A: same(sum(s_ * a * M.det() for (a, _, M), s_ in zip(nz, signs)), A.det())
            mins = [M.det() for _, _, M in nz]
            labels = [rf"M_{{{i + 1}{j + 1}}}" for (i, j) in pos if A[i, j] != 0]
            pv = lambda v: f"\\left({tex(v)}\\right)" if v < 0 else tex(v)
            prod = " + ".join(f"{pv(sg * a)}\\cdot {pv(mm)}" for (a, sg, _), mm in zip(nz, mins))
            steps = [
                step(rf"{name}\ \text{{전개:}}\ \det A = {expansion}", lambda f=ok_exp, nz=nz: f([sg for _, sg, _ in nz])),
                vstep(r",\ ".join(f"{lb} = {tex(mm)}" for lb, mm in zip(labels, mins)), mins, [M.det() for _, _, M in nz]),
                step(rf"\det A = {prod}", lambda: True),
                vstep(rf"\det A = {tex(D)}", D, A.det()),
            ]
            plus = join_terms([(a, vmat(M)) for a, sg, M in nz])
            decoys = [vdecoy(3, rf"\det A = {tex(-D)}", -D, A.det(), "sign", WHY["cof_sign"]),
                      vdecoy(3, rf"\det A = {tex(D + 2)}", D + 2, A.det(), "algebra", WHY["sum"])]
            if any(sg < 0 for _, sg, _ in nz):
                decoys.append(decoy(0, rf"{name}\ \text{{전개:}}\ \det A = {plus}", lambda f=ok_exp, nz=nz: f([1] * len(nz)), "sign", WHY["cof_row"]))
            bad = list(mins)
            bad[0] += 1
            decoys.append(vdecoy(1, r",\ ".join(f"{lb} = {tex(mm)}" for lb, mm in zip(labels, bad)), bad, [M.det() for _, _, M in nz], "algebra", WHY["minor"]))
            if kind == "tri":
                decoys.append(vdecoy(3, rf"\det A = {tex(A[0, 0] + A[1, 1] + A[2, 2])}", A[0, 0] + A[1, 1] + A[2, 2], A.det(), "algebra", WHY["tri"]))
            prob = rf"\det{mat(A)}\ \text{{를 여인수 전개로}}" + (r"\ (\text{0이 많은 줄을 골라})" if kind == "zero" else (r"\ (\text{1열로})" if kind == "col1" else ""))
            made += 1
            out.append({"params": {"A": list(A), "family": kind}, "tier": {"zero": 1, "tri": 1, "col1": 2}[kind],
                        "problem": prob, "steps": steps, "decoys": decoys})
    return out


def gauss_jordan_inverse():
    """[A | I]를 행 연산으로 [I | A⁻¹]로. 가족: 2×2 · 3×3(정수 역행렬) · 3×3(분수) · 3×3(행 교환 필요)."""
    out = []
    rng = random.Random(51)
    seen = set()
    for kind, want in (("2x2", 16), ("3x3", 18), ("frac", 14), ("swap", 12)):
        made = 0
        tries = 0
        while made < want and tries < 20000:
            tries += 1
            n = 2 if kind == "2x2" else 3
            A = sp.Matrix(n, n, [rng.randint(-2, 3) for _ in range(n * n)])
            D = A.det()
            if D == 0 or tuple(A) in seen:
                continue
            if kind in ("2x2", "3x3", "swap") and abs(D) != 1:
                continue
            if kind == "frac" and abs(D) not in (2, 3):
                continue
            if kind == "swap" and A[0, 0] != 0:
                continue
            if kind != "swap" and A[0, 0] == 0:
                continue
            Ai = A.inv()
            M = A.row_join(sp.eye(n))
            stages = []
            Mc = M.copy()
            ok = True
            for j in range(n):
                if Mc[j, j] == 0:
                    k = next((i for i in range(j + 1, n) if Mc[i, j] != 0), None)
                    if k is None:
                        ok = False
                        break
                    Mc.row_swap(j, k)
                Mc[j, :] = Mc[j, :] / Mc[j, j]
                for i in range(n):
                    if i != j:
                        Mc[i, :] = Mc[i, :] - Mc[i, j] * Mc[j, :]
                stages.append(Mc.copy())
            if not ok or any(e.is_Rational and e.q > 6 for st in stages for e in st):
                continue
            seen.add(tuple(A))
            same_row_space = lambda S, A=A, n=n: same(sp.Matrix(S)[:, n:] * A, sp.Matrix(S)[:, :n])     # [L | R]가 [A | I]와 행 동치 ⇔ R·A = L
            steps = [step(rf"[A \mid I] = {aug(M, n)}", lambda: True)]
            for j, S in enumerate(stages):
                steps.append(step(rf"\text{{{j + 1}열 정리:}}\ {aug(S, n)}", lambda S=S, f=same_row_space, j=j, n=n: f(S) and all(S[i, j] == (1 if i == j else 0) for i in range(n))))
            steps.append(step(rf"A^{{-1}} = {mat(Ai)}", lambda X=Ai, A=A, n=n: same(A * X, sp.eye(n))))
            bad = stages[0].copy()
            bad[:, n:] = stages[0][:, n:] * 0 + (M[:, n:] if True else 0)  # 오른쪽 I에 연산을 안 한 실수
            decoys = [
                decoy(1, rf"\text{{1열 정리:}}\ {aug(bad, n)}", lambda S=bad, f=same_row_space: f(S), "algebra", WHY["gj_op"]),
                decoy(len(steps) - 1, rf"A^{{-1}} = {mat(Ai.T)}", lambda X=Ai.T, A=A, n=n: same(A * X, sp.eye(n)), "algebra", WHY["gj_inv"]),
                decoy(len(steps) - 1, rf"A^{{-1}} = {mat(-Ai)}", lambda X=-Ai, A=A, n=n: same(A * X, sp.eye(n)), "sign", WHY["gj_inv"]),
            ]
            made += 1
            out.append({"params": {"A": list(A), "family": kind}, "tier": {"2x2": 1, "3x3": 2, "frac": 3, "swap": 3}[kind],
                        "problem": rf"A = {mat(A)}\ \text{{의 역행렬을 Gauss–Jordan으로}}", "steps": steps, "decoys": decoys,
                        "verify": lambda X=Ai, A=A: None if A * X == sp.eye(A.rows) else "AA⁻¹ ≠ I"})
    return out


def cramer():
    """Cramer 공식. 가족: 2×2 정수해 · 2×2 분수해 · 3×3 · 행렬식이 음수."""
    out = []
    rng = random.Random(61)
    seen = set()
    for kind, want in (("2x2", 16), ("2frac", 14), ("3x3", 18), ("neg", 12)):
        made = 0
        tries = 0
        while made < want and tries < 20000:
            tries += 1
            n = 3 if kind == "3x3" else 2
            A = sp.Matrix(n, n, [rng.randint(-3, 4) for _ in range(n * n)])
            D = A.det()
            if D == 0 or tuple(A) in seen or list(A).count(0) > (1 if n == 3 else 0):
                continue
            if kind == "neg" and D > 0:
                continue
            if kind != "neg" and D < 0 and kind != "3x3":
                continue
            if kind == "2frac":
                b = sp.Matrix([rng.randint(-4, 5) for _ in range(n)])
                xs = A.LUsolve(b)
                if all(v.q == 1 for v in xs) or any(v.q > 6 for v in xs):
                    continue
            else:
                xs = sp.Matrix([rng.randint(-3, 3) for _ in range(n)])
                b = A * xs
            if max(abs(e) for e in b) > 15 or len(set(xs)) < n or 0 in xs:
                continue
            seen.add(tuple(A))
            Ds = []
            for i in range(n):
                Ai = A.copy()
                Ai[:, i] = b
                Ds.append(Ai.det())
            names = [f"x_{i + 1}" for i in range(n)]
            var = ["x", "y", "z"][:n]
            eqs = r",\ ".join(join_terms([(A[r, c], var[c]) for c in range(n)]) + f" = {tex(b[r])}" for r in range(n))
            steps = [vstep(rf"\det A = {tex(D)}", D, A.det()),
                     vstep(r",\ ".join(rf"\det A_{{{i + 1}}} = {tex(Ds[i])}" for i in range(n)), Ds, [A.copy().col_del(i) or 0 for i in range(n)] if False else Ds),
                     vstep(rf"({', '.join(var)}) = {tup(xs)}", xs, A.LUsolve(b))]
            def _ok_Ds(Ds=Ds, A=A, b=b, n=n):
                for i in range(n):
                    M_ = A.copy()
                    M_[:, i] = b
                    if not same(Ds[i], M_.det()):
                        return False
                return True
            steps[1] = step(steps[1]["tex"], _ok_Ds)
            wrongA = A.copy()
            wrongA[0, :] = b.T
            bad_inv = sp.Matrix([D / d if d != 0 else 0 for d in Ds])
            decoys = [
                vdecoy(2, rf"({', '.join(var)}) = {tup(bad_inv)}", bad_inv, A.LUsolve(b), "algebra", WHY["cr_div"]),
                vdecoy(0, rf"\det A = {tex(-D)}", -D, A.det(), "sign", WHY["cr_det"]),
                decoy(1, rf"\det A_1 = {tex(wrongA.det())},\ " + r",\ ".join(rf"\det A_{{{i + 1}}} = {tex(Ds[i])}" for i in range(1, n)),
                      lambda v=wrongA.det(), t_=Ds[0]: same(v, t_), "wrong_pair", WHY["cr_col"]),
            ]
            if not any(same(d.get("expr", 0) if isinstance(d, dict) else 0, 0) for d in []):
                pass
            made += 1
            out.append({"params": {"A": list(A), "b": list(b), "family": kind}, "tier": {"2x2": 1, "2frac": 2, "3x3": 3, "neg": 2}[kind],
                        "problem": rf"{eqs}\ \text{{를 Cramer 공식으로}}", "steps": steps, "decoys": decoys,
                        "verify": lambda A=A, b=b, xs=xs: None if A * xs == b else "해 확인 실패"})
    return out
