"""1장 벡터공간과 내적 — 생성기."""
import itertools
import random
import sympy as sp
from texkit import tex, tup, join_terms
from checks import same, opt, step, vstep, decoy, vdecoy

B = r"\mathbf"


def _vecs(n, k, lo=-3, hi=3, seed=0, nonzero=True):
    rng = random.Random(seed)
    out = set()
    while len(out) < k:
        v = tuple(rng.randint(lo, hi) for _ in range(n))
        if nonzero and all(c == 0 for c in v):
            continue
        out.add(v)
    return [sp.Matrix(v) for v in sorted(out)]


def _ok_val(val, truth):
    return lambda v=val, tr=truth: same(v, tr)


# ---------------------------------------------------------------- 사실 원자
def dot():
    out = []
    us, vs = _vecs(3, 12, seed=1), _vecs(3, 12, seed=2)
    for u, v in zip(us, vs):
        truth = u.dot(v)
        p = rf"{B}{{u}} = {tup(u)},\quad {B}{{v}} = {tup(v)} \qquad {B}{{u}}\cdot{B}{{v}} = \;?"
        cand = [
            (u[0] * v[0] - u[1] * v[1] + u[2] * v[2], "sign"),
            (u[0] * v[0] + u[1] * v[1], "missing_factor"),
            (sum(u) * sum(v), "algebra"),
            (truth + 2, "algebra"),
            (truth - 2, "algebra"),
        ]
        out.append({"params": {"u": list(u), "v": list(v)}, "tier": 1, "prompt": p,
                    "answer": opt(tex(truth), _ok_val(truth, truth)),
                    "wrong": [opt(tex(c), _ok_val(c, truth), e) for c, e in cand]})
    return out


def norm():
    out = []
    for v in _vecs(3, 14, seed=3):
        truth = v.norm()
        ss = sum(c**2 for c in v)
        cand = [(ss, "missing_factor"), (sum(abs(c) for c in v), "wrong_pair"),
                (sp.sqrt(abs(sum(v))), "algebra"), (max(abs(c) for c in v), "wrong_pair")]
        out.append({"params": {"v": list(v)}, "tier": 1,
                    "prompt": rf"\left\|{tup(v)}\right\| = \;?",
                    "answer": opt(tex(truth), _ok_val(truth, sp.sqrt(v.dot(v)))),
                    "wrong": [opt(tex(c), _ok_val(c, truth), e) for c, e in cand]})
    return out


def proj():
    out = []
    pairs = [(u, v) for u in _vecs(3, 9, seed=4) for v in _vecs(3, 6, -2, 2, seed=5)]
    random.Random(6).shuffle(pairs)
    for u, v in pairs[:20]:
        a, b = u.dot(v), v.dot(v)
        if a == 0:
            continue
        p = (a / b) * v

        def ok(q, u=u, v=v):
            q = sp.Matrix(q)
            return same((u - q).dot(v), 0) and same(q.cross(v), sp.zeros(3, 1))  # u−p ⟂ v, p ∥ v

        cand = [((a / sp.sqrt(b)) * v, "normalization"), (a * v, "missing_factor"),
                ((a / u.dot(u)) * u, "wrong_pair"), (-(a / b) * v, "sign")]
        out.append({"params": {"u": list(u), "v": list(v)}, "tier": 2,
                    "prompt": rf"{B}{{u}} = {tup(u)},\ {B}{{v}} = {tup(v)} \qquad \operatorname{{proj}}_{{{B}{{v}}}}{B}{{u}} = \;?",
                    "answer": opt(tup(p), lambda q=p, ok=ok: ok(q)),
                    "wrong": [opt(tup(c), lambda q=c, ok=ok: ok(q), e) for c, e in cand]})
    return out


