"""3장 고유값 문제 — 생성기."""
import itertools
import random
import sympy as sp
from texkit import tex, mat, tup, join_terms, poly_tex
from checks import same, opt, step, vstep, decoy, vdecoy, lam

UNIMOD = [sp.Matrix(m) for m in ([[1, 1], [0, 1]], [[2, 1], [1, 1]], [[1, 2], [1, 3]], [[1, -1], [1, 0]],
                                  [[1, 0], [1, 1]], [[3, 2], [1, 1]], [[1, 1], [1, 2]], [[2, 1], [3, 2]], [[1, -1], [0, 1]])]


def nice2(k, seed=0, distinct=True):
    """정수 고유값을 갖는 2×2 정수 행렬 A = P D P⁻¹."""
    rng = random.Random(seed)
    out, seen = [], set()
    while len(out) < k:
        P = rng.choice(UNIMOD)
        d1, d2 = rng.randint(-3, 4), rng.randint(-3, 4)
        if distinct and d1 == d2:
            continue
        A = P * sp.diag(d1, d2) * P.inv()
        if max(abs(e) for e in A) > 9 or tuple(A) in seen or A.is_diagonal():
            continue
        seen.add(tuple(A))
        out.append((A, P, (d1, d2)))
    return out


def _eigset(A):
    return {k for k, m in A.eigenvals().items() for _ in range(m)} if True else None


def _lam_tex(vals):
    return r"\lambda = " + r",\ ".join(tex(v) for v in vals)


def _vec_ok(A, l):
    return lambda v, A=A, l=l: (sp.Matrix(v) != sp.zeros(2, 1)) and same(A * sp.Matrix(v), l * sp.Matrix(v))


# ---------------------------------------------------------------- 사실 원자
def charpoly2():
    out = []
    for A, P, d in nice2(30, seed=1):
        tr, D = A.trace(), A.det()
        truth = (A - lam * sp.eye(2)).det()
        ok = lambda e, truth=truth: same(sp.expand(e), sp.expand(truth))
        cands = [(lam**2 + tr * lam + D, "sign"), (lam**2 - tr * lam - D, "sign"), (lam**2 - D * lam + tr, "algebra"),
                 (lam**2 - tr * lam + D + 1, "algebra")]
        out.append({"params": {"A": list(A)}, "tier": 1, "prompt": rf"A = {mat(A)}\qquad \det(A - \lambda I) = \;?",
                    "answer": opt(poly_tex(truth, lam), lambda e=truth, ok=ok: ok(e)),
                    "wrong": [opt(poly_tex(e, lam), lambda e=e, ok=ok: ok(e), er) for e, er in cands]})
    return out


def eig2():
    out = []
    for A, P, d in nice2(30, seed=2):
        truth = _eigset(A)
        ok = lambda vals, truth=truth: same(set(vals), truth)
        tr, D = A.trace(), A.det()
        cands = [((A[0, 0], A[1, 1]), "wrong_pair"), ((-d[0], -d[1]), "sign"), ((tr, D), "algebra"), ((d[0] + 1, d[1] - 1), "algebra")]
        ans = tuple(sorted(d))
        out.append({"params": {"A": list(A)}, "tier": 1, "prompt": rf"{mat(A)}\ \text{{의 고유값은?}}",
                    "answer": opt(_lam_tex(ans), lambda v=ans, ok=ok: ok(v)),
                    "wrong": [opt(_lam_tex(sorted(v)), lambda v=v, ok=ok: ok(v), er) for v, er in cands if len(set(v)) == 2]})
    return out


