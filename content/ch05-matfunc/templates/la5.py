"""5장 행렬함수와 이차형식 — 생성기."""
import itertools
import random
import sympy as sp
from texkit import tex, mat, tup, join_terms
from checks import same, opt, step, vstep, decoy, vdecoy, x, y, t

UNIMOD = [sp.Matrix(m) for m in ([[1, 1], [0, 1]], [[2, 1], [1, 1]], [[1, 2], [1, 3]], [[1, -1], [1, 0]],
                                  [[1, 0], [1, 1]], [[1, 1], [1, 2]], [[2, 1], [3, 2]])]
LABELS = {"pd": r"\text{양의 정부호}", "nd": r"\text{음의 정부호}", "indef": r"\text{부정부호}", "psd": r"\text{양의 준정부호}", "nsd": r"\text{음의 준정부호}"}


def _qtex(a, b, c):
    return join_terms([(a, "x^{2}"), (b, "xy"), (c, "y^{2}")])


def _classify(M):
    ev = [sp.nsimplify(e) for e in M.eigenvals()]
    if all(e > 0 for e in ev):
        return "pd"
    if all(e < 0 for e in ev):
        return "nd"
    if all(e >= 0 for e in ev):
        return "psd"
    if all(e <= 0 for e in ev):
        return "nsd"
    return "indef"


def qform_matrix():
    out = []
    for a, b, c in itertools.product([1, 2, 3, -1, 5], [-4, -2, 2, 4, 6, 3], [1, 2, -3, 4]):
        q = a * x**2 + b * x * y + c * y**2
        M = sp.Matrix([[a, sp.Rational(b, 2)], [sp.Rational(b, 2), c]])
        v = sp.Matrix([x, y])
        ok = lambda X, q=q, v=v: X == X.T and same(sp.expand((v.T * X * v)[0]), q)
        cands = [(sp.Matrix([[a, b], [b, c]]), "missing_factor"), (sp.Matrix([[a, b], [0, c]]), "algebra"),
                 (sp.Matrix([[a, -sp.Rational(b, 2)], [-sp.Rational(b, 2), c]]), "sign"), (sp.Matrix([[c, sp.Rational(b, 2)], [sp.Rational(b, 2), a]]), "algebra")]
        out.append({"params": {"abc": [a, b, c]}, "tier": 1, "prompt": rf"q(x, y) = {_qtex(a, b, c)} = \mathbf{{x}}^{{T}}A\,\mathbf{{x}},\quad A = \;?",
                    "answer": opt(mat(M), lambda X=M, ok=ok: ok(X)),
                    "wrong": [opt(mat(X), lambda X=X, ok=ok: ok(X), er) for X, er in cands]})
    return out


def definiteness():
    out = []
    for a, b, c in itertools.product([-3, -1, 1, 2, 4], [-4, -2, 0, 2, 4], [-3, -1, 1, 2, 4]):
        M = sp.Matrix([[a, sp.Rational(b, 2)], [sp.Rational(b, 2), c]])
        truth = _classify(M)
        ok = lambda lab, truth=truth: lab == truth
        out.append({"params": {"abc": [a, b, c]}, "tier": 2, "prompt": rf"q(x, y) = {_qtex(a, b, c)}\ \text{{은?}}",
                    "answer": opt(LABELS[truth], lambda l=truth, ok=ok: ok(l)),
                    "wrong": [opt(LABELS[l], lambda l=l, ok=ok: ok(l), "theorem_condition") for l in LABELS if l != truth]})
    return out


def exp_diag():
    out = []
    for a, b in itertools.permutations([-3, -2, -1, 1, 2, 3], 2):
        A = sp.diag(a, b)
        truth = (A * t).exp()
        ea, eb = sp.exp(a * t), sp.exp(b * t)
        cands = [(sp.diag(sp.exp(-a * t), sp.exp(-b * t)), "sign"), (sp.diag(1 + a * t, 1 + b * t), "algebra"),
                 (sp.Matrix([[ea, 1], [1, eb]]), "algebra"), (sp.diag(sp.exp(a) * t, sp.exp(b) * t), "algebra")]
        out.append({"params": {"a": a, "b": b}, "tier": 1, "prompt": rf"A = {mat(A)}\qquad e^{{At}} = \;?",
                    "answer": opt(mat(sp.diag(ea, eb)), lambda X=sp.diag(ea, eb), tr=truth: same(X, tr)),
                    "wrong": [opt(mat(X), lambda X=X, tr=truth: same(X, tr), er) for X, er in cands]})
    return out


def exp_jordan():
    out = []
    for a in [-3, -2, -1, 1, 2, 3]:
        A = sp.Matrix([[a, 1], [0, a]])
        truth = (A * t).exp()
        e = sp.exp(a * t)
        ans = sp.Matrix([[e, t * e], [0, e]])
        cands = [(sp.Matrix([[e, 0], [0, e]]), "missing_factor"), (sp.Matrix([[e, e], [0, e]]), "algebra"),
                 (sp.Matrix([[e, sp.exp(t)], [0, e]]), "algebra"), (sp.Matrix([[e, -t * e], [0, e]]), "sign")]
        out.append({"params": {"a": a}, "tier": 2, "prompt": rf"A = {mat(A)}\qquad e^{{At}} = \;?",
                    "answer": opt(mat(ans), lambda X=ans, tr=truth: same(X, tr)),
                    "wrong": [opt(mat(X), lambda X=X, tr=truth: same(X, tr), er) for X, er in cands]})
    return out


