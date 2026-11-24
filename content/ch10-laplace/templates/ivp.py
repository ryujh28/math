"""10장 풀이 뼈대 생성기: Laplace 변환으로 초기값 문제 풀기.

각 함수는 문제 사례 목록을 돌려준다. 사례 하나는:
  problem : 문제 TeX
  tier    : 난이도 단계 1–3
  steps   : [{kind, expr, tex}]  kind = eqY(변환된 방정식) | Y(s 영역 식) | y(시간 영역 해)
  decoys  : [{pos, kind, expr, tex, error, why}]  그럴듯한 오답 블록 후보
  verify  : 빌드가 해를 독립적으로 검증할 때 쓰는 정보 (방정식, 초기조건)
검증은 tools/build.py가 한다. 여기서는 만들기만 한다.
"""
import itertools
import sympy as sp
from texkit import t, s, Y, tex, join_terms, sum_tex, shift, tshift

P2 = r"y^{\prime\prime}"
P1 = r"y^{\prime}"

WHY = {
    "ic_drop_p": "y′의 변환 sY − y(0)에서 −y(0)을 빠뜨렸습니다.",
    "ic_drop_1": "ℒ{y′} = sY − y(0)인데 −y(0) 항이 빠졌습니다.",
    "ic_sign": "도함수 변환의 초기값 항은 모두 − 부호입니다: s²Y − s·y(0) − y′(0).",
    "num": "Y로 정리할 때 분자의 초기값 항을 잘못 모았습니다.",
    "pf_sign": "부분분수 계수의 부호가 틀렸습니다. 통분하면 원래 분자와 달라집니다.",
    "pf_coef": "부분분수 계수를 잘못 구했습니다. 통분하면 원래 분자와 달라집니다.",
    "exp_sign": "1/(s − r) ↔ e^{rt}: 지수의 부호는 극점과 같습니다.",
    "swap": "계수를 서로 바꿔 붙였습니다. 각 계수는 자기 극점의 항에 붙습니다.",
    "rep_t": "1/(s − r)²의 역변환은 t·e^{rt}입니다. t가 빠졌습니다.",
    "rep_coef": "(s − r)² 꼴로 나눌 때 분자를 (s − r)로 다시 써야 합니다. r·y(0) 항이 빠졌습니다.",
    "csq_sign": "완전제곱 s² + ps + q = (s − α)² + β²에서 α의 부호가 틀렸습니다.",
    "csq_beta": "sin 항은 β/((s − α)² + β²) 꼴이어야 합니다. 계수를 β로 나누지 않았습니다.",
    "imp_u": "e^{−cs}가 붙은 항은 t-이동 정리로 되돌립니다. u(t − c)가 빠지면 t < c에서도 진동하게 됩니다.",
    "imp_shift": "t-이동 정리는 함수 전체를 c만큼 옮깁니다: sin ω(t − c)여야 합니다.",
    "imp_delta": "δ(t − c)의 변환은 1이 아니라 e^{−cs}입니다.",
    "y_coef": "초기조건으로 정한 계수가 틀렸습니다.",
}


def _ics_tex(y0, v0=None):
    out = f"y(0) = {tex(y0)}"
    if v0 is not None:
        out += rf",\; {P1}(0) = {tex(v0)}"
    return out


# ---------------------------------------------------------------- 1계
def ivp1():
    out = []
    for a, y0 in itertools.product([1, 2, 3, 4], [-3, -2, -1, 1, 2, 3]):  # 동차
        out.append(_ivp1_case(a, y0, 0, None, tier=1))
    for a, y0, m in itertools.product([1, 2, 3], [-2, -1, 0, 1, 2, 3], [-2, -1, 1, 2, 3]):  # 상수 강제항
        k = a * m
        if y0 == m:
            continue
        out.append(_ivp1_case(a, y0, k, None, tier=2))
    for a, b, y0, k in itertools.product([1, 2, 3], [-1, 1, 2], [-1, 0, 1, 2], [1, 2, 3, 4]):  # 지수 강제항
        if a + b == 0:
            continue
        A = sp.Rational(k, a + b)
        if A.q != 1 or y0 - A == 0:
            continue
        out.append(_ivp1_case(a, y0, k, b, tier=3))
    return out


