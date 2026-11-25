"""해설 작성용 도구 (templates/exN.py 에서 쓴다)."""
import math
import sympy as sp
from texkit import tex, tup, mat, join_terms  # noqa: F401

x, y, t, s, r = sp.symbols("x y t s r")


def M(flat, rows, cols=None):
    """params의 평평한 목록 → 행렬."""
    flat = list(flat)
    cols = cols or len(flat) // rows
    return sp.Matrix(rows, cols, flat)


def sq(flat):
    """정사각행렬 (원소 개수로 크기를 정한다)."""
    n = int(math.isqrt(len(flat)))
    return M(flat, n, n)


def V(flat):
    return sp.Matrix(list(flat))


def p(e):
    """음수·합이면 괄호로 감싼 TeX."""
    e = sp.sympify(e)
    t_ = tex(e)
    if e.is_Add or (e.is_number and e.could_extract_minus_sign()) or t_.startswith("-"):
        return r"\left(" + t_ + r"\right)"
    return t_


def prod(*xs):
    """a·b·c 를 괄호 붙여 TeX로."""
    return r" \cdot ".join(p(v) for v in xs)


def m(t_):
    """인라인 수식."""
    return f"${t_}$"


def dm(t_):
    """수식 블록."""
    return f"$${t_}$$"
