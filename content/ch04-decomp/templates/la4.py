"""4장 행렬 분해 — 생성기."""
import itertools
import random
import sympy as sp
from texkit import tex, mat, tup, join_terms
from checks import same, opt, step, vstep, decoy, vdecoy

# 피타고라스 회전 (cos, sin) 유리수
ROT = [(sp.Rational(3, 5), sp.Rational(4, 5)), (sp.Rational(4, 5), sp.Rational(3, 5)), (1, 0), (0, 1),
       (sp.Rational(5, 13), sp.Rational(12, 13)), (sp.Rational(-3, 5), sp.Rational(4, 5))]


def _R(c, s_):
    return sp.Matrix([[c, -s_], [s_, c]])


def _sv_tex(vals):
    return r"\sigma_1 = " + tex(vals[0]) + r",\ \sigma_2 = " + tex(vals[1])


def singular_values():
    out = []
    rng = random.Random(1)
    seen = set()
    for _ in range(300):
        U, V = _R(*rng.choice(ROT)), _R(*rng.choice(ROT))
        s1, s2 = sorted(rng.sample([1, 2, 3, 5, 10], 2), reverse=True)
        A = U * sp.diag(s1, s2) * V.T
        if any(e.q != 1 for e in A) or tuple(A) in seen or A.is_diagonal():
            continue
        seen.add(tuple(A))
        truth = sorted(A.singular_values(), reverse=True)        # 독립 계산
        ok = lambda v, tr=truth: same(sorted(v, key=lambda q: -float(q)), tr)
        ev = sorted((A.T * A).eigenvals().keys(), reverse=True)
        eA = list(A.eigenvals().keys())
        cands = [(ev, "missing_factor"), ([sp.sqrt(abs((A.T * A)[0, 0])), sp.sqrt(abs((A.T * A)[1, 1]))], "algebra"),
                 ([s1 + 1, s2], "algebra"), ([s1, s2 + 1], "algebra"), ([sp.sqrt(s1), sp.sqrt(s2)], "algebra"),
                 ([s1 + s2, s1 - s2], "algebra")]
        if all(e.is_real for e in eA) and len(eA) == 2:
            cands.append(([abs(e) for e in eA], "wrong_pair"))
        out.append({"params": {"A": list(A)}, "tier": 2, "prompt": rf"A = {mat(A)}\ \text{{의 특이값은?}}",
                    "answer": opt(_sv_tex([s1, s2]), lambda v=[s1, s2], ok=ok: ok(v)),
                    "wrong": [opt(_sv_tex(sorted(v, key=lambda q: -float(q))), lambda v=v, ok=ok: ok(v), er) for v, er in cands]})
        if len(out) >= 20:
            break
    return out


def ata():
    out = []
    rng = random.Random(2)
    for _ in range(30):
        A = sp.Matrix(3, 2, [rng.randint(-2, 3) for _ in range(6)])
        truth = A.T * A
        G = A.T * A
        diagonly = sp.diag(G[0, 0], G[1, 1])
        cands = [(sp.Matrix([[G[0, 0], -G[0, 1]], [-G[1, 0], G[1, 1]]]), "sign"), (diagonly, "algebra"),
                 (sp.Matrix([[G[0, 0], G[0, 1] + 1], [G[1, 0] + 1, G[1, 1]]]), "algebra"),
                 (sp.Matrix(2, 2, [sum(A[:, 0]) ** 2, sum(A[:, 0]) * sum(A[:, 1]), sum(A[:, 0]) * sum(A[:, 1]), sum(A[:, 1]) ** 2]), "algebra")]
        out.append({"params": {"A": list(A)}, "tier": 1, "prompt": rf"A = {mat(A)}\qquad A^{{T}}A = \;?",
                    "answer": opt(mat(truth), lambda X=truth, t=truth: same(X, t)),
                    "wrong": [opt(mat(X), lambda X=X, t=truth: same(X, t), er) for X, er in cands]})
    return out