def _ivp1_case(a, y0, k, b, tier):
    R_t = k * sp.exp(b * t) if b is not None else sp.Integer(k)
    R_s = sp.Integer(0) if k == 0 else (k / (s - b) if b is not None else k / s)
    problem = f"{join_terms([(1, P1), (a, 'y')])} = {tex(R_t)},\\quad {_ics_tex(y0)}"
    eq = s * Y - y0 + a * Y - R_s
    eq_tex = f"{join_terms([(1, 'sY'), (-y0, ''), (a, 'Y')])} = {tex(R_s)}"
    Ys = sp.factor((y0 + R_s) / (s + a))
    steps = [{"kind": "eqY", "expr": eq, "tex": eq_tex},
             {"kind": "Y", "expr": Ys, "tex": "Y = " + tex(Ys)}]
    decoys = []
    # 초기조건 누락
    decoys.append({"pos": 0, "kind": "eqY", "expr": s * Y + a * Y - R_s,
                   "tex": f"{join_terms([(1, 'sY'), (a, 'Y')])} = {tex(R_s)}",
                   "error": "initial_condition", "why": WHY["ic_drop_1"]})
    decoys.append({"pos": 0, "kind": "eqY", "expr": s * Y + y0 + a * Y - R_s,
                   "tex": f"{join_terms([(1, 'sY'), (y0, ''), (a, 'Y')])} = {tex(R_s)}",
                   "error": "sign", "why": WHY["ic_sign"]})
    if k == 0:
        y = y0 * sp.exp(-a * t)
        decoys.append({"pos": 1, "kind": "Y", "expr": y0 / (s - a), "tex": "Y = " + tex(y0 / (s - a)),
                       "error": "sign", "why": "sY + aY = (s + a)Y 이므로 분모는 s + a입니다."})
        decoys.append({"pos": 2, "kind": "y", "expr": y0 * sp.exp(a * t), "tex": "y = " + tex(y0 * sp.exp(a * t)),
                       "error": "sign", "why": WHY["exp_sign"]})
    else:
        pf = sp.apart(Ys, s)
        steps.append({"kind": "Y", "expr": pf, "tex": "Y = " + sum_tex(pf)})
        terms = sp.Add.make_args(pf)
        flipped = pf - 2 * terms[-1]
        decoys.append({"pos": 2, "kind": "Y", "expr": flipped, "tex": "Y = " + sum_tex(flipped),
                       "error": "sign", "why": WHY["pf_sign"]})
        if b is None:
            y = sp.Rational(k, a) + (y0 - sp.Rational(k, a)) * sp.exp(-a * t)
        else:
            A = sp.Rational(k, a + b)
            y = A * sp.exp(b * t) + (y0 - A) * sp.exp(-a * t)
        if b is None:
            ybad = (y - k / a) .subs(t, -t) + sp.Rational(k, a)
        else:
            ybad = y.subs(t, -t)
        decoys.append({"pos": 3, "kind": "y", "expr": ybad, "tex": "y = " + sum_tex(ybad),
                       "error": "sign", "why": WHY["exp_sign"]})
    steps.append({"kind": "y", "expr": y, "tex": "y = " + sum_tex(y)})
    return {"params": {"a": a, "y0": y0, "k": k, "b": b}, "tier": tier, "problem": problem,
            "steps": steps, "decoys": decoys,
            "verify": {"coeffs": [a], "rhs": R_t, "ics": [y0], "y": y}}


# ---------------------------------------------------------------- 2계 공통
def _eq2(p, q, y0, v0, R_s, drop_p_ic=False, flip_ic=False):
    sg = 1 if flip_ic else -1
    if drop_p_ic or y0 == 0:
        pterm = (p, "sY")
        pexpr = p * s * Y
    else:
        pterm = (p, f"(sY {'-' if y0 > 0 else '+'} {abs(y0)})")
        pexpr = p * (s * Y - y0)
    parts = [(1, "s^{2}Y"), (sg * y0, "s"), (sg * v0, ""), pterm, (q, "Y")]
    expr = s**2 * Y + sg * y0 * s + sg * v0 + pexpr + q * Y - R_s
    return expr, f"{join_terms(parts)} = {tex(R_s)}"


