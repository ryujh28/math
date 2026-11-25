"""1장 공식 원자의 구체적 적용 문제. 공식을 외운 대로 숫자에 적용할 수 있는지 본다."""
import itertools
import random
import sympy as sp
from texkit import tex, tup
from checks import same, opt


def _case(prompt, ans_tex, ans_ok, wrong, tier=None, params=None):
    c = {"params": params or {}, "prompt": prompt, "answer": opt(ans_tex, ans_ok),
         "wrong": [opt(tx, ok, e) for tx, ok, e in wrong]}
    if tier is not None:
        c["tier"] = tier
    return c


def _vec_pairs(n, k, seed):
    rng = random.Random(seed)
    out, seen = [], set()
    while len(out) < k:
        u = sp.Matrix([rng.randint(-3, 3) for _ in range(n)])
        v = sp.Matrix([rng.randint(-3, 3) for _ in range(n)])
        key = (tuple(u), tuple(v))
        if key in seen or u.norm() == 0 or v.norm() == 0 or u.dot(v) == 0:
            continue
        if u.cross(v) == sp.zeros(3, 1) if n == 3 else u[0] * v[1] - u[1] * v[0] == 0:
            continue
        seen.add(key)
        out.append((u, v))
    return out


def _uv(u, v):
    return rf"\mathbf{{u}} = {tup(u)},\ \mathbf{{v}} = {tup(v)}"


def angle():
    out = []
    for n, k, seed in ((2, 10, 11), (3, 10, 12)):
        for u, v in _vec_pairs(n, k, seed):
            d, nu, nv = u.dot(v), u.norm(), v.norm()
            truth = sp.radsimp(d / (nu * nv))
            cand = [(-truth, "sign"), (sp.radsimp(d / (nu ** 2 * nv ** 2)), "normalization"),
                    (sp.radsimp(d / (nu + nv)), "algebra"), (sp.radsimp(d / nu), "missing_factor"),
                    (sp.radsimp(nu * nv / d), "algebra")]
            out.append(_case(_uv(u, v) + r"\text{일 때 } \cos\theta = \;?", tex(truth),
                             lambda c=truth, tr=truth: same(c, tr),
                             [(tex(c), lambda c=c, tr=truth: same(c, tr), e) for c, e in cand],
                             tier=1 if n == 2 else 2, params={"u": list(u), "v": list(v)}))
    return out


def cs():
    """‖u‖, ‖v‖가 주어졌을 때 u·v로 가능한 값 (|u·v| ≤ ‖u‖‖v‖)."""
    out = []
    rng = random.Random(13)
    for a, b in itertools.product([1, 2, 3, 4, 5], [2, 3, 4]):
        m = a * b
        ans = rng.choice([m, -m, m - 1, -(m - 1), sp.Rational(m, 2)])
        bad = [m + 1, -(m + 2), m + 3, 2 * m, a + b + m]
        bad = [w for w in bad if abs(w) > m]
        out.append(_case(rf"\|\mathbf{{u}}\| = {a},\ \|\mathbf{{v}}\| = {b}\text{{일 때 }} \mathbf{{u}}\cdot\mathbf{{v}}\text{{로 가능한 값은?}}",
                         tex(ans), lambda c=ans, m=m: bool(abs(c) <= m),
                         [(tex(w), lambda c=w, m=m: bool(abs(c) <= m), "theorem_condition") for w in bad],
                         params={"a": a, "b": b}))
    return out


def triangle():
    """‖u+v‖로 가능한 값: | ‖u‖ − ‖v‖ | ≤ ‖u+v‖ ≤ ‖u‖ + ‖v‖."""
    out = []
    rng = random.Random(14)
    for a, b in itertools.product([1, 2, 3, 5, 6], [2, 4, 7]):
        lo, hi = abs(a - b), a + b
        ans = rng.choice([hi, lo, sp.Rational(lo + hi, 2)])
        bad = [hi + 1, hi + 3, 2 * hi, sp.Rational(2 * hi + 1, 2)] + ([lo - 1] if lo >= 2 else [])
        ok = lambda c, lo=lo, hi=hi: bool(lo <= c) and bool(c <= hi)
        out.append(_case(rf"\|\mathbf{{u}}\| = {a},\ \|\mathbf{{v}}\| = {b}\text{{일 때 }} \|\mathbf{{u}}+\mathbf{{v}}\|\text{{로 가능한 값은?}}",
                         tex(ans), lambda c=ans, ok=ok: ok(c),
                         [(tex(w), lambda c=w, ok=ok: ok(c), "theorem_condition") for w in bad],
                         tier=2, params={"a": a, "b": b}))
    return out


def gs():
    """u₁ = v₁일 때 u₂ = v₂ − proj_{u₁} v₂."""
    out = []
    for n, k, seed in ((2, 10, 15), (3, 10, 16)):
        for v1, v2 in _vec_pairs(n, k, seed):
            u1 = v1
            c = v2.dot(u1) / u1.dot(u1)
            truth = v2 - c * u1
            cand = [(v2 + c * u1, "sign"), (v2 - v2.dot(u1) * u1, "normalization"),
                    (v2 - (v2.dot(u1) / u1.norm()) * u1, "normalization"), (v1 - (v1.dot(v2) / v2.dot(v2)) * v2, "wrong_pair"),
                    (c * u1, "algebra")]
            prompt = (rf"\mathbf{{v}}_1 = {tup(v1)},\ \mathbf{{v}}_2 = {tup(v2)},\ \mathbf{{u}}_1 = \mathbf{{v}}_1"
                      r"\text{일 때 Gram–Schmidt의 } \mathbf{u}_2 = \;?")
            out.append(_case(prompt, tup(truth), lambda X=truth, tr=truth: same(X, tr),
                             [(tup(X), lambda X=X, tr=truth: same(X, tr), e) for X, e in cand if all(q.is_rational for q in X)],
                             tier=1 if n == 2 else 2, params={"v1": list(v1), "v2": list(v2)}))
    return out
