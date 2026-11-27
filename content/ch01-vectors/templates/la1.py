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
    us, vs = _vecs(3, 30, seed=1), _vecs(3, 30, seed=2)
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
    for v in _vecs(3, 30, seed=3):
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
    "gs_sign": r"Gram–Schmidt는 사영 성분을 빼야 합니다: $\mathbf{u}_2 = \mathbf{v}_2 - \operatorname{proj}_{\mathbf{u}_1}\mathbf{v}_2$.",
    "gs_norm": r"사영 계수의 분모는 $\|\mathbf{u}_1\|$가 아니라 $\|\mathbf{u}_1\|^2 = \mathbf{u}_1\cdot\mathbf{u}_1$입니다.",
    "gs_dot": r"분자는 $\mathbf{v}_2\cdot\mathbf{u}_1$입니다. $\mathbf{u}_1\cdot\mathbf{u}_1$과 섞였습니다.",
    "gs_unit": r"$\mathbf{e}_2$는 $\mathbf{u}_2$를 자기 길이 $\|\mathbf{u}_2\|$로 나눈 것입니다. $\|\mathbf{v}_2\|$로 나누면 단위벡터가 아닙니다.",
    "pl_sign": r"평면 위로의 사영은 $\mathbf{v}$에서 법선 성분을 빼야 합니다.",
    "pl_norm": r"법선 방향 성분의 계수는 $\dfrac{\mathbf{n}\cdot\mathbf{v}}{\mathbf{n}\cdot\mathbf{n}}$입니다. $\|\mathbf{n}\|$로 나누면 안 됩니다.",
    "pl_dot": r"$\mathbf{n}\cdot\mathbf{v}$ 계산이 틀렸습니다.",
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


# ---------------------------------------------------------------- M3.6 2단계: 가족 추가
WHY.update({
    "gs_orth": r"$\mathbf{v}_2\cdot\mathbf{u}_1 = 0$이면 이미 직교라서 뺄 것이 없습니다: $\mathbf{u}_2 = \mathbf{v}_2$.",
    "gs_e1": r"$\mathbf{e}_1 = \dfrac{\mathbf{u}_1}{\|\mathbf{u}_1\|}$입니다. 길이로 나누지 않으면 단위벡터가 아닙니다.",
    "pl_off": r"평면 $\mathbf{n}\cdot\mathbf{x} = d$로의 사영은 $\mathbf{v} - \dfrac{\mathbf{n}\cdot\mathbf{v} - d}{\mathbf{n}\cdot\mathbf{n}}\mathbf{n}$입니다. $d$를 빼지 않았습니다.",
    "ln_sub": r"직선 위로의 사영은 방향벡터 성분 자체입니다. 빼면 직선에 수직인 성분이 됩니다.",
    "pd_sign": r"$d$를 빼야 하는데 더했습니다. 평면 $\mathbf{n}\cdot\mathbf{x} = d$에서 법선 방향으로 떨어진 정도는 $\mathbf{n}\cdot\mathbf{p} - d$입니다.",
    "off_sign": r"$\mathbf{n}\cdot\mathbf{v} - d$에서 $d$를 빼야 하는데 더했습니다.",
    "ln_norm": r"사영 계수의 분모는 $\|\mathbf{d}\|$가 아니라 $\|\mathbf{d}\|^2 = \mathbf{d}\cdot\mathbf{d}$입니다.",
    "ln_dot": r"$\mathbf{d}\cdot\mathbf{v}$ 계산이 틀렸습니다. 성분끼리 곱해 더해 보세요.",
    "dist_abs": r"거리는 $\dfrac{|\mathbf{n}\cdot\mathbf{p} - d|}{\|\mathbf{n}\|}$입니다. $\|\mathbf{n}\|^2$으로 나누면 안 됩니다.",
})


