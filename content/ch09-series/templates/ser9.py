"""9장 급수해와 Frobenius — 생성기.

참값 확인은 '잘린 급수를 방정식에 넣었을 때 낮은 차수 계수가 모두 0인가'로 한다
(재귀식·계수·급수 모두 이 한 가지 기준으로 판정). 정규화된 다항식 해는 SymPy의
legendre·hermite·chebyshevt·laguerre와 비교한다.
"""
import itertools
import random
import sympy as sp
from texkit import tex, join_terms, poly_tex
from checks import same, opt, step, vstep, decoy, vdecoy, x

n = sp.Symbol("n", integer=True)
A0, A1 = sp.symbols("a_0 a_1")
AS = sp.symbols("q0:14")          # 계수 기호 (판정용)
P2, P1 = r"y^{\prime\prime}", r"y^{\prime}"


def _get(a, k):
    return a[k] if 0 <= k < len(a) else sp.Integer(0)


def _coeff_of(L, a, j):
    """L(Σ a_k x^k)의 x^j 계수."""
    yv = sum(a[k] * x**k for k in range(len(a)))
    return sp.expand(L(yv)).coeff(x, j)


# ---------------------------------------------------------------- 거듭제곱급수 가족
def _families():
    """(가족, L, ODE TeX, 대괄호 bracket(n, a), bracket TeX, 재귀식 rec(n, a) → a_{n+2}, 재귀식 TeX, 오답 재귀식들, 시작 메모)"""
    out = []
    for c in [1, 4, 9, -1, -4, 2, 3, -2, -9, 16]:
        L = lambda g, c=c: sp.diff(g, x, 2) + c * g
        out.append(dict(fam="const", key=c, L=L, ode=f"{join_terms([(1, P2), (c, 'y')])} = 0",
                        br=lambda m, a, c=c: (m + 2) * (m + 1) * _get(a, m + 2) + c * _get(a, m),
                        br_tex=rf"(n + 2)(n + 1)a_{{n+2}} {'+' if c > 0 else '-'} {tex(abs(c)) if abs(c) != 1 else ''}a_n",
                        rec=lambda m, a, c=c: -c * _get(a, m) / ((m + 2) * (m + 1)),
                        rec_tex=rf"a_{{n+2}} = {'-' if c > 0 else ''}\frac{{{tex(abs(c))}}}{{(n + 2)(n + 1)}}a_n",
                        bad=[(lambda m, a, c=c: c * _get(a, m) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = {'' if c > 0 else '-'}\frac{{{tex(abs(c))}}}{{(n + 2)(n + 1)}}a_n", "sign"),
                             (lambda m, a, c=c: -c * _get(a, m) / (m + 2), rf"a_{{n+2}} = {'-' if c > 0 else ''}\frac{{{tex(abs(c))}}}{{n + 2}}a_n", "missing_factor"),
                             (lambda m, a, c=c: -c * _get(a, m + 1) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = {'-' if c > 0 else ''}\frac{{{tex(abs(c))}}}{{(n + 2)(n + 1)}}a_{{n+1}}", "algebra")],
                        bad_br=(lambda m, a, c=c: m * (m - 1) * _get(a, m + 2) + c * _get(a, m), rf"n(n - 1)a_{{n+2}} {'+' if c > 0 else '-'} {tex(abs(c)) if abs(c) != 1 else ''}a_n"),
                        start=r"\sum_{n=0}^{\infty}"))
    for c in [1, 2, -1, 3, -2, 4, -3, 6, -4, 5]:
        L = lambda g, c=c: sp.diff(g, x, 2) - c * x * g
        out.append(dict(fam="airy", key=c, L=L, ode=f"{join_terms([(1, P2), (-c, 'xy')])} = 0",
                        br=lambda m, a, c=c: (m + 2) * (m + 1) * _get(a, m + 2) - c * _get(a, m - 1),
                        br_tex=rf"(n + 2)(n + 1)a_{{n+2}} {'-' if c > 0 else '+'} {tex(abs(c)) if abs(c) != 1 else ''}a_{{n-1}}",
                        rec=lambda m, a, c=c: c * _get(a, m - 1) / ((m + 2) * (m + 1)),
                        rec_tex=rf"a_{{n+2}} = {'' if c > 0 else '-'}\frac{{{tex(abs(c))}}}{{(n + 2)(n + 1)}}a_{{n-1}}\ (a_2 = 0)",
                        bad=[(lambda m, a, c=c: c * _get(a, m) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = {'' if c > 0 else '-'}\frac{{{tex(abs(c))}}}{{(n + 2)(n + 1)}}a_n", "algebra"),
                             (lambda m, a, c=c: -c * _get(a, m - 1) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = {'-' if c > 0 else ''}\frac{{{tex(abs(c))}}}{{(n + 2)(n + 1)}}a_{{n-1}}\ (a_2 = 0)", "sign"),
                             (lambda m, a, c=c: c * _get(a, m - 1) / (m + 2), rf"a_{{n+2}} = {'' if c > 0 else '-'}\frac{{{tex(abs(c))}}}{{n + 2}}a_{{n-1}}\ (a_2 = 0)", "missing_factor")],
                        bad_br=(lambda m, a, c=c: (m + 2) * (m + 1) * _get(a, m + 2) - c * _get(a, m + 1), rf"(n + 2)(n + 1)a_{{n+2}} {'-' if c > 0 else '+'} {tex(abs(c)) if abs(c) != 1 else ''}a_{{n+1}}"),
                        start=r"2a_2 + \sum_{n=1}^{\infty}"))
    for lm in [1, 3, -1, -4, 5, 2, 7, -2, 9, -6]:
        L = lambda g, lm=lm: sp.diff(g, x, 2) - 2 * x * sp.diff(g, x) + lm * g
        num = 2 * n - lm
        out.append(dict(fam="herm", key=lm, L=L, ode=f"{join_terms([(1, P2), (-2, 'x' + P1), (lm, 'y')])} = 0",
                        br=lambda m, a, lm=lm: (m + 2) * (m + 1) * _get(a, m + 2) - (2 * m - lm) * _get(a, m),
                        br_tex=rf"(n + 2)(n + 1)a_{{n+2}} - ({tex(num)})a_n",
                        rec=lambda m, a, lm=lm: (2 * m - lm) * _get(a, m) / ((m + 2) * (m + 1)),
                        rec_tex=rf"a_{{n+2}} = \frac{{{tex(num)}}}{{(n + 2)(n + 1)}}a_n",
                        bad=[(lambda m, a, lm=lm: (2 * m + lm) * _get(a, m) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = \frac{{{tex(2 * n + lm)}}}{{(n + 2)(n + 1)}}a_n", "sign"),
                             (lambda m, a, lm=lm: (m - lm) * _get(a, m) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = \frac{{{tex(n - lm)}}}{{(n + 2)(n + 1)}}a_n", "missing_factor"),
                             (lambda m, a, lm=lm: -(2 * m - lm) * _get(a, m) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = \frac{{{tex(-num)}}}{{(n + 2)(n + 1)}}a_n", "sign")],
                        bad_br=(lambda m, a, lm=lm: (m + 2) * (m + 1) * _get(a, m + 2) - (2 * (m + 2) - lm) * _get(a, m), rf"(n + 2)(n + 1)a_{{n+2}} - ({tex(2 * (n + 2) - lm)})a_n"),
                        start=r"\sum_{n=0}^{\infty}"))
    for lm in [2, -2, 3, 5, 8, 1, 4, -6, 10, 7]:
        L = lambda g, lm=lm: (1 - x**2) * sp.diff(g, x, 2) - 2 * x * sp.diff(g, x) + lm * g
        num = n * (n + 1) - lm
        out.append(dict(fam="leg", key=lm, L=L, ode=rf"(1 - x^{{2}}){P2} - 2x{P1} {'+' if lm > 0 else '-'} {tex(abs(lm))}y = 0",
                        br=lambda m, a, lm=lm: (m + 2) * (m + 1) * _get(a, m + 2) - (m * (m + 1) - lm) * _get(a, m),
                        br_tex=rf"(n + 2)(n + 1)a_{{n+2}} - ({tex(sp.expand(num))})a_n",
                        rec=lambda m, a, lm=lm: (m * (m + 1) - lm) * _get(a, m) / ((m + 2) * (m + 1)),
                        rec_tex=rf"a_{{n+2}} = \frac{{{tex(sp.expand(num))}}}{{(n + 2)(n + 1)}}a_n",
                        bad=[(lambda m, a, lm=lm: (m * (m - 1) - lm) * _get(a, m) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = \frac{{{tex(sp.expand(n * (n - 1) - lm))}}}{{(n + 2)(n + 1)}}a_n", "missing_factor"),
                             (lambda m, a, lm=lm: (m * (m + 1) + lm) * _get(a, m) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = \frac{{{tex(sp.expand(n * (n + 1) + lm))}}}{{(n + 2)(n + 1)}}a_n", "sign"),
                             (lambda m, a, lm=lm: -(m * (m + 1) - lm) * _get(a, m) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = \frac{{{tex(sp.expand(lm - n * (n + 1)))}}}{{(n + 2)(n + 1)}}a_n", "sign")],
                        bad_br=(lambda m, a, lm=lm: (m + 2) * (m + 1) * _get(a, m + 2) - (m * (m - 1) - lm) * _get(a, m), rf"(n + 2)(n + 1)a_{{n+2}} - ({tex(sp.expand(n * (n - 1) - lm))})a_n"),
                        start=r"\sum_{n=0}^{\infty}"))
    for b, c in [(1, 1), (2, 1), (1, 2), (-1, 1), (2, -1), (1, -3), (-1, 2), (3, 1), (-2, 3), (1, 4), (2, 3)]:
        L = lambda g, b=b, c=c: sp.diff(g, x, 2) + b * x * sp.diff(g, x) + c * g
        num = -(b * n + c)
        out.append(dict(fam="damp", key=(b, c), L=L, ode=f"{join_terms([(1, P2), (b, 'x' + P1), (c, 'y')])} = 0",
                        br=lambda m, a, b=b, c=c: (m + 2) * (m + 1) * _get(a, m + 2) + (b * m + c) * _get(a, m),
                        br_tex=rf"(n + 2)(n + 1)a_{{n+2}} + ({tex(b * n + c)})a_n",
                        rec=lambda m, a, b=b, c=c: -(b * m + c) * _get(a, m) / ((m + 2) * (m + 1)),
                        rec_tex=rf"a_{{n+2}} = -\frac{{{tex(b * n + c)}}}{{(n + 2)(n + 1)}}a_n",
                        bad=[(lambda m, a, b=b, c=c: (b * m + c) * _get(a, m) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = \frac{{{tex(b * n + c)}}}{{(n + 2)(n + 1)}}a_n", "sign"),
                             (lambda m, a, b=b, c=c: -(b * (m + 2) + c) * _get(a, m) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = -\frac{{{tex(b * (n + 2) + c)}}}{{(n + 2)(n + 1)}}a_n", "algebra"),
                             (lambda m, a, b=b, c=c: -c * _get(a, m) / ((m + 2) * (m + 1)), rf"a_{{n+2}} = -\frac{{{tex(c)}}}{{(n + 2)(n + 1)}}a_n", "missing_factor")],
                        bad_br=(lambda m, a, b=b, c=c: (m + 2) * (m + 1) * _get(a, m + 2) + (b * (m + 2) + c) * _get(a, m), rf"(n + 2)(n + 1)a_{{n+2}} + ({tex(b * (n + 2) + c)})a_n"),
                        start=r"\sum_{n=0}^{\infty}"))
    return out


def _br_ok(L):
    """bracket(n, a)가 L(Σ a_k x^k)의 xⁿ 계수와 같은지 (n = 0..5)."""
    def ok(br, L=L):
        a = list(AS)
        return all(same(sp.expand(br(m, a)), _coeff_of(L, a, m)) for m in range(6))
    return ok


def _coeffs(rec, N=9):
    a = [A0, A1]
    for m in range(N - 1):
        a.append(sp.expand(rec(m, a)))
    return a


def _series_ok(L, upto=6):
    """계수 목록 a가 만드는 잘린 급수가 xʲ (j ≤ upto)까지 방정식을 만족하는지. a₀, a₁은 임의."""
    def ok(a, L=L, upto=upto):
        return len(a) > upto + 2 and all(same(_coeff_of(L, list(a), j), 0) for j in range(upto + 1))
    return ok


def _rec_ok(L):
    sok = _series_ok(L)
    return lambda rec, sok=sok: sok(_coeffs(rec))


WHY = {
    "rec_sign": r"$x^{n}$의 계수를 $0$으로 놓고 가장 높은 첨자의 계수에 대해 풀 때 부호가 바뀌었습니다. 잘린 급수를 넣어 보면 방정식을 만족하지 않습니다.",
    "rec_fac": r"$y^{\prime\prime}$에서 나온 계수는 $(n + 2)(n + 1)$입니다. 하나를 빠뜨렸습니다.",
    "rec_idx": r"$x^{n}$ 항끼리 모아야 합니다. 지수를 맞추지 않고 다른 첨자의 계수와 짝지었습니다.",
    "shift": r"$\sum n(n-1)a_nx^{n-2}$에서 $n \to n + 2$로 바꾸면 $\sum (n+2)(n+1)a_{n+2}x^{n}$입니다. 계수도 함께 바꿔야 합니다.",
    "deriv": r"$y^{\prime\prime} = \sum n(n - 1)a_nx^{n-2}$입니다. 지수는 두 번 미분하면 $2$ 줄어듭니다.",
    "coef": r"재귀식에 $n = 0, 1, 2, 3$을 차례로 넣어 계산한 값과 다릅니다.",
    "group": r"$a_0$에 붙는 항과 $a_1$에 붙는 항을 섞었습니다. 짝수·홀수 차수(또는 3칸 간격)로 따로 모입니다.",
}


# ================================================================ 원자
def _sum_tex(start, coef, shift, mult=1):
    """Σ_{n=start} coef(n)·a_{n+shift} xⁿ 의 TeX."""
    idx = "n" if shift == 0 else (f"n+{shift}" if shift > 0 else f"n-{-shift}")
    c = sp.factor(coef * mult)
    ct = "" if c == 1 else ("-" if c == -1 else (tex(c) if len(sp.Add.make_args(sp.expand(c))) == 1 and not c.is_Mul or c.is_number else _paren_prod(c)))
    return rf"\sum_{{n={start}}}^{{\infty}} {ct}a_{{{idx}}}x^{{n}}"


def _paren_prod(c):
    """(n + 2)(n + 1) 같은 곱을 괄호째로."""
    num, rest = c.as_coeff_Mul()
    facs = sp.Mul.make_args(rest)
    body = "".join(f"({tex(f)})" if f.is_Add else tex(f) for f in facs)
    return ("-" if num == -1 else ("" if num == 1 else tex(num))) + body


def _ff(m, d):
    out = sp.Integer(1)
    for j in range(d):
        out *= (m - j)
    return out


def _term_k(start_, coef_, shift_, k):
    """Σ_{n=start} coef(n)a_{n+shift}xⁿ 의 xᵏ 계수 (aⱼ는 기호 AS[j])."""
    if k < start_:
        return sp.Integer(0)
    c = sp.expand(coef_.subs(n, k))
    if k + shift_ < 0:
        return sp.Integer(0) if c == 0 else sp.Symbol("UNDEF")   # 없는 계수 a₋₁ 등을 쓰면 틀린 범위
    return c * AS[k + shift_]


def index_shift():
    """x^m · (d계 도함수의 급수)를 Σ (…)a_{n+s} xⁿ 꼴로."""
    out = []
    for d, mpow, c in itertools.product([0, 1, 2], [0, 1, 2, 3], [1, 2, -3]):
        p = mpow - d                       # xⁿ⁺ᵖ
        if p == 0:
            continue
        # 원래: Σ_{n=d} c·ff(n,d) a_n x^{n+p}  →  k = n + p:  Σ_{k=d+p} c·ff(k−p, d) a_{k−p} x^k
        start = d + p
        coef = c * _ff(n - p, d)
        shift = -p
        ok = lambda st, cf, sh, st0=start, cf0=coef, sh0=shift: all(same(_term_k(st, cf, sh, k), _term_k(st0, cf0, sh0, k)) for k in range(0, 9))
        src_coef = c * _ff(n, d)
        src = rf"{'x' if mpow == 1 else (f'x^{{{mpow}}}' if mpow else '')}\sum_{{n={d}}}^{{\infty}} {_ct(src_coef)}a_nx^{{{tex(n - d)}}}"
        wr = [(start, c * _ff(n, d), shift, "algebra"), (start + 1 if start < 3 else start - 1, coef, shift, "bounds"),
              (start, c * _ff(n + p, d), -shift, "sign"), (d, coef, shift, "bounds")]
        seen = {(start, sp.expand(coef), shift)}
        wrong = []
        for st, cf, sh, e in wr:
            key = (st, sp.expand(cf), sh)
            if key in seen:
                continue
            seen.add(key)
            wrong.append(opt(_sum_tex(st, cf, sh), lambda st=st, cf=cf, sh=sh, ok=ok: ok(st, cf, sh), e))
        out.append({"params": {"d": d, "m": mpow, "c": c}, "tier": 1 if d < 2 else 2,
                    "prompt": rf"{src}\ \text{{을}}\ x^{{n}}\ \text{{꼴로}}",
                    "answer": opt(_sum_tex(start, coef, shift), lambda st=start, cf=coef, sh=shift, ok=ok: ok(st, cf, sh)),
                    "wrong": wrong})
    return out


def _ct(c):
    c = sp.factor(c)
    if c == 1:
        return ""
    if c == -1:
        return "-"
    return _paren_prod(c) if c.is_Mul else tex(c)


def recurrence():
    out = []
    for F in _families():
        ok = _rec_ok(F["L"])
        out.append({"params": {"family": F["fam"], "key": str(F["key"])}, "tier": {"const": 1, "airy": 2, "herm": 2, "leg": 2, "damp": 2}[F["fam"]], "pace": "compute",
                    "prompt": rf"{F['ode']},\ y = \sum a_nx^n\ \text{{의 재귀식}}",
                    "answer": opt(F["rec_tex"], lambda rc=F["rec"], ok=ok: ok(rc)),
                    "wrong": [opt(tx, lambda rc=rc, ok=ok: ok(rc), e) for rc, tx, e in F["bad"]]})
    return out


# ---------------------------------------------------------------- 특이점 분류
def _sing_kind(Pp, Qq, Rr, x0):
    p, q = sp.cancel(Qq / Pp), sp.cancel(Rr / Pp)
    if sp.denom(p).subs(x, x0) != 0 and sp.denom(q).subs(x, x0) != 0:
        return "ord"
    xp, xq = sp.cancel((x - x0) * p), sp.cancel((x - x0) ** 2 * q)
    return "reg" if sp.denom(xp).subs(x, x0) != 0 and sp.denom(xq).subs(x, x0) != 0 else "irr"


KIND = {"reg": r"\text{정칙특이점}", "irr": r"\text{비정칙특이점}"}


def singular_points():
    out = []
    rng = random.Random(41)
    specs = []
    for e0, e1 in itertools.product([1, 2, 3], [0, 1, 2]):
        for qa, ra in itertools.product([1, 3, x, x + 1], [1, 2, x, -1]):
            specs.append((e0, e1, qa, ra))
    rng.shuffle(specs)
    seen = set()
    for e0, e1, qa, ra in specs:
        Pp = x**e0 * (x - 1) ** e1
        pts = [0] + ([1] if e1 else [])
        kinds = [_sing_kind(Pp, qa, ra, p0) for p0 in pts]
        if "ord" in kinds:
            continue
        key = (tuple(kinds), e0, e1)
        if key in seen and rng.random() < 0.7:
            continue
        seen.add(key)
        truth = list(zip(pts, kinds))
        ok = lambda lst, Pp=Pp, qa=qa, ra=ra: sorted(p0 for p0, _ in lst) == sorted(sp.roots(sp.Poly(Pp, x)).keys()) and all(_sing_kind(Pp, qa, ra, p0) == k for p0, k in lst)
        txt = lambda lst: r",\ ".join(f"x = {tex(p0)}\\ ({KIND[k]})" for p0, k in lst)
        flip = {"reg": "irr", "irr": "reg"}
        wr = [([(p0, flip[k]) for p0, k in truth], "theorem_condition")]
        if len(truth) == 2:
            wr += [([truth[0], (truth[1][0], flip[truth[1][1]])], "theorem_condition"), ([(truth[0][0], flip[truth[0][1]]), truth[1]], "theorem_condition"), (truth[:1], "missing_factor")]
        else:
            wr += [(truth + [(1, "reg")], "algebra"), (truth + [(-1, "irr")], "algebra"), ([(0, flip[truth[0][1]]), (1, "reg")], "algebra")]
        lhs = join_terms([(1, f"{_ptex(Pp)}{P2}")]) + " " + _term(qa, P1) + " " + _term(ra, "y")
        out.append({"params": {"e0": e0, "e1": e1, "q": str(qa), "r": str(ra)}, "tier": 2, "pace": "compute",
                    "prompt": rf"{lhs} = 0\ \text{{의 특이점과 종류}}",
                    "answer": opt(txt(truth), lambda l=truth, ok=ok: ok(l)),
                    "wrong": [opt(txt(l), lambda l=l, ok=ok: ok(l), e) for l, e in wr]})
        if len(out) >= 30:
            break
    return out


def _ptex(Pp):
    return tex(sp.factor(Pp)) if Pp != 1 else ""


def _term(c, body):
    c = sp.sympify(c)
    if c.is_number:
        return ("+ " if c > 0 else "- ") + (tex(abs(c)) if abs(c) != 1 else "") + body
    if c.is_Add:
        return rf"+ \left({tex(c)}\right){body}"
    num, rest = c.as_coeff_Mul()
    return ("+ " if num > 0 else "- ") + (tex(abs(num)) if abs(num) != 1 else "") + tex(rest) + body


# ---------------------------------------------------------------- 결정방정식
r_ = sp.Symbol("r")


def _frob_specs():
    """(가족, D, p0, q0) — 결정방정식의 근 (r₁, r₂)에서 p0 = 1 − (r₁ + r₂), q0 = r₁r₂.
    방정식은 D·[x²y'' + x(p0 + …)y' + (q0 + …)y] = 0 으로 정수 계수가 되게 쓴다."""
    R = sp.Rational
    pairs = {"nonint": [(R(1, 2), -1), (1, R(-1, 2)), (R(1, 3), 0), (R(1, 2), 0), (R(3, 2), 0), (R(1, 4), R(-1, 2)), (R(1, 2), R(-1, 3)), (R(2, 3), 0), (1, R(1, 3))],
             "equal": [(0, 0), (1, 1), (-1, -1), (R(1, 2), R(1, 2)), (2, 2), (R(-1, 2), R(-1, 2))],
             "intdiff": [(1, 0), (2, 0), (1, -1), (2, -1), (3, 0), (1, -2), (R(1, 2), R(-1, 2)), (R(3, 2), R(-1, 2))]}
    out = []
    for fam, lst in pairs.items():
        for r1, r2 in lst:
            P0, Q0 = 1 - (sp.nsimplify(r1) + sp.nsimplify(r2)), sp.nsimplify(r1) * sp.nsimplify(r2)
            D = sp.ilcm(sp.nsimplify(P0).q, sp.nsimplify(Q0).q)
            out.append((fam, D, P0, Q0))
    return out


def _indicial(P0, Q0):
    return sp.expand(r_ * (r_ - 1) + P0 * r_ + Q0)


def _roots_desc(P0, Q0):
    rs = sp.roots(sp.Poly(_indicial(P0, Q0), r_))
    return sorted([k for k, m in rs.items() for _ in range(m)], reverse=True)


def _frob_ode_tex(D, P0, p1, Q0, q1, q2):
    """D·x²y'' + D·x(p0 + p1x)y' + D(q0 + q1x + q2x²)y = 0 을 정수 계수로."""
    a2 = D
    bx, bx2 = D * P0, D * p1                 # x y', x² y'
    c0, c1, c2 = D * Q0, D * q1, D * q2      # y, xy, x²y
    parts = [(a2, f"x^{{2}}{P2}"), (bx, f"x{P1}"), (bx2, f"x^{{2}}{P1}")]
    y_coef = join_terms([(c2, "x^{2}"), (c1, "x"), (c0, "")])
    s_ = join_terms(parts)
    if y_coef != "0":
        if len([v for v in (c0, c1, c2) if v]) == 1:
            s_ += " " + _term(c2 * x**2 + c1 * x + c0, "y")
        else:
            s_ += rf" + \left({y_coef}\right)y"
    return s_ + " = 0"


def indicial_roots():
    out = []
    for fam, D, P0, Q0 in _frob_specs():
        for q1 in [1, -1]:
            rts = _roots_desc(P0, Q0)
            ok = lambda vs, P0=P0, Q0=Q0: sorted(vs, reverse=True) == _roots_desc(P0, Q0)
            txt = lambda vs: "r = " + (rf"{tex(vs[0])}\ (\text{{중근}})" if vs[0] == vs[1] else r",\ ".join(tex(v) for v in vs))
            def _rr(poly):
                vs = [k for k, m in sp.roots(sp.Poly(poly, r_)).items() for _ in range(m)]
                return sorted(vs, reverse=True) if len(vs) == 2 and all(v.is_real for v in vs) else []
            cand = [([-v for v in rts], "sign"), (_rr(r_**2 + P0 * r_ + Q0), "missing_factor"),
                    (_rr(r_ * (r_ - 1) + D * P0 * r_ + D * Q0), "missing_factor"), (_rr(r_ * (r_ + 1) + P0 * r_ + Q0), "sign"),
                    (_rr(r_ * (r_ - 1) + P0 * r_ - Q0), "sign"), (_rr(r_ * (r_ - 1) + Q0), "missing_factor")]
            uniq = []
            for c_, e_ in cand:
                if c_ and c_ != rts and all(c_ != u for u, _ in uniq):
                    uniq.append((c_, e_))
            cand = uniq
            if any(len(tex(v)) > 18 for c, _ in cand for v in c):
                continue
            out.append({"params": {"D": D, "P0": str(P0), "Q0": str(Q0), "q1": q1, "family": fam}, "tier": 2, "pace": "compute",
                        "prompt": rf"{_frob_ode_tex(D, P0, 0, Q0, q1, 0)}\ \text{{의}}\ x = 0\ \text{{에서 결정방정식의 근}}",
                        "answer": opt(txt(rts), lambda vs=rts, ok=ok: ok(vs)),
                        "wrong": [opt(txt(c), lambda vs=c, ok=ok: ok(vs), e) for c, e in cand]})
    return out


# ---------------------------------------------------------------- 수렴 반경
def radius():
    out = []
    for (a, b), x0 in itertools.product([(0, 1), (0, 4), (0, 9), (1, 1), (-1, 4), (2, 1), (0, 16)], [0, 1, 2, -1, 3]):
        Pp = (x - a) ** 2 + b                 # 근 a ± √b i
        zs = [a + sp.sqrt(b) * sp.I, a - sp.sqrt(b) * sp.I]
        R = sp.sqrt((x0 - a) ** 2 + b)
        ok = lambda v, x0=x0, zs=zs: same(v, min([sp.sqrt(sp.re(z - x0) ** 2 + sp.im(z - x0) ** 2) for z in zs], key=lambda e: float(e)))
        cand = [(sp.Abs(x0 - a), "conjugate"), (sp.sqrt(b), "theorem_condition"), (sp.Integer(b), "algebra"), (sp.oo, "theorem_condition"), (sp.Abs(x0 - a) + sp.sqrt(b), "algebra")]
        seen = {sp.nsimplify(R)}
        wr = []
        for c, e in cand:
            c = sp.nsimplify(c)
            if c in seen:
                continue
            seen.add(c)
            wr.append(opt(r"\infty" if c == sp.oo else tex(c), (lambda: False) if c == sp.oo else (lambda v=c, ok=ok: ok(v)), e))
        out.append({"params": {"a": a, "b": b, "x0": x0}, "tier": 1 if x0 == a else 2, "pace": "compute",
                    "prompt": rf"({tex(sp.expand(Pp))}){P2} + xy = 0,\ x_0 = {x0}\ \text{{에서 거듭제곱급수 해의 수렴 반경 (보장되는 최소)}}",
                    "answer": opt(tex(R), lambda v=R, ok=ok: ok(v)),
                    "wrong": wr[:4]})
    return out


# ---------------------------------------------------------------- 둘째 해의 꼴
FORMS = {"nonint": r"y_2 = x^{r_2}\sum b_nx^n", "equal": r"y_2 = y_1\ln x + x^{r_1}\sum b_nx^n",
         "intdiff": r"y_2 = Cy_1\ln x + x^{r_2}\sum b_nx^n\ (C\text{는 0일 수도})", "xy1": r"y_2 = x\,y_1"}


def _case_of(r1, r2):
    d = r1 - r2
    return "equal" if d == 0 else ("intdiff" if d.is_integer else "nonint")


def second_form():
    out = []
    pairs = [(sp.Rational(1, 2), -1), (1, sp.Rational(-1, 2)), (sp.Rational(1, 3), 0), (sp.Rational(3, 2), sp.Rational(1, 3)), (sp.Rational(2, 3), sp.Rational(-1, 3)),
             (0, 0), (1, 1), (sp.Rational(1, 2), sp.Rational(1, 2)), (-1, -1), (2, 2), (sp.Rational(-1, 3), sp.Rational(-1, 3)),
             (1, 0), (2, 0), (1, -1), (3, 1), (sp.Rational(1, 2), sp.Rational(-1, 2)), (sp.Rational(3, 2), sp.Rational(-1, 2)), (2, -2)]
    for r1, r2 in pairs:
        r1, r2 = sp.nsimplify(r1), sp.nsimplify(r2)
        cs = _case_of(r1, r2)
        ok = lambda k, cs=cs: k == cs
        out.append({"params": {"r1": str(r1), "r2": str(r2), "family": cs}, "tier": 2,
                    "prompt": rf"\text{{결정방정식의 근}}\ r_1 = {tex(r1)},\ r_2 = {tex(r2)}\ \text{{일 때 둘째 해의 꼴}}",
                    "answer": opt(FORMS[cs], lambda k=cs, ok=ok: ok(k)),
                    "wrong": [opt(FORMS[k], lambda k=k, ok=ok: ok(k), "theorem_condition") for k in FORMS if k != cs]})
    return out


# ---------------------------------------------------------------- 테일러 계수
yy, pp_, qq_ = sp.symbols("Y P Q")   # y, y', y'' 자리


def _taylor_truth(order, f, ics, N=5):
    """y^{(order)} = f(x, y, y') 의 해의 테일러 계수 c_0..c_N (계수를 미지수로 두고 맞춘다)."""
    cs = [sp.Integer(v) for v in ics] + list(sp.symbols(f"t{order}:{N + 1}"))
    Y = sum(sp.Rational(1, sp.factorial(k)) * cs[k] * x**k for k in range(N + 1))
    lhs = sp.diff(Y, x, order)
    rhs = f.subs({yy: Y, pp_: sp.diff(Y, x)})
    eqs = [sp.expand(lhs - rhs).coeff(x, j) for j in range(N + 1 - order)]
    sol = sp.solve(eqs, cs[len(ics):], dict=True)[0]
    return [sp.nsimplify(c.subs(sol)) for c in cs]   # cs[k] = y^{(k)}(0)


def _taylor_cases():
    out = []
    for a, b, y0, v0 in [(1, 0, 1, 0), (1, 1, 0, 1), (-1, 0, 1, 1), (2, 1, 1, 0), (2, 0, 0, 1), (-1, 1, 2, 0), (1, 1, 2, 1), (-1, 1, 0, 0), (2, 1, 2, 1), (1, 0, 2, 1), (-1, 0, 2, 0)]:
        out.append(("lin", 2, -a * yy + b * x, (y0, v0), rf"{P2} = {join_terms([(-a, 'y'), (b, 'x')])}"))
    for y0, v0 in [(1, 0), (0, 1), (1, 1), (2, -1), (1, 2)]:
        out.append(("var", 2, x * pp_ + yy, (y0, v0), rf"{P2} = x{P1} + y"))
        out.append(("var", 2, -x * yy, (y0, v0), rf"{P2} = -xy"))
        out.append(("var", 2, x**2 * yy - pp_, (y0, v0), rf"{P2} = x^{{2}}y - {P1}"))
    for y0 in [1, 0, 2, -1]:
        out.append(("nl1", 1, x**2 + yy**2, (y0,), rf"{P1} = x^{{2}} + y^{{2}}"))
        out.append(("nl1", 1, x + yy**2, (y0,), rf"{P1} = x + y^{{2}}"))
        out.append(("nl1", 1, x * yy + 1, (y0,), rf"{P1} = xy + 1"))
    for y0, v0 in [(1, 0), (1, 1), (2, 0), (0, 1), (1, -1), (2, 1)]:
        out.append(("nl2", 2, -yy**2, (y0, v0), rf"{P2} = -y^{{2}}"))
        out.append(("nl2", 2, yy * pp_, (y0, v0), rf"{P2} = y{P1}"))
        out.append(("nl2", 2, pp_**2 - yy, (y0, v0), rf"{P2} = ({P1})^{{2}} - y"))
    return out


def _ic_tex(ics):
    names = ["y", P1, P2]
    return r",\ ".join(f"{names[k]}(0) = {tex(v)}" for k, v in enumerate(ics))


def taylor_coef():
    out = []
    for fam, order, f, ics, ode in _taylor_cases():
        c = _taylor_truth(order, f, ics)
        k = 3
        val = c[k] / sp.factorial(k)
        if val == 0:
            continue
        ok = lambda v, val=val: same(v, val)
        cand = [(c[k], "missing_factor"), (-val, "sign"), (c[k] / k, "missing_factor"), (val + sp.Rational(1, 6), "algebra"), (c[2] / 2, "wrong_pair")]
        seen = {val}
        wr = []
        for v, e in cand:
            v = sp.nsimplify(v)
            if v in seen:
                continue
            seen.add(v)
            wr.append(opt(tex(v), lambda v=v, ok=ok: ok(v), e))
        out.append({"params": {"family": fam, "ode": ode, "ics": [str(v) for v in ics]}, "tier": 1 if fam == "lin" else 2, "pace": "compute",
                    "prompt": rf"{ode},\ {_ic_tex(ics)}\ \text{{의 해를}}\ x = 0\ \text{{에서 전개할 때}}\ x^{{3}}\ \text{{의 계수}}",
                    "answer": opt(tex(val), lambda v=val, ok=ok: ok(v)),
                    "wrong": wr[:4]})
    return out


# ---------------------------------------------------------------- 방정식 이름
NAMES = {"legendre": r"\text{Legendre 방정식}", "bessel": r"\text{Bessel 방정식}", "hermite": r"\text{Hermite 방정식}",
         "airy": r"\text{Airy 방정식}", "laguerre": r"\text{Laguerre 방정식}", "cheb": r"\text{Chebyshev 방정식}"}


def named_equation():
    out = []
    forms = []
    for k in [1, 2, 3, 4]:
        forms.append(("legendre", rf"(1 - x^{{2}}){P2} - 2x{P1} + {k * (k + 1)}y = 0"))
        forms.append(("hermite", rf"{P2} - 2x{P1} + {2 * k}y = 0"))
        forms.append(("laguerre", rf"x{P2} + (1 - x){P1} + {k}y = 0"))
        forms.append(("cheb", rf"(1 - x^{{2}}){P2} - x{P1} + {k * k}y = 0"))
    for nu in ["0", r"\frac{1}{2}", "1", "2", "3"]:
        forms.append(("bessel", rf"x^{{2}}{P2} + x{P1} + (x^{{2}} - {nu}^{{2}})y = 0".replace("(x^{2} - 0^{2})", "x^{2}")))
    forms.append(("airy", rf"{P2} - xy = 0"))
    forms.append(("airy", rf"{P2} = xy"))
    near = {"legendre": ["cheb", "hermite", "bessel"], "cheb": ["legendre", "hermite", "laguerre"], "hermite": ["legendre", "laguerre", "airy"],
            "laguerre": ["bessel", "hermite", "legendre"], "bessel": ["laguerre", "legendre", "cheb"], "airy": ["hermite", "bessel", "laguerre"]}
    for nm, tx in forms:
        ok = lambda k, nm=nm: k == nm
        out.append({"params": {"family": nm}, "tier": 1,
                    "prompt": rf"{tx}\ \text{{는 어떤 방정식}}",
                    "answer": opt(NAMES[nm], lambda k=nm, ok=ok: ok(k)),
                    "wrong": [opt(NAMES[k], lambda k=k, ok=ok: ok(k), "wrong_pair") for k in near[nm]]})
    return out


# ================================================================ 풀이 뼈대
WHY.update({
    "sub": r"$y^{\prime\prime}$의 급수는 $\sum n(n-1)a_nx^{n-2}$입니다. 계수를 $n(n+1)$로 쓰면 미분한 결과가 아닙니다.",
    "trunc": r"$a_0$에 붙는 급수와 $a_1$에 붙는 급수를 바꿔 묶었습니다. 차수가 $0, 2, 4, \dots$인 항이 $a_0$ 쪽입니다.",
    "y2": r"방정식에 $x = 0$과 초기값을 그대로 넣으면 이 도함수 값이 나옵니다. 대입이 틀렸습니다.",
    "chain": r"방정식을 $x$로 미분할 때 $y$와 $y^{\prime}$도 $x$의 함수라 연쇄법칙 항($y^{\prime}$, $y^{\prime\prime}$이 붙은 항)이 생깁니다.",
    "fact": r"$x^{k}$의 계수는 $y^{(k)}(0)/k!$입니다. $k!$로 나누지 않았습니다.",
    "p0q0": r"$p_0 = \lim_{x\to 0} xp(x)$, $q_0 = \lim_{x\to 0} x^2q(x)$입니다. $x^2y^{\prime\prime}$의 계수로 먼저 나눠야 합니다.",
    "ind": r"결정방정식은 $r(r - 1) + p_0r + q_0 = 0$입니다. $r(r-1)$ 대신 $r^2$을 썼습니다.",
    "frec": r"$x^{n+r}$의 계수를 모으면 $F(n + r)a_n$과 앞 계수들의 항이 나옵니다. $F(n + r)$ 대신 $F(n)$을 썼습니다.",
    "froot": r"첫 해는 큰 근 $r_1$으로 만듭니다. 작은 근으로는 정수 차이일 때 재귀식이 막힐 수 있습니다.",
    "pterm": r"재귀식은 $n$이 방정식의 매개변수와 맞을 때 분자가 $0$이 되어 그 뒤 계수가 모두 $0$입니다. 끊기는 쪽은 그 짝수(또는 홀수) 계열입니다.",
    "norm": r"표준 정규화와 맞지 않습니다. $P_n(1) = 1$, $T_n(1) = 1$, $L_n(0) = 1$이고 $H_n$은 최고차 계수 $2^n$, $He_n$은 최고차 계수 $1$로 맞춥니다.",
})


def _series_tex(a, upto=5):
    """a₀(…) + a₁(…) 꼴."""
    g0 = sum(sp.expand(a[k]).coeff(A0) * x**k for k in range(upto + 1))
    g1 = sum(sp.expand(a[k]).coeff(A1) * x**k for k in range(upto + 1))
    return rf"y = a_0\left({_ptx(g0)} + \cdots\right) + a_1\left({_ptx(g1)} + \cdots\right)"


def _ptx(g):
    P = sp.Poly(sp.expand(g), x)
    parts = []
    for (k,), c in sorted(P.terms(), key=lambda q: q[0][0]):
        parts.append((c, "" if k == 0 else ("x" if k == 1 else f"x^{{{k}}}")))
    return join_terms(parts)


def power_solve():
    """거듭제곱급수 해: 대입 → 지수 맞추기 → 재귀식 → 계수 → 급수.
    가족: 상수계수 · Airy형(3칸 재귀) · Hermite형 · Legendre형 · y'' + bxy' + cy."""
    out = []
    for F in _families():
        L = F["L"]
        a = _coeffs(F["rec"])
        if all(sp.expand(a[k]) == 0 for k in range(2, 6)):
            continue
        sok = _series_ok(L)
        bok = _br_ok(L)
        rok = _rec_ok(L)
        ctx = lambda a_: r",\ ".join(f"a_{k} = {tex(sp.expand(a_[k]))}" for k in range(2, 6))
        ok_c = lambda a_, truth=a: all(same(sp.expand(a_[k]), sp.expand(truth[k])) for k in range(2, 6))
        idx_n = 2 if F["fam"] != "airy" else 2
        steps = [
            step(r"y = \sum_{n=0}^{\infty} a_nx^n,\ y^{\prime\prime} = \sum_{n=2}^{\infty} n(n - 1)a_nx^{n-2}", lambda: same(sp.diff(sum(AS[k] * x**k for k in range(8)), x, 2), sum(k * (k - 1) * AS[k] * x**(k - 2) for k in range(2, 8)))),
            step(rf"{F['start']}\left[{F['br_tex']}\right]x^n = 0", lambda br=F["br"], ok=bok: ok(br)),
            step(F["rec_tex"], lambda rc=F["rec"], ok=rok: ok(rc)),
            step(ctx(a), lambda a_=a, ok=ok_c: ok(a_)),
            step(_series_tex(a), lambda a_=a, ok=sok: ok(a_)),
        ]
        badb, badbtx = F["bad_br"]
        decoys = [
            step(r"y = \sum_{n=0}^{\infty} a_nx^n,\ y^{\prime\prime} = \sum_{n=2}^{\infty} n(n + 1)a_nx^{n-2}", lambda: same(sp.diff(sum(AS[k] * x**k for k in range(8)), x, 2), sum(k * (k + 1) * AS[k] * x**(k - 2) for k in range(2, 8)))) | {"pos": 0, "error": "algebra", "why": WHY["sub"]},
            step(rf"{F['start']}\left[{badbtx}\right]x^n = 0", lambda br=badb, ok=bok: ok(br)) | {"pos": 1, "error": "algebra", "why": WHY["shift"] if F["fam"] != "airy" else WHY["rec_idx"]},
        ]
        for rc, tx, e in F["bad"][:2]:
            decoys.append(step(tx, lambda rc=rc, ok=rok: ok(rc)) | {"pos": 2, "error": e, "why": WHY["rec_sign"] if e == "sign" else (WHY["rec_fac"] if e == "missing_factor" else WHY["rec_idx"])})
        ab = list(a)
        k_ = next(k for k in range(2, 6) if sp.expand(a[k]) != 0)
        ab[k_] = -ab[k_]
        decoys.append(step(ctx(ab), lambda a_=ab, ok=ok_c: ok(a_)) | {"pos": 3, "error": "sign", "why": WHY["coef"]})
        wa = _coeffs(F["bad"][0][0])
        if _series_tex(wa) != _series_tex(a):
            decoys.append(step(_series_tex(wa), lambda a_=wa, ok=sok: ok(a_)) | {"pos": 4, "error": F["bad"][0][2], "why": WHY["coef"]})
        out.append({"params": {"family": F["fam"], "key": str(F["key"])}, "tier": {"const": 1, "damp": 2, "herm": 2, "leg": 3, "airy": 3}[F["fam"]],
                    "problem": rf"{F['ode']}\ \text{{를}}\ x = 0\ \text{{근처 거듭제곱급수로 풀기}}",
                    "steps": steps, "decoys": decoys,
                    "verify": lambda a_=a, ok=sok: None if ok(a_) else "급수가 방정식을 만족하지 않음"})
    return out


# ---------------------------------------------------------------- 초기값 문제의 테일러 급수
def _dtex(e):
    """Y, P, Q(= y, y', y'')를 화면 기호로. x가 앞에 오도록 x 뒤에 정렬되는 이름으로 잠시 바꾼다."""
    zy, zp, zq = sp.symbols("zy zp zq")
    out = tex(sp.sympify(e).subs({yy: zy, pp_: zp, sp.Symbol("Q"): zq}))
    out = out.replace("zp^{", "(" + P1 + ")^{").replace("zq^{", "(" + P2 + ")^{")
    return out.replace("zp", P1).replace("zq", P2).replace("zy", "y")


def taylor_ivp():
    """y^{(k)} = f 에서 초기값으로 y^{(k)}(0), 미분해서 다음 도함수 값, 급수.
    가족: 선형 상수계수(강제항) · 변수계수 · 1계 비선형 · 2계 비선형."""
    out = []
    for fam, order, f, ics, ode in _taylor_cases():
        c = _taylor_truth(order, f, ics)          # c[k] = y^{(k)}(0)
        # 다음 도함수: d/dx f(x, y, y') = f_x + f_y y' + f_P y''  (y''은 2계이면 f 자체)
        Qs = sp.Symbol("Q")
        df = sp.diff(f, x) + sp.diff(f, yy) * pp_ + sp.diff(f, pp_) * Qs
        if order == 1:
            df = df.subs(pp_, f)          # 1계: y' = f
            nxt = r"y^{\prime\prime}"
            sub0 = {x: 0, yy: c[0]}
        else:
            df = df.subs(Qs, f)
            nxt = r"y^{\prime\prime\prime}"
            sub0 = {x: 0, yy: c[0], pp_: c[1]}
        dfe = sp.expand(df)
        v_o = c[order]
        v_n = c[order + 1]
        N = order + 1
        poly = sum(c[k] / sp.factorial(k) * x**k for k in range(N + 1))
        if all(c[k] == 0 for k in range(order, N + 1)):
            continue
        bad_df = sp.expand(sp.diff(f, x))        # 연쇄법칙 빠뜨림
        if same(bad_df, dfe):
            continue
        ok_poly = lambda g, c=c, N=N: all(same(sp.expand(g).coeff(x, k), c[k] / sp.factorial(k)) for k in range(N + 1))
        named = {1: r"y^{\prime}", 2: r"y^{\prime\prime}"}[order]
        truth_df = lambda e, f=f, order=order: same(sp.expand(e), _total_d(f, order))
        steps = [
            step(rf"{named}(0) = {tex(v_o)}", lambda v=v_o, c=c, order=order: same(v, c[order])),
            step(rf"{nxt} = {_dtex(dfe)}", lambda e=dfe, ok=truth_df: ok(e)),
            step(rf"{nxt}(0) = {tex(v_n)}", lambda v=v_n, c=c, N=N: same(v, c[N])),
            step(rf"y \approx {_ptx(poly)}", lambda g=poly, ok=ok_poly: ok(g)),
        ]
        poly_nf = sum(c[k] * x**k for k in range(N + 1))
        decoys = [
            step(rf"{nxt} = {_dtex(bad_df)}", lambda e=bad_df, ok=truth_df: ok(e)) | {"pos": 1, "error": "missing_factor", "why": WHY["chain"]},
            step(rf"y \approx {_ptx(poly_nf)}", lambda g=poly_nf, ok=ok_poly: ok(g)) | {"pos": 3, "error": "missing_factor", "why": WHY["fact"]} if not same(poly_nf, poly) else None,
            step(rf"{named}(0) = {tex(-v_o)}", lambda v=-v_o, c=c, order=order: same(v, c[order])) | {"pos": 0, "error": "sign", "why": WHY["y2"]} if v_o != 0 else
            step(rf"{named}(0) = 1", lambda v=1, c=c, order=order: same(v, c[order])) | {"pos": 0, "error": "algebra", "why": WHY["y2"]},
            step(rf"{nxt}(0) = {tex(v_n + 1)}", lambda v=v_n + 1, c=c, N=N: same(v, c[N])) | {"pos": 2, "error": "algebra", "why": WHY["coef"].replace("재귀식에 $n = 0, 1, 2, 3$을 차례로 넣어 계산한", "도함수 식에 $x = 0$과 초기값을 넣은")},
        ]
        out.append({"params": {"family": fam, "ode": ode, "ics": [str(v) for v in ics]}, "tier": {"lin": 1, "var": 2, "nl1": 2, "nl2": 3}[fam],
                    "problem": rf"{ode},\ {_ic_tex(ics)}\ \text{{의 해를}}\ x^{{{N}}}\ \text{{항까지 테일러 급수로}}",
                    "steps": steps, "decoys": [d for d in decoys if d]})
    return out


def _total_d(f, order):
    """해를 따라 d/dx f(x, y, y')를 x, Y, P로 (2계이면 y'' = f를 넣는다)."""
    Y_f = sp.Function("Yf")(x)
    if order == 1:
        e = f.subs(yy, Y_f)
        d = sp.diff(e, x).subs(sp.Derivative(Y_f, x), f.subs(yy, Y_f))
        return sp.expand(d.subs(Y_f, yy))
    e = f.subs({pp_: sp.diff(Y_f, x)}).subs(yy, Y_f)
    d = sp.diff(e, x)
    d = d.subs(sp.Derivative(Y_f, (x, 2)), f.subs({pp_: sp.diff(Y_f, x)}).subs(yy, Y_f))
    d = d.subs(sp.Derivative(Y_f, x), pp_).subs(Y_f, yy)
    return sp.expand(d)


# ---------------------------------------------------------------- Frobenius
def _frob_coeffs(P0, p1, Q0, q1, q2, r0, N=5):
    F = lambda s_: s_ * (s_ - 1) + P0 * s_ + Q0
    a = [sp.Integer(1)]
    for m in range(1, N + 1):
        num = -((p1 * (m - 1 + r0) + q1) * a[m - 1] + (q2 * a[m - 2] if m >= 2 else 0))
        den = F(m + r0)
        if den == 0:
            return None
        a.append(sp.nsimplify(num / den))
    return a


def _frob_L(P0, p1, Q0, q1, q2):
    return lambda g: sp.expand(x**2 * sp.diff(g, x, 2) + x * (P0 + p1 * x) * sp.diff(g, x) + (Q0 + q1 * x + q2 * x**2) * g)


def _frob_ok(L, r0, N):
    """x^{r0}·(Σ a_k x^k)를 넣었을 때 x^{r0+j} (j ≤ N) 계수가 0인지."""
    def ok(a, L=L, r0=r0, N=N):
        if a is None or len(a) < N + 1:
            return False
        z = sp.Symbol("z", positive=True)
        g = z**r0 * sum(a[k] * z**k for k in range(N + 1))
        R = sp.expand(sp.powsimp(sp.expand(L(g.subs(z, x)).subs(x, z) / z**r0), force=True))
        return all(same(sp.expand(R).coeff(z, j), 0) for j in range(N + 1))
    return ok


def frobenius():
    """Frobenius: p₀, q₀ → 결정방정식 → 근 → 재귀식 → 첫 해.
    가족: 근의 차가 정수 아님 · 중근 · 정수 차이 · x² 항이 있는 Bessel형(2칸 재귀)."""
    out = []
    specs = [(fam, D, P0, Q0) for fam, D, P0, Q0 in _frob_specs()]
    rng = random.Random(47)
    for fam, D, P0, Q0 in specs:
        for p1, q1, q2 in [(0, 1, 0), (0, -1, 0), (1, 0, 0), (0, 2, 0)] + ([(0, 0, 1), (0, 0, -1)] if fam != "nonint" else []):
            r1, r2 = _roots_desc(P0, Q0)
            a = _frob_coeffs(P0, p1, Q0, q1, q2, r1)
            if a is None or all(v == 0 for v in a[1:]) or any(sp.nsimplify(v).q > 400 for v in a[:4]):
                continue
            ffam = "bessel" if q2 else fam
            L = _frob_L(P0, p1, Q0, q1, q2)
            N = 3
            ok = _frob_ok(L, r1, N)
            Ftx = lambda s_: tex(sp.expand(s_ * (s_ - 1) + P0 * s_ + Q0))
            m_ = sp.Symbol("n")
            Fn = sp.factor(sp.expand((m_ + r1) * (m_ + r1 - 1) + P0 * (m_ + r1) + Q0))
            num1 = sp.expand(-(p1 * (m_ - 1 + r1) + q1))
            rec_tex = (rf"a_n = {_frac(num1, Fn)}a_{{n-1}}" if not q2 else rf"a_n = {_frac(-q2, Fn)}a_{{n-2}}\ (a_1 = 0)")
            rec_ok = lambda rc, ok=ok: ok(rc)
            def mk(numf, denf, two=False):
                b = [sp.Integer(1)]
                for k in range(1, N + 1):
                    den = denf(k)
                    if den == 0:
                        return None
                    if two:
                        b.append(sp.nsimplify(numf(k) * (b[k - 2] if k >= 2 else 0) / den))
                    else:
                        b.append(sp.nsimplify(numf(k) * b[k - 1] / den))
                return b
            if q2:
                truth_rec = mk(lambda k: -q2, lambda k: (k + r1) * (k + r1 - 1) + P0 * (k + r1) + Q0, True)
                bad_rec = mk(lambda k: -q2, lambda k: k * (k - 1) + P0 * k + Q0, True)
                bad_tx = rf"a_n = {_frac(-q2, m_ * (m_ - 1) + P0 * m_ + Q0)}a_{{n-2}}\ (a_1 = 0)"
            else:
                truth_rec = mk(lambda k: -(p1 * (k - 1 + r1) + q1), lambda k: (k + r1) * (k + r1 - 1) + P0 * (k + r1) + Q0)
                bad_rec = mk(lambda k: -(p1 * (k - 1 + r1) + q1), lambda k: k * (k - 1) + P0 * k + Q0)
                bad_tx = rf"a_n = {_frac(num1, m_ * (m_ - 1) + P0 * m_ + Q0)}a_{{n-1}}"
            if bad_rec is not None and ok(bad_rec):
                bad_rec = None
            yt = _y1(r1, sum(a[k] * x**k for k in range(N + 1)))
            ip = sp.Poly(_indicial(P0, Q0), r_)
            steps = [
                step(rf"p_0 = {tex(P0)},\ q_0 = {tex(Q0)}", lambda v=(P0, Q0), P0=P0, Q0=Q0: same(v, (P0, Q0))),
                step(" ".join(p_ for p_ in ["r(r - 1)", _signed(P0, 'r'), _signed(Q0, ''), "= 0"] if p_), lambda e=_indicial(P0, Q0), P0=P0, Q0=Q0: same(e, _indicial(P0, Q0))),
                step(rf"r_1 = {tex(r1)},\ r_2 = {tex(r2)}" if r1 != r2 else rf"r_1 = r_2 = {tex(r1)}", lambda v=(r1, r2), P0=P0, Q0=Q0: list(v) == _roots_desc(P0, Q0)),
                step(rec_tex, lambda rc=truth_rec, ok=ok: ok(rc)),
                step(yt, lambda a_=a, ok=ok: ok(a_)),
            ]
            decoys = [
                step(rf"p_0 = {tex(D * P0)},\ q_0 = {tex(D * Q0)}", lambda v=(D * P0, D * Q0), P0=P0, Q0=Q0: same(v, (P0, Q0))) | {"pos": 0, "error": "missing_factor", "why": WHY["p0q0"]} if D != 1 and (P0 or Q0) else None,
                step(" ".join(p_ for p_ in ["r^{2}", _signed(P0, 'r'), _signed(Q0, ''), "= 0"] if p_), lambda e=r_**2 + P0 * r_ + Q0, P0=P0, Q0=Q0: same(e, _indicial(P0, Q0))) | {"pos": 1, "error": "missing_factor", "why": WHY["ind"]},
                step(rf"r_1 = {tex(-r2)},\ r_2 = {tex(-r1)}" if r1 != r2 else rf"r_1 = r_2 = {tex(-r1)}", lambda v=(-r2, -r1), P0=P0, Q0=Q0: list(v) == _roots_desc(P0, Q0)) | {"pos": 2, "error": "sign", "why": r"결정방정식의 근의 부호가 틀렸습니다. 인수분해해 다시 확인하세요."} if r1 != 0 or r2 != 0 else None,
                step(bad_tx, lambda rc=bad_rec, ok=ok: ok(rc)) | {"pos": 3, "error": "algebra", "why": WHY["frec"]} if bad_rec is not None and bad_tx != rec_tex else None,
            ]
            if r1 != r2:
                a2 = _frob_coeffs(P0, p1, Q0, q1, q2, r2)
                if a2 is not None and any(v != 0 for v in a2[1:]):
                    yt2 = _y1(r1, sum(a2[k] * x**k for k in range(N + 1)))
                    if yt2 != yt:
                        decoys.append(step(yt2, lambda a_=a2, ok=ok: ok(a_)) | {"pos": 4, "error": "wrong_pair", "why": WHY["froot"]})
            ab = list(a)
            ab[1] = -ab[1] if ab[1] != 0 else ab[1]
            if ab[1] == 0:
                ab[2] = -ab[2]
            decoys.append(step(_y1(r1, sum(ab[k] * x**k for k in range(N + 1))), lambda a_=ab, ok=ok: ok(a_)) | {"pos": 4, "error": "sign", "why": WHY["coef"].replace("$n = 0, 1, 2, 3$", "$n = 1, 2, 3$")})
            out.append({"params": {"P0": str(P0), "Q0": str(Q0), "p1": p1, "q1": q1, "q2": q2, "D": D, "family": ffam},
                        "tier": {"nonint": 1, "equal": 1, "intdiff": 2, "bessel": 3}[ffam],
                        "problem": rf"{_frob_ode_tex(D, P0, p1, Q0, q1, q2)}\ \text{{의 Frobenius 해 (큰 근)}}",
                        "steps": steps, "decoys": [d for d in decoys if d],
                        "verify": lambda a_=a, ok=ok: None if ok(a_) else "급수가 방정식을 만족하지 않음"})
    return out


def _xr(r0):
    return "" if r0 == 0 else (f"x^{{{tex(r0)}}}" if r0 != 1 else "x")


def _frac(num, den):
    """num/den을 한 분수로 (분자·분모의 분수 정리)."""
    e = sp.factor(sp.cancel(sp.sympify(num) / sp.sympify(den)))
    out = tex(e)
    return out if out.startswith("-") or out.startswith(r"\frac") else out + r"\,"


def _y1(r0, poly):
    body = _ptx(poly) + r" + \cdots"
    return rf"y_1 = {body}" if r0 == 0 else rf"y_1 = {_xr(r0)}\left({body}\right)"


def _signed(c, body):
    c = sp.nsimplify(c)
    if c == 0:
        return ""
    s_ = "+" if c > 0 else "-"
    mag = tex(abs(c)) if (abs(c) != 1 or body == "") else ""
    return f"{s_} {mag}{body}"


# ---------------------------------------------------------------- 끊기는 급수 (다항식 해)
def poly_solution():
    """재귀식이 끊겨 다항식 해가 나오는 방정식. 가족: Legendre · Hermite · Chebyshev · Laguerre."""
    out = []
    kk = sp.Symbol("k")
    for fam, nn in itertools.product(["legendre", "hermite", "cheb", "laguerre", "he"], [2, 3, 4, 5, 6, 7]):
        if fam == "legendre":
            L = lambda g, nn=nn: (1 - x**2) * sp.diff(g, x, 2) - 2 * x * sp.diff(g, x) + nn * (nn + 1) * g
            ode = rf"(1 - x^{{2}}){P2} - 2x{P1} + {nn * (nn + 1)}y = 0"
            num = sp.expand(kk * (kk + 1) - nn * (nn + 1))
            target = sp.legendre(nn, x)
            norm = r"P_n(1) = 1"
            name = f"P_{{{nn}}}(x)"
        elif fam == "hermite":
            L = lambda g, nn=nn: sp.diff(g, x, 2) - 2 * x * sp.diff(g, x) + 2 * nn * g
            ode = rf"{P2} - 2x{P1} + {2 * nn}y = 0"
            num = sp.expand(2 * kk - 2 * nn)
            target = sp.hermite(nn, x)
            norm = rf"\text{{최고차 계수}}\ 2^{{{nn}}}"
            name = f"H_{{{nn}}}(x)"
        elif fam == "he":
            L = lambda g, nn=nn: sp.diff(g, x, 2) - x * sp.diff(g, x) + nn * g
            ode = rf"{P2} - x{P1} + {nn}y = 0"
            num = sp.expand(kk - nn)
            target = sp.expand(sp.hermite_prob(nn, x)) if hasattr(sp, "hermite_prob") else sp.expand(2 ** sp.Rational(-nn, 2) * sp.hermite(nn, x / sp.sqrt(2)))
            norm = r"\text{최고차 계수}\ 1"
            name = f"He_{{{nn}}}(x)"
        elif fam == "cheb":
            L = lambda g, nn=nn: (1 - x**2) * sp.diff(g, x, 2) - x * sp.diff(g, x) + nn**2 * g
            ode = rf"(1 - x^{{2}}){P2} - x{P1} + {nn * nn}y = 0"
            num = sp.expand(kk**2 - nn**2)
            target = sp.chebyshevt(nn, x)
            norm = r"T_n(1) = 1"
            name = f"T_{{{nn}}}(x)"
        else:
            L = lambda g, nn=nn: x * sp.diff(g, x, 2) + (1 - x) * sp.diff(g, x) + nn * g
            ode = rf"x{P2} + (1 - x){P1} + {nn}y = 0"
            target = sp.laguerre(nn, x)
            norm = r"L_n(0) = 1"
            name = f"L_{{{nn}}}(x)"
        if fam == "laguerre":
            rec_tex = rf"a_{{k+1}} = \frac{{k - {nn}}}{{(k + 1)^{{2}}}}a_k"
            coefs = [sp.Integer(1)]
            for k in range(nn):
                coefs.append(sp.Rational(k - nn, (k + 1) ** 2) * coefs[-1])
            raw = sum(coefs[k] * x**k for k in range(nn + 1))
            start = "a_0 = 1"
            rec_chk = lambda nn=nn: _laguerre_rec_ok(nn)
            bad_rec_tex = rf"a_{{k+1}} = \frac{{k + {nn}}}{{(k + 1)^{{2}}}}a_k"
            bad_rec_chk = lambda: False
            stop = rf"k = {nn}\ \text{{에서}}\ a_{{{nn + 1}}} = 0"
        else:
            rec_tex = rf"a_{{k+2}} = \frac{{{tex(num)}}}{{(k + 2)(k + 1)}}a_k"
            par = nn % 2
            coefs = [sp.Integer(0)] * (nn + 1)
            coefs[par] = sp.Integer(1)
            for k in range(par, nn - 1, 2):
                coefs[k + 2] = num.subs(kk, k) / ((k + 2) * (k + 1)) * coefs[k]
            raw = sum(coefs[k] * x**k for k in range(nn + 1))
            start = f"a_{par} = 1,\\ a_{1 - par} = 0"
            rec_chk = lambda L=L, num=num, kk=kk: _rec2_ok(L, num, kk)
            bad_rec_tex = rf"a_{{k+2}} = \frac{{{tex(-num)}}}{{(k + 2)(k + 1)}}a_k"
            bad_rec_chk = lambda L=L, num=-num, kk=kk: _rec2_ok(L, num, kk)
            stop = rf"k = {nn}\ \text{{에서 분자가}}\ 0 \Rightarrow a_{{{nn + 2}}} = a_{{{nn + 4}}} = \cdots = 0"
        scale = sp.nsimplify(sp.Poly(target, x).coeffs()[0] / sp.Poly(raw, x).coeffs()[0])
        final = sp.expand(scale * raw)
        ok_raw = lambda g, L=L, nn=nn: sp.degree(sp.expand(g), x) == nn and same(sp.expand(L(g)), 0)
        ok_fin = lambda g, target=target: same(sp.expand(g), sp.expand(target))
        steps = [
            step(rec_tex, rec_chk),
            step(stop, lambda: True),
            step(rf"{start}\ \Rightarrow\ y = {poly_tex(raw, x)}", lambda g=raw, ok=ok_raw: ok(g)),
            step(rf"{norm}\ \Rightarrow\ {name} = {poly_tex(final, x)}", lambda g=final, ok=ok_fin: ok(g)),
        ]
        decoys = [step(bad_rec_tex, bad_rec_chk) | {"pos": 0, "error": "sign", "why": WHY["rec_sign"]}]
        if final != raw:
            decoys.append(step(rf"{norm}\ \Rightarrow\ {name} = {poly_tex(raw, x)}", lambda g=raw, ok=ok_fin: ok(g)) | {"pos": 3, "error": "normalization", "why": WHY["norm"]})
        bad_f = sp.expand(-final) if fam not in ("hermite", "he") else sp.expand(final * 2 if fam == "he" else final / 2)
        decoys.append(step(rf"{norm}\ \Rightarrow\ {name} = {poly_tex(bad_f, x)}", lambda g=bad_f, ok=ok_fin: ok(g)) | {"pos": 3, "error": "normalization", "why": WHY["norm"]})
        if fam != "laguerre":
            wrong_par = 1 - nn % 2
            bc = [sp.Integer(0)] * (nn + 3)
            bc[wrong_par] = sp.Integer(1)
            for k in range(wrong_par, nn + 1, 2):
                bc[k + 2] = num.subs(kk, k) / ((k + 2) * (k + 1)) * bc[k]
            braw = sum(bc[k] * x**k for k in range(min(nn + 1, len(bc))))
            decoys.append(step(rf"a_{wrong_par} = 1,\ a_{1 - wrong_par} = 0\ \Rightarrow\ y = {poly_tex(braw, x)}", lambda g=braw, ok=ok_raw: ok(g)) | {"pos": 2, "error": "algebra", "why": WHY["pterm"]})
        else:
            bl = list(coefs)
            bl[1] = -bl[1]
            braw = sum(bl[k] * x**k for k in range(nn + 1))
            decoys.append(step(rf"{start}\ \Rightarrow\ y = {poly_tex(braw, x)}", lambda g=braw, ok=ok_raw: ok(g)) | {"pos": 2, "error": "sign", "why": WHY["coef"].replace("$n = 0, 1, 2, 3$", "$k = 0, 1, 2, \\dots$")})
        out.append({"params": {"family": fam, "n": nn}, "tier": 1 if nn <= 3 else (2 if nn <= 5 else 3),
                    "problem": rf"{ode}\ \text{{의 다항식 해 (정규화까지)}}",
                    "steps": steps, "decoys": decoys,
                    "verify": lambda g=final, L=L: None if same(sp.expand(L(g)), 0) else "다항식이 해가 아님"})
    return out


def _rec2_ok(L, num, kk):
    rec = lambda m, a, num=num, kk=kk: num.subs(kk, m) * _get(a, m) / ((m + 2) * (m + 1))
    return _series_ok(L)(_coeffs(rec))


def _laguerre_rec_ok(nn):
    L = lambda g: x * sp.diff(g, x, 2) + (1 - x) * sp.diff(g, x) + nn * g
    a = [sp.Integer(1)]
    for k in range(7):
        a.append(sp.Rational(k - nn, (k + 1) ** 2) * a[-1])
    return all(same(_coeff_of(L, a, j), 0) for j in range(6))
