"""7장 공식 원자의 구체적 적용 문제."""
import itertools
import sympy as sp
from texkit import tex, join_terms, poly_tex
from checks import same, opt, is_family_solution, independent, x, r, C1, C2

P2, P1 = r"y^{\prime\prime}", r"y^{\prime}"


def _case(prompt, ans_tex, ans_ok, wrong, tier=None, params=None):
    c = {"params": params or {}, "prompt": prompt, "answer": opt(ans_tex, ans_ok),
         "wrong": [opt(tx, ok, e) for tx, ok, e in wrong]}
    if tier is not None:
        c["tier"] = tier
    return c


def _euler_tex(a, b):
    return join_terms([(1, "x^{2}" + P2), (a, "x" + P1), (b, "y")]) + " = 0"


def _euler_L(a, b):
    return lambda g, a=a, b=b: x ** 2 * sp.diff(g, x, 2) + a * x * sp.diff(g, x) + b * g


def eulerform():
    out = []
    pairs = [(r1, r2) for r1, r2 in itertools.combinations([-3, -2, -1, 1, 2, 3, 4], 2)]
    for i, (r1, r2) in enumerate(pairs):
        a, b = 1 - (r1 + r2), r1 * r2
        truth = sp.expand(r * (r - 1) + a * r + b)
        okp = lambda P, tr=truth: same(sp.expand(P), tr)
        cand = [(r ** 2 + a * r + b, "algebra"), (r ** 2 + (a + 1) * r + b, "sign"), (r ** 2 - (a - 1) * r + b, "sign"),
                (r ** 2 + (a - 1) * r - b, "sign")]
        out.append(_case(_euler_tex(a, b) + r"\text{에 } y = x^{r}\text{을 넣으면?}", poly_tex(truth, r) + " = 0",
                         lambda P=truth, ok=okp: ok(P), [(poly_tex(P, r) + " = 0", lambda P=P, ok=okp: ok(P), e) for P, e in cand],
                         params={"a": a, "b": b}))
        if i % 2 == 0:  # 일반해까지
            L = _euler_L(a, b)
            ok = lambda g, L=L: is_family_solution(g, L, [C1, C2]) and independent([sp.diff(g, C1), sp.diff(g, C2)])
            ans = C1 * x ** r1 + C2 * x ** r2
            cand2 = [(C1 * sp.exp(r1 * x) + C2 * sp.exp(r2 * x), "wrong_pair"), (C1 * x ** (-r1) + C2 * x ** (-r2), "sign"),
                     (C1 * x ** (r1 + 1) + C2 * x ** (r2 + 1), "algebra"), (C1 * x ** r1 + C2 * x ** r1 * sp.log(x), "algebra")]
            out.append(_case(_euler_tex(a, b) + r"\ (x > 0)\text{의 일반해}", "y = " + tex(ans), lambda g=ans, ok=ok: ok(g),
                             [("y = " + tex(g), lambda g=g, ok=ok: ok(g), e) for g, e in cand2], tier=2, params={"a": a, "b": b}))
    return out


def _second_ok(L, y1):
    return lambda g, L=L, y1=y1: same(sp.simplify(L(g)), 0) and independent([y1, g])


