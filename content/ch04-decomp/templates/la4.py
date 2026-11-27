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


# ---------------------------------------------------------------- M3.6 2단계: 가족 추가 · 새 뼈대
WHY.update({
    "orig": r"원점을 지나는 직선 $y = cx$는 $A$가 $x_i$ 한 열뿐입니다. 1로 된 열을 넣으면 절편이 생깁니다.",
    "quad": r"이차곡선 맞춤에서 $A$의 열은 $1, x_i, x_i^2$입니다. $A^TA$의 성분은 $\sum x_i^k$ 꼴입니다.",
    "lu2": r"$l_{21} = \dfrac{a_{21}}{a_{11}}$입니다. 분자와 분모가 바뀌었습니다.",
    "sv_sq": r"특이값은 $A^TA$ 고유값의 제곱근입니다. 고유값 자체가 아닙니다.",
    "sv_u": r"$\mathbf{u}_i = \dfrac{A\mathbf{v}_i}{\sigma_i}$입니다. $\sigma_i$로 나누지 않으면 단위벡터가 아닙니다.",
    "sv_ord": r"$\Sigma$의 특이값은 큰 것부터 쓰고, $V$의 열도 같은 순서로 맞춥니다.",
    "sv_ata": r"$A^TA$를 계산하다 틀렸습니다. $AA^T$와 섞였거나 산술 실수가 있습니다.",
    "ata1": r"한 열뿐이면 $A^TA = \sum x_i^2$입니다. 데이터 개수 $n$이 아닙니다.",
    "c02": r"$c_0$(상수항)과 $c_2$($x^2$의 계수)를 바꿔 적었습니다.",
    "pm_dot": r"$\mathbf{a}^T\mathbf{a} = \sum a_i^2$입니다. 성분을 제곱하지 않고 그냥 더했습니다.",
    "pm_noden": r"분모 $\mathbf{n}^T\mathbf{n}$을 빠뜨렸습니다. $\mathbf{n}$이 단위벡터가 아니면 $P^2 \neq P$입니다.",
    "pm_inv": r"$P = A(A^TA)^{-1}A^T$입니다. $(A^TA)^{-1}$을 빠뜨리면 $P^2 \neq P$입니다.",
    "pm_line": r"직선 위로의 사영행렬은 $\dfrac{\mathbf{a}\mathbf{a}^T}{\mathbf{a}^T\mathbf{a}}$입니다. 분모를 빠뜨렸습니다.",
    "pm_comp": r"평면(법선 $\mathbf{n}$) 위로의 사영은 $I - \dfrac{\mathbf{n}\mathbf{n}^T}{\mathbf{n}^T\mathbf{n}}$입니다. 법선 위로의 사영과 바꿨습니다.",
})