# ---------------------------------------------------------------- 풀이 뼈대
WHY = {
    "order": "e^{At} = P e^{Dt} P⁻¹ 입니다. P⁻¹ e^{Dt} P는 다른 행렬입니다.",
    "edt": "e^{Dt}는 대각성분 λᵢ에 대해 e^{λᵢt}입니다. 부호가 틀렸습니다.",
    "vec": "고유벡터가 아닙니다: (A − λI)v ≠ 0.",
    "half": "xy 계수 b는 반으로 나눠 두 비대각 자리에 들어갑니다.",
    "eig": "이차형식 행렬의 고유값을 잘못 구했습니다.",
    "type": "고유값의 부호로 판정합니다: 모두 양수면 양의 정부호, 부호가 섞이면 부정부호.",
}


def exp_At():
    out = []
    rng = random.Random(11)
    seen = set()
    for _ in range(2000):
        P = rng.choice(UNIMOD)
        d1, d2 = rng.sample([-3, -2, -1, 1, 2], 2)
        A = P * sp.diag(d1, d2) * P.inv()
        if tuple(A) in seen or A.is_diagonal() or max(abs(e) for e in A) > 8:
            continue
        seen.add(tuple(A))
        truth = (A * t).exp()                                  # 독립 계산
        eD = sp.diag(sp.exp(d1 * t), sp.exp(d2 * t))
        res = sp.simplify(P * eD * P.inv())
        ok_vec = lambda P_, d_, A=A: P_.det() != 0 and all(same(A * P_[:, j], d_[j] * P_[:, j]) for j in range(2))
        steps = [
            step(rf"\lambda = {tex(d1)},\ {tex(d2)},\quad P = {mat(P)}", lambda P_=P, d_=(d1, d2), f=ok_vec: f(P_, d_)),
            vstep(rf"e^{{Dt}} = {mat(eD)}", eD, (sp.diag(d1, d2) * t).exp()),
            step(rf"e^{{At}} = P\,e^{{Dt}}P^{{-1}}", lambda: True),
            vstep(rf"e^{{At}} = {mat(res)}", res, truth),
        ]
        bad_res = sp.simplify(P.inv() * eD * P)
        bad_eD = sp.diag(sp.exp(-d1 * t), sp.exp(-d2 * t))
        Pb = sp.Matrix([[P[0, 1], P[0, 0]], [P[1, 0], P[1, 1]]])
        decoys = [
            vdecoy(3, rf"e^{{At}} = {mat(bad_res)}", bad_res, truth, "algebra", WHY["order"]),
            vdecoy(1, rf"e^{{Dt}} = {mat(bad_eD)}", bad_eD, (sp.diag(d1, d2) * t).exp(), "sign", WHY["edt"]),
            decoy(0, rf"\lambda = {tex(d1)},\ {tex(d2)},\quad P = {mat(Pb)}", lambda P_=Pb, d_=(d1, d2), f=ok_vec: f(P_, d_), "algebra", WHY["vec"]),
        ]
        out.append({"params": {"A": list(A)}, "tier": 2, "problem": rf"A = {mat(A)}\ \text{{일 때}}\ e^{{At}}",
                    "steps": steps, "decoys": decoys,
                    "verify": lambda X=res, A=A: None if same(sp.diff(X, t), A * X) and same(X.subs(t, 0), sp.eye(2)) else "X′ ≠ AX 또는 X(0) ≠ I"})
        if len(out) >= 40:
            break
    return out


def principal_axes():
    out = []
    for a, b, c in itertools.product([1, 2, 3, 5, -1, -3], [-4, -2, 2, 4, 6], [1, 2, 3, 5, -2]):
        M = sp.Matrix([[a, sp.Rational(b, 2)], [sp.Rational(b, 2), c]])
        ev = sorted(M.eigenvals().keys(), key=lambda e: float(e))
        if len(ev) != 2 or any(not e.is_rational for e in ev):
            continue
        l1, l2 = ev
        truth_cls = _classify(M)
        q = a * x**2 + b * x * y + c * y**2
        v = sp.Matrix([x, y])
        ok_M = lambda X, q=q, v=v: X == X.T and same(sp.expand((v.T * X * v)[0]), q)
        eigs = set(M.eigenvals().keys())
        X_, Y_ = sp.symbols("X Y")
        steps = [
            step(rf"A = {mat(M)}", lambda X=M, f=ok_M: f(X)),
            step(rf"\lambda_1 = {tex(l1)},\ \lambda_2 = {tex(l2)}", lambda v=(l1, l2), e=eigs: same(set(v), e)),
            step(rf"q = {join_terms([(l1, 'X^{2}'), (l2, 'Y^{2}')])}\ \ (\text{{주축 좌표}})", lambda v=(l1, l2), e=eigs: same(set(v), e)),
            step(rf"\Rightarrow\ {LABELS[truth_cls]}", lambda l=truth_cls, M=M: l == _classify(M)),
        ]
        Mb = sp.Matrix([[a, b], [b, c]])
        evb = sorted(Mb.eigenvals().keys(), key=lambda e: float(sp.N(e)))
        wrong_cls = [l for l in ("pd", "indef", "nd") if l != truth_cls][0]
        decoys = [
            decoy(0, rf"A = {mat(Mb)}", lambda X=Mb, f=ok_M: f(X), "missing_factor", WHY["half"]),
            decoy(1, rf"\lambda_1 = {tex(-l2)},\ \lambda_2 = {tex(-l1)}", lambda v=(-l2, -l1), e=eigs: same(set(v), e), "sign", WHY["eig"]),
            decoy(3, rf"\Rightarrow\ {LABELS[wrong_cls]}", lambda l=wrong_cls, M=M: l == _classify(M), "theorem_condition", WHY["type"]),
        ]
        out.append({"params": {"abc": [a, b, c]}, "tier": 2, "problem": rf"q(x, y) = {_qtex(a, b, c)}\ \text{{의 주축 변환}}",
                    "steps": steps, "decoys": decoys})
    return out