def reduction():
    out = []
    # 상수계수 중근: y1 = e^{mx} → y2 = x e^{mx}
    for m in [-3, -2, -1, 1, 2, 3]:
        L = lambda g, m=m: sp.diff(g, x, 2) - 2 * m * sp.diff(g, x) + m * m * g
        y1 = sp.exp(m * x)
        ok = _second_ok(L, y1)
        cand = [(x ** 2 * y1, "algebra"), (sp.exp(-m * x), "sign"), (y1 / x, "algebra"), (sp.exp(2 * m * x), "algebra")]
        out.append(_case(join_terms([(1, P2), (-2 * m, P1), (m * m, "y")]) + rf" = 0,\ y_1 = {tex(y1)}\text{{일 때 }} y_2 = \;?",
                         tex(x * y1), lambda g=x * y1, ok=ok: ok(g), [(tex(g), lambda g=g, ok=ok: ok(g), e) for g, e in cand],
                         params={"m": m}))
    # Euler 중근: y1 = x^m → y2 = x^m ln x
    for m in [-2, -1, 1, 2, 3]:
        a, b = 1 - 2 * m, m * m
        L = _euler_L(a, b)
        y1 = x ** m
        ok = _second_ok(L, y1)
        cand = [(x * y1, "wrong_pair"), (x ** (-m), "sign"), (y1 * sp.log(x) ** 2, "algebra"), (y1 * sp.exp(x), "algebra")]
        out.append(_case(_euler_tex(a, b).replace(" = 0", "") + rf" = 0,\ y_1 = {tex(y1)}\text{{일 때 }} y_2 = \;?",
                         tex(y1 * sp.log(x)), lambda g=y1 * sp.log(x), ok=ok: ok(g),
                         [(tex(g), lambda g=g, ok=ok: ok(g), e) for g, e in cand], tier=2, params={"m": m}))
    # 변수계수 고전 예
    extra = [
        (lambda g: x ** 2 * sp.diff(g, x, 2) - 2 * g, r"x^{2}" + P2 + " - 2y = 0", x ** 2, 1 / x, [x ** 2 * sp.log(x), x ** -2, x ** 3]),
        (lambda g: sp.diff(g, x, 2) - 2 / x * sp.diff(g, x) + 2 / x ** 2 * g, P2 + r" - \frac{2}{x}" + P1 + r" + \frac{2}{x^{2}}y = 0",
         x, x ** 2, [x * sp.log(x), x ** -1, x ** 3]),
        (lambda g: x * sp.diff(g, x, 2) + 2 * sp.diff(g, x), r"x" + P2 + " + 2" + P1 + " = 0", sp.Integer(1), 1 / x,
         [sp.log(x), x, x ** -2]),
    ]
    for L, et, y1, y2, wr in extra:
        ok = _second_ok(L, y1)
        out.append(_case(et + rf",\ y_1 = {tex(y1)}\text{{일 때 }} y_2 = \;?", tex(y2), lambda g=y2, ok=ok: ok(g),
                         [(tex(g), lambda g=g, ok=ok: ok(g), "algebra") for g in wr], tier=3, params={"eq": et}))
    return out


def superpos():
    out = []
    for (r1, r2), R in itertools.product([(-1, -2), (1, -1), (-1, 3), (2, -3), (1, 2)],
                                          [sp.Integer(6), sp.exp(4 * x), sp.exp(-4 * x), 2 * x]):
        p, q = -(r1 + r2), r1 * r2
        L = lambda g, p=p, q=q: sp.diff(g, x, 2) + p * sp.diff(g, x) + q * g
        if R.has(sp.exp):
            k = sp.diff(R, x) / R
            yp = R / (k ** 2 + p * k + q)
        elif R.has(x):
            # A x + B: q(Ax + B) + pA = 2x
            Aq = sp.Rational(2, q)
            yp = Aq * x - p * Aq / q
        else:
            yp = R / q
        yh = C1 * sp.exp(r1 * x) + C2 * sp.exp(r2 * x)
        Lr = lambda g, L=L, R=R: L(g) - R
        ok = lambda g, Lr=Lr: is_family_solution(g, Lr, [C1, C2]) and independent([sp.diff(g, C1), sp.diff(g, C2)])
        ans = yp + yh
        cand = [(yh, "missing_factor"), (yp + C1 * sp.exp(r1 * x), "missing_factor"), (-yp + yh, "sign"),
                (yp + C1 * sp.exp(-r1 * x) + C2 * sp.exp(-r2 * x), "sign")]
        et = join_terms([(1, P2), (p, P1), (q, "y")]) + " = " + tex(R)
        out.append(_case(rf"{et},\ y_p = {tex(yp)}\text{{일 때 일반해는?}}", "y = " + tex(ans), lambda g=ans, ok=ok: ok(g),
                         [("y = " + tex(g), lambda g=g, ok=ok: ok(g), e) for g, e in cand],
                         tier=1 if not R.has(x) else 2, params={"r": [r1, r2], "R": str(R)}))
    return out


