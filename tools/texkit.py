"""TeX 조립 도우미. 생성기들이 공통으로 쓴다.

원칙: 화면에 보이는 TeX는 교과서처럼 읽히도록 손으로 조립하고,
검증용 SymPy 식은 따로 들고 다닌다. 둘이 같은지는 build.py가 확인한다.
"""
import re

import sympy as sp

t, s, Y = sp.symbols("t s Y")


def tex(e) -> str:
    """SymPy 식 → TeX. sin{(2t)} 대신 sin 2t처럼 괄호를 줄인다."""
    out = sp.latex(sp.sympify(e), fold_func_brackets=True)
    out = out.replace(r"\theta\left(", "u\\left(")  # Heaviside → u(t − c)
    out = out.replace(r"\log", r"\ln").replace(r"\operatorname{atan}", r"\arctan ")
    out = re.sub(r"\\ln\{\\left\((\w) \\right\)\}", r"\\ln \1", out)          # \ln{\left(x \right)} → \ln x
    out = re.sub(r"\\(cos|sin)\{\\left\((\\ln [a-z]|\d*\s?\\ln [a-z]) \\right\)\}", r"\\\1(\2)", out)   # \cos{\left(\ln x \right)} → \cos(\ln x)
    return re.sub(r"\\ln\{(\\left\(.*?\\right\))\}", r"\\ln\1", out)         # 중괄호만 걷기


def join_terms(parts) -> str:
    """[(계수, 본문TeX), ...] → '3sY - s + 2Y'. 본문이 ''이면 상수항."""
    out = ""
    for c, body in parts:
        c = sp.nsimplify(c)
        if c == 0:
            continue
        neg = bool(c < 0)
        a = -c if neg else c
        if body == "":
            mag = tex(a)
        elif a == 1:
            mag = body
        else:
            mag = tex(a) + body
        if out == "":
            out = ("-" if neg else "") + mag
        else:
            out += (" - " if neg else " + ") + mag
    return out or "0"


def sum_tex(expr) -> str:
    """합을 양의 항부터 보여준다: '\\frac{2}{s+1} - \\frac{1}{s+2}'."""
    terms = list(sp.Add.make_args(sp.sympify(expr)))

    def rank(x):
        # 양의 항 먼저, 그 안에서 다항식 차수가 높은 것 먼저, 상수는 맨 뒤 (2 + x → x + 2)
        if x.is_number:
            return (x.could_extract_minus_sign(), 1, 0)
        syms = sorted(x.free_symbols, key=str)
        try:
            deg = sp.Poly(x, *syms).total_degree()
        except sp.PolynomialError:
            deg = 0
        return (x.could_extract_minus_sign(), 0, -deg)
    terms.sort(key=rank)
    out = ""
    for x in terms:
        neg = x.could_extract_minus_sign()
        m = tex(-x if neg else x)
        if out == "":
            out = ("-" if neg else "") + m
        else:
            out += (" - " if neg else " + ") + m
    return out


def shift(a) -> str:
    """'s - a' 꼴을 부호에 맞게: a=2 → 's - 2', a=-1 → 's + 1'."""
    a = sp.nsimplify(a)
    if a == 0:
        return "s"
    return f"s - {tex(a)}" if a > 0 else f"s + {tex(-a)}"


def tshift(c) -> str:
    return f"t - {tex(c)}" if c > 0 else f"t + {tex(-c)}"


def mat(M) -> str:
    """행렬 → pmatrix."""
    M = sp.Matrix(M)
    rows = [" & ".join(tex(e) for e in M.row(i)) for i in range(M.rows)]
    return r"\begin{pmatrix}" + r" \\ ".join(rows) + r"\end{pmatrix}"


def vmat(M) -> str:
    """행렬식 표기 |A|."""
    M = sp.Matrix(M)
    rows = [" & ".join(tex(e) for e in M.row(i)) for i in range(M.rows)]
    return r"\begin{vmatrix}" + r" \\ ".join(rows) + r"\end{vmatrix}"


def aug(M) -> str:
    """첨가행렬 [A | b]."""
    M = sp.Matrix(M)
    cols = "c" * (M.cols - 1) + "|c"
    rows = [" & ".join(tex(e) for e in M.row(i)) for i in range(M.rows)]
    return r"\left(\begin{array}{" + cols + "}" + r" \\ ".join(rows) + r"\end{array}\right)"


def tup(v) -> str:
    """(a, b, c) 꼴의 순서쌍."""
    return r"\left(" + r",\ ".join(tex(e) for e in v) + r"\right)"


def poly_tex(expr, var) -> str:
    """다항식을 내림차순으로: λ² − 5λ + 6."""
    P = sp.Poly(sp.expand(expr), var)
    parts = []
    deg = P.degree()
    for (k,), c in sorted(P.terms(), key=lambda q: -q[0][0]):
        body = "" if k == 0 else (tex(var) if k == 1 else f"{tex(var)}^{{{k}}}")
        parts.append((c, body))
    return join_terms(parts)
