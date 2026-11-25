"""3장 공식 원자의 구체적 적용 문제."""
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


def _sv(c):
    """스칼라 c 곱하기 v → TeX."""
    c = sp.nsimplify(c)
    if c == 1:
        return r"\mathbf{v}"
    if c == -1:
        return r"-\mathbf{v}"
    return tex(c) + r"\mathbf{v}"


# (A의 함수 TeX, λ에 대한 함수, 오답 후보 함수들)
POWS = [
    ("A^{-1}", lambda l: 1 / l, [lambda l: l, lambda l: -l, lambda l: -1 / l]),
    ("A^{2}", lambda l: l ** 2, [lambda l: 2 * l, lambda l: l, lambda l: 1 / l ** 2]),
    ("A^{3}", lambda l: l ** 3, [lambda l: 3 * l, lambda l: l ** 2, lambda l: l]),
    ("A^{-2}", lambda l: l ** -2, [lambda l: -2 * l, lambda l: l ** 2, lambda l: -1 / l ** 2]),
    ("(A + 2I)", lambda l: l + 2, [lambda l: 2 * l, lambda l: l, lambda l: l + 1]),
    ("(A - 3I)", lambda l: l - 3, [lambda l: -3 * l, lambda l: l + 3, lambda l: l]),
    ("(2A - I)^{-1}", lambda l: 1 / (2 * l - 1), [lambda l: 2 * l - 1, lambda l: 1 / (2 * l) - 1, lambda l: 2 / l - 1]),
]


def eigpow():
    out = []
    for (form, f, wf), lam in itertools.product(POWS, [2, -1, 3, sp.Rational(1, 2), -2]):
        lam = sp.nsimplify(lam)
        if f(lam) in (sp.zoo, sp.nan) or (2 * lam - 1 == 0):
            continue
        truth = sp.nsimplify(f(lam))
        cand = [(sp.nsimplify(g(lam)), "algebra") for g in wf]
        tier = 1 if form in ("A^{-1}", "A^{2}", "(A + 2I)") else 2
        out.append(_case(rf"A\mathbf{{v}} = {tex(lam)}\mathbf{{v}}\text{{일 때 }} {form}\mathbf{{v}} = \;?", _sv(truth),
                         lambda c=truth, tr=truth: same(c, tr), [(_sv(c), lambda c=c, tr=truth: same(c, tr), e) for c, e in cand],
                         tier=tier, params={"form": form, "lam": str(lam)}))
    return out


def similar():
    """B = P⁻¹AP의 trace·det·고유값은 A와 같다."""
    out = []
    rng = random.Random(31)
    seen = set()
    while len(out) < 24:
        A = sp.Matrix(2, 2, [rng.randint(-3, 4) for _ in range(4)])
        P = sp.Matrix(2, 2, [rng.randint(-2, 3) for _ in range(4)])
        if tuple(A) + tuple(P) in seen or P.det() in (0, 1, -1) or A.det() == 0 or A.trace() == 0:
            continue
        seen.add(tuple(A) + tuple(P))
        B = P.inv() * A * P
        dA, tA, dP = A.det(), A.trace(), P.det()
        kind = len(out) % 3
        head = rf"A = {mat(A)},\ P = {mat(P)},\ B = P^{{-1}}AP\text{{일 때 }} "
        if kind == 0:
            truth = B.det()
            cand = [(dA * dP, "algebra"), (dA * dP ** 2, "algebra"), (dA / dP, "algebra"), (tA, "wrong_pair")]
            out.append(_case(head + r"\det B = \;?", tex(truth), lambda c=truth, tr=B.det(): same(c, tr),
                             [(tex(c), lambda c=c, tr=B.det(): same(c, tr), e) for c, e in cand], params={"A": list(A), "P": list(P)}))
        elif kind == 1:
            truth = B.trace()
            cand = [(tA * dP, "algebra"), (tA + P.trace(), "algebra"), (dA, "wrong_pair"), (-tA, "sign")]
            out.append(_case(head + r"\operatorname{tr} B = \;?", tex(truth), lambda c=truth, tr=B.trace(): same(c, tr),
                             [(tex(c), lambda c=c, tr=B.trace(): same(c, tr), e) for c, e in cand], params={"A": list(A), "P": list(P)}))
        else:
            lam = sp.symbols("lambda")
            truth = sp.expand((B - lam * sp.eye(2)).det())
            cand = [(sp.expand((P - lam * sp.eye(2)).det()), "wrong_pair"), (sp.expand(lam ** 2 + tA * lam + dA), "sign"),
                    (sp.expand(lam ** 2 - tA * lam - dA), "sign"), (sp.expand(lam ** 2 - tA * lam + dA * dP), "algebra")]
            pt = lambda e: tex(sp.Poly(e, lam).as_expr())
            out.append(_case(head + r"B\text{의 특성다항식 } \det(B - \lambda I) = \;?", pt(truth),
                             lambda c=truth, tr=truth: same(c, tr), [(pt(c), lambda c=c, tr=truth: same(c, tr), e) for c, e in cand],
                             tier=2, params={"A": list(A), "P": list(P)}))
    return out


def symeig():
    """대칭행렬에서 다른 고유값의 고유벡터는 직교한다."""
    out = []
    rng = random.Random(32)
    pairs = [(a, b) for a, b in itertools.product(range(-3, 4), repeat=2) if (a, b) != (0, 0) and abs(a) != abs(b) and a * b != 0]
    rng.shuffle(pairs)
    for a, b in pairs[:12]:
        v = sp.Matrix([a, b])
        good = sp.Matrix([-b, a]) * rng.choice([1, -1, 2])
        cand = [sp.Matrix([b, a]), sp.Matrix([a, -b]), sp.Matrix([a, b]) * 2, sp.Matrix([b, -a]) + sp.Matrix([1, 0])]
        ok = lambda w, v=v: w.dot(v) == 0 and any(w)
        out.append(_case(rf"A = A^{{T}},\ \lambda_1 \ne \lambda_2,\ \lambda_1\text{{의 고유벡터가 }} {tup(v)}\text{{일 때 }} \lambda_2\text{{의 고유벡터는?}}",
                         tup(good), lambda w=good, ok=ok: ok(w), [(tup(w), lambda w=w, ok=ok: ok(w), "normalization") for w in cand],
                         params={"v": [a, b]}))
    # 3×3: 두 고유벡터가 주어지면 세 번째는 둘 다에 직교
    trip = 0
    while trip < 10:
        v1 = sp.Matrix([rng.randint(-2, 2) for _ in range(3)])
        v2 = sp.Matrix([rng.randint(-2, 2) for _ in range(3)])
        if v1.dot(v2) != 0 or not any(v1) or not any(v2) or not any(v1.cross(v2)):
            continue
        w = v1.cross(v2)
        g = sp.gcd(list(w))
        w = w / g
        ok = lambda x, v1=v1, v2=v2: x.dot(v1) == 0 and x.dot(v2) == 0 and any(x)
        cand = [v1 + v2, v1 - v2, sp.Matrix([w[0], w[1], -w[2]]), sp.Matrix([w[1], w[0], w[2]])]
        out.append(_case(rf"A\ (3\times 3) = A^{{T}},\ \text{{고유값이 모두 다르고 두 고유벡터가 }} {tup(v1)},\ {tup(v2)}\text{{일 때 나머지 고유벡터는?}}",
                         tup(w), lambda x=w, ok=ok: ok(x), [(tup(x), lambda x=x, ok=ok: ok(x), "normalization") for x in cand],
                         tier=2, params={"v1": list(v1), "v2": list(v2)}))
        trip += 1
    return out