def _problem2(p, q, y0, v0, R_t=0):
    return f"{join_terms([(1, P2), (p, P1), (q, 'y')])} = {tex(R_t)},\\quad {_ics_tex(y0, v0)}"


def _ic_decoys(p, q, y0, v0, R_s):
    out = []
    if p != 0 and y0 != 0:
        e, tx = _eq2(p, q, y0, v0, R_s, drop_p_ic=True)
        out.append({"pos": 0, "kind": "eqY", "expr": e, "tex": tx, "error": "initial_condition", "why": WHY["ic_drop_p"]})
    if y0 != 0 or v0 != 0:
        e, tx = _eq2(p, q, y0, v0, R_s, flip_ic=True)
        out.append({"pos": 0, "kind": "eqY", "expr": e, "tex": tx, "error": "sign", "why": WHY["ic_sign"]})
    return out


# ---------------------------------------------------------------- 서로 다른 실근
def ivp2_real():
    out = []
    roots = [-4, -3, -2, -1, 1, 2]
    for r1, r2 in itertools.combinations(roots, 2):
        for y0, v0 in itertools.product([-2, -1, 0, 1, 2], [-3, -2, -1, 0, 1, 2, 3]):
            if y0 == 0 and v0 == 0:
                continue
            p, q = -(r1 + r2), r1 * r2
            num = y0 * s + v0 + p * y0
            A = sp.Rational(num.subs(s, r1), r1 - r2)
            B = sp.Rational(num.subs(s, r2), r2 - r1)
            if A == 0 or B == 0:
                continue
            small = r1 < 0 and r2 < 0 and abs(r1) <= 3 and abs(r2) <= 3 and A.q == 1 and B.q == 1 and y0 >= 0
            tier = 1 if small else 2
            Ys = num / ((s - r1) * (s - r2))
            pf = A / (s - r1) + B / (s - r2)
            y = A * sp.exp(r1 * t) + B * sp.exp(r2 * t)
            eq, eqt = _eq2(p, q, y0, v0, 0)
            steps = [{"kind": "eqY", "expr": eq, "tex": eqt},
                     {"kind": "Y", "expr": Ys, "tex": "Y = " + tex(sp.factor(Ys))},
                     {"kind": "Y", "expr": pf, "tex": "Y = " + sum_tex(pf)},
                     {"kind": "y", "expr": y, "tex": "y = " + sum_tex(y)}]
            decoys = _ic_decoys(p, q, y0, v0, 0)
            if p * y0 != 0:
                bad = (y0 * s + v0) / ((s - r1) * (s - r2))
                decoys.append({"pos": 1, "kind": "Y", "expr": bad, "tex": "Y = " + tex(sp.factor(bad)),
                               "error": "algebra", "why": WHY["num"]})
            bad = A / (s - r1) - B / (s - r2)
            decoys.append({"pos": 2, "kind": "Y", "expr": bad, "tex": "Y = " + sum_tex(bad), "error": "sign", "why": WHY["pf_sign"]})
            bad = A * sp.exp(-r1 * t) + B * sp.exp(-r2 * t)
            decoys.append({"pos": 3, "kind": "y", "expr": bad, "tex": "y = " + sum_tex(bad), "error": "sign", "why": WHY["exp_sign"]})
            if A != B:
                bad = B * sp.exp(r1 * t) + A * sp.exp(r2 * t)
                decoys.append({"pos": 3, "kind": "y", "expr": bad, "tex": "y = " + sum_tex(bad), "error": "algebra", "why": WHY["swap"]})
            out.append({"params": {"r1": r1, "r2": r2, "y0": y0, "v0": v0}, "tier": tier,
                        "problem": _problem2(p, q, y0, v0), "steps": steps, "decoys": decoys,
                        "verify": {"coeffs": [p, q], "rhs": 0, "ics": [y0, v0], "y": y}})
    return out