def eigvec2():
    out = []
    for A, P, d in nice2(24, seed=3):
        for j in (0, 1):
            l = d[j]
            v = P[:, j]
            other = P[:, 1 - j]
            ok = _vec_ok(A, l)
            cands = [(other, "wrong_pair"), (sp.Matrix([v[1], v[0]]), "algebra"), (sp.Matrix([v[0], -v[1]]), "sign"),
                     (sp.Matrix([v[0] + 1, v[1]]), "algebra")]
            out.append({"params": {"A": list(A), "lambda": l}, "tier": 2,
                        "prompt": rf"A = {mat(A)},\ \lambda = {tex(l)}\ \text{{에 대한 고유벡터는?}}",
                        "answer": opt(mat(v), lambda q=v, ok=ok: ok(q)),
                        "wrong": [opt(mat(q), lambda q=q, ok=ok: ok(q), er) for q, er in cands]})
    return out


def eig_triangular():
    out = []
    rng = random.Random(4)
    while len(out) < 24:
        dg = [rng.randint(-3, 4) for _ in range(3)]
        if len(set(dg)) < 3:
            continue
        A = sp.Matrix([[dg[0], rng.randint(-3, 3), rng.randint(-3, 3)], [0, dg[1], rng.randint(-3, 3)], [0, 0, dg[2]]])
        if rng.random() < 0.5:
            A = A.T
        truth = _eigset(A)
        ok = lambda vals, truth=truth: same(sorted(vals, key=float), sorted(truth, key=float)) if len(vals) == len(truth) else False
        ans = sorted([A[i, i] for i in range(3)])
        row = [A[0, i] for i in range(3)]
        cands = [(sorted(row), "wrong_pair"), (sorted([-v for v in ans]), "sign"), (sorted([A[0, 2], A[1, 1], A[2, 0]]), "wrong_pair"),
                 (sorted([ans[0], ans[1], A.trace()]), "algebra")]
        out.append({"params": {"A": list(A)}, "tier": 1, "prompt": rf"{mat(A)}\ \text{{의 고유값은?}}",
                    "answer": opt(_lam_tex(ans), lambda v=ans, ok=ok: ok(v)),
                    "wrong": [opt(_lam_tex(v), lambda v=v, ok=ok: ok(v), er) for v, er in cands]})
    return out


def trace_det():
    out = []
    for l1, l2 in itertools.combinations([-3, -2, -1, 1, 2, 3, 4, 5], 2):
        A = sp.diag(l1, l2)
        for ask in ("det", "tr"):
            truth = A.det() if ask == "det" else A.trace()
            other = A.trace() if ask == "det" else A.det()
            cands = [(other, "wrong_pair"), (-truth, "sign"), (l1 - l2, "algebra"), (truth + 1, "algebra")]
            label = r"\det A" if ask == "det" else r"\operatorname{tr} A"
            out.append({"params": {"l": [l1, l2], "ask": ask}, "tier": 1,
                        "prompt": rf"2\times 2\ \text{{행렬}}\ A\text{{의 고유값이}}\ {tex(l1)},\ {tex(l2)}\text{{일 때}}\ {label} = \;?",
                        "answer": opt(tex(truth), lambda v=truth, t=truth: same(v, t)),
                        "wrong": [opt(tex(v), lambda v=v, t=truth: same(v, t), er) for v, er in cands]})
    return out


# ---------------------------------------------------------------- 풀이 뼈대
WHY = {
    "cp_sign": r"$\det(A - \lambda I) = \lambda^2 - (\operatorname{tr}A)\lambda + \det A$. trace 항의 부호가 틀렸습니다.",
    "root": r"특성방정식의 근을 잘못 구했습니다.",
    "vec": r"$(A - \lambda I)\mathbf{v} = \mathbf{0}$을 만족하지 않습니다. 고유벡터가 아닙니다.",
    "order": r"$P$의 열 순서와 $D$의 대각 순서가 맞지 않습니다. 같은 고유값끼리 짝지어야 합니다.",
    "pinv": r"$A = PDP^{-1}$입니다. $P^{-1}DP$는 다른 행렬입니다.",
    "dpow": r"$D^n$은 대각성분을 각각 $n$제곱한 것입니다. $n$을 곱하면 안 됩니다.",
}


def _pv(P):
    return rf"\mathbf{{v}}_1 = {mat(P[:, 0])},\ \mathbf{{v}}_2 = {mat(P[:, 1])}"