def _gs_case(v1, v2, family, tier):
    a, b = v2.dot(v1), v1.dot(v1)
    ref = sp.GramSchmidt([v1, v2])
    refn = sp.GramSchmidt([v1, v2], True)
    u2 = v2 - (a / b) * v1
    e1, e2 = v1 / v1.norm(), u2 / u2.norm()
    prob = rf"{B}{{v}}_1 = {tup(v1)},\ {B}{{v}}_2 = {tup(v2)}\ \text{{을 Gram–Schmidt로 정규직교화}}"
    u2tx = rf"{B}{{u}}_2 = {B}{{v}}_2 = {tup(u2)}\ (\text{{이미 직교}})" if a == 0 else rf"{B}{{u}}_2 = {join_terms([(1, B + '{v}_2'), (-(a / b), B + '{u}_1')])} = {tup(u2)}"
    steps = [
        vstep(rf"{B}{{v}}_2\cdot{B}{{u}}_1 = {tex(a)},\quad {B}{{u}}_1\cdot{B}{{u}}_1 = {tex(b)}\quad ({B}{{u}}_1 = {B}{{v}}_1)", (a, b), (v2.dot(ref[0]), ref[0].dot(ref[0]))),
        vstep(u2tx, u2, ref[1]),
        vstep(rf"{B}{{e}}_1 = {tup(e1)}", e1, refn[0]),
        vstep(rf"{B}{{e}}_2 = {tup(e2)}", e2, refn[1]),
    ]
    decoys = [vdecoy(2, rf"{B}{{e}}_1 = {tup(v1 / b)}", v1 / b, refn[0], "normalization", WHY["gs_e1"]) if b != 1 else None,
              vdecoy(3, rf"{B}{{e}}_2 = {tup(u2 / v1.norm())}", u2 / v1.norm(), refn[1], "normalization", WHY["gs_unit"]) if not same(u2.norm(), v1.norm()) else None]
    if a == 0:
        bad = v2 - v1
        decoys.append(vdecoy(1, rf"{B}{{u}}_2 = {B}{{v}}_2 - {B}{{u}}_1 = {tup(bad)}", bad, ref[1], "algebra", WHY["gs_orth"]))
    else:
        bad_s = v2 + (a / b) * v1
        decoys.append(vdecoy(1, rf"{B}{{u}}_2 = {join_terms([(1, B + '{v}_2'), ((a / b), B + '{u}_1')])} = {tup(bad_s)}", bad_s, ref[1], "sign", WHY["gs_sign"]))
        decoys.append(vdecoy(0, rf"{B}{{v}}_2\cdot{B}{{u}}_1 = {tex(b)},\quad {B}{{u}}_1\cdot{B}{{u}}_1 = {tex(b)}\quad ({B}{{u}}_1 = {B}{{v}}_1)",
                             (b, b), (v2.dot(ref[0]), ref[0].dot(ref[0])), "algebra", WHY["gs_dot"]))
    decoys = [d for d in decoys if d]

    def verify(e1=e1, e2=e2):
        return None if same(e1.dot(e2), 0) and same(e1.norm(), 1) and same(e2.norm(), 1) else "정규직교 아님"
    return {"params": {"v1": list(v1), "v2": list(v2), "family": family}, "tier": tier, "problem": prob, "steps": steps, "decoys": decoys, "verify": verify}