# ---------------------------------------------------------------- 중근
def ivp2_repeated():
    out = []
    for r in [-3, -2, -1, 1, 2]:
        for y0, v0 in itertools.product([-2, -1, 1, 2], [-3, -2, -1, 0, 1, 2, 3]):
            p, q = -2 * r, r * r
            K = v0 + p * y0 + r * y0
            if K == 0:
                continue
            num = y0 * s + v0 + p * y0
            Ys = num / (s - r) ** 2
            pf = y0 / (s - r) + K / (s - r) ** 2
            y = y0 * sp.exp(r * t) + K * t * sp.exp(r * t)
            eq, eqt = _eq2(p, q, y0, v0, 0)
            steps = [{"kind": "eqY", "expr": eq, "tex": eqt},
                     {"kind": "Y", "expr": Ys, "tex": "Y = " + tex(sp.factor(Ys))},
                     {"kind": "Y", "expr": pf, "tex": "Y = " + sum_tex(pf)},
                     {"kind": "y", "expr": y, "tex": "y = " + sum_tex(y)}]
            decoys = _ic_decoys(p, q, y0, v0, 0)
            K2 = v0 + p * y0
            if K2 != 0 and K2 != K:
                bad = y0 / (s - r) + K2 / (s - r) ** 2
                decoys.append({"pos": 2, "kind": "Y", "expr": bad, "tex": "Y = " + sum_tex(bad), "error": "algebra", "why": WHY["rep_coef"]})
            bad = y0 * sp.exp(r * t) + K * sp.exp(r * t)
            if sp.simplify(bad) != 0:
                decoys.append({"pos": 3, "kind": "y", "expr": bad,
                               "tex": "y = " + join_terms([(y0, tex(sp.exp(r * t))), (K, tex(sp.exp(r * t)))]),
                               "error": "wrong_pair", "why": WHY["rep_t"]})
            bad = y0 * sp.exp(-r * t) + K * t * sp.exp(-r * t)
            decoys.append({"pos": 3, "kind": "y", "expr": bad, "tex": "y = " + sum_tex(bad), "error": "sign", "why": WHY["exp_sign"]})
            tier = 2 if r < 0 and y0 > 0 else 3
            out.append({"params": {"r": r, "y0": y0, "v0": v0}, "tier": tier,
                        "problem": _problem2(p, q, y0, v0), "steps": steps, "decoys": decoys,
                        "verify": {"coeffs": [p, q], "rhs": 0, "ics": [y0, v0], "y": y}})
    return out


# ---------------------------------------------------------------- 복소근 (완전제곱 → s-이동)
def ivp2_complex():
    out = []
    for al, be in itertools.product([-3, -2, -1, 1], [1, 2, 3]):
        for y0, v0 in itertools.product([-2, -1, 1, 2], [-3, -2, -1, 0, 1, 2, 3]):
            p, q = -2 * al, al * al + be * be
            C = v0 - al * y0          # 분자 = y0(s − α) + C
            num = y0 * s + v0 + p * y0
            den = s**2 + p * s + q
            Ys = num / den
            sq = f"\\left({shift(al)}\\right)^{{2}} + {be * be}"
            csq = (y0 * (s - al) + C) / ((s - al) ** 2 + be**2)
            csq_tex = rf"Y = \frac{{{join_terms([(y0, f'({shift(al)})'), (C, '')])}}}{{{sq}}}"
            Cb = sp.Rational(C, be)
            y = sp.exp(al * t) * (y0 * sp.cos(be * t) + Cb * sp.sin(be * t))
            inner = join_terms([(y0, rf"\cos {tex(be * t)}"), (Cb, rf"\sin {tex(be * t)}")])
            y_tex = rf"y = {tex(sp.exp(al * t))}\left({inner}\right)"
            eq, eqt = _eq2(p, q, y0, v0, 0)
            steps = [{"kind": "eqY", "expr": eq, "tex": eqt},
                     {"kind": "Y", "expr": Ys, "tex": rf"Y = \frac{{{tex(num)}}}{{{tex(den)}}}"},
                     {"kind": "Y", "expr": csq, "tex": csq_tex},
                     {"kind": "y", "expr": y, "tex": y_tex}]
            decoys = _ic_decoys(p, q, y0, v0, 0)
            bad = (y0 * (s + al) + C) / ((s + al) ** 2 + be**2)
            sqb = f"\\left({shift(-al)}\\right)^{{2}} + {be * be}"
            decoys.append({"pos": 2, "kind": "Y", "expr": bad,
                           "tex": rf"Y = \frac{{{join_terms([(y0, f'({shift(-al)})'), (C, '')])}}}{{{sqb}}}",
                           "error": "sign", "why": WHY["csq_sign"]})
            bad = sp.exp(-al * t) * (y0 * sp.cos(be * t) + Cb * sp.sin(be * t))
            decoys.append({"pos": 3, "kind": "y", "expr": bad, "tex": rf"y = {tex(sp.exp(-al * t))}\left({inner}\right)",
                           "error": "sign", "why": WHY["exp_sign"]})
            if be != 1 and C != 0:
                bad = sp.exp(al * t) * (y0 * sp.cos(be * t) + C * sp.sin(be * t))
                inner2 = join_terms([(y0, rf"\cos {tex(be * t)}"), (C, rf"\sin {tex(be * t)}")])
                decoys.append({"pos": 3, "kind": "y", "expr": bad, "tex": rf"y = {tex(sp.exp(al * t))}\left({inner2}\right)",
                               "error": "missing_factor", "why": WHY["csq_beta"]})
            tier = 2 if (al < 0 and Cb.q == 1) else 3
            out.append({"params": {"alpha": al, "beta": be, "y0": y0, "v0": v0}, "tier": tier,
                        "problem": _problem2(p, q, y0, v0), "steps": steps, "decoys": decoys,
                        "verify": {"coeffs": [p, q], "rhs": 0, "ics": [y0, v0], "y": y}})
    return out