def diagonalize():
    out = []
    for A, P, d in nice2(60, seed=11):
        cp = (A - lam * sp.eye(2)).det()
        D = sp.diag(*d)
        eig = _eigset(A)
        ok_pd = lambda P_, D_, A=A: P_.det() != 0 and same(P_ * D_ * P_.inv(), A)
        ok_vecs = lambda P_, d_, A=A: all(same(A * P_[:, j], d_[j] * P_[:, j]) for j in range(2)) and P_.det() != 0
        steps = [
            vstep(rf"\det(A - \lambda I) = {poly_tex(cp, lam)} = 0", cp, (A - lam * sp.eye(2)).det()),
            step(rf"{_lam_tex(d)}", lambda v=d, e=eig: same(set(v), e)),
            step(rf"{_pv(P)}", lambda P_=P, d_=d, f=ok_vecs: f(P_, d_)),
            step(rf"P = {mat(P)},\ D = {mat(D)}", lambda P_=P, D_=D, f=ok_pd: f(P_, D_)),
        ]
        tr, Dt = A.trace(), A.det()
        bad_cp = lam**2 + tr * lam + Dt
        bad_P = sp.Matrix([[P[1, 0], P[0, 1]], [P[0, 0], P[1, 1]]])
        Dsw = sp.diag(d[1], d[0])
        decoys = [
            vdecoy(0, rf"\det(A - \lambda I) = {poly_tex(bad_cp, lam)} = 0", bad_cp, (A - lam * sp.eye(2)).det(), "sign", WHY["cp_sign"]),
            decoy(2, rf"{_pv(bad_P)}", lambda P_=bad_P, d_=d, f=ok_vecs: f(P_, d_), "algebra", WHY["vec"]),
            decoy(3, rf"P = {mat(P)},\ D = {mat(Dsw)}", lambda P_=P, D_=Dsw, f=ok_pd: f(P_, D_), "algebra", WHY["order"]),
            decoy(1, rf"{_lam_tex((-d[0], -d[1]))}", lambda v=(-d[0], -d[1]), e=eig: same(set(v), e), "sign", WHY["root"]),
        ]
        tier = 1 if all(abs(e) <= 4 for e in A) else 2
        out.append({"params": {"A": list(A)}, "tier": tier, "problem": rf"A = {mat(A)}\ \text{{를 대각화}}",
                    "steps": steps, "decoys": decoys,
                    "verify": lambda A=A, P=P, D=D: None if P * D * P.inv() == A else "PDP⁻¹ ≠ A"})
    return out


def matrix_power():
    out = []
    for A, P, d in nice2(60, seed=21):
        if max(abs(v) for v in d) > 3:
            continue
        n = random.Random(str(A)).choice([3, 4, 5])
        D = sp.diag(*d)
        Dn = sp.diag(d[0] ** n, d[1] ** n)
        An = A ** n                                  # 독립 계산
        res = P * Dn * P.inv()
        steps = [
            step(rf"A = PDP^{{-1}},\ P = {mat(P)},\ D = {mat(D)}", lambda P_=P, D_=D, A=A: same(P_ * D_ * P_.inv(), A)),
            vstep(rf"D^{{{n}}} = {mat(Dn)}", Dn, D ** n),
            step(rf"A^{{{n}}} = PD^{{{n}}}P^{{-1}}", lambda: True),
            vstep(rf"A^{{{n}}} = {mat(res)}", res, An),
        ]
        bad_D = n * D
        bad_res = P.inv() * Dn * P
        decoys = [
            vdecoy(1, rf"D^{{{n}}} = {mat(bad_D)}", bad_D, D ** n, "algebra", WHY["dpow"]),
            vdecoy(3, rf"A^{{{n}}} = {mat(bad_res)}", bad_res, An, "algebra", WHY["pinv"]),
            vdecoy(3, rf"A^{{{n}}} = {mat(-res)}", -res, An, "sign", "부호가 틀렸습니다. 고유값의 거듭제곱 부호를 확인하세요."),
        ]
        out.append({"params": {"A": list(A), "n": n}, "tier": 2, "problem": rf"A = {mat(A)}\ \text{{일 때}}\ A^{{{n}}}\ \text{{를 대각화로}}",
                    "steps": steps, "decoys": decoys})
    return out