def lsq_families():
    """최소제곱. 가족: 직선 y = c₀ + c₁x(기존) · 원점을 지나는 직선 y = cx · 이차곡선 y = c₀ + c₁x + c₂x²."""
    out = []
    for c in lsq_line():
        c["params"]["family"] = "line"
        out.append(c)
    out = out[:30]
    rng = random.Random(21)
    seen = set()
    orig, quad = [], []
    cs = sp.symbols("c0 c1 c2")
    for _ in range(4000):
        n = rng.choice([3, 4])
        xs = sorted(rng.sample([-2, -1, 1, 2, 3], n))
        ys = [rng.randint(-3, 6) for _ in range(n)]
        if (tuple(xs), tuple(ys)) in seen:
            continue
        seen.add((tuple(xs), tuple(ys)))
        pts = r",\ ".join(f"({xi},\\ {yi})" for xi, yi in zip(xs, ys))
        b = sp.Matrix(ys)
        if len(orig) < 18:
            A = sp.Matrix([[xi] for xi in xs])
            G, h = A.T * A, A.T * b
            c = G.solve(h)
            S = sum((cs[0] * xi - yi) ** 2 for xi, yi in zip(xs, ys))
            truth = sp.Matrix([sp.solve(sp.diff(S, cs[0]), cs[0])[0]])
            if c[0].q <= 9 and (A * c - b).norm() != 0:
                A2 = sp.Matrix([[1, xi] for xi in xs])
                steps = [
                    step(rf"A = {mat(A)},\ \mathbf{{b}} = {mat(b)}", lambda A=A: True),
                    vstep(rf"A^{{T}}A = {tex(G[0])},\ A^{{T}}\mathbf{{b}} = {tex(h[0])}", (G[0], h[0]), (sum(xi**2 for xi in xs), sum(xi * yi for xi, yi in zip(xs, ys)))),
                    vstep(rf"c = {tex(c[0])}", c[0], truth[0]),
                    vstep(rf"y = {join_terms([(c[0], 'x')])}", c[0], truth[0]),
                ]
                decoys = [
                    step(rf"A = {mat(A2)},\ \mathbf{{b}} = {mat(b)}", lambda: False) | {"pos": 0, "error": "wrong_pair", "why": WHY["orig"]},
                    vdecoy(2, rf"c = {tex(h[0] / n)}", h[0] / n, truth[0], "algebra", WHY["sol"]),
                    vdecoy(1, rf"A^{{T}}A = {tex(n)},\ A^{{T}}\mathbf{{b}} = {tex(h[0])}", (n, h[0]), (sum(xi**2 for xi in xs), sum(xi * yi for xi, yi in zip(xs, ys))), "algebra", WHY["ata1"]),
                ]
                orig.append({"params": {"x": xs, "y": ys, "family": "origin"}, "tier": 1,
                             "problem": rf"\text{{점}}\ {pts}\ \text{{에 원점을 지나는 직선}}\ y = cx\ \text{{를 최소제곱으로}}", "steps": steps, "decoys": decoys})
        if len(quad) < 18 and n == 4:
            A = sp.Matrix([[1, xi, xi**2] for xi in xs])
            G, h = A.T * A, A.T * b
            c = G.solve(h)
            if any(ci.q > 12 for ci in c) or (A * c - b).norm() == 0:
                continue
            S = sum((cs[0] + cs[1] * xi + cs[2] * xi**2 - yi) ** 2 for xi, yi in zip(xs, ys))
            ind = sp.solve([sp.diff(S, ci) for ci in cs], cs)
            truth = sp.Matrix([ind[ci] for ci in cs])
            steps = [
                step(rf"A = {mat(A)},\ \mathbf{{b}} = {mat(b)}", lambda: True),
                vstep(rf"A^{{T}}A = {mat(G)},\ A^{{T}}\mathbf{{b}} = {mat(h)}", (G, h), (A.T * A, A.T * b)),
                vstep(rf"(c_0, c_1, c_2) = {tup(c)}", c, truth),
                vstep(rf"y = {join_terms([(c[0], ''), (c[1], 'x'), (c[2], 'x^{2}')])}", c, truth),
            ]
            Ab = sp.Matrix([[1, xi, xi] for xi in xs])
            decoys = [
                step(rf"A = {mat(Ab)},\ \mathbf{{b}} = {mat(b)}", lambda: False) | {"pos": 0, "error": "algebra", "why": WHY["quad"]},
                vdecoy(1, rf"A^{{T}}A = {mat(G)},\ A^{{T}}\mathbf{{b}} = {mat(h + sp.Matrix([1, 0, 0]))}", (G, h + sp.Matrix([1, 0, 0])), (A.T * A, A.T * b), "algebra", WHY["atb"]),
                vdecoy(3, rf"y = {join_terms([(c[2], ''), (c[1], 'x'), (c[0], 'x^{2}')])}", sp.Matrix([c[2], c[1], c[0]]), truth, "algebra", WHY["c02"]),
            ]
            quad.append({"params": {"x": xs, "y": ys, "family": "quad"}, "tier": 3,
                         "problem": rf"\text{{점}}\ {pts}\ \text{{에 이차곡선}}\ y = c_0 + c_1x + c_2x^{{2}}\ \text{{을 최소제곱으로}}", "steps": steps, "decoys": decoys})
    return out + orig + quad


