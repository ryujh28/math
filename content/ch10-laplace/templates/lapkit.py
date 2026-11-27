"""Laplace 초기값 문제 공통 생성기.

방정식 m·y⁽ⁿ⁾ + … = r(t)와 초기값만 주면 네 단계(변환 → Y 정리 → 부분분수 → 역변환)와
흔한 오답 블록을 만든다. 입력 r(t)는 상수·지수·사인·계단 u(t − c)·델타 δ(t − c)의 합.
e^{-cs}가 붙는 항(계단·델타)은 따로 모아 t-이동 정리로 되돌린다.

검증은 지금처럼 tools/build.py가 한다 (해가 방정식·초기값을 만족하는지, 각 단계 식이 Y와 같은지).
여기서는 식과 TeX만 만든다.
"""
import sympy as sp
from texkit import t, s, Y, tex, join_terms, sum_tex, tshift

P2 = r"y^{\prime\prime}"
P1 = r"y^{\prime}"
TAU = sp.Symbol("tau")

WHY = {
    "ic_sign": r"도함수 변환의 초기값 항은 모두 $-$ 부호입니다: $\mathcal{L}\{y^{\prime}\} = sY - y(0)$, $\mathcal{L}\{y^{\prime\prime}\} = s^2Y - sy(0) - y^{\prime}(0)$.",
    "ic_drop_p": r"$y^{\prime}$의 변환 $sY - y(0)$에서 $-y(0)$을 빠뜨렸습니다.",
    "const_s": r"상수 $K$의 변환은 $K$가 아니라 $\dfrac{K}{s}$입니다.",
    "exp_s": r"$e^{bt}$의 변환은 $\dfrac{1}{s - b}$입니다. 극점의 부호가 지수와 같습니다.",
    "sin_pair": r"$\sin bt$의 변환은 $\dfrac{b}{s^2 + b^2}$입니다. $\dfrac{s}{s^2 + b^2}$는 $\cos bt$의 변환입니다.",
    "step_s": r"$u(t - c)$의 변환은 $\dfrac{e^{-cs}}{s}$입니다. $\dfrac{1}{s}$이 빠졌습니다.",
    "delta_s": r"$\delta(t - c)$의 변환은 $1$이 아니라 $e^{-cs}$입니다.",
    "res_s": r"$te^{at}$의 변환은 $\dfrac{1}{(s - a)^2}$입니다.",
    "num": r"$Y$로 정리할 때 분자의 초기값 항을 잘못 모았습니다.",
    "monic": r"분모는 방정식 계수 그대로 $ms^2 + ps + q$입니다. 최고차 계수를 빠뜨렸습니다.",
    "pf_sign": r"부분분수 계수의 부호가 틀렸습니다. 통분하면 원래 분자와 달라집니다.",
    "pf_miss": r"부분분수로 나눌 때 항 하나를 빠뜨렸습니다. 분모의 인수마다 항이 하나씩 있어야 합니다.",
    "exp_sign": r"$\dfrac{1}{s - r} \leftrightarrow e^{rt}$: 지수의 부호는 극점과 같습니다.",
    "rep_t": r"$\dfrac{1}{(s - r)^k}$의 역변환은 $\dfrac{t^{k-1}}{(k-1)!}e^{rt}$입니다. $t$의 거듭제곱이 빠지거나 틀렸습니다.",
    "u_drop": r"$e^{-cs}$가 붙은 항은 $t$-이동 정리로 되돌립니다. $u(t - c)$가 빠지면 $t < c$에서도 반응이 생깁니다.",
    "u_noshift": r"$t$-이동 정리는 함수 전체를 $c$만큼 옮깁니다: $f(t)$가 아니라 $f(t - c)$입니다.",
}


def F(e):
    """한 분수로: 분자 전개, 분모 인수분해. 음수 분자는 앞에 - 를 뺀다."""
    e = sp.cancel(sp.together(e))
    n, d = sp.fraction(e)
    n, d = sp.expand(n), sp.factor(d)
    if d == 1:
        return tex(n)
    neg = n.could_extract_minus_sign()
    if neg:
        n = sp.expand(-n)
    return ("- " if neg else "") + rf"\frac{{{tex(n)}}}{{{tex(d)}}}"


def _split_shift(R_s):
    """R(s) = R0 + Σ e^{-cs}·R_c 로 나눈다 → (R0, {c: R_c})."""
    R0, sh = sp.Integer(0), {}
    for term in sp.Add.make_args(sp.expand(R_s)):
        c = None
        for f in sp.Mul.make_args(term):
            if f.func == sp.exp:
                c = sp.simplify(-f.args[0] / s)
        if c is None:
            R0 += term
        else:
            sh[c] = sh.get(c, 0) + sp.simplify(term * sp.exp(c * s))
    return sp.simplify(R0), sh