# ---------------------------------------------------------------- M3.6 2단계: 가족 추가 · 새 뼈대
WHY.update({
    "orth": r"대칭행렬은 고유벡터를 정규화한 직교행렬 $Q$로 대각화합니다($Q^{-1} = Q^{T}$). 정규화하지 않으면 $Q^{T} \neq Q^{-1}$입니다.",
    "tri_ev": r"삼각행렬의 고유값은 대각성분입니다. 다른 성분과 섞지 마세요.",
    "npow": r"$D^n$은 대각성분을 각각 $n$제곱한 것입니다. $\lambda^n$이 아니라 $n\lambda$로 썼습니다.",
    "idem": r"고유값이 0과 1뿐이면 $D^n = D$라서 $A^n = A$입니다.",
    "invol": r"고유값이 $\pm 1$이면 $D^n$은 $n$이 짝수일 때 $I$, 홀수일 때 $D$입니다.",
    "limit": r"$|\lambda| < 1$인 고유값의 거듭제곱은 0으로 갑니다. 1인 고유값만 남습니다.",
    "cp3": r"$\det(A - \lambda I)$ 전개가 틀렸습니다. 대각성분에서 $\lambda$를 빼고 전개합니다.",
    "fac3": r"인수분해가 틀렸습니다. 전개해서 특성다항식과 비교해 보세요.",
    "ev3": r"고유값은 특성다항식의 근입니다. 부호가 틀렸습니다.",
    "vec3": r"$(A - \lambda I)\mathbf{v} = \mathbf{0}$을 만족하지 않습니다.",
})


def _sym_cases(k, seed):
    rng = random.Random(seed)
    Ps = [sp.Matrix([[1, 1], [1, -1]]), sp.Matrix([[1, 2], [2, -1]]), sp.Matrix([[2, 1], [1, -2]]), sp.Matrix([[1, 3], [3, -1]])]
    out, seen = [], set()
    while len(out) < k:
        P = rng.choice(Ps)
        d1, d2 = rng.sample([-3, -2, -1, 1, 2, 3, 4, 5], 2)
        A = P * sp.diag(d1, d2) * P.inv()
        if any(e.q != 1 for e in A) or tuple(A) in seen or max(abs(e) for e in A) > 9:
            continue
        seen.add(tuple(A))
        out.append((A, P, (d1, d2)))
    return out