def gs_families():
    """Gram–Schmidt. 가족: ℝ³ 두 벡터(기존) · ℝ² 두 벡터 · 이미 직교인 쌍(ℝ³)."""
    out = []
    for c in gram_schmidt():
        c["params"]["family"] = "r3"
        c["tier"] = min(3, c["tier"] + 1)        # ℝ³은 ℝ²보다 한 단계 위 (단계당 30문제 상한도 고르게)
        out.append(c)
    out = out[:26]
    v1s, v2s = _vecs(2, 12, -3, 3, seed=31), _vecs(2, 12, -3, 4, seed=32)
    r2 = []
    for v1, v2 in itertools.product(v1s, v2s):
        if v1[0] * v2[1] - v1[1] * v2[0] == 0 or v2.dot(v1) == 0:
            continue
        r2.append(_gs_case(v1, v2, "r2", 1 if (v2.dot(v1) / v1.dot(v1)).q == 1 else 2))
    out += r2[::max(1, len(r2) // 20)][:20]
    orth = []
    for v1, v2 in itertools.product(_vecs(3, 14, -2, 2, seed=33), _vecs(3, 30, -3, 3, seed=34)):
        if v2.dot(v1) == 0 and v1.cross(v2) != sp.zeros(3, 1):
            orth.append(_gs_case(v1, v2, "orth", 1))
    out += orth[::max(1, len(orth) // 14)][:14]
    return out


def plane_families():
    """사영과 거리. 가족: 원점을 지나는 평면(기존) · 평면 n·x = d · 직선 위로 사영 · 점과 평면 사이 거리."""
    out = []
    for c in plane_projection():
        c["params"]["family"] = "plane0"
        out.append(c)
    out = out[:24]
    ns, vs = _vecs(3, 8, -2, 2, seed=41), _vecs(3, 12, -3, 3, seed=42)
    off, line, dist = [], [], []
    for (n, v), d in zip(itertools.product(ns, vs), itertools.cycle([1, 2, -1, 3, -2])):
        nn, nv = n.dot(n), n.dot(v)
        if nv - d != 0:
            w = v - ((nv - d) / nn) * n
            ok_w = lambda q, n=n, v=v, d=d: same(sp.Matrix(q).dot(n), d) and same((v - sp.Matrix(q)).cross(n), sp.zeros(3, 1))
            pl = join_terms([(n[0], "x"), (n[1], "y"), (n[2], "z")])
            steps = [
                vstep(rf"{B}{{n}}\cdot{B}{{v}} - d = {tex(nv - d)},\quad {B}{{n}}\cdot{B}{{n}} = {tex(nn)}", (nv - d, nn), (v.dot(n) - d, n.norm() ** 2)),
                step(rf"\frac{{{B}{{n}}\cdot{B}{{v}} - d}}{{{B}{{n}}\cdot{B}{{n}}}}{B}{{n}} = {tup(((nv - d) / nn) * n)}", lambda q=((nv - d) / nn) * n, ok=ok_w, v=v: ok(v - q)),
                step(rf"{B}{{v}} - \frac{{{B}{{n}}\cdot{B}{{v}} - d}}{{{B}{{n}}\cdot{B}{{n}}}}{B}{{n}} = {tup(w)}", lambda q=w, ok=ok_w: ok(q)),
            ]
            bw = v - (nv / nn) * n
            decoys = [
                decoy(2, rf"{B}{{v}} - \frac{{{B}{{n}}\cdot{B}{{v}}}}{{{B}{{n}}\cdot{B}{{n}}}}{B}{{n}} = {tup(bw)}", lambda q=bw, ok=ok_w: ok(q), "algebra", WHY["pl_off"]),
                decoy(2, rf"{B}{{v}} + \frac{{{B}{{n}}\cdot{B}{{v}} - d}}{{{B}{{n}}\cdot{B}{{n}}}}{B}{{n}} = {tup(v + ((nv - d) / nn) * n)}", lambda q=v + ((nv - d) / nn) * n, ok=ok_w: ok(q), "sign", WHY["pl_sign"]),
                vdecoy(0, rf"{B}{{n}}\cdot{B}{{v}} - d = {tex(nv + d)},\quad {B}{{n}}\cdot{B}{{n}} = {tex(nn)}", (nv + d, nn), (v.dot(n) - d, n.norm() ** 2), "sign", WHY["off_sign"]),
            ]
            off.append({"params": {"n": list(n), "v": list(v), "d": d, "family": "offset"}, "tier": 3,
                        "problem": rf"{B}{{v}} = {tup(v)}\ \text{{를 평면}}\ {pl} = {d}\ \text{{위로 사영}}", "steps": steps, "decoys": decoys,
                        "verify": lambda w=w, n=n, d=d: None if same(w.dot(n), d) else "평면 위가 아님"})
        if nv != 0:
            pr = (nv / nn) * n
            ok_p = lambda q, n=n, v=v: same(sp.Matrix(q).cross(n), sp.zeros(3, 1)) and same((v - sp.Matrix(q)).dot(n), 0)
            steps = [
                vstep(rf"{B}{{d}} = {tup(n)},\quad {B}{{d}}\cdot{B}{{v}} = {tex(nv)},\quad {B}{{d}}\cdot{B}{{d}} = {tex(nn)}", (nv, nn), (v.dot(n), n.norm() ** 2)),
                step(rf"\operatorname{{proj}}_{{{B}{{d}}}}{B}{{v}} = {join_terms([(nv / nn, B + '{d}')])} = {tup(pr)}", lambda q=pr, ok=ok_p: ok(q)),
                step(rf"{B}{{v}} - \operatorname{{proj}}_{{{B}{{d}}}}{B}{{v}} = {tup(v - pr)}\ \perp {B}{{d}}\ (\text{{확인}})", lambda q=v - pr, n=n: same(q.dot(n), 0)),
            ]
            decoys = [
                decoy(1, rf"\operatorname{{proj}}_{{{B}{{d}}}}{B}{{v}} = {join_terms([(nv / sp.sqrt(nn), B + '{d}')])} = {tup((nv / sp.sqrt(nn)) * n)}", lambda q=(nv / sp.sqrt(nn)) * n, ok=ok_p: ok(q), "normalization", WHY["ln_norm"]),
                decoy(1, rf"\operatorname{{proj}}_{{{B}{{d}}}}{B}{{v}} = {tup(v - pr)}", lambda q=v - pr, ok=ok_p: ok(q), "wrong_pair", WHY["ln_sub"]),
                vdecoy(0, rf"{B}{{d}} = {tup(n)},\quad {B}{{d}}\cdot{B}{{v}} = {tex(nv + 1)},\quad {B}{{d}}\cdot{B}{{d}} = {tex(nn)}", (nv + 1, nn), (v.dot(n), n.norm() ** 2), "algebra", WHY["ln_dot"]),
            ]
            line.append({"params": {"d": list(n), "v": list(v), "family": "line"}, "tier": 1,
                         "problem": rf"{B}{{v}} = {tup(v)}\ \text{{를 방향}}\ {B}{{d}} = {tup(n)}\ \text{{인 원점 지나는 직선 위로 사영}}", "steps": steps, "decoys": decoys,
                         "verify": lambda q=pr, ok=ok_p: None if ok(q) else "사영 확인 실패"})
        if nv - d != 0:
            nrm = sp.sqrt(nn)
            D_ = sp.Abs(nv - d) / nrm
            pl = join_terms([(n[0], "x"), (n[1], "y"), (n[2], "z")])
            steps = [
                vstep(rf"{B}{{n}}\cdot{B}{{p}} - d = {tex(nv - d)}", nv - d, v.dot(n) - d),
                vstep(rf"\|{B}{{n}}\| = {tex(nrm)}", nrm, n.norm()),
                vstep(rf"\text{{거리}} = \frac{{|{tex(nv - d)}|}}{{{tex(nrm)}}} = {tex(sp.radsimp(D_))}", D_, sp.Abs(v.dot(n) - d) / n.norm()),
            ]
            decoys = [
                vdecoy(2, rf"\text{{거리}} = \frac{{|{tex(nv - d)}|}}{{{tex(nn)}}} = {tex(sp.Abs(nv - d) / nn)}", sp.Abs(nv - d) / nn, sp.Abs(v.dot(n) - d) / n.norm(), "normalization", WHY["dist_abs"]),
                vdecoy(0, rf"{B}{{n}}\cdot{B}{{p}} - d = {tex(nv + d)}", nv + d, v.dot(n) - d, "sign", WHY["pd_sign"]),
                vdecoy(1, rf"\|{B}{{n}}\| = {tex(nn)}", nn, n.norm(), "normalization", WHY["dist_abs"]),
            ]
            dist.append({"params": {"n": list(n), "p": list(v), "d": d, "family": "dist"}, "tier": 2,
                         "problem": rf"\text{{점}}\ {B}{{p}} = {tup(v)}\ \text{{와 평면}}\ {pl} = {d}\ \text{{사이의 거리}}", "steps": steps, "decoys": decoys})
    pick = lambda L, k: L[::max(1, len(L) // k)][:k]
    return out + pick(off, 18) + pick(line, 18) + pick(dist, 18)
