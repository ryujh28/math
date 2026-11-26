"""6장 공식 원자의 구체적 적용 문제."""
import itertools
import math
import sympy as sp
from texkit import tex, join_terms
from checks import same, opt, is_family_solution, x, y, C

P1 = r"y^{\prime}"


def _case(prompt, ans_tex, ans_ok, wrong, tier=None, params=None):
    c = {"params": params or {}, "prompt": prompt, "answer": opt(ans_tex, ans_ok),
         "wrong": [opt(tx, ok, e) for tx, ok, e in wrong]}
    if tier is not None:
        c["tier"] = tier
    return c


def _lin_ok(a, q):
    resid = lambda g, a=a, q=q: sp.diff(g, x) + a * g - q
    return lambda g, resid=resid: is_family_solution(g, resid, [C]) and not same(sp.diff(g, C), 0)


def linformula():
    """y′ + ay = q(x): y = (1/μ)(∫μq dx + C), μ = e^{ax}."""
    out = []
    for a in [1, 2, 3, -1, -2]:
        for q in [sp.Integer(2), sp.Integer(6), sp.Integer(-3), sp.exp(x), sp.exp(2 * x), sp.exp(-3 * x), x, 2 * x]:
            if q.has(sp.exp) and sp.simplify(q.diff(x) / q) == -a:
                continue  # 공명은 생략
            mu = sp.exp(a * x)
            yp = sp.simplify(sp.integrate(mu * q, x) / mu)
            truth = yp + C * sp.exp(-a * x)
            ok = _lin_ok(a, q)
            cand = [(yp + C * sp.exp(a * x), "sign"), (C * sp.exp(-a * x), "missing_factor"),
                    (sp.simplify(a * yp) + C * sp.exp(-a * x), "missing_factor"), (-yp + C * sp.exp(-a * x), "sign"),
                    (sp.simplify(q / a * x) + C * sp.exp(-a * x), "algebra")]
            lhs = join_terms([(1, P1), (a, "y")])
            out.append(_case(rf"{lhs} = {tex(q)}\ \text{{의 일반해}}", "y = " + tex(truth), lambda g=truth, ok=ok: ok(g),
                             [("y = " + tex(g), lambda g=g, ok=ok: ok(g), e) for g, e in cand],
                             tier=1 if not q.has(x) else 2, params={"a": a, "q": str(q)}))
            if q.has(x):
                out[-1]["pace"] = "heavy"  # 우변 적분에 부분적분이 들어간다
    return out


def _md(M, N):
    return rf"\left({tex(M)}\right)dx + \left({tex(N)}\right)dy = 0"


POT = [x ** 2 * y, x * y ** 2, x ** 3 + x * y, sp.exp(x) * y, x * sp.sin(y), y * sp.cos(x), x ** 2 * y ** 2 + y,
       x * y + y ** 3, sp.exp(x * y), x ** 2 + 3 * x * y, sp.log(x) * y, x * sp.exp(y)]


def exactcond():
    out = []
    ok = lambda M, N: sp.simplify(sp.diff(M, y) - sp.diff(N, x)) == 0
    for i, F in enumerate(POT):
        M, N = sp.diff(F, x), sp.diff(F, y)
        bads = [(M, -N), (N, M), (M, N + x), (M * y, N), (M + y, N)]
        bads = [(Mb, Nb) for Mb, Nb in bads if not ok(Mb, Nb)][:4]
        out.append(_case(r"\text{완전(exact)인 방정식은?}", _md(M, N), lambda M=M, N=N, ok=ok: ok(M, N),
                         [(_md(Mb, Nb), lambda M=Mb, N=Nb, ok=ok: ok(M, N), "theorem_condition") for Mb, Nb in bads],
                         tier=1 if i < 8 else 2, params={"F": str(F)}))
    return out


def _pow(n):
    n = sp.nsimplify(n)
    if n == 1:
        return "y"
    return "y^{" + tex(n) + "}"


def _lin(d, coef, var):
    """d + coef·var → 'y′ + 2y', 'v′ - \\frac{1}{x}v'."""
    coef = sp.expand(coef)
    if coef == 0:
        return d
    neg = coef.could_extract_minus_sign()
    mag = -coef if neg else coef
    return d + (" - " if neg else " + ") + ("" if mag == 1 else tex(mag)) + var


