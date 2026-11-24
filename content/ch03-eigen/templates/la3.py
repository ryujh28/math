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
    for A, P, d in nice2(18, seed=1):
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
    for A, P, d in nice2(20, seed=2):
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
    for _ in range(16):
        dg = [rng.randint(-3, 4) for _ in range(3)]
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
    "cp_sign": "det(A − λI) = λ² − (tr A)λ + det A. trace 항의 부호가 틀렸습니다.",
    "root": "특성방정식의 근을 잘못 구했습니다.",
    "vec": "(A − λI)v = 0을 만족하지 않습니다. 고유벡터가 아닙니다.",
    "order": "P의 열 순서와 D의 대각 순서가 맞지 않습니다. 같은 고유값끼리 짝지어야 합니다.",
    "pinv": "A = PDP⁻¹입니다. P⁻¹DP는 다른 행렬입니다.",
    "dpow": "Dⁿ은 대각성분을 각각 n제곱한 것입니다. n을 곱하면 안 됩니다.",
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
