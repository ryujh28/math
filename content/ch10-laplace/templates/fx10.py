"""10장 변환 정리(공식 원자)의 구체적 적용 문제. 판정은 수치 적분 ℒ{f}(s₀)와 비교한다."""
import itertools
import sympy as sp
from texkit import t, s, Y, tex, join_terms, tshift as tsh
from build import laplace_same, same as bsame, S_PTS

tau = sp.symbols("tau", positive=True)
H = sp.Heaviside


def _case(prompt, ans_tex, ans_ok, wrong, tier=None, params=None):
    c = {"params": params or {}, "prompt": prompt, "answer": {"tex": ans_tex, "ok": ans_ok, "error": None},
         "wrong": [{"tex": tx, "ok": ok, "error": e} for tx, ok, e in wrong]}
    if tier is not None:
        c["tier"] = tier
    return c


def _F(e):
    """보기 표시용: 통분·약분한 꼴."""
    return tex(sp.factor(sp.cancel(sp.together(e))))


def _ytex(e):
    """a·Y + (s의 다항식) → 's^{2}Y - 3s + 1'."""
    e = sp.expand(e)
    cY = e.coeff(Y)
    rest = sp.expand(e - cY * Y)
    body = "Y" if cY == 1 else tex(cY) + "Y"
    return join_terms([(1, body), (rest.coeff(s, 2), "s^{2}"), (rest.coeff(s, 1), "s"), (rest.coeff(s, 0), "")])


def _etex(k, G):
    """e^{ks}·G: 합이면 e^{-2s}(…), 아니면 한 분수로."""
    G = sp.sympify(G)
    if k == 0:
        return _F(G)
    if not isinstance(G, sp.Add):
        return tex(sp.exp(k * s) * sp.factor(G))
    pre = "e^{" + ("-" if k < 0 else "") + ("" if abs(k) == 1 else tex(abs(k))) + "s}"
    return pre + r"\left(" + tex(G) + r"\right)"


def _lap(f):
    return sp.simplify(sp.laplace_transform(f, t, s, noconds=True))


def _lap_ok(f):
    """보기 G가 ℒ{f}와 같은가 (수치 적분으로)."""
    return lambda G, f=f: laplace_same(f, G)


# 정리를 적용할 기본 함수들 (TeX, f)
BASE = [
    (r"\cos 2t", sp.cos(2 * t)), (r"\sin 3t", sp.sin(3 * t)), (r"e^{2t}", sp.exp(2 * t)), (r"e^{-t}", sp.exp(-t)),
    (r"t^{2}", t ** 2), (r"t", t), (r"\cos t", sp.cos(t)), (r"\sin t", sp.sin(t)), (r"t^{3}", t ** 3),
    (r"\sinh 2t", sp.sinh(2 * t)), (r"\cosh t", sp.cosh(t)), (r"e^{-3t}", sp.exp(-3 * t)),
]


def _items(prompt_of, truth_of, wrongs_of, tier_of=lambda i: None):
    out = []
    for i, (ft, f) in enumerate(BASE):
        F = _lap(f)
        target, truth = truth_of(f, F)
        if target is None:
            continue
        ok = _lap_ok(target)
        cand = wrongs_of(f, F)
        out.append(_case(prompt_of(ft), _F(truth), lambda G=truth, ok=ok: ok(G),
                         [(_F(G), lambda G=G, ok=ok: ok(G), e) for G, e in cand], tier=tier_of(i), params={"f": ft}))
    return out


def deriv1():
    f0 = lambda f: f.subs(t, 0)
    out = _items(lambda ft: rf"f(t) = {ft}\text{{일 때 }} \mathcal{{L}}\{{f^{{\prime}}(t)\}} = \;?",
                 lambda f, F: (sp.diff(f, t), s * F - f0(f)),
                 lambda f, F: [(s * F, "initial_condition"), (s * F + f0(f), "sign"), (F / s, "wrong_pair"), (-sp.diff(F, s), "wrong_pair"),
                               (s * F - f0(f) + 1, "initial_condition")])
    # Y(s)와 초기값만으로
    for y0 in [1, -2, 3, 0, 5, -1]:
        truth = s * Y - y0
        ok = lambda e, tr=truth: bsame(e.subs(Y, sp.Rational(7, 3)), tr.subs(Y, sp.Rational(7, 3)), s, S_PTS)
        cand = [(s * Y + y0, "sign"), (s * Y, "initial_condition"), (Y - y0, "missing_factor"), (s * Y - y0 * s, "algebra")]
        out.append(_case(rf"y(0) = {y0},\ Y = \mathcal{{L}}\{{y\}}\text{{일 때 }} \mathcal{{L}}\{{y^{{\prime}}\}} = \;?", _ytex(truth),
                         lambda e=truth, ok=ok: ok(e), [(_ytex(e), lambda e=e, ok=ok: ok(e), er) for e, er in cand], params={"y0": y0}))
    return out


