"""생성기와 빌드가 함께 쓰는 검증 도구.

원칙: 생성기는 화면에 보일 TeX를 손으로 조립하고, 각 보기·단계가 맞는지 판정하는
함수(ok)를 SymPy의 고수준 연산(det, eigenvals, dsolve, exp 등)으로 따로 만든다.
빌드는 정답·정답 단계는 ok() == True, 오답은 ok() == False 인지 확인한다.
"""
import math
import sympy as sp
from sympy.matrices import MatrixBase

x, y, t, s, r, lam = sp.symbols("x y t s r lambda")
C1, C2, C = sp.symbols("C1 C2 C")

# 기호별 표본점 (정수·특이점 회피)
PTS = {
    "s": [sp.Rational(13, 2), sp.Rational(33, 4), sp.Integer(11)],
    "x": [sp.Rational(21, 100), sp.Rational(43, 100), sp.Rational(67, 100), sp.Rational(89, 100)],
}
DEFAULT_PTS = [sp.Rational(31, 100), sp.Rational(57, 100), sp.Rational(83, 100), sp.Rational(119, 100)]


def _num(e):
    v = complex(sp.N(e, 30))
    return v


def close(a, b):
    a, b = _num(a), _num(b)
    if not (math.isfinite(abs(a)) and math.isfinite(abs(b))):
        return False
    return abs(a - b) <= 1e-9 * max(abs(a), abs(b)) + 1e-12


def same(a, b, pts=None):
    """두 값이 같은지: 스칼라·식(자유 기호는 표본점에서)·행렬·튜플·집합."""
    if isinstance(a, (set, frozenset)) or isinstance(b, (set, frozenset)):
        if not (isinstance(a, (set, frozenset)) and isinstance(b, (set, frozenset))) or len(a) != len(b):
            return False
        bl = list(b)
        for ai in a:
            hit = next((bj for bj in bl if same(ai, bj, pts)), None)
            if hit is None:
                return False
            bl.remove(hit)
        return True
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        if not (isinstance(a, (list, tuple)) and isinstance(b, (list, tuple))) or len(a) != len(b):
            return False
        return all(same(ai, bi, pts) for ai, bi in zip(a, b))
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    a, b = sp.sympify(a), sp.sympify(b)
    if isinstance(a, MatrixBase) or isinstance(b, MatrixBase):
        if not (isinstance(a, MatrixBase) and isinstance(b, MatrixBase)) or a.shape != b.shape:
            return False
        return all(same(ai, bi, pts) for ai, bi in zip(a, b))
    syms = sorted(a.free_symbols | b.free_symbols, key=lambda q: q.name)
    if not syms:
        return close(a, b)
    n = 4
    for k in range(n):
        sub = {}
        for q in syms:
            p = pts if (pts and q.name in ("x", "t")) else PTS.get(q.name, DEFAULT_PTS)
            sub[q] = p[(k + syms.index(q)) % len(p)]
        if not close(a.subs(sub), b.subs(sub)):
            return False
    return True


def is_family_solution(expr, residual, consts, var=x, pts=None):
    """expr(var; consts)가 임의의 상수에서 미분방정식을 만족하는지.
    residual(f) → L[f] − R (0이면 해). 상수 값을 몇 가지 바꿔 확인한다."""
    trials = [(2, -1), (sp.Rational(1, 3), 5), (-3, sp.Rational(7, 2))]
    for tr in trials:
        sub = dict(zip(consts, tr))
        if not same(sp.simplify(residual(expr.subs(sub))), 0, pts):
            return False
    return True


def independent(funcs, var=x, pts=None):
    """함수들이 일차독립인지 (Wronskian이 표본점에서 0이 아님)."""
    n = len(funcs)
    W = sp.Matrix([[sp.diff(f, var, k) for f in funcs] for k in range(n)]).det()
    p = (pts or PTS["x"])[1]
    return abs(_num(W.subs(var, p))) > 1e-9


def fit_constants(expr, target, consts, var=x, pts=None):
    """expr(var; consts) = target(var)가 되도록 상수를 맞춘 뒤, 다른 점에서도 같은지."""
    pts = pts or PTS["x"]
    eqs = [sp.Eq(expr.subs(var, p), target.subs(var, p)) for p in pts[: len(consts)]]
    sol = sp.solve(eqs, consts, dict=True)
    if not sol:
        return False
    e2 = expr.subs(sol[0])
    return same(e2, target, pts)


def relation_holds(rel, ytrue, consts, var=x, pts=None):
    """rel(var, y; consts) = 0 이 참 해 y(var)를 따라 성립하는 상수가 있는지."""
    e = rel.subs(y, ytrue)
    if not consts:
        return same(e, 0, pts)
    return fit_constants(e, sp.Integer(0), consts, var, pts)


# ---------------------------------------------------------------- 생성기 편의 함수
def step(tex, ok):
    return {"tex": tex, "ok": ok}


def vstep(tex, expr, ref, pts=None):
    return {"tex": tex, "ok": lambda: same(expr, ref, pts)}


def decoy(pos, tex, ok, error, why):
    return {"pos": pos, "tex": tex, "ok": ok, "error": error, "why": why}


def vdecoy(pos, tex, expr, ref, error, why, pts=None):
    return decoy(pos, tex, lambda: same(expr, ref, pts), error, why)


def opt(tex, ok, error=None):
    """객관식 보기 하나. ok() → 이 보기가 맞는가."""
    return {"tex": tex, "ok": ok, "error": error}