def _ilt(e):
    """유리식의 역변환 (항마다)."""
    out = 0
    for term in sp.Add.make_args(sp.apart(e, s)):
        g = sp.inverse_laplace_transform(term, s, t)
        out += g.subs(sp.Heaviside(t), 1)
    return sp.expand(out)


def _shift_tex(g, c):
    """g(t)를 t - c 자리에 넣은 꼴의 TeX: u(t - c)·g(t - c)."""
    body = sum_tex(g.subs(t, TAU)).replace(r"\tau", f"({tshift(c)})")
    single = len(sp.Add.make_args(g)) == 1
    return rf"u({tshift(c)})" + (body if single and not body.startswith("-") else rf"\left({body}\right)")


def _frac_parts(tx):
    """'\\frac{A}{B}' → (A, B), 아니면 None."""
    if not tx.startswith(r"\frac{"):
        return None
    depth, i = 0, len(r"\frac")
    for j in range(i, len(tx)):
        depth += {"{": 1, "}": -1}.get(tx[j], 0)
        if depth == 0:
            A, rest = tx[i + 1:j], tx[j + 1:]
            break
    if not rest.startswith("{") or not rest.endswith("}"):
        return None
    depth = 0
    for j, ch in enumerate(rest):
        depth += {"{": 1, "}": -1}.get(ch, 0)
        if depth == 0 and j != len(rest) - 1:
            return None
    return A, rest[1:-1]


def _with_exp(e, tx):
    """e^{-cs}와 식 tx를 곱한 TeX: 분수면 분자에 넣는다 (\\frac{4e^{-s}}{s})."""
    neg = tx.startswith("-")
    body = tx[1:].lstrip() if neg else tx
    fp = _frac_parts(body)
    if fp:
        A, B = fp
        num = e if A == "1" else f"{A} {e}"
        out = rf"\frac{{{num}}}{{{B}}}"
    elif body in ("", "1"):
        out = e
    elif "(" not in body and "\\" not in body:
        out = f"{body} {e}"          # 3 e^{-2s}
    else:
        out = f"{e}{body}"
    return ("- " if neg else "") + out


def _tail(base, parts):
    """base TeX 뒤에 e^{-cs} 꼴 항들을 붙인다. parts = [(c, tex)]"""
    out = base
    for c, tx in parts:
        e = tex(sp.exp(-c * s))
        piece = _with_exp(e, tx)
        if out in ("", "0"):
            out = piece
        else:
            out += f" - {piece[1:].lstrip()}" if piece.startswith("-") else f" + {piece}"
    return out


def eq_tex(m, co, ics, R_s, flip=False, drop_p=False):
    """변환된 방정식 (expr, TeX). co = [p] (1계) 또는 [p, q] (2계), m은 최고차 계수."""
    sg = 1 if flip else -1
    if len(co) == 1:
        (a,), (y0,) = co, ics
        inner = join_terms([(1, "sY"), (sg * y0, "")])
        lead = (m, rf"\left({inner}\right)" if (m != 1 and y0) else inner if m == 1 else "sY")
        parts = [lead] if m != 1 else [(1, "sY"), (sg * y0, "")]
        parts += [(a, "Y")]
        expr = m * (s * Y + sg * y0) + a * Y - R_s
    else:
        (p, q), (y0, v0) = co, ics
        if drop_p or y0 == 0:
            pterm, pexpr = (p, "sY"), p * s * Y
        else:
            pterm = (p, f"(sY {'-' if (y0 > 0) != flip else '+'} {abs(y0)})")
            pexpr = p * (s * Y + sg * y0)
        if m == 1:
            parts = [(1, "s^{2}Y"), (sg * y0, "s"), (sg * v0, ""), pterm, (q, "Y")]
        else:
            inner = join_terms([(1, "s^{2}Y"), (sg * y0, "s"), (sg * v0, "")])
            parts = [(m, rf"\left({inner}\right)" if (y0 or v0) else "s^{2}Y"), pterm, (q, "Y")]
        expr = m * (s**2 * Y + sg * y0 * s + sg * v0) + pexpr + q * Y - R_s
    rhs = "0" if R_s == 0 else _tail(F(_split_shift(R_s)[0]) if _split_shift(R_s)[0] != 0 else "",
                                     [(c, F(r) if r != 1 else "") for c, r in sorted(_split_shift(R_s)[1].items())])
    return expr, f"{join_terms(parts)} = {rhs}"