def diag_families():
    """대각화. 가족: 일반(기존) · 고유값 0 (특이행렬) · 대칭(직교 대각화) · 삼각행렬."""
    out = []
    for c in diagonalize():
        c["params"]["family"] = "general" if 0 not in [e for e in c["verify"].__defaults__[2].diagonal()] else "zero"
        out.append(c)
    gen = [c for c in out if c["params"]["family"] == "general" and sum(1 for d in c["decoys"] if d["ok"]() is not True) >= 2][:26]
    zer = [c for c in out if c["params"]["family"] == "zero"]
    rng = random.Random(71)
    while len(zer) < 14:
        P = rng.choice(UNIMOD)
        k = rng.choice([-3, -2, -1, 1, 2, 3, 4])
        A = P * sp.diag(0, k) * P.inv()
        if max(abs(e) for e in A) > 9 or A.is_diagonal() or any(tuple(A) == tuple(sp.Matrix(c["params"]["A"]).reshape(2, 2)) for c in zer):
            continue
        tmp = [c for c in _diag_one(A, P, (0, k), "zero")]
        zer += tmp
    out = gen + zer[:14]
    for A, P, d in _sym_cases(16, 72):
        Q = sp.Matrix.hstack(*[P[:, j] / P[:, j].norm() for j in range(2)])
        D = sp.diag(*d)
        cp = (A - lam * sp.eye(2)).det()
        eig = _eigset(A)
        ok_q = lambda Q_, D_, A=A: same(Q_.T * Q_, sp.eye(2)) and same(Q_ * D_ * Q_.T, A)
        steps = [
            vstep(rf"\det(A - \lambda I) = {poly_tex(cp, lam)} = 0", cp, (A - lam * sp.eye(2)).det()),
            step(rf"{_lam_tex(d)}", lambda v=d, e=eig: same(set(v), e)),
            step(rf"{_pv(P)}\ (\mathbf{{v}}_1 \cdot \mathbf{{v}}_2 = 0)", lambda P_=P, d_=d, A=A: all(same(A * P_[:, j], d_[j] * P_[:, j]) for j in range(2)) and P_[:, 0].dot(P_[:, 1]) == 0),
            step(rf"Q = {mat(Q)},\ D = {mat(D)},\ Q^{{-1}} = Q^{{T}}", lambda Q_=Q, D_=D, f=ok_q: f(Q_, D_)),
        ]
        decoys = [
            decoy(3, rf"Q = {mat(P)},\ D = {mat(D)},\ Q^{{-1}} = Q^{{T}}", lambda Q_=P, D_=D, f=ok_q: f(Q_, D_), "normalization", WHY["orth"]),
            decoy(1, rf"{_lam_tex((-d[0], -d[1]))}", lambda v=(-d[0], -d[1]), e=eig: same(set(v), e), "sign", WHY["root"]),
            decoy(3, rf"Q = {mat(Q)},\ D = {mat(sp.diag(d[1], d[0]))},\ Q^{{-1}} = Q^{{T}}", lambda Q_=Q, D_=sp.diag(d[1], d[0]), f=ok_q: f(Q_, D_), "algebra", WHY["order"]),
        ]
        out.append({"params": {"A": list(A), "family": "sym"}, "tier": 2, "problem": rf"\text{{대칭행렬}}\ A = {mat(A)}\ \text{{를 직교 대각화}}",
                    "steps": steps, "decoys": decoys, "verify": lambda Q=Q, D=D, A=A: None if Q * D * Q.T == A else "QDQᵀ ≠ A"})
    for a, b, dd in itertools.product([1, 2, -1, 3], [1, 2, -2, 3], [-2, 4, 2, -1]):
        if a == dd:
            continue
        A = sp.Matrix([[a, b], [0, dd]])
        c2 = sp.Matrix([b, dd - a])
        g = sp.gcd(b, dd - a)
        c2 = c2 / g * (1 if c2[1] / g > 0 else -1)          # 정수 기약, 둘째 성분 양수
        P = sp.Matrix.hstack(sp.Matrix([1, 0]), c2)
        out += _diag_one(A, P, (a, dd), "tri", tier=1)
        if sum(1 for c in out if c["params"]["family"] == "tri") >= 16:
            break
    return out