def bernoulli():
    out = []
    pq = [(2, x), (1, sp.Integer(1)), (-1, x ** 2), (3, sp.exp(x)), (sp.Rational(1, 1) / x, x)]
    ns = [2, 3, -1, sp.Rational(1, 2), -2, 4, sp.Rational(1, 3)]
    for (p, q), n in itertools.product(pq[:4], ns):
        n = sp.nsimplify(n)
        prompt = rf"{_lin(P1, p, 'y')} = {tex(q) if q != 1 else ''}{_pow(n)}\ \text{{을 선형으로 바꾸는 치환}}"
        truth = 1 - n
        cand = [(n - 1, "sign"), (n, "algebra"), (1 + n, "sign"), (-n, "algebra")]
        ok = lambda e, tr=truth: same(e, tr)
        out.append(_case(prompt, "v = " + _pow(truth), lambda e=truth, ok=ok: ok(e),
                         [("v = " + _pow(e), lambda e=e, ok=ok: ok(e), er) for e, er in cand if e != 0],
                         params={"p": str(p), "q": str(q), "n": str(n)}))
    # 치환 뒤의 선형식: v′ + (1−n)p v = (1−n) q
    for (p, q), n in itertools.product(pq, [2, 3, -1, sp.Rational(1, 2)]):
        n = sp.nsimplify(n)
        k = 1 - n
        prompt = rf"{_lin(P1, p, 'y')} = {tex(q) if q != 1 else ''}{_pow(n)},\ v = {_pow(k)}\text{{일 때 }} v\text{{의 방정식은?}}"
        eq = lambda c1, c2, p=p, q=q: _lin(r"v^{\prime}", c1 * p, "v") + " = " + tex(sp.expand(c2 * q))
        ok = lambda c1, c2, k=k: same(c1, k) and same(c2, k)
        cand = [(1, k, "missing_factor"), (k, 1, "missing_factor"), (-k, -k, "sign"), (k, -k, "sign"), (n, n, "algebra")]
        out.append(_case(prompt, eq(k, k), lambda c1=k, c2=k, ok=ok: ok(c1, c2),
                         [(eq(c1, c2), lambda c1=c1, c2=c2, ok=ok: ok(c1, c2), e) for c1, c2, e in cand],
                         tier=2, params={"p": str(p), "q": str(q), "n": str(n)}))
    return out


# (f, 유일성이 깨지는 초기점, 괜찮은 초기점) — 판정은 f와 ∂f/∂y가 그 점에서 유한한지로 따로 계산
EXIST = [
    (3 * y ** sp.Rational(2, 3), [(0, 0), (2, 0), (-1, 0)], [(0, 1), (1, 8), (-2, 1), (3, 27)]),
    (sp.sqrt(y - 2), [(0, 2), (1, 2), (-3, 2)], [(0, 3), (1, 6), (2, 11), (-1, 18)]),
    (y / (x - 3), [(3, 1), (3, -2), (3, 0)], [(0, 1), (1, 2), (4, -1), (-2, 5)]),
    ((y + 1) ** sp.Rational(1, 3), [(0, -1), (2, -1), (5, -1)], [(0, 0), (1, 7), (2, 26), (0, 1)]),
    (x * y / (x + 1), [(-1, 1), (-1, 3), (-1, -2)], [(0, 1), (1, 1), (2, -3), (-2, 2)]),
    (sp.sqrt(x * y), [(1, 0), (2, 0), (4, 0)], [(1, 1), (2, 2), (1, 4), (3, 3)]),
]


def _finite(e):
    try:
        v = complex(sp.N(e))
    except (TypeError, ValueError):
        return False
    return math.isfinite(v.real) and math.isfinite(v.imag) and abs(v.imag) < 1e-12


def existence():
    out = []
    for F, bads, goods in EXIST:
        Fy = sp.diff(F, y)
        fails = lambda pt, F=F, Fy=Fy: not (_finite(F.subs({x: pt[0], y: pt[1]})) and _finite(Fy.subs({x: pt[0], y: pt[1]})))
        for i, bp in enumerate(bads):
            gs = goods[i:] + goods[:i]
            out.append(_case(rf"{P1} = {tex(F)}\ \text{{에서 해의 유일성이 보장되지 않는 초기조건은?}}",
                             rf"y({bp[0]}) = {bp[1]}", lambda pt=bp, f=fails: f(pt),
                             [(rf"y({g[0]}) = {g[1]}", lambda pt=g, f=fails: f(pt), "theorem_condition") for g in gs[:3]],
                             tier=2, params={"f": str(F), "pt": list(bp)}))
    return out