def orth_k():
    out = []
    k = sp.Symbol("k")
    rng = random.Random(7)
    for _ in range(30):
        u = sp.Matrix([rng.choice([1, 2, 3, -1, -2]) for _ in range(3)])
        v = sp.Matrix([rng.randint(-3, 3), rng.randint(-3, 3), k])
        sol = sp.solve(u.dot(v), k)
        if not sol or sol[0] == 0:
            continue
        kv = sol[0]
        ok = lambda val, u=u, v=v: same(u.dot(v.subs(k, val)), 0)
        cand = [(-kv, "sign"), (sp.Rational(1, 1) / kv if kv != 0 else 99, "algebra"),
                (kv + 1, "algebra"), (u[2], "wrong_pair")]
        vt = tup([v[0], v[1], k]).replace("k", "k")
        out.append({"params": {"u": list(u), "v": [v[0], v[1]]}, "tier": 1,
                    "prompt": rf"{B}{{u}} = {tup(u)},\ {B}{{v}} = {vt}\ \text{{이 직교하는}}\ k = \;?",
                    "answer": opt(tex(kv), lambda q=kv, ok=ok: ok(q)),
                    "wrong": [opt(tex(c), lambda q=c, ok=ok: ok(q), e) for c, e in cand]})
    return out


# ---------------------------------------------------------------- 풀이 뼈대
WHY = {
    "gs_sign": "Gram–Schmidt은 사영 성분을 빼야 합니다: u₂ = v₂ − proj_{u₁}v₂.",
    "gs_norm": "사영 계수의 분모는 ‖u₁‖가 아니라 ‖u₁‖² = u₁·u₁ 입니다.",
    "gs_dot": "분자는 v₂·u₁ 입니다. u₁·u₁과 섞였습니다.",
    "gs_unit": "e₂는 u₂를 자기 길이 ‖u₂‖로 나눈 것입니다. ‖v₂‖로 나누면 단위벡터가 아닙니다.",
    "pl_sign": "평면 위로의 사영은 v에서 법선 성분을 빼야 합니다.",
    "pl_norm": "법선 방향 성분의 계수는 (n·v)/(n·n) 입니다. ‖n‖로 나누면 안 됩니다.",
    "pl_dot": "n·v 계산이 틀렸습니다.",
}


def gram_schmidt():
    out = []
    v1s, v2s = _vecs(3, 10, -2, 2, seed=11), _vecs(3, 10, -2, 3, seed=12)
    for v1, v2 in itertools.product(v1s, v2s):
        if v1.cross(v2) == sp.zeros(3, 1):
            continue
        a, b = v2.dot(v1), v1.dot(v1)
        if a == 0:
            continue
        ref = sp.GramSchmidt([v1, v2])                     # 독립 계산
        refn = sp.GramSchmidt([v1, v2], True)
        u2 = v2 - (a / b) * v1
        e1, e2 = v1 / v1.norm(), u2 / u2.norm()
        prob = rf"{B}{{v}}_1 = {tup(v1)},\ {B}{{v}}_2 = {tup(v2)}\ \text{{을 Gram–Schmidt로 정규직교화}}"
        steps = [
            vstep(rf"{B}{{v}}_2\cdot{B}{{u}}_1 = {tex(a)},\quad {B}{{u}}_1\cdot{B}{{u}}_1 = {tex(b)}\quad ({B}{{u}}_1 = {B}{{v}}_1)",
                  (a, b), (v2.dot(ref[0]), ref[0].dot(ref[0]))),
            vstep(rf"{B}{{u}}_2 = {join_terms([(1, B + '{v}_2'), (-(a / b), B + '{u}_1')])} = {tup(u2)}", u2, ref[1]),
            vstep(rf"{B}{{e}}_1 = {tup(e1)}", e1, refn[0]),
            vstep(rf"{B}{{e}}_2 = {tup(e2)}", e2, refn[1]),
        ]
        bad_s = v2 + (a / b) * v1
        bad_n = v2 - (a / sp.sqrt(b)) * v1
        bad_e = u2 / v2.norm()
        decoys = [
            vdecoy(1, rf"{B}{{u}}_2 = {join_terms([(1, B + '{v}_2'), ((a / b), B + '{u}_1')])} = {tup(bad_s)}", bad_s, ref[1], "sign", WHY["gs_sign"]),
            vdecoy(1, rf"{B}{{u}}_2 = {join_terms([(1, B + '{v}_2'), (-(a / sp.sqrt(b)), B + '{u}_1')])} = {tup(bad_n)}", bad_n, ref[1], "normalization", WHY["gs_norm"]),
            vdecoy(0, rf"{B}{{v}}_2\cdot{B}{{u}}_1 = {tex(b)},\quad {B}{{u}}_1\cdot{B}{{u}}_1 = {tex(b)}\quad ({B}{{u}}_1 = {B}{{v}}_1)",
                   (b, b), (v2.dot(ref[0]), ref[0].dot(ref[0])), "algebra", WHY["gs_dot"]),
            vdecoy(3, rf"{B}{{e}}_2 = {tup(bad_e)}", bad_e, refn[1], "normalization", WHY["gs_unit"]),
        ]

        def verify(e1=e1, e2=e2):
            if not same(e1.dot(e2), 0):
                return "e₁·e₂ ≠ 0"
            if not (same(e1.norm(), 1) and same(e2.norm(), 1)):
                return "단위벡터 아님"
            return None

        tier = 1 if (a / b).q == 1 else 2
        out.append({"params": {"v1": list(v1), "v2": list(v2)}, "tier": tier, "problem": prob,
                    "steps": steps, "decoys": decoys, "verify": verify})
    return out