def lu_families():
    """LU 분해. 가족: 3×3 일반(기존) · 3×3 승수가 0인 자리 있음 · 2×2."""
    out = []
    for c in lu3():
        c["params"]["family"] = "general"
        c["tier"] = 3                           # 승수 세 개를 모두 구하는 3×3이 가장 어렵다
        out.append(c)
    out = out[:26]
    rng = random.Random(31)
    seen = set()
    zero, two = [], []
    for _ in range(6000):
        if len(zero) < 20:
            L = sp.Matrix([[1, 0, 0], [rng.randint(-2, 2), 1, 0], [rng.randint(-2, 2), rng.randint(-2, 2), 1]])
            U = sp.Matrix([[rng.choice([1, 2, -1, 3]), rng.randint(-2, 3), rng.randint(-2, 3)], [0, rng.choice([1, -1, 2]), rng.randint(-2, 3)], [0, 0, rng.choice([1, -1, 2, 3])]])
            if (L[1, 0] == 0) == (L[2, 1] == 0) and L[2, 0] != 0:
                pass
            if not (L[1, 0] == 0 or L[2, 1] == 0 or L[2, 0] == 0) or (L[1, 0] == 0 and L[2, 0] == 0 and L[2, 1] == 0):
                continue
            A = L * U
            if tuple(A) in seen or max(abs(e) for e in A) > 12:
                continue
            seen.add(tuple(A))
            Lr, Ur, _ = A.LUdecomposition()
            l21, l31 = A[1, 0] / A[0, 0], A[2, 0] / A[0, 0]
            A1 = A.copy()
            A1[1, :] = A[1, :] - l21 * A[0, :]
            A1[2, :] = A[2, :] - l31 * A[0, :]
            l32 = A1[2, 1] / A1[1, 1]
            ok_lu = lambda L_, U_, A=A: L_.is_lower and U_.is_upper and all(L_[i, i] == 1 for i in range(3)) and same(L_ * U_, A)
            steps = [
                vstep(rf"l_{{21}} = {tex(l21)},\ l_{{31}} = {tex(l31)}", (l21, l31), (Lr[1, 0], Lr[2, 0])),
                step(rf"\text{{1열 소거 후}}\ {mat(A1)}", lambda M=A1, Ur=Ur: same(M[0, :], Ur[0, :]) and M[1, 0] == 0 and M[2, 0] == 0 and same(M[1, :], Ur[1, :])),
                vstep(rf"l_{{32}} = {tex(l32)}", l32, Lr[2, 1]),
                step(rf"L = {mat(L)},\ U = {mat(U)}", lambda L_=L, U_=U, f=ok_lu: f(L_, U_)),
            ]
            Ub = U.copy()
            Ub[1, 2] = U[1, 2] + 1
            Lt = L.T
            decoys = [
                decoy(3, rf"L = {mat(Lt)},\ U = {mat(U)}", lambda L_=Lt, U_=U, f=ok_lu: f(L_, U_), "algebra", WHY["l_pos"]),
                decoy(3, rf"L = {mat(L)},\ U = {mat(Ub)}", lambda L_=L, U_=Ub, f=ok_lu: f(L_, U_), "algebra", WHY["u_arith"]),
                vdecoy(2, rf"l_{{32}} = {tex(-l32 if l32 else 1)}", -l32 if l32 else 1, Lr[2, 1], "sign", WHY["l_sign"]),
            ]
            if l21 or l31:
                decoys.append(vdecoy(0, rf"l_{{21}} = {tex(-l21)},\ l_{{31}} = {tex(-l31)}", (-l21, -l31), (Lr[1, 0], Lr[2, 0]), "sign", WHY["l_sign"]))
            zero.append({"params": {"A": list(A), "family": "zeros"}, "tier": 2, "problem": rf"A = {mat(A)}\ \text{{의 LU 분해}}", "steps": steps, "decoys": decoys,
                         "verify": lambda L=L, U=U, A=A: None if L * U == A else "LU ≠ A"})
        if len(two) < 20:
            a, b_ = rng.choice([1, 2, -1, 3, -2]), rng.randint(-3, 4)
            l = rng.choice([1, 2, -1, -2, 3, sp.Rational(1, 2)])
            dd = rng.choice([1, -1, 2, 3, -3])
            L = sp.Matrix([[1, 0], [l, 1]])
            U = sp.Matrix([[a, b_], [0, dd]])
            A = L * U
            if any(e.q != 1 for e in A) or ("2", tuple(A)) in seen:
                continue
            seen.add(("2", tuple(A)))
            l21 = A[1, 0] / A[0, 0]
            A1 = A.copy()
            A1[1, :] = A[1, :] - l21 * A[0, :]
            ok_lu = lambda L_, U_, A=A: L_.is_lower and U_.is_upper and L_[0, 0] == 1 and L_[1, 1] == 1 and same(L_ * U_, A)
            steps = [
                vstep(rf"l_{{21}} = \dfrac{{a_{{21}}}}{{a_{{11}}}} = {tex(l21)}", l21, A[1, 0] / A[0, 0]),
                step(rf"R_2 - l_{{21}}R_1:\ {mat(A1)}", lambda M=A1, U=U: same(M, U)),
                step(rf"L = {mat(L)},\ U = {mat(U)}", lambda L_=L, U_=U, f=ok_lu: f(L_, U_)),
            ]
            Lb = sp.Matrix([[1, 0], [A[0, 0] / A[1, 0] if A[1, 0] else 2, 1]])
            decoys = [
                vdecoy(0, rf"l_{{21}} = \dfrac{{a_{{11}}}}{{a_{{21}}}} = {tex(A[0, 0] / A[1, 0])}", A[0, 0] / A[1, 0], A[1, 0] / A[0, 0], "algebra", WHY["lu2"]) if A[1, 0] else None,
                decoy(2, rf"L = {mat(sp.Matrix([[1, 0], [-l, 1]]))},\ U = {mat(U)}", lambda L_=sp.Matrix([[1, 0], [-l, 1]]), U_=U, f=ok_lu: f(L_, U_), "sign", WHY["l_sign"]),
                decoy(2, rf"L = {mat(L.T)},\ U = {mat(U)}", lambda L_=L.T, U_=U, f=ok_lu: f(L_, U_), "algebra", WHY["l_pos"]),
            ]
            two.append({"params": {"A": list(A), "family": "2x2"}, "tier": 1, "problem": rf"A = {mat(A)}\ \text{{의 LU 분해}}", "steps": steps,
                        "decoys": [d for d in decoys if d], "verify": lambda L=L, U=U, A=A: None if L * U == A else "LU ≠ A"})
        if len(zero) >= 20 and len(two) >= 20:
            break
    return out + zero + two