# ---------------------------------------------------------------- 충격 (δ 강제항 → t-이동)
def ivp2_impulse():
    out = []
    for w, c, v0 in itertools.product([1, 2, 3], [1, 2, 3], [0, 1, 2]):
        q = w * w
        R_s = sp.exp(-c * s)
        eq, eqt = _eq2(0, q, 0, v0, R_s)
        cs = "s" if c == 1 else f"{c}s"
        eqt = eqt.replace(tex(R_s), f"e^{{-{cs}}}")
        Ys = (v0 + sp.exp(-c * s)) / (s**2 + q)
        den = f"s^{{2}} + {q}"
        Y_tex = "Y = " + (rf"\frac{{{v0}}}{{{den}}} + " if v0 else "") + rf"\frac{{e^{{-{cs}}}}}{{{den}}}"
        a1 = sp.Rational(v0, w)
        a2 = sp.Rational(1, w)
        y = a1 * sp.sin(w * t) + a2 * sp.Heaviside(t - c) * sp.sin(w * (t - c))
        wt = "t" if w == 1 else f"{w}t"
        wtc = f"({tshift(c)})" if w == 1 else f"{w}({tshift(c)})"
        y_tex = "y = " + join_terms([(a1, rf"\sin {wt}"), (a2, rf"\,u({tshift(c)})\sin {wtc}")])
        steps = [{"kind": "eqY", "expr": eq, "tex": eqt},
                 {"kind": "Y", "expr": Ys, "tex": Y_tex},
                 {"kind": "y", "expr": y, "tex": y_tex}]
        bad_eq, bad_eqt = _eq2(0, q, 0, v0, 1)
        decoys = [{"pos": 0, "kind": "eqY", "expr": bad_eq, "tex": bad_eqt, "error": "wrong_pair", "why": WHY["imp_delta"]}]
        bad = a1 * sp.sin(w * t) + a2 * sp.sin(w * (t - c))
        decoys.append({"pos": 2, "kind": "y", "expr": bad,
                       "tex": "y = " + join_terms([(a1, rf"\sin {wt}"), (a2, rf"\sin {wtc}")]),
                       "error": "theorem_condition", "why": WHY["imp_u"]})
        bad = a1 * sp.sin(w * t) + a2 * sp.Heaviside(t - c) * sp.sin(w * t)
        decoys.append({"pos": 2, "kind": "y", "expr": bad,
                       "tex": "y = " + join_terms([(a1, rf"\sin {wt}"), (a2, rf"\,u({tshift(c)})\sin {wt}")]),
                       "error": "algebra", "why": WHY["imp_shift"]})
        out.append({"params": {"omega": w, "c": c, "v0": v0}, "tier": 3,
                    "problem": f"{join_terms([(1, P2), (q, 'y')])} = \\delta({tshift(c)}),\\quad {_ics_tex(0, v0)}",
                    "steps": steps, "decoys": decoys,
                    "verify": {"coeffs": [0, q], "rhs": 0, "ics": [0, v0], "y": y, "impulse": c}})
    return out