def deriv2():
    out = _items(lambda ft: rf"f(t) = {ft}\text{{일 때 }} \mathcal{{L}}\{{f^{{\prime\prime}}(t)\}} = \;?",
                 lambda f, F: (sp.diff(f, t, 2), s ** 2 * F - s * f.subs(t, 0) - sp.diff(f, t).subs(t, 0)),
                 lambda f, F: [(s ** 2 * F, "initial_condition"),
                               (s ** 2 * F - f.subs(t, 0) - s * sp.diff(f, t).subs(t, 0), "initial_condition"),
                               (s ** 2 * F + s * f.subs(t, 0) + sp.diff(f, t).subs(t, 0), "sign"),
                               (s ** 2 * F - s * f.subs(t, 0), "initial_condition"), (sp.diff(F, s, 2), "wrong_pair")],
                 tier_of=lambda i: 2)
    for y0, v0 in itertools.product([1, -2, 0, 3], [2, -1, 0]):
        if y0 == 0 and v0 == 0:
            continue
        truth = s ** 2 * Y - y0 * s - v0
        ok = lambda e, tr=truth: bsame(e.subs(Y, sp.Rational(7, 3)), tr.subs(Y, sp.Rational(7, 3)), s, S_PTS)
        cand = [(s ** 2 * Y - v0 * s - y0, "initial_condition"), (s ** 2 * Y + y0 * s + v0, "sign"),
                (s ** 2 * Y - y0 * s, "initial_condition"), (s ** 2 * Y - y0 - v0, "missing_factor"), (s ** 2 * Y - y0 * s + v0, "sign")]
        out.append(_case(rf"y(0) = {y0},\ y^{{\prime}}(0) = {v0}\text{{일 때 }} \mathcal{{L}}\{{y^{{\prime\prime}}\}} = \;?", _ytex(truth),
                         lambda e=truth, ok=ok: ok(e), [(_ytex(e), lambda e=e, ok=ok: ok(e), er) for e, er in cand], params={"y0": y0, "v0": v0}))
    return out


def sshift():
    out = []
    for (ft, f), a in itertools.product(BASE[:9], [2, -1, 3, -2]):
        if f.has(sp.exp):
            continue
        F = _lap(f)
        target = sp.exp(a * t) * f
        truth = F.subs(s, s - a)
        ok = _lap_ok(target)
        cand = [(F.subs(s, s + a), "sign"), (F / (s - a), "wrong_pair"), (F, "missing_factor"), (sp.exp(-a * s) * F, "wrong_pair")]
        et = "e^{" + (tex(a) if a != 1 else "") + "t}"
        out.append(_case(rf"\mathcal{{L}}\{{{et}{ft}\}} = \;?", _F(truth), lambda G=truth, ok=ok: ok(G),
                         [(_F(G), lambda G=G, ok=ok: ok(G), e) for G, e in cand], tier=1 if ft in ("t", r"t^{2}") else 2,
                         params={"f": ft, "a": a}))
    return out