def problem_tex(m, co, R_t, ics):
    if len(co) == 1:
        lhs = join_terms([(m, P1), (co[0], "y")])
        ic = f"y(0) = {tex(ics[0])}"
    else:
        lhs = join_terms([(m, P2), (co[0], P1), (co[1], "y")])
        ic = f"y(0) = {tex(ics[0])},\\; {P1}(0) = {tex(ics[1])}"
    rt = tex(R_t).replace(r"\theta\left(", "u\\left(") if R_t != 0 else "0"
    return f"{lhs} = {rt},\\quad {ic}"


def case(m, co, R_t, ics, *, family, tier, bad_R=None, params=None):
    """사례 하나. bad_R = [(틀린 R(s), why 키)] — 입력 변환 실수."""
    R_t = sp.sympify(R_t)
    R_s = sp.laplace_transform(R_t, t, s, noconds=True) if R_t != 0 else sp.Integer(0)
    R_s = sp.simplify(R_s)
    R0, sh = _split_shift(R_s)
    if len(co) == 1:
        den = m * s + co[0]
        icn = m * ics[0]
    else:
        den = m * s**2 + co[0] * s + co[1]
        icn = m * (ics[0] * s + ics[1]) + co[0] * ics[0]
    part0 = sp.cancel((icn + R0) / den)
    if part0 != 0 and sp.degree(sp.fraction(part0)[1], s) < sp.degree(sp.fraction(sp.together((icn + R0) / den))[1], s):
        return None      # 초기값이 과도 응답을 정확히 지워 극점이 사라지는 특수한 경우: 문제로 어색하므로 뺀다
    parts1 = {c: sp.cancel(r / den) for c, r in sorted(sh.items())}
    Ys = part0 + sum(sp.exp(-c * s) * e for c, e in parts1.items())
    a0 = sp.apart(part0, s) if part0 != 0 else sp.Integer(0)
    a1 = {c: sp.apart(e, s) for c, e in parts1.items()}
    g0 = _ilt(part0) if part0 != 0 else sp.Integer(0)
    g1 = {c: _ilt(e) for c, e in parts1.items()}
    y = g0 + sum(sp.Heaviside(t - c) * g.subs(t, t - c) for c, g in g1.items())

    eq, eqt = eq_tex(m, co, ics, R_s)
    Yt = "Y = " + _tail(F(part0) if part0 != 0 else "", [(c, F(e)) for c, e in parts1.items()])
    pft = "Y = " + _tail(sum_tex(a0) if a0 != 0 else "", [(c, rf"\left({sum_tex(e)}\right)" if len(sp.Add.make_args(e)) > 1 else F(e)) for c, e in a1.items()])
    yt = "y = " + (sum_tex(g0) if g0 != 0 else "")
    for c, g in g1.items():
        piece = _shift_tex(g, c)
        yt = (yt + " + " + piece) if yt != "y = " else yt + piece
    steps = [{"kind": "eqY", "expr": eq, "tex": eqt}, {"kind": "Y", "expr": Ys, "tex": Yt}]
    if pft.replace(" ", "") != Yt.replace(" ", ""):
        steps.append({"kind": "Y", "expr": a0 + sum(sp.exp(-c * s) * e for c, e in a1.items()), "tex": pft})
    steps.append({"kind": "y", "expr": y, "tex": yt})

    dec = []
    if any(ics):
        e, tx = eq_tex(m, co, ics, R_s, flip=True)
        dec.append({"pos": 0, "kind": "eqY", "expr": e, "tex": tx, "error": "sign", "why": WHY["ic_sign"]})
    if len(co) == 2 and co[0] and ics[0]:
        e, tx = eq_tex(m, co, ics, R_s, drop_p=True)
        dec.append({"pos": 0, "kind": "eqY", "expr": e, "tex": tx, "error": "initial_condition", "why": WHY["ic_drop_p"]})
    for bR, why in bad_R or []:
        e, tx = eq_tex(m, co, ics, bR)
        dec.append({"pos": 0, "kind": "eqY", "expr": e, "tex": tx, "error": "wrong_pair", "why": WHY[why]})
    if m != 1:
        bad = sp.cancel((icn + R0) / (den - (m - 1) * s ** (len(co))))
        if len(parts1) == 0:
            dec.append({"pos": 1, "kind": "Y", "expr": bad, "tex": "Y = " + F(bad), "error": "algebra", "why": WHY["monic"]})
    elif len(co) == 2 and co[0] and ics[0]:
        bad = sp.cancel((m * (ics[0] * s + ics[1]) + R0) / den) + sum(sp.exp(-c * s) * e for c, e in parts1.items())
        dec.append({"pos": 1, "kind": "Y", "expr": bad, "tex": "Y = " + _tail(F(bad.subs({sp.exp(-c * s): 0 for c in parts1})), [(c, F(e)) for c, e in parts1.items()]),
                    "error": "algebra", "why": WHY["num"]})
    terms = sp.Add.make_args(a0) if a0 != 0 else ()
    if len(steps) == 4 and len(terms) >= 2:
        bad0 = a0 - 2 * terms[-1]
        dec.append({"pos": 2, "kind": "Y", "expr": bad0 + sum(sp.exp(-c * s) * e for c, e in a1.items()),
                    "tex": "Y = " + _tail(sum_tex(bad0), [(c, rf"\left({sum_tex(e)}\right)" if len(sp.Add.make_args(e)) > 1 else F(e)) for c, e in a1.items()]),
                    "error": "sign", "why": WHY["pf_sign"]})
        bad0 = a0 - terms[0]
        if bad0 != 0:
            dec.append({"pos": 2, "kind": "Y", "expr": bad0 + sum(sp.exp(-c * s) * e for c, e in a1.items()),
                        "tex": "Y = " + _tail(sum_tex(bad0), [(c, rf"\left({sum_tex(e)}\right)" if len(sp.Add.make_args(e)) > 1 else F(e)) for c, e in a1.items()]),
                        "error": "missing_factor", "why": WHY["pf_miss"]})
    # 역변환 실수
    flip = lambda g: g.replace(sp.exp, lambda a: sp.exp(-a))
    last = len(steps) - 1
    if g0 != 0 and g0.has(sp.exp) and flip(g0) != g0:
        bad = flip(g0) + (y - g0)
        tx = "y = " + sum_tex(flip(g0))
        for c, g in g1.items():
            tx += " + " + _shift_tex(g, c)
        dec.append({"pos": last, "kind": "y", "expr": bad, "tex": tx, "error": "sign", "why": WHY["exp_sign"]})
    if g0 != 0:
        # te^{rt} 꼴에서 t를 빠뜨린 실수 (중근·공명)
        def drop_t(term):
            k = sum(int(f.exp) if f.is_Pow else 1 for f in sp.Mul.make_args(term) if f == t or (f.is_Pow and f.base == t))
            return sp.cancel(term / t**k) if term.has(sp.exp) and k >= 1 else term
        bad0 = sum(drop_t(term) for term in sp.Add.make_args(g0))
        if sp.simplify(bad0 - g0) != 0 and len(sp.Add.make_args(bad0)) == len(sp.Add.make_args(g0)) and bad0.has(t):
            tx = "y = " + sum_tex(bad0)
            for c, g in g1.items():
                tx += " + " + _shift_tex(g, c)
            dec.append({"pos": last, "kind": "y", "expr": bad0 + (y - g0), "tex": tx, "error": "wrong_pair", "why": WHY["rep_t"]})
    for c, g in g1.items():
        bad = g0 + sum(sp.Heaviside(t - cc) * gg.subs(t, t - cc) for cc, gg in g1.items() if cc != c) + g.subs(t, t - c)
        tx = "y = " + (sum_tex(g0) + " + " if g0 != 0 else "")
        body = sum_tex(g.subs(t, TAU)).replace(r"\tau", f"({tshift(c)})")
        tx += body if g0 == 0 else (body if not body.startswith("-") else body)
        tx = tx.replace("+ -", "- ")
        others = [_shift_tex(gg, cc) for cc, gg in g1.items() if cc != c]
        for o in others:
            tx += " + " + o
        dec.append({"pos": last, "kind": "y", "expr": bad, "tex": tx, "error": "theorem_condition", "why": WHY["u_drop"]})
        bad2 = g0 + sp.Heaviside(t - c) * g + sum(sp.Heaviside(t - cc) * gg.subs(t, t - cc) for cc, gg in g1.items() if cc != c)
        tx2 = "y = " + (sum_tex(g0) + " + " if g0 != 0 else "") + rf"u({tshift(c)})" + (rf"\left({sum_tex(g)}\right)" if len(sp.Add.make_args(g)) > 1 else sum_tex(g))
        for o in others:
            tx2 += " + " + o
        dec.append({"pos": last, "kind": "y", "expr": bad2, "tex": tx2, "error": "algebra", "why": WHY["u_noshift"]})

    v = {"coeffs": [sp.Rational(c_, m) for c_ in co], "rhs": R_t / m, "ics": list(ics), "y": y}
    if R_t.has(sp.DiracDelta):
        cs = [a.args[0] for a in R_t.atoms(sp.DiracDelta)]
        assert len(cs) == 1 and m == 1
        c = sp.solve(cs[0], t)[0]
        v["rhs"] = R_t.subs(sp.DiracDelta(t - c), 0)
        v["impulse"] = c
    return {"params": {**(params or {}), "family": family, "m": m, "co": list(co), "R": str(R_t), "ics": list(ics)},
            "tier": tier, "problem": problem_tex(m, co, R_t, ics), "steps": steps, "decoys": dec, "verify": v}