def _diag_one(A, P, d, family, tier=2):
    cp = (A - lam * sp.eye(2)).det()
    D = sp.diag(*d)
    eig = _eigset(A)
    ok_pd = lambda P_, D_, A=A: P_.det() != 0 and same(P_ * D_ * P_.inv(), A)
    ok_vecs = lambda P_, d_, A=A: all(same(A * P_[:, j], d_[j] * P_[:, j]) for j in range(2)) and P_.det() != 0
    steps = [
        vstep(rf"\det(A - \lambda I) = {poly_tex(cp, lam)} = 0", cp, (A - lam * sp.eye(2)).det()),
        step(rf"{_lam_tex(d)}", lambda v=d, e=eig: same(set(v), e)),
        step(rf"{_pv(P)}", lambda P_=P, d_=d, f=ok_vecs: f(P_, d_)),
        step(rf"P = {mat(P)},\ D = {mat(D)}", lambda P_=P, D_=D, f=ok_pd: f(P_, D_)),
    ]
    bad_P = sp.Matrix([[P[1, 0], P[0, 1]], [P[0, 0], P[1, 1]]])
    decoys = [
        decoy(2, rf"{_pv(bad_P)}", lambda P_=bad_P, d_=d, f=ok_vecs: f(P_, d_), "algebra", WHY["vec"]),
        decoy(3, rf"P = {mat(P)},\ D = {mat(sp.diag(d[1], d[0]))}", lambda P_=P, D_=sp.diag(d[1], d[0]), f=ok_pd: f(P_, D_), "algebra", WHY["order"]),
        decoy(1, rf"{_lam_tex((-d[0], -d[1]))}", lambda v=(-d[0], -d[1]), e=eig: same(set(v), e), "sign", WHY["root"]),
    ]
    if family == "tri":
        decoys.append(decoy(1, rf"{_lam_tex((A[0, 0], A[0, 1]))}", lambda v=(A[0, 0], A[0, 1]), e=eig: same(set(v), e), "wrong_pair", WHY["tri_ev"]))
    return [{"params": {"A": list(A), "family": family}, "tier": tier, "problem": rf"A = {mat(A)}\ \text{{를 대각화}}", "steps": steps, "decoys": decoys,
             "verify": lambda A=A, P=P, D=D: None if P * D * P.inv() == A else "PDP⁻¹ ≠ A"}]