def _orth2(c, s_):
    return sp.Matrix([[c, -s_], [s_, c]])


def svd2():
    """2×2 SVD: AᵀA → 특이값 → V → U = AV/σ. 가족: 일반 · 대칭 양정부호 · 계수 1(rank 1) · 대각(음수 성분)."""
    out = []
    import math
    rng = random.Random(51)
    cands = {"general": [], "sym": [], "rank1": [], "diag": []}
    rngv = range(-5, 6)
    for a_, b_, c_, d_ in itertools.product(rngv, rngv, rngv, rngv):
        g11, g12, g22 = a_ * a_ + c_ * c_, a_ * b_ + c_ * d_, b_ * b_ + d_ * d_
        t, dt = g11 + g22, g11 * g22 - g12 * g12
        disc = t * t - 4 * dt
        if t == 0 or disc <= 0 or math.isqrt(disc) ** 2 != disc or (t + math.isqrt(disc)) % 2:
            continue
        l1, l2 = (t + math.isqrt(disc)) // 2, (t - math.isqrt(disc)) // 2
        sq = lambda v: math.isqrt(v) ** 2 == v
        if b_ == 0 and c_ == 0:
            fam = "diag" if a_ * d_ != 0 and (a_ < 0 or d_ < 0) and abs(a_) != abs(d_) else None
        elif a_ * d_ - b_ * c_ == 0:
            fam = "rank1" if sq(l1) else None
        elif b_ == c_:
            fam = "sym" if sq(l1) and sq(l2) else None
        else:
            fam = "general" if (sq(l1) and sq(l2)) or (sq(l1 // math.gcd(l1, l2)) and sq(l2 // math.gcd(l1, l2))) else None
        if fam:
            cands[fam].append((a_, b_, c_, d_))
    seen = set()
    specs = []
    for fam, k in (("general", 22), ("sym", 16), ("rank1", 14), ("diag", 8)):
        pool = cands[fam]
        rng.shuffle(pool)
        specs += [(fam, sp.Matrix([[q[0], q[1]], [q[2], q[3]]])) for q in pool[:k * 3]]
    counts = {}
    for fam, A in specs:
        if counts.get(fam, 0) >= {"general": 22, "sym": 16, "rank1": 14, "diag": 8}[fam]:
            continue
        if tuple(A) in seen:
            continue
        seen.add(tuple(A))
        G = A.T * A
        ev = sorted(G.eigenvals().keys(), reverse=True)
        if all(e in (0, 1) for e in ev):
            continue
        sv = [sp.sqrt(e) for e in ev]
        Vcols = []
        for e in ev:
            ns = (G - e * sp.eye(2)).nullspace()
            v = ns[0] / ns[0].norm()
            Vcols.append(v)
        if len(ev) == 1:
            continue
        Vm = sp.Matrix.hstack(*Vcols)
        Ucols = []
        for j in range(2):
            if sv[j] != 0:
                Ucols.append(A * Vm[:, j] / sv[j])
            else:
                u0 = Ucols[0]
                Ucols.append(sp.Matrix([-u0[1], u0[0]]))
        Um = sp.Matrix.hstack(*Ucols).applyfunc(sp.radsimp)
        Vm = Vm.applyfunc(sp.radsimp)
        if max(len(tex(e)) for e in list(Um) + list(Vm)) > 26:
            continue
        S = sp.diag(*sv)
        ok_svd = lambda U_, S_, V_, A=A: same(U_.T * U_, sp.eye(2)) and same(V_.T * V_, sp.eye(2)) and same(U_ * S_ * V_.T, A) and bool(S_[0, 0] >= S_[1, 1]) and bool(S_[1, 1] >= 0)
        steps = [
            vstep(rf"A^{{T}}A = {mat(G)}", G, A.T * A),
            step(rf"\lambda = {tex(ev[0])},\ {tex(ev[1])}\ \Rightarrow\ \sigma_1 = {tex(sv[0])},\ \sigma_2 = {tex(sv[1])}", lambda sv=sv, A=A: same(sorted(sv, reverse=True), sorted([sp.sqrt(e) for e in (A.T * A).eigenvals()], reverse=True))),
            step(rf"V = {mat(Vm)}", lambda V_=Vm, G=G, ev=ev: same(V_.T * V_, sp.eye(2)) and all(same(G * V_[:, j], ev[j] * V_[:, j]) for j in range(2))),
            step(rf"U = {mat(Um)}\ \left(\mathbf{{u}}_i = \tfrac{{A\mathbf{{v}}_i}}{{\sigma_i}}\right)", lambda U_=Um, S_=S, V_=Vm, f=ok_svd: f(U_, S_, V_)),
            step(rf"A = U\Sigma V^{{T}},\ \Sigma = {mat(S)}", lambda U_=Um, S_=S, V_=Vm, f=ok_svd: f(U_, S_, V_)),
        ]
        Ub = sp.Matrix.hstack(*[A * Vm[:, j] for j in range(2)])
        decoys = [
            step(rf"\lambda = {tex(ev[0])},\ {tex(ev[1])}\ \Rightarrow\ \sigma_1 = {tex(ev[0])},\ \sigma_2 = {tex(ev[1])}", lambda ev=ev, sv=sv: same(list(ev), list(sv))) | {"pos": 1, "error": "missing_factor", "why": WHY["sv_sq"]},
            step(rf"A = U\Sigma V^{{T}},\ \Sigma = {mat(sp.diag(sv[1], sv[0]))}", lambda U_=Um, S_=sp.diag(sv[1], sv[0]), V_=Vm, f=ok_svd: f(U_, S_, V_)) | {"pos": 4, "error": "algebra", "why": WHY["sv_ord"]},
            vdecoy(0, rf"A^{{T}}A = {mat(A * A.T)}", A * A.T, A.T * A, "algebra", WHY["sv_ata"]) if not same(A * A.T, A.T * A) else None,
        ]
        if sv[1] != 0:
            decoys.append(step(rf"U = {mat(Ub)}\ \left(\mathbf{{u}}_i = \tfrac{{A\mathbf{{v}}_i}}{{\sigma_i}}\right)", lambda U_=Ub, S_=S, V_=Vm, f=ok_svd: f(U_, S_, V_)) | {"pos": 3, "error": "normalization", "why": WHY["sv_u"]})
        counts[fam] = counts.get(fam, 0) + 1
        out.append({"params": {"A": list(A), "family": fam}, "tier": {"diag": 1, "sym": 2, "general": 3, "rank1": 2}[fam],
                    "problem": rf"A = {mat(A)}\ \text{{의 특이값 분해}}", "steps": steps, "decoys": [d for d in decoys if d],
                    "verify": lambda U_=Um, S_=S, V_=Vm, f=ok_svd: None if f(U_, S_, V_) else "UΣVᵀ ≠ A"})
    return out


def projection_matrix():
    """사영행렬. 가족: ℝ² 직선 aaᵀ/aᵀa · ℝ³ 직선 · ℝ³ 평면(두 열의 열공간, A(AᵀA)⁻¹Aᵀ) · ℝ³ 평면(법선, I − nnᵀ/nᵀn)."""
    out = []
    rng = random.Random(41)
    seen = set()
    vec = lambda n, lo, hi: sp.Matrix([rng.randint(lo, hi) for _ in range(n)])
    for fam, want in (("line2", 14), ("line3", 14), ("plane_cols", 16), ("plane_n", 14)):
        made = 0
        for _ in range(3000):
            if made >= want:
                break
            if fam in ("line2", "line3"):
                a = vec(2 if fam == "line2" else 3, -3, 3)
                if a.dot(a) <= 1 or tuple(a) in seen:
                    continue
                seen.add(tuple(a))
                aa = a.dot(a)
                P = a * a.T / aa
                steps = [vstep(rf"\mathbf{{a}}^{{T}}\mathbf{{a}} = {tex(aa)}", aa, a.dot(a)),
                         vstep(rf"\mathbf{{a}}\mathbf{{a}}^{{T}} = {mat(a * a.T)}", a * a.T, a * a.T),
                         vstep(rf"P = \frac{{\mathbf{{a}}\mathbf{{a}}^{{T}}}}{{\mathbf{{a}}^{{T}}\mathbf{{a}}}} = {mat(P)}", P, a * (a.T * a).inv() * a.T),
                         step(rf"P^{{2}} = P,\ P\mathbf{{a}} = \mathbf{{a}}\ (\text{{확인}})", lambda P=P, a=a: same(P * P, P) and same(P * a, a))]
                decoys = [vdecoy(2, rf"P = {mat(a * a.T)}", a * a.T, a * (a.T * a).inv() * a.T, "missing_factor", WHY["pm_line"]),
                          vdecoy(2, rf"P = \frac{{\mathbf{{a}}\mathbf{{a}}^{{T}}}}{{\mathbf{{a}}^{{T}}\mathbf{{a}}}} = {mat(sp.eye(a.rows) - P)}", sp.eye(a.rows) - P, P, "wrong_pair", WHY["pm_comp"]),
                          vdecoy(0, rf"\mathbf{{a}}^{{T}}\mathbf{{a}} = {tex(sum(a))}", sum(a), a.dot(a), "algebra", WHY["pm_dot"])]
                prob = rf"\mathbf{{a}} = {tup(a)}\ \text{{방향 직선 위로의 사영행렬}}"
            elif fam == "plane_cols":
                c1, c2 = vec(3, -2, 2), vec(3, -2, 2)
                A = sp.Matrix.hstack(c1, c2)
                if A.rank() < 2 or tuple(A) in seen:
                    continue
                G = A.T * A
                if G.det() == 0 or any(e.q > 20 for e in G.inv()):
                    continue
                seen.add(tuple(A))
                Gi = G.inv()
                P = A * Gi * A.T
                if any(e.q > 20 for e in P):
                    continue
                steps = [vstep(rf"A^{{T}}A = {mat(G)}", G, A.T * A),
                         vstep(rf"(A^{{T}}A)^{{-1}} = {mat(Gi)}", Gi, G.inv()),
                         vstep(rf"P = A(A^{{T}}A)^{{-1}}A^{{T}} = {mat(P)}", P, A * (A.T * A).inv() * A.T),
                         step(rf"P^{{2}} = P,\ PA = A\ (\text{{확인}})", lambda P=P, A=A: same(P * P, P) and same(P * A, A))]
                decoys = [vdecoy(2, rf"P = AA^{{T}} = {mat(A * A.T)}", A * A.T, A * (A.T * A).inv() * A.T, "missing_factor", WHY["pm_inv"]),
                          vdecoy(1, rf"(A^{{T}}A)^{{-1}} = {mat(G.adjugate())}", G.adjugate(), G.inv(), "missing_factor", r"역행렬은 $\dfrac{1}{\det}$를 곱한 수반행렬입니다. 행렬식으로 나누지 않았습니다.") if G.det() != 1 else None,
                          vdecoy(2, rf"P = A(A^{{T}}A)^{{-1}}A^{{T}} = {mat(sp.eye(3) - P)}", sp.eye(3) - P, P, "wrong_pair", WHY["pm_comp"])]
                prob = rf"A = {mat(A)}\ \text{{의 열공간 위로의 사영행렬}}"
            else:
                n_ = vec(3, -2, 2)
                if n_ == sp.zeros(3, 1) or ("n", tuple(n_)) in seen:
                    continue
                seen.add(("n", tuple(n_)))
                nn = n_.dot(n_)
                Pn = n_ * n_.T / nn
                P = sp.eye(3) - Pn
                steps = [vstep(rf"\mathbf{{n}}^{{T}}\mathbf{{n}} = {tex(nn)}", nn, n_.dot(n_)),
                         vstep(rf"\frac{{\mathbf{{n}}\mathbf{{n}}^{{T}}}}{{\mathbf{{n}}^{{T}}\mathbf{{n}}}} = {mat(Pn)}", Pn, n_ * n_.T / n_.dot(n_)),
                         vstep(rf"P = I - \frac{{\mathbf{{n}}\mathbf{{n}}^{{T}}}}{{\mathbf{{n}}^{{T}}\mathbf{{n}}}} = {mat(P)}", P, sp.eye(3) - n_ * n_.T / n_.dot(n_)),
                         step(rf"P^{{2}} = P,\ P\mathbf{{n}} = \mathbf{{0}}\ (\text{{확인}})", lambda P=P, n_=n_: same(P * P, P) and same(P * n_, sp.zeros(3, 1)))]
                decoys = [vdecoy(2, rf"P = {mat(Pn)}", Pn, sp.eye(3) - n_ * n_.T / n_.dot(n_), "wrong_pair", WHY["pm_comp"]),
                          vdecoy(2, rf"P = I - \mathbf{{n}}\mathbf{{n}}^{{T}} = {mat(sp.eye(3) - n_ * n_.T)}", sp.eye(3) - n_ * n_.T, sp.eye(3) - n_ * n_.T / n_.dot(n_), "missing_factor", WHY["pm_noden"]) if nn != 1 else None,
                          vdecoy(0, rf"\mathbf{{n}}^{{T}}\mathbf{{n}} = {tex(sum(n_))}", sum(n_), n_.dot(n_), "algebra", r"$\mathbf{n}^T\mathbf{n} = \sum n_i^2$입니다. 성분을 제곱하지 않고 그냥 더했습니다.") if sum(n_) != nn else None]
                prob = rf"\text{{평면}}\ {join_terms([(n_[0], 'x'), (n_[1], 'y'), (n_[2], 'z')])} = 0\ \text{{위로의 사영행렬}}"
            made += 1
            out.append({"params": {"family": fam, "key": str(seen and list(seen)[-1])}, "tier": {"line2": 1, "line3": 2, "plane_cols": 3, "plane_n": 2}[fam],
                        "problem": prob, "steps": steps, "decoys": [d for d in decoys if d]})
    return out
