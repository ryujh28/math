"""그래프 예측용 데이터를 팩에 붙인다 (초기값 문제의 해 곡선).

각 순서 문제(초기값 문제)에 대해:
  - 해 y(t)를 구한다: 팩의 sol(빌드가 저장한 SymPy 식) 또는 params로 dsolve.
  - 곡선 표본 61점, 같은 축의 오답 곡선 3개(지수 부호, 감쇠 제거, 진동수, 부호, 공명 등 흔한 실수).
    오답은 정답과 모양이 충분히 다르고(정규화 RMS ≥ 0.25) 서로도 다른 것만 남긴다.
  - 특징: 장기 거동(zero·const·grow·osc)과 진동 여부를 식에서 계산한다.
결과: item["graph"] = {var, x0, x1, y, wrong: [{y, error, why}], lim, osc}

사용: python3 tools/graphs.py [장 번호 ...]   (빌드 없이 팩에만 다시 붙인다. 빌드도 끝에 이걸 부른다)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import sympy as sp

ROOT = Path(__file__).resolve().parent.parent
t, x = sp.symbols("t x", real=True)
N = 61
LOC = {"t": t, "x": x, "Heaviside": sp.Heaviside, "E": sp.E}


# ---------------------------------------------------------------- 해 구하기
def _dsolve(eq_fn, var, order, ics_at, ics):
    f = sp.Function("f")
    ode = sp.Eq(eq_fn(f(var)), 0)
    cond = {f(ics_at): ics[0]}
    if order == 2:
        cond[f(var).diff(var).subs(var, ics_at)] = ics[1]
    return sp.simplify(sp.dsolve(ode, f(var), ics=cond).rhs)


def solution(item):
    """(식, 변수, 구간) 또는 None."""
    u, P = item["unit"], item.get("params", {})
    if item.get("sol"):
        e = sp.sympify(item["sol"], locals=LOC)
        e = e.subs(sp.Symbol("t"), t)
        return e, t, 0.0
    num = lambda v: sp.sympify(v)  # noqa: E731
    if u == "ode.linear":
        a, q, y0 = num(P["a"]), sp.sympify(P["q"], locals={"x": x}), num(P["y0"])
        return _dsolve(lambda g: g.diff(x) + a * g - q, x, 1, 0, [y0]).subs(x, t), t, 0.0
    if "y0" not in P and u in ("ode2.const", "ode2.euler"):
        return None                       # 일반해만 묻는 문제: 정해진 곡선이 없다
    if u == "ode2.const":
        p, q, y0, v0 = (num(P[k]) for k in ("p", "q", "y0", "v0"))
        return _dsolve(lambda g: g.diff(x, 2) + p * g.diff(x) + q * g, x, 2, 0, [y0, v0]).subs(x, t), t, 0.0
    if u == "ode2.euler":
        a, b = num(P["a"]), num(P["b"])
        y0, v0 = num(P["y0"]), num(P["v0"])
        return _dsolve(lambda g: x**2 * g.diff(x, 2) + a * x * g.diff(x) + b * g, x, 2, 1, [y0, v0]), x, 1.0
    return None


# ---------------------------------------------------------------- 특징
def _terms(e, var):
    """항마다 (지수 속도 r, 다항 차수 d, 진동 여부). Euler(x 영역)는 x^k를 속도 k로 본다."""
    e = sp.expand(e.replace(sp.Heaviside, lambda *a: sp.Integer(1)))
    e = sp.expand(sp.powsimp(e))
    out = []
    for term in sp.Add.make_args(e):
        if term.free_symbols.isdisjoint({var}):
            out.append((0, 0, False, term))
            continue
        r, d, osc = 0, 0, False
        for f_ in sp.Mul.make_args(term):
            if f_.func == sp.exp:
                r += sp.Poly(f_.args[0], var).coeff_monomial(var)
            elif f_.has(sp.sin, sp.cos) and f_.has(var):
                osc = True
            elif f_.is_Pow and f_.base == var:
                if var == x:
                    r += f_.exp          # x^k ~ e^{k ln x}
                else:
                    d += f_.exp
            elif f_ == var:
                if var == x:
                    r += 1
                else:
                    d += 1
            elif f_.func == sp.log:
                d += 1
        out.append((float(r), float(d), osc, term))
    return out


def features(e, var):
    ts = _terms(e, var)
    osc = any(o for _, _, o, _ in ts)
    rmax = max(r for r, *_ in ts)
    dmax = max(d for r, d, *_ in ts if abs(r - rmax) < 1e-12)
    if rmax > 1e-12 or (abs(rmax) < 1e-12 and dmax > 0):
        lim = "grow"
    elif abs(rmax) < 1e-12:
        lim = "osc" if any(o for r, _, o, _ in ts if abs(r) < 1e-12) else "const"
    else:
        lim = "zero"
    return lim, osc


def _span(e, var, x0, extra=0.0):
    """보여 줄 구간 끝: 가장 느린 지수·진동이 드러나게."""
    if var == x:
        return 5.0
    rates, freqs = [], []
    for r, d, o, term in _terms(e, var):
        if abs(r) > 1e-9:
            rates.append(abs(r))
        for f_ in term.atoms(sp.sin, sp.cos):
            try:
                w = abs(float(sp.Poly(f_.args[0], var).coeff_monomial(var)))
                if w > 0:
                    freqs.append(w)
            except sp.PolynomialError:
                pass
    T = 3.0
    if rates:
        T = max(T, 4.0 / min(rates))
    if freqs:
        T = max(T, 2.5 * 2 * math.pi / min(freqs))
    T = max(T, extra)
    return float(min(12.0, T))


# ---------------------------------------------------------------- 표본·오답
def sample(e, var, x0, x1):
    f = sp.lambdify(var, e, modules=[{"Heaviside": lambda z, *a: np.heaviside(z, 1.0)}, "numpy"])
    xs = np.linspace(x0, x1, N)
    ys = np.asarray(f(xs), dtype=float) * np.ones_like(xs)
    if not np.all(np.isfinite(ys)):
        return None
    return ys


def _norm(ys):
    m = np.max(np.abs(ys))
    return ys / m if m > 1e-12 else ys


def dist(a, b):
    return float(np.sqrt(np.mean((_norm(a) - _norm(b)) ** 2)))


def _euler_swap(e):
    """C1 x^a + C2 x^b → (지수들, 서로 바꾼 계수들)."""
    terms = sp.Add.make_args(e)
    ks, cs = [], []
    for term in terms:
        c, k = term.as_coeff_exponent(x)
        ks.append(k)
        cs.append(c)
    if len(ks) != 2:
        return [], []
    return ks, cs[::-1]


def variants(e, var, lim, osc):
    """흔한 실수로 만든 오답 해 (식, 오류 종류, 이유)."""
    out = []
    if var == t:
        flip = e.replace(sp.exp, lambda a: sp.exp(-a))
        out.append((flip, "sign", "지수의 부호가 반대입니다. 근(극점) $r$에 대해 해는 $e^{rt}$이므로, $r < 0$이면 줄고 $r > 0$이면 커집니다."))
        nodamp = e.replace(sp.exp, lambda a: sp.Integer(1) if sp.Poly(a, t).coeff_monomial(t) < 0 else sp.exp(a))
        out.append((nodamp, "missing_factor", "감쇠 인자 $e^{\\alpha t}$($\\alpha < 0$)가 빠졌습니다. 근의 실수부가 음수면 진폭이 줄어듭니다."))
    else:
        flip = e.replace(lambda z: z.is_Pow and z.base == x, lambda z: x ** (-z.exp))
        out.append((flip, "sign", "Euler 방정식의 해는 $x^r$입니다. 지수 $r$의 부호가 반대입니다."))
        asexp = e.replace(lambda z: z.is_Pow and z.base == x, lambda z: sp.exp(z.exp * (x - 1)))
        out.append((asexp, "wrong_pair", "Euler 방정식을 상수계수처럼 $e^{rx}$로 풀었습니다. 해는 $x^r$ 꼴입니다."))
        swap = sum((c * (x ** k if k != 0 else 1)) for k, c in zip(*_euler_swap(e)))
        if swap is not None:
            out.append((swap, "algebra", "두 해의 계수가 서로 바뀌었습니다. 초기조건 두 개로 $C_1$, $C_2$를 다시 구하세요."))
    if osc:
        dbl = e.replace(sp.sin, lambda a: sp.sin(2 * a)).replace(sp.cos, lambda a: sp.cos(2 * a))
        out.append((dbl, "algebra", "진동수가 틀렸습니다. 복소근 $\\alpha \\pm i\\beta$의 허수부 $\\beta$가 각진동수입니다."))
        noosc = e.replace(sp.sin, lambda a: sp.Integer(0)).replace(sp.cos, lambda a: sp.Integer(1))
        out.append((noosc, "wrong_pair", "진동이 사라졌습니다. 근이 복소수면 $\\cos\\beta t$, $\\sin\\beta t$ 진동이 생깁니다."))
    else:
        wig = e * sp.cos(2 * var) if var == t else None
        if wig is not None:
            out.append((wig, "wrong_pair", "근이 실수면 진동하지 않습니다. 진동은 복소근일 때만 생깁니다."))
    out.append((-e, "initial_condition", "부호가 반대입니다. 초기값 $y(0)$(또는 $y'(0)$)의 부호를 확인하세요."))
    if lim != "grow":
        out.append((var * e if var == t else e * x, "wrong_pair", "$t$가 곱해져 커지는 꼴은 공명(중근이 강제항과 겹칠 때)입니다. 이 문제는 그런 경우가 아닙니다."))
    if e.has(sp.Heaviside):
        nos = e.replace(sp.Heaviside, lambda *a: sp.Integer(1))
        out.append((nos, "theorem_condition", "충격은 $t = c$에 들어옵니다. $u(t - c)$가 빠지면 처음부터 반응한 것처럼 됩니다."))
    return out


def make_graph(item):
    got = solution(item)
    if not got:
        return None
    e, var, x0 = got
    e = sp.expand(sp.powsimp(sp.expand(e)))
    lim, osc = features(e, var)
    extra = 0.0
    if e.has(sp.Heaviside):
        cs = [float(-sp.Poly(h.args[0], t).coeff_monomial(1)) for h in e.atoms(sp.Heaviside)]
        extra = max(cs) + 6.0
    x1 = _span(e, var, x0, extra) + (x0 if var == x else 0.0)
    ys = sample(e, var, x0, x1)
    if ys is None or np.max(np.abs(ys)) < 1e-9:
        return None
    keep = []
    for ew, err, why in variants(e, var, lim, osc):
        yw = sample(ew, var, x0, x1)
        if yw is None or np.max(np.abs(yw)) < 1e-9:
            continue
        if dist(yw, ys) < 0.25 or any(dist(yw, k[0]) < 0.2 for k in keep):
            continue
        # 같은 특징(장기 거동)만 다른 오답은 특징 고르기 단계와 겹치지만, 그래프 고르기에서는 모양으로 구별되면 충분하다
        keep.append((yw, err, why))
        if len(keep) == 3:
            break
    if len(keep) < 3:
        return None
    q = lambda arr: [int(round(v * 1000)) for v in _norm(arr)]  # noqa: E731
    return {"var": "t" if var == t else "x", "x0": x0, "x1": round(x1, 3), "y": q(ys),
            "wrong": [{"y": q(yw), "error": err, "why": why} for yw, err, why in keep], "lim": lim, "osc": bool(osc),
            "sol": sp.latex(e).replace(r"\theta\left(", "u\\left(")}


GRAPH_UNITS = {"lap.ivp1", "lap.ivp2.real", "lap.ivp2.repeated", "lap.ivp2.complex", "lap.ivp2.impulse", "lap.ivp.step",
               "ode.linear", "ode2.const", "ode2.euler"}


def apply(cid):
    pp = ROOT / "packs" / f"ch{cid:02d}.json"
    pack = json.loads(pp.read_text())
    n = ok = 0
    units = set()
    for it in pack["items"]:
        if it["type"] != "order" or it["unit"] not in GRAPH_UNITS:
            continue
        n += 1
        try:
            g = make_graph(it)
        except Exception as ex:  # noqa: BLE001
            print(f"  그래프 오류 {it['id']}: {ex!r}"[:200])
            g = None
        if g:
            it["graph"] = g
            ok += 1
            units.add(it["unit"])
        else:
            it.pop("graph", None)
    for u in pack["units"]:
        if u["id"] in units:
            u["graph"] = True
        else:
            u.pop("graph", None)
    pp.write_text(json.dumps(pack, ensure_ascii=False, separators=(",", ":")))
    if n:
        print(f"ch{cid:02d} 그래프: 초기값 문제 {n}개 중 {ok}개")


if __name__ == "__main__":
    ids = [int(a) for a in sys.argv[1:]] or sorted(int(p.stem[2:]) for p in (ROOT / "packs").glob("ch*.json"))
    for c in ids:
        apply(c)