# ---------------------------------------------------------------- 풀이 뼈대
WHY = {
    "ata": r"$A^TA$의 $(1,1)$ 성분은 데이터 개수 $n$이고 $(2,2)$ 성분이 $\sum x_i^2$입니다. 두 자리를 바꿨습니다.",
    "atb": r"$A^T\mathbf{b}$ 계산이 틀렸습니다: 첫 성분은 $\sum y_i$, 둘째 성분은 $\sum x_iy_i$.",
    "sol": r"정규방정식의 해가 아닙니다.",
    "swap": r"절편과 기울기를 바꿔 적었습니다.",
    "l_sign": r"$L$에 들어가는 승수는 $R_i - l_{ij}R_j$의 $l_{ij}$ 그대로입니다. 부호를 바꾸면 안 됩니다.",
    "l_pos": r"승수는 $L$의 대각 아래(하삼각)에 들어갑니다.",
    "u_arith": r"소거 계산이 틀렸습니다. $LU \ne A$가 됩니다.",
}


def lsq_line():
    out = []
    rng = random.Random(11)
    seen = set()
    for _ in range(3000):
        n = rng.choice([3, 4])
        xs = sorted(rng.sample(range(-2, 5), n))
        ys = [rng.randint(-2, 6) for _ in range(n)]
        key = (tuple(xs), tuple(ys))
        if key in seen:
            continue
        seen.add(key)
        A = sp.Matrix([[1, xi] for xi in xs])
        b = sp.Matrix(ys)
        G, h = A.T * A, A.T * b
        c = G.solve(h)
        if any(abs(ci.q) > 4 for ci in c) or (A * c - b).norm() == 0:
            continue
        c0, c1 = sp.symbols("c0 c1")
        Ssq = sum((c0 + c1 * xi - yi) ** 2 for xi, yi in zip(xs, ys))
        ind = sp.solve([sp.diff(Ssq, c0), sp.diff(Ssq, c1)], [c0, c1])   # 독립: 제곱합 최소화
        truth = sp.Matrix([ind[c0], ind[c1]])
        pts = r",\ ".join(f"({xi},\\ {yi})" for xi, yi in zip(xs, ys))
        prob = rf"\text{{점}}\ {pts}\ \text{{에 직선}}\ y = c_0 + c_1x\ \text{{를 최소제곱으로}}"
        ok_c = lambda v, tr=truth: same(sp.Matrix(v), tr)
        steps = [
            step(rf"A = {mat(A)},\ \mathbf{{b}} = {mat(b)}", lambda A=A, xs=xs: same(A, sp.Matrix([[1, xi] for xi in xs]))),
            vstep(rf"A^{{T}}A = {mat(G)},\ A^{{T}}\mathbf{{b}} = {mat(h)}", (G, h), (A.T * A, A.T * b)),
            step(rf"(c_0, c_1) = {tup(c)}", lambda v=c, f=ok_c: f(v)),
            step(rf"y = {join_terms([(c[0], ''), (c[1], 'x')])}", lambda v=c, f=ok_c: f(v)),
        ]
        Gb = sp.Matrix([[sum(xs) ** 2 if False else G[1, 1], G[0, 1]], [G[1, 0], G[0, 0]]])
        hb = sp.Matrix([h[0] + 1, h[1]])
        decoys = [
            vdecoy(1, rf"A^{{T}}A = {mat(Gb)},\ A^{{T}}\mathbf{{b}} = {mat(h)}", (Gb, h), (A.T * A, A.T * b), "algebra", WHY["ata"]),
            vdecoy(1, rf"A^{{T}}A = {mat(G)},\ A^{{T}}\mathbf{{b}} = {mat(hb)}", (G, hb), (A.T * A, A.T * b), "algebra", WHY["atb"]),
            decoy(3, rf"y = {join_terms([(c[1], ''), (c[0], 'x')])}", lambda v=(c[1], c[0]), f=ok_c: f(v), "algebra", WHY["swap"]),
            decoy(2, rf"(c_0, c_1) = {tup(c + sp.Matrix([1, 0]))}", lambda v=c + sp.Matrix([1, 0]), f=ok_c: f(v), "algebra", WHY["sol"]),
        ]
        tier = 2 if all(ci.q == 1 for ci in c) else 3
        out.append({"params": {"x": xs, "y": ys}, "tier": tier, "problem": prob, "steps": steps, "decoys": decoys})
        if len(out) >= 60:
            break
    return out