def plane_projection():
    out = []
    ns, vs = _vecs(3, 8, -2, 2, seed=21), _vecs(3, 10, -3, 3, seed=22)
    for n, v in itertools.product(ns, vs):
        a, b = n.dot(v), n.dot(n)
        if a == 0:
            continue
        pn = (a / b) * n
        w = v - pn
        prob = rf"{B}{{v}} = {tup(v)}\ \text{{를 평면}}\ {join_terms([(n[0], 'x'), (n[1], 'y'), (n[2], 'z')])} = 0\ \text{{위로 사영}}"
        ok_w = lambda q, n=n, v=v: same(sp.Matrix(q).dot(n), 0) and same((v - sp.Matrix(q)).cross(n), sp.zeros(3, 1))
        steps = [
            vstep(rf"{B}{{n}} = {tup(n)},\quad {B}{{n}}\cdot{B}{{v}} = {tex(a)},\quad {B}{{n}}\cdot{B}{{n}} = {tex(b)}", (a, b), (v.dot(n), n.norm() ** 2)),
            step(rf"\operatorname{{proj}}_{{{B}{{n}}}}{B}{{v}} = {join_terms([(a / b, B + '{n}')])} = {tup(pn)}", lambda q=pn, ok=ok_w, v=v: ok(v - q)),
            step(rf"{B}{{v}} - \operatorname{{proj}}_{{{B}{{n}}}}{B}{{v}} = {tup(w)}", lambda q=w, ok=ok_w: ok(q)),
        ]
        bs = v + pn
        bn = (a / sp.sqrt(b)) * n
        bd = ((a + 1) / b) * n
        decoys = [
            decoy(2, rf"{B}{{v}} + \operatorname{{proj}}_{{{B}{{n}}}}{B}{{v}} = {tup(bs)}", lambda q=bs, ok=ok_w: ok(q), "sign", WHY["pl_sign"]),
            decoy(1, rf"\operatorname{{proj}}_{{{B}{{n}}}}{B}{{v}} = {join_terms([(a / sp.sqrt(b), B + '{n}')])} = {tup(bn)}", lambda q=bn, ok=ok_w, v=v: ok(v - q), "normalization", WHY["pl_norm"]),
            vdecoy(0, rf"{B}{{n}} = {tup(n)},\quad {B}{{n}}\cdot{B}{{v}} = {tex(a + 1)},\quad {B}{{n}}\cdot{B}{{n}} = {tex(b)}", (a + 1, b), (v.dot(n), n.norm() ** 2), "algebra", WHY["pl_dot"]),
        ]
        tier = 2 if (a / b).q == 1 else 3
        out.append({"params": {"n": list(n), "v": list(v)}, "tier": tier, "problem": prob, "steps": steps, "decoys": decoys,
                    "verify": lambda w=w, n=n: None if same(w.dot(n), 0) else "결과가 평면 위에 있지 않음"})
    return out