# 매개변수 변환 고전 예: (방정식 TeX, L, y1, y2, R, y_p)
VP = [
    (P2 + r" + y = \sec x", sp.cos(x), sp.sin(x), 1 / sp.cos(x)),
    (P2 + r" + y = \tan x", sp.cos(x), sp.sin(x), sp.tan(x)),
    (P2 + r" + y = \csc x", sp.cos(x), sp.sin(x), 1 / sp.sin(x)),
    (P2 + r" - 2" + P1 + r" + y = \frac{e^{x}}{x}", sp.exp(x), x * sp.exp(x), sp.exp(x) / x),
    (P2 + r" - 2" + P1 + r" + y = \frac{e^{x}}{x^{2}}", sp.exp(x), x * sp.exp(x), sp.exp(x) / x ** 2),
    (P2 + r" + 4y = \sec 2x", sp.cos(2 * x), sp.sin(2 * x), 1 / sp.cos(2 * x)),
    (P2 + r" - y = \frac{2}{1 + e^{x}}", sp.exp(x), sp.exp(-x), 2 / (1 + sp.exp(x))),
]


def varparam():
    out = []
    for et, y1, y2, R in VP:
        W = sp.simplify(y1 * sp.diff(y2, x) - y2 * sp.diff(y1, x))
        # 방정식 계수는 (y1, y2)에서 되살린다: y'' + p y' + q y
        p = sp.simplify(-sp.diff(W, x) / W)
        q = sp.simplify(-(sp.diff(y1, x, 2) + p * sp.diff(y1, x)) / y1)
        L = lambda g, p=p, q=q: sp.diff(g, x, 2) + p * sp.diff(g, x) + q * g
        head = rf"{et},\ y_1 = {tex(y1)},\ y_2 = {tex(y2)}\text{{일 때 }} "
        # (1) Wronskian
        wc = [(-W, "sign"), (sp.simplify(y1 * y2), "algebra"), (sp.simplify(y1 * sp.diff(y2, x) + y2 * sp.diff(y1, x)), "sign")]
        out.append(_case(head + r"W = \;?", tex(W), lambda w=W, tr=W: same(w, tr),
                         [(tex(w), lambda w=w, tr=W: same(w, tr), e) for w, e in wc], tier=2, params={"eq": et, "q": "W"}))
        # (2) u1′ = −y2 R / W
        u1p = sp.simplify(-y2 * R / W)
        uc = [(-u1p, "sign"), (sp.simplify(-y1 * R / W), "wrong_pair"), (sp.simplify(-y2 * R), "missing_factor"),
              (sp.simplify(y2 * R * W), "algebra")]
        out.append(_case(head + r"y_p = u_1y_1 + u_2y_2\text{에서 } u_1^{\prime} = \;?", tex(u1p), lambda u=u1p, tr=u1p: same(u, tr),
                         [(tex(u), lambda u=u, tr=u1p: same(u, tr), e) for u, e in uc], tier=2, params={"eq": et, "q": "u1"}))
        # (3) y_p 자체
        u1 = sp.integrate(u1p, x)
        u2 = sp.integrate(sp.simplify(y1 * R / W), x)
        yp = sp.simplify(u1 * y1 + u2 * y2)
        okp = lambda g, L=L, R=R: same(sp.simplify(L(g) - R), 0)
        pc = [(sp.simplify(-u1 * y1 + u2 * y2), "sign"), (sp.simplify(u1 * y2 + u2 * y1), "wrong_pair"),
              (sp.simplify(u1 * y1 - u2 * y2), "sign"), (sp.simplify(W * (u1 * y1 + u2 * y2)), "missing_factor")]
        out.append(_case(head + r"y_p = \;?", tex(yp), lambda g=yp, ok=okp: ok(g),
                         [(tex(g), lambda g=g, ok=okp: ok(g), e) for g, e in pc], tier=3, params={"eq": et, "q": "yp"}))
    return out