def lu3():
    out = []
    rng = random.Random(21)
    seen = set()
    for _ in range(4000):
        L = sp.Matrix([[1, 0, 0], [rng.randint(-2, 2), 1, 0], [rng.randint(-2, 2), rng.randint(-2, 2), 1]])
        U = sp.Matrix([[rng.choice([1, 2, -1, 3]), rng.randint(-2, 3), rng.randint(-2, 3)],
                       [0, rng.choice([1, -1, 2]), rng.randint(-2, 3)], [0, 0, rng.choice([1, -1, 2, 3])]])
        if L[1, 0] == 0 or L[2, 1] == 0:
            continue
        A = L * U
        if tuple(A) in seen or max(abs(e) for e in A) > 12:
            continue
        seen.add(tuple(A))
        Lr, Ur, _ = A.LUdecomposition()                # 독립 계산
        l21, l31 = A[1, 0] / A[0, 0], A[2, 0] / A[0, 0]
        A1 = A.copy()
        A1[1, :] = A[1, :] - l21 * A[0, :]
        A1[2, :] = A[2, :] - l31 * A[0, :]
        l32 = A1[2, 1] / A1[1, 1]
        ok_lu = lambda L_, U_, A=A: L_.is_lower and U_.is_upper and all(L_[i, i] == 1 for i in range(3)) and same(L_ * U_, A)
        steps = [
            vstep(rf"l_{{21}} = {tex(l21)},\ l_{{31}} = {tex(l31)}", (l21, l31), (Lr[1, 0], Lr[2, 0])),
            step(rf"\text{{1열 소거 후}}\ {mat(A1)}", lambda M=A1, A=A, Ur=Ur: same(M[0, :], Ur[0, :]) and M[1, 0] == 0 and M[2, 0] == 0
                 and same(M[1, :], Ur[1, :])),
            vstep(rf"l_{{32}} = {tex(l32)}", l32, Lr[2, 1]),
            step(rf"L = {mat(L)},\ U = {mat(U)}", lambda L_=L, U_=U, f=ok_lu: f(L_, U_)),
        ]
        Ls = sp.Matrix([[1, 0, 0], [-L[1, 0], 1, 0], [-L[2, 0], -L[2, 1], 1]])
        Lt = L.T
        Ub = U.copy()
        Ub[1, 2] = U[1, 2] + 1
        decoys = [
            vdecoy(0, rf"l_{{21}} = {tex(-l21)},\ l_{{31}} = {tex(-l31)}", (-l21, -l31), (Lr[1, 0], Lr[2, 0]), "sign", WHY["l_sign"]),
            decoy(3, rf"L = {mat(Ls)},\ U = {mat(U)}", lambda L_=Ls, U_=U, f=ok_lu: f(L_, U_), "sign", WHY["l_sign"]),
            decoy(3, rf"L = {mat(Lt)},\ U = {mat(U)}", lambda L_=Lt, U_=U, f=ok_lu: f(L_, U_), "algebra", WHY["l_pos"]),
            decoy(3, rf"L = {mat(L)},\ U = {mat(Ub)}", lambda L_=L, U_=Ub, f=ok_lu: f(L_, U_), "algebra", WHY["u_arith"]),
        ]
        out.append({"params": {"A": list(A)}, "tier": 2, "problem": rf"A = {mat(A)}\ \text{{의 LU 분해}}", "steps": steps, "decoys": decoys,
                    "verify": lambda L=L, U=U, A=A: None if L * U == A else "LU ≠ A"})
        if len(out) >= 60:
            break
    return out