def tshift():
    out = []
    shapes = [(r"(t - {c})", lambda c: t - c, t), (r"(t - {c})^{{2}}", lambda c: (t - c) ** 2, t ** 2),
              (r"\sin\left(t - {c}\right)", lambda c: sp.sin(t - c), sp.sin(t)), (r"e^{{t - {c}}}", lambda c: sp.exp(t - c), sp.exp(t)),
              (r"\cos 2(t - {c})", lambda c: sp.cos(2 * (t - c)), sp.cos(2 * t))]
    for (tt, fc, g), c in itertools.product(shapes, [1, 2, 3]):
        G = _lap(g)
        target = H(t - c) * fc(c)
        truth = sp.exp(-c * s) * G
        ok = _lap_ok(target)
        cand = [(c, G, "sign"), (0, G, "missing_factor"), (-c, G.subs(s, s - c), "wrong_pair"), (-c, 1 / s, "missing_factor")]
        out.append(_case(rf"\mathcal{{L}}\{{u({tsh(c)})\,{tt.format(c=c)}\}} = \;?", _etex(-c, G), lambda G=truth, ok=ok: ok(G),
                         [(_etex(k, Gw), lambda G=sp.exp(k * s) * Gw, ok=ok: ok(G), e) for k, Gw, e in cand], params={"g": str(g), "c": c}))
    # 함정: u(t − c)·t 는 t = (t − c) + c 로 고쳐 써야 한다
    for c in [1, 2, 3, 4]:
        target = H(t - c) * t
        truth = sp.exp(-c * s) * (1 / s ** 2 + c / s)
        ok = _lap_ok(target)
        cand = [(-c, 1 / s ** 2, "theorem_condition"), (-c, 1 / s ** 2 - c / s, "sign"), (c, 1 / s ** 2 + c / s, "sign"),
                (0, 1 / s ** 2 + c / s, "missing_factor")]
        out.append(_case(rf"\mathcal{{L}}\{{u({tsh(c)})\,t\}} = \;?", _etex(-c, 1 / s ** 2 + c / s), lambda G=truth, ok=ok: ok(G),
                         [(_etex(k, Gw), lambda G=sp.exp(k * s) * Gw, ok=ok: ok(G), e) for k, Gw, e in cand], tier=3, params={"c": c, "trap": 1}))
    return out


CONV = [(r"e^{t}", sp.exp(t), r"1", sp.Integer(1)), (r"e^{2t}", sp.exp(2 * t), r"e^{-t}", sp.exp(-t)),
        (r"t", t, r"e^{t}", sp.exp(t)), (r"\sin t", sp.sin(t), r"1", sp.Integer(1)), (r"t", t, r"t", t),
        (r"\cos t", sp.cos(t), r"e^{-2t}", sp.exp(-2 * t)), (r"e^{-t}", sp.exp(-t), r"e^{-3t}", sp.exp(-3 * t)),
        (r"t^{2}", t ** 2, r"1", sp.Integer(1)), (r"\sin 2t", sp.sin(2 * t), r"t", t), (r"e^{3t}", sp.exp(3 * t), r"\cos t", sp.cos(t))]


def conv():
    out = []
    for ft, f, gt, g in CONV:
        F, G = _lap(f), _lap(g)
        h = sp.simplify(sp.integrate(f.subs(t, tau) * g.subs(t, t - tau), (tau, 0, t)))
        ok = _lap_ok(h)
        truth = F * G
        cand = [(F + G, "algebra"), (F / G, "algebra"), (F * G / s, "missing_factor"), (-F * G, "sign"), (sp.diff(F * G, s), "wrong_pair")]
        out.append(_case(rf"f(t) = {ft},\ g(t) = {gt}\text{{일 때 }} \mathcal{{L}}\left\{{(f * g)(t)\right\}} = \;?", _F(truth),
                         lambda G=truth, ok=ok: ok(G), [(_F(Gw), lambda G=Gw, ok=ok: ok(G), e) for Gw, e in cand], params={"f": ft, "g": gt}))
    return out


def tmult():
    return _items(lambda ft: rf"\mathcal{{L}}\{{t\cdot {ft}\}} = \;?",
                  lambda f, F: (t * f, -sp.diff(F, s)),
                  lambda f, F: [(sp.diff(F, s), "sign"), (F / s, "wrong_pair"), (s * F, "wrong_pair"), (-sp.diff(F, s) / s, "algebra"),
                                (F ** 2, "algebra")],
                  tier_of=lambda i: 2 if i < 4 else 3)


def integral():
    return _items(lambda ft: rf"\mathcal{{L}}\left\{{\int_0^t {ft.replace('t', r'\tau')}\,d\tau\right\}} = \;?",
                  lambda f, F: (sp.integrate(f.subs(t, tau), (tau, 0, t)), F / s),
                  lambda f, F: [(s * F, "wrong_pair"), (F / s ** 2, "algebra"), (F, "missing_factor"), (-sp.diff(F, s), "wrong_pair"),
                                (F / s - f.subs(t, 0) / s, "initial_condition")],
                  tier_of=lambda i: 2)
