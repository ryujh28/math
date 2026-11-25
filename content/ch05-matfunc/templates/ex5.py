"""5장 문제별 해설."""
import sympy as sp
from exkit import tex, mat, sq, prod, m, dm, p, t


def qmat(P, it):
    a, b, c = P["abc"]
    A = sp.Matrix([[a, sp.Rational(b, 2)], [sp.Rational(b, 2), c]])
    return [f"{m(r'\mathbf{x}^{T}A\mathbf{x} = a_{11}x^{2} + 2a_{12}xy + a_{22}y^{2}')}: 대각에는 제곱항 계수, 비대각에는 {m('xy')} 계수의 절반.",
            f"{m('xy')} 계수 {m(tex(b))} → {m('a_{12} = a_{21} = ' + tex(sp.Rational(b, 2)))}", dm("A = " + mat(A))], []


def definite(P, it):
    a, b, c = P["abc"]
    A = sp.Matrix([[a, sp.Rational(b, 2)], [sp.Rational(b, 2), c]])
    ev = sorted(A.eigenvals().keys(), key=lambda e: float(e))
    D = A.det()
    return [f"{m('A = ' + mat(A))}의 고유값으로 판정: {m(r'\lambda = ' + r',\ '.join(tex(sp.nsimplify(e)) for e in ev))}",
            f"(빠른 판정: {m(r'\det A = ' + tex(D))}, {m('a_{11} = ' + tex(a))}. {m(r'\det A > 0')}이면 {m('a_{11}')}의 부호대로 정부호, {m(r'\det A < 0')}이면 부정부호, {m('0')}이면 준정부호)"], []


def expdiag(P, it):
    a, b = P["a"], P["b"]
    E = sp.diag(sp.exp(a * t), sp.exp(b * t))
    return [f"대각행렬은 {m('A^{k}')}도 대각이라 급수가 성분마다 따로 더해진다: {m(r'e^{At} = \operatorname{diag}(e^{a t}, e^{b t})')}",
            dm("e^{At} = " + mat(E))], [(E, (sp.diag(a, b) * t).exp())]


def expjordan(P, it):
    a, c = P["a"], P["c"]
    A = sp.Matrix([[a, c], [0, a]])
    N = sp.Matrix([[0, c], [0, 0]])
    E = sp.Matrix([[sp.exp(a * t), c * t * sp.exp(a * t)], [0, sp.exp(a * t)]])
    return [f"{m('A = aI + N')}, {m('N = ' + mat(N))}, {m('N^{2} = 0')}이고 {m('aI')}와 {m('N')}은 교환한다.",
            f"{m(r'e^{At} = e^{at}e^{Nt} = e^{at}(I + Nt)')}", dm("e^{At} = " + mat(E))], \
        [(E.diff(t), A * E), (E.subs(t, 0), sp.eye(2))]


def expdiagform(P, it):
    Pm = sq(P["P"])
    l1, l2 = P["d"]
    D = sp.diag(l1, l2)
    A = Pm * D * Pm.inv()
    E = Pm * sp.diag(sp.exp(l1 * t), sp.exp(l2 * t)) * Pm.inv()
    return [f"{m('A = PDP^{-1}')}이면 {m('A^{k} = PD^{k}P^{-1}')}이라 {m('e^{At} = Pe^{Dt}P^{-1}')}",
            f"{m('P^{-1} = ' + mat(Pm.inv()))}, {m('e^{Dt} = ' + mat(sp.diag(sp.exp(l1 * t), sp.exp(l2 * t))))}",
            "세 행렬을 곱하면 정답 보기. 순서가 바뀐 $P^{-1}e^{Dt}P$나 $e^{Dt}$만 쓴 것은 오답."], \
        [(sp.expand(E.diff(t) - A * E), sp.zeros(2, 2)), (E.subs(t, 0), sp.eye(2))]


def expderiv(P, it):
    A = sq(P["A"])
    return [f"{m(r'\frac{d}{dt}e^{At} = Ae^{At}')}이고 {m('e^{A\\cdot 0} = I')}이므로 {m(r'A = \left.\frac{d}{dt}e^{At}\right|_{t = 0}')}",
            "주어진 행렬을 성분마다 미분하고 $t = 0$을 넣으면", dm("A = " + mat(A))], []


def expcommute(P, it):
    A, B = sq(P["A"]), sq(P["B"])
    return [f"{m('e^{A+B} = e^{A}e^{B}')}는 {m('AB = BA')}일 때 보장된다 (지수 급수를 전개해 항을 맞출 때 교환이 필요하다).",
            f"정답 쌍은 {m('B')}가 {m('A')}의 다항식({m('pA + qI')} 꼴)이라 교환한다: {m('AB = BA = ' + mat(A * B))}"], [(A * B, B * A)]


def sylvester(P, it):
    A = sq(P["A"])
    mins = [A[:k, :k].det() for k in range(1, A.rows + 1)]
    return [f"Sylvester: 왼쪽 위부터의 소행렬식이 모두 양수 ⟺ 양의 정부호",
            f"정답 행렬: {m(r',\ '.join(f'D_{k + 1} = {tex(v)}' for k, v in enumerate(mins)))} → 모두 양수",
            "다른 보기는 첫 원소는 양수지만 뒤의 소행렬식 중 하나가 $0$ 이하."], []


EXPLAIN = {"la.qmat": qmat, "la.definite": definite, "la.expdiag": expdiag, "la.expjordan": expjordan,
           "la.expdiagform": expdiagform, "la.expderiv": expderiv, "la.expcommute": expcommute, "la.sylvester": sylvester}