def apow_families():
    """거듭제곱. 가족: 특정 n(기존) · 일반 n 공식 · 사영(A² = A) · 고유값 ±1 · 극한 lim Aⁿ."""
    out = []
    for c in matrix_power():
        c["params"]["family"] = "spec"
        out.append(c)
    out = out[:26]
    nn = sp.Symbol("n", integer=True, positive=True)
    rng = random.Random(81)
    seen = set()

    def build(P, d, fam, power, tier, problem, Dtx=None):
        A = P * sp.diag(*d) * P.inv()
        if max(abs(e) for e in A) > 9 or A.is_diagonal() or (fam, tuple(A), str(power)) in seen or any(e.q > 4 for e in A if e.is_Rational):
            return None
        seen.add((fam, tuple(A), str(power)))
        D = sp.diag(*d)
        Dn = sp.diag(*[sp.Pow(v, power) if power != "inf" else (1 if v == 1 else 0) for v in d])
        res = (P * Dn * P.inv()).applyfunc(sp.simplify)
        chk = (lambda X, A=A: all(same(X.subs(nn, k), A ** k) for k in (1, 2, 3, 4))) if power == nn else \
              ((lambda X, A=A: max(abs(float(e)) for e in (sp.Matrix(X) - A ** 80)) < 1e-12) if power == "inf" else
               (lambda X, A=A, k=power: same(X, A ** k)))
        pw = "n" if power == nn else (r"\infty" if power == "inf" else str(power))
        steps = [
            step(rf"A = PDP^{{-1}},\ P = {mat(P)},\ D = {mat(D)}", lambda P_=P, D_=D, A=A: same(P_ * D_ * P_.inv(), A)),
            step(rf"{Dtx or 'D^{' + pw + '}'} = {mat(Dn)}", lambda Dn=Dn, d=d, power=power: same(Dn, sp.diag(*[sp.Pow(v, power) if power != 'inf' else (1 if v == 1 else 0) for v in d]))),
            step(rf"{'A^{' + pw + '}' if power != 'inf' else r'\lim_{n \to \infty} A^{n}'} = PD^{{{'n' if power in (nn, 'inf') else pw}}}P^{{-1}}", lambda: True),
            step(rf"{'A^{' + pw + '}' if power != 'inf' else r'\lim A^{n}'} = {mat(res)}", lambda X=res, f=chk: f(X)),
        ]
        bad = (P.inv() * Dn * P).applyfunc(sp.simplify)
        decoys = [decoy(3, rf"{'A^{' + pw + '}' if power != 'inf' else r'\lim A^{n}'} = {mat(bad)}", lambda X=bad, f=chk: f(X), "algebra", WHY["pinv"])]
        if power == nn:
            bD = sp.diag(*[nn * v for v in d])
            decoys.append(decoy(1, rf"D^{{n}} = {mat(bD)}", lambda: False, "algebra", WHY["npow"]))
        elif power == "inf":
            bD = sp.diag(*[1 for v in d])
            decoys.append(decoy(1, rf"D^{{\infty}} = {mat(bD)}", lambda: False, "algebra", WHY["limit"]))
        else:
            decoys.append(decoy(3, rf"A^{{{pw}}} = {mat(-res)}", lambda X=-res, f=chk: f(X), "sign", WHY["invol" if fam == "invol" else "idem"]))
            if fam == "proj":
                decoys.append(decoy(3, rf"A^{{{pw}}} = {mat(sp.zeros(2))}", lambda X=sp.zeros(2), f=chk: f(X), "algebra", WHY["idem"]))
            if fam == "invol":
                alt = A if power % 2 == 0 else sp.eye(2)
                decoys.append(decoy(3, rf"A^{{{pw}}} = {mat(alt)}", lambda X=alt, f=chk: f(X), "algebra", WHY["invol"]))
        return {"params": {"A": list(A), "family": fam, "n": str(power)}, "tier": tier, "problem": problem(A), "steps": steps, "decoys": decoys}

    gen = []
    for P, d in itertools.product(UNIMOD, [(1, 2), (2, 3), (-1, 2), (1, 3), (2, -1), (3, -1)]):
        c = build(P, d, "general", nn, 3, lambda A: rf"A = {mat(A)}\ \text{{일 때}}\ A^{{n}}\ \text{{의 일반항}}")
        if c:
            gen.append(c)
    out += gen[::max(1, len(gen) // 16)][:16]
    pro = []
    for P, k in itertools.product(UNIMOD, [5, 8, 10, 7]):
        c = build(P, (0, 1), "proj", k, 1, lambda A, k=k: rf"A = {mat(A)}\ \text{{일 때}}\ A^{{{k}}}")
        if c:
            pro.append(c)
    out += pro[:12]
    inv = []
    for P, k in itertools.product(UNIMOD, [10, 11, 20, 7]):
        c = build(P, (1, -1), "invol", k, 2, lambda A, k=k: rf"A = {mat(A)}\ \text{{일 때}}\ A^{{{k}}}")
        if c:
            inv.append(c)
    out += inv[:12]
    lim = []
    for P, h in itertools.product(UNIMOD, [sp.Rational(1, 2), sp.Rational(-1, 2), sp.Rational(1, 3)]):
        c = build(P, (1, h), "limit", "inf", 3, lambda A: rf"A = {mat(A)}\ \text{{일 때}}\ \lim_{{n \to \infty}} A^{{n}}")
        if c:
            lim.append(c)
    out += lim[:12]
    return out


def eig3():
    """3×3 고유값. 가족: 삼각행렬 · 블록(2×2 + 1) · 일반(정수 고유값) · 중근."""
    out = []
    rng = random.Random(91)
    U3 = [sp.Matrix(m) for m in ([[1, 1, 1], [1, 2, 2], [1, 2, 3]], [[1, 0, 1], [1, 1, 1], [0, 1, 1]], [[1, 1, 0], [0, 1, 1], [1, 1, 1]],
                                  [[1, 0, 1], [0, 1, 0], [1, 0, 2]], [[1, 1, 0], [0, 1, 1], [0, 0, 1]])]   # 행렬식 1, 대부분 삼각이 아님
    seen = set()
    specs = []
    for _ in range(400):
        kind = rng.choice(["tri", "block", "general", "rep"])
        if kind == "tri":
            d = rng.sample([-2, -1, 1, 2, 3, 4], 3)
            A = sp.Matrix([[d[0], rng.randint(-2, 2), rng.randint(-2, 2)], [0, d[1], rng.randint(-2, 2)], [0, 0, d[2]]])
        elif kind == "block":
            P = rng.choice(UNIMOD)
            d2 = rng.sample([-2, -1, 1, 2, 3], 2)
            B2 = P * sp.diag(*d2) * P.inv()
            c3 = rng.choice([-1, 2, 3, 4, -3])
            A = sp.diag(B2, sp.Matrix([[c3]]))
        else:
            P = rng.choice(U3)
            d = rng.sample([-2, -1, 1, 2, 3], 3) if kind == "general" else (lambda a, b: [a, a, b])(*rng.sample([-1, 1, 2, 3], 2))
            A = P * sp.diag(*d) * P.inv()
        if any(e.q != 1 for e in A) or max(abs(e) for e in A) > 9 or tuple(A) in seen or A.is_diagonal():
            continue
        seen.add(tuple(A))
        specs.append((kind, A))
    counts = {}
    for kind, A in specs:
        if counts.get(kind, 0) >= 16:
            continue
        cp = sp.expand((A - lam * sp.eye(3)).det())
        ev = A.eigenvals()
        fac = sp.factor(cp)
        vals = sorted([k for k, m in ev.items() for _ in range(m)])
        l1 = max(ev, key=lambda k: (ev[k] == 1, k))
        ns = (A - l1 * sp.eye(3)).nullspace()
        if not ns:
            continue
        v = ns[0] * sp.lcm([e.q for e in ns[0]])
        steps = [
            vstep(rf"\det(A - \lambda I) = {poly_tex(cp, lam)}", cp, sp.expand((A - lam * sp.eye(3)).det())),
            vstep(rf"= {tex(fac)}", fac, cp),
            step(r"\lambda = " + r",\ ".join(tex(x_) for x_ in vals), lambda vals=vals, ev=ev: sorted(vals) == sorted([k for k, m in ev.items() for _ in range(m)])),
            step(rf"\lambda = {tex(l1)}:\ \mathbf{{v}} = {mat(v)}", lambda v=v, A=A, l=l1: v != sp.zeros(3, 1) and same(A * v, l * v)),
        ]
        badcp = sp.expand(cp.subs(lam, -lam)) if kind != "tri" else sp.expand(-cp)
        decoys = [
            vdecoy(2 - 2, rf"\det(A - \lambda I) = {poly_tex(sp.expand(cp + lam), lam)}", sp.expand(cp + lam), sp.expand((A - lam * sp.eye(3)).det()), "algebra", WHY["cp3"]),
            decoy(2, r"\lambda = " + r",\ ".join(tex(-x_) for x_ in vals), lambda vals=[-x_ for x_ in vals], ev=ev: sorted(vals) == sorted([k for k, m in ev.items() for _ in range(m)]), "sign", WHY["ev3"]),
            decoy(3, rf"\lambda = {tex(l1)}:\ \mathbf{{v}} = {mat(v + sp.Matrix([1, 0, 0]))}", lambda v=v + sp.Matrix([1, 0, 0]), A=A, l=l1: v != sp.zeros(3, 1) and same(A * v, l * v), "algebra", WHY["vec3"]),
        ]
        if kind == "tri":
            decoys.append(decoy(2, r"\lambda = " + r",\ ".join(tex(x_) for x_ in (A[0, 0], A[0, 1], A[0, 2])), lambda vals=[A[0, 0], A[0, 1], A[0, 2]], ev=ev: sorted(vals) == sorted([k for k, m in ev.items() for _ in range(m)]), "wrong_pair", WHY["tri_ev"]))
        counts[kind] = counts.get(kind, 0) + 1
        out.append({"params": {"A": list(A), "family": kind}, "tier": {"tri": 1, "block": 2, "general": 3, "rep": 3}[kind],
                    "problem": rf"A = {mat(A)}\ \text{{의 고유값과 고유벡터 하나}}", "steps": steps, "decoys": decoys})
    return out
