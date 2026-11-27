#!/usr/bin/env python3
"""derivations.yaml에 쓴 유도의 수식 주장을 SymPy로 하나씩 확인한다.

python3 tools/verify_derivations.py
- 기호로 일반 성립을 보일 수 있는 것은 기호로, 아니면 구체적인 예로 확인한다.
- 수식 주장이 없는 개념 설명 줄은 CONCEPT에 이유와 함께 적어 둔다.
"""
import glob
import sys

import sympy as sp
import yaml

x, y, t, s, lam, k, C = sp.symbols("x y t s lambda k C")
a, b, c, d, p, q, n_ = sp.symbols("a b c d p q n")
r, al = sp.symbols("r alpha", real=True)
be, w, cc = sp.symbols("beta omega c", positive=True)
Z = lambda e: sp.simplify(sp.expand(e)) == 0          # noqa: E731
MZ = lambda M: all(Z(e) for e in M)                     # noqa: E731
V3 = lambda nm: sp.Matrix(sp.symbols(f"{nm}1:4", real=True))  # noqa: E731
u, v = V3("u"), V3("v")
f = sp.Function("f")
L = lambda e: sp.laplace_transform(e, t, s, noconds=True)  # noqa: E731


def M2(nm):
    return sp.Matrix(2, 2, sp.symbols(f"{nm}11 {nm}12 {nm}21 {nm}22"))


def M3(nm):
    return sp.Matrix(3, 3, sp.symbols(f"{nm}1:4(1:4)"))


A2, B2, A3, B3 = M2("a"), M2("b"), M3("a"), M3("b")
NUM = sp.Matrix([[2, 1], [1, 3]])
P0 = sp.Matrix([[1, 1], [1, 2]])
A0 = P0 * sp.diag(2, -1) * P0.inv()      # 정수 고유값 2, −1

CHECKS = {
    # ---------------- 1장
    "la.dot": [("u·v = Σ uᵢvᵢ", lambda: Z(u.dot(v) - sum(u[i] * v[i] for i in range(3))))],
    "la.norm": [("‖v‖² = v·v", lambda: Z(v.norm() ** 2 - v.dot(v)))],
    "la.orth": [("‖u − v‖² = ‖u‖² + ‖v‖² − 2u·v", lambda: Z((u - v).dot(u - v) - u.dot(u) - v.dot(v) + 2 * u.dot(v)))],
    "la.angle": [("‖u − v‖² = ‖u‖² + ‖v‖² − 2u·v", lambda: Z((u - v).dot(u - v) - u.dot(u) - v.dot(v) + 2 * u.dot(v)))],
    "la.proj": [("(u − cv)·v = 0 ⇒ c = u·v / v·v", lambda: Z(sp.solve((u - k * v).dot(v), k)[0] - u.dot(v) / v.dot(v)))],
    "la.cs": [("‖u − tv‖² = ‖v‖²t² − 2(u·v)t + ‖u‖²", lambda: Z((u - t * v).dot(u - t * v) - (v.dot(v) * t**2 - 2 * u.dot(v) * t + u.dot(u)))),
              ("판별식/4 = (u·v)² − ‖u‖²‖v‖²", lambda: Z(sp.discriminant(v.dot(v) * t**2 - 2 * u.dot(v) * t + u.dot(u), t) / 4 - (u.dot(v) ** 2 - u.dot(u) * v.dot(v))))],
    "la.gsformula": [("(v₂ − c u₁)·u₁ = 0 ⇒ c = v₂·u₁ / u₁·u₁", lambda: Z(sp.solve((v - k * u).dot(u), k)[0] - v.dot(u) / u.dot(u)))],
    "la.triangle": [("‖u + v‖² = ‖u‖² + 2u·v + ‖v‖²", lambda: Z((u + v).dot(u + v) - u.dot(u) - 2 * u.dot(v) - v.dot(v)))],
    "la.gs": [("u₂ = v₂ − (v₂·u₁/u₁·u₁)u₁ 는 u₁에 직교", lambda: Z((v - v.dot(u) / u.dot(u) * u).dot(u)))],
    "la.planeproj": [("v − (n·v/n·n)n 은 n에 직교", lambda: Z((v - u.dot(v) / u.dot(u) * u).dot(u)))],
    # ---------------- 2장
    "la.det2": [("소거하면 (ad − bc)x₁ = d b₁ − b b₂", lambda: Z(sp.solve([a * x + b * y - sp.Symbol("b1"), c * x + d * y - sp.Symbol("b2")], [x, y])[x] * (a * d - b * c) - (d * sp.Symbol("b1") - b * sp.Symbol("b2")))),
                ("평행사변형 넓이 = |ad − bc| (외적의 z성분)", lambda: Z(sp.Matrix([a, c, 0]).cross(sp.Matrix([b, d, 0]))[2] - (a * d - b * c)))],
    "la.inv2": [("[[a,b],[c,d]]·[[d,−b],[−c,a]] = (ad − bc)I", lambda: MZ(sp.Matrix([[a, b], [c, d]]) * sp.Matrix([[d, -b], [-c, a]]) - (a * d - b * c) * sp.eye(2)))],
    "la.matmul": [("(AB)x = A(Bx), (AB)ᵢⱼ = Σ aᵢₖbₖⱼ", lambda: MZ((A2 * B2) * sp.Matrix([x, y]) - A2 * (B2 * sp.Matrix([x, y])))
                  and all(Z((A2 * B2)[i, j] - sum(A2[i, m] * B2[m, j] for m in range(2))) for i in range(2) for j in range(2)))],
    "la.det3": [("det A = a₁₁M₁₁ − a₁₂M₁₂ + a₁₃M₁₃", lambda: Z(A3.det() - sum((-1) ** j * A3[0, j] * A3.minor(0, j) for j in range(3))))],
    "la.cofactor": [("det A = a₁₁M₁₁ − a₁₂M₁₂ + a₁₃M₁₃", lambda: Z(A3.det() - sum((-1) ** j * A3[0, j] * A3.minor(0, j) for j in range(3))))],
    "la.detprod": [("det(AB) = det A det B (2×2, 3×3)", lambda: Z((A2 * B2).det() - A2.det() * B2.det()) and Z((A3 * B3).det() - A3.det() * B3.det()))],
    "la.invprod": [("(AB)(B⁻¹A⁻¹) = I", lambda: MZ(sp.simplify((A2 * B2) * (B2.inv() * A2.inv())) - sp.eye(2)))],
    "la.transprod": [("(AB)ᵀ = BᵀAᵀ", lambda: MZ((A3 * B3).T - B3.T * A3.T))],
    "la.detscale": [("det(kA) = kⁿ det A (n = 2, 3)", lambda: Z((k * A2).det() - k**2 * A2.det()) and Z((k * A3).det() - k**3 * A3.det()))],
    "la.invertible": [("det A = det L · det U = 피벗들의 곱", lambda: (lambda Lm, Um: Z((Lm * Um).det() - Um[0, 0] * Um[1, 1] * Um[2, 2]))(
        sp.Matrix([[1, 0, 0], [a, 1, 0], [b, c, 1]]), sp.Matrix([[p, x, y], [0, q, k], [0, 0, d]])))],
    "la.gauss": [("R₂ ← R₂ − l R₁ 해도 해가 같다", lambda: (lambda sol1, sol2: all(Z(sol1[z] - sol2[z]) for z in (x, y)))(
        sp.solve([a * x + b * y - p, c * x + d * y - q], [x, y]),
        sp.solve([a * x + b * y - p, (c - (c / a) * a) * x + (d - (c / a) * b) * y - (q - (c / a) * p)], [x, y]))),
                 ("x_n = c_n / u_nn부터 뒤에서 대입", lambda: (lambda sol: Z(sol[y] - q / d))(sp.solve([a * x + b * y - p, d * y - q], [x, y])))],
    # ---------------- 3장
    "la.charpoly": [("det(A − λI) = λ² − (a + d)λ + (ad − bc)", lambda: Z((sp.Matrix([[a, b], [c, d]]) - lam * sp.eye(2)).det() - (lam**2 - (a + d) * lam + a * d - b * c)))],
    "la.eig2": [("근의 합 = tr, 곱 = det (Vieta)", lambda: (lambda rts: Z(sum(rts) - (a + d)) and Z(rts[0] * rts[1] - (a * d - b * c)))(
        sp.solve(lam**2 - (a + d) * lam + a * d - b * c, lam)))],
    "la.eigvec": [("v = (b, λ − a)이면 (A − λI)v = (0, −특성다항식)", lambda: MZ((sp.Matrix([[a, b], [c, d]]) - lam * sp.eye(2)) * sp.Matrix([b, lam - a])
                                                                   - sp.Matrix([0, -(lam**2 - (a + d) * lam + a * d - b * c)])))],
    "la.eigtri": [("삼각행렬의 det(A − λI) = Π(aᵢᵢ − λ)", lambda: (lambda T: Z((T - lam * sp.eye(3)).det() - (T[0, 0] - lam) * (T[1, 1] - lam) * (T[2, 2] - lam)))(
        sp.Matrix([[a, b, c], [0, d, p], [0, 0, q]])))],
    "la.trdet": [("(λ₁ − λ)(λ₂ − λ)에서 λ = 0 → λ₁λ₂, 일차항 → −(λ₁ + λ₂)", lambda: (lambda l1, l2: Z(((l1 - lam) * (l2 - lam)).subs(lam, 0) - l1 * l2)
                                                                                and Z(sp.Poly((l1 - lam) * (l2 - lam), lam).coeff_monomial(lam) + (l1 + l2)))(*sp.symbols("l1 l2")))],
    "la.symeig": [("대칭 A: (Av₁)·v₂ = v₁·(Av₂)", lambda: (lambda S: Z((S * u[:2, :]).dot(v[:2, :]) - u[:2, :].dot(S * v[:2, :])))(sp.Matrix([[a, b], [b, d]]))),
                  ("대칭 실행렬의 고유값 판별식 ≥ 0: (a − d)² + 4b²", lambda: Z(sp.discriminant(lam**2 - (a + d) * lam + a * d - b**2, lam) - ((a - d) ** 2 + 4 * b**2)))],
    "la.similar": [("det(P⁻¹AP − λI) = det(A − λI)", lambda: Z(sp.simplify((P0.inv() * A2 * P0 - lam * sp.eye(2)).det() - (A2 - lam * sp.eye(2)).det())))],
    "la.eigpow": [("Aᵏv = λᵏv, A⁻¹v = λ⁻¹v (예: A = PDP⁻¹, λ = 2)", lambda: MZ(A0**3 * P0[:, 0] - 8 * P0[:, 0]) and MZ(A0.inv() * P0[:, 0] - sp.Rational(1, 2) * P0[:, 0]))],
    "la.diag": [("AP = PD (고유벡터를 열로)", lambda: MZ(A0 * P0 - P0 * sp.diag(2, -1)))],
    "la.apow": [("PDⁿP⁻¹ = Aⁿ (n = 5)", lambda: MZ(P0 * sp.diag(2, -1) ** 5 * P0.inv() - A0**5))],
    # ---------------- 4장
    "la.ata": [("(AᵀA)ᵢⱼ = aᵢ·aⱼ, 대칭", lambda: (lambda A: all(Z((A.T * A)[i, j] - A[:, i].dot(A[:, j])) for i in range(2) for j in range(2)) and MZ(A.T * A - (A.T * A).T))(
        sp.Matrix(3, 2, sp.symbols("m1:7"))))],
    "la.sv": [("A = UΣVᵀ ⇒ AᵀA = VΣᵀΣVᵀ, σᵢ = √λᵢ(AᵀA)", lambda: (lambda U, S, Vm: MZ((U * S * Vm.T).T * (U * S * Vm.T) - Vm * S.T * S * Vm.T)
        and sorted((U * S * Vm.T).singular_values(), reverse=True) == [3, 2])(
        sp.Matrix([[sp.Rational(3, 5), -sp.Rational(4, 5)], [sp.Rational(4, 5), sp.Rational(3, 5)]]), sp.diag(3, 2),
        sp.Matrix([[sp.Rational(5, 13), -sp.Rational(12, 13)], [sp.Rational(12, 13), sp.Rational(5, 13)]])))],
    "la.svd": [("uᵢ = Avᵢ/σᵢ 정규직교, AV = UΣ (예)", lambda: (lambda A: (lambda ev: (lambda Vm: (lambda S: (lambda U: MZ(U.T * U - sp.eye(2)) and MZ(A * Vm - U * S))(
        A * Vm * S.inv()))(sp.diag(*[sp.sqrt(e) for e in ev])))(sp.Matrix.hstack(*[(A.T * A - e * sp.eye(2)).nullspace()[0].normalized() for e in ev])))(
        sorted((A.T * A).eigenvals().keys(), reverse=True)))(sp.Matrix([[2, 2], [-1, 1]])))],
    "la.normaleq": [("∇‖Ax − b‖² = 2Aᵀ(Ax − b)", lambda: (lambda A, bb, X: MZ(sp.Matrix([sp.diff(((A * X - bb).T * (A * X - bb))[0], z) for z in X]) - 2 * A.T * (A * X - bb)))(
        sp.Matrix(3, 2, sp.symbols("m1:7")), sp.Matrix(sp.symbols("b1:4")), sp.Matrix(sp.symbols("x1:3"))))],
    "la.projmat": [("P = A(AᵀA)⁻¹Aᵀ 이면 P² = P, Pᵀ = P", lambda: (lambda A: (lambda Pm: MZ(Pm * Pm - Pm) and MZ(Pm.T - Pm))(A * (A.T * A).inv() * A.T))(
        sp.Matrix([[1, 0], [1, 1], [1, 2]])))],
    "la.qr": [("A = QR, QᵀQ = I, R 위삼각, rᵢⱼ = qᵢ·aⱼ", lambda: (lambda A: (lambda QR: MZ(QR[0] * QR[1] - A) and MZ(QR[0].T * QR[0] - sp.eye(2)) and QR[1][1, 0] == 0
        and Z(QR[1][0, 1] - QR[0][:, 0].dot(A[:, 1])))(A.QRdecomposition()))(sp.Matrix([[1, 1], [1, 0], [0, 1]])))],
    "la.orthmat": [("QᵀQ = I ⇒ ‖Qx‖ = ‖x‖, (det Q)² = 1", lambda: (lambda Q: Z((Q * u[:2, :]).dot(Q * u[:2, :]) - u[:2, :].dot(u[:2, :])) and Z(Q.det() ** 2 - 1))(
        sp.Matrix([[sp.cos(a), -sp.sin(a)], [sp.sin(a), sp.cos(a)]])))],
    "la.lsq": [("AᵀA = [[n, Σx], [Σx, Σx²]], Aᵀb = [Σy, Σxy]", lambda: (lambda X, Y: (lambda A: MZ(A.T * A - sp.Matrix([[3, sum(X)], [sum(X), sum(xi**2 for xi in X)]]))
        and MZ(A.T * sp.Matrix(Y) - sp.Matrix([sum(Y), sum(xi * yi for xi, yi in zip(X, Y))])))(sp.Matrix([[1, xi] for xi in X])))(sp.symbols("x1:4"), sp.symbols("y1:4")))],
    "la.lu": [("승수를 부호 그대로 모은 L에 대해 LU = A", lambda: (lambda A: (lambda l21, l31: (lambda A1: (lambda l32: (lambda U: MZ(sp.Matrix([[1, 0, 0], [l21, 1, 0], [l31, l32, 1]]) * U - A))(
        sp.Matrix.vstack(A1[0, :], A1[1, :], A1[2, :] - l32 * A1[1, :])))(A1[2, 1] / A1[1, 1]))(
        sp.Matrix.vstack(A[0, :], A[1, :] - l21 * A[0, :], A[2, :] - l31 * A[0, :])))(A[1, 0] / A[0, 0], A[2, 0] / A[0, 0]))(sp.Matrix([[2, 1, 1], [4, 3, 3], [8, 7, 9]])))],
    # ---------------- 5장
    "la.qmat": [("xᵀAx = a₁₁x² + (a₁₂ + a₂₁)xy + a₂₂y²", lambda: Z((sp.Matrix([[x, y]]) * A2 * sp.Matrix([x, y]))[0] - (A2[0, 0] * x**2 + (A2[0, 1] + A2[1, 0]) * x * y + A2[1, 1] * y**2)))],
    "la.definite": [("A = QΛQᵀ, y = Qᵀx ⇒ q = λ₁y₁² + λ₂y₂² (예)", lambda: (lambda A: (lambda Pm, D: (lambda Q: (lambda yv: Z((sp.Matrix([[x, y]]) * A * sp.Matrix([x, y]))[0]
        - (D[0, 0] * yv[0] ** 2 + D[1, 1] * yv[1] ** 2)))(Q.T * sp.Matrix([x, y])))(sp.Matrix.hstack(*[Pm[:, i].normalized() for i in range(2)])))(*A.diagonalize()))(NUM))],
    "la.expdiag": [("e^{Dt} = diag(e^{λ₁t}, e^{λ₂t})", lambda: MZ((sp.diag(a, b) * t).exp() - sp.diag(sp.exp(a * t), sp.exp(b * t))))],
    "la.expjordan": [("A = aI + N, N² = 0 ⇒ e^{At} = e^{at}[[1, t], [0, 1]]", lambda: MZ((sp.Matrix([[a, 1], [0, a]]) * t).exp() - sp.exp(a * t) * sp.Matrix([[1, t], [0, 1]])))],
    "la.expdiagform": [("e^{At} = Pe^{Dt}P⁻¹ (예)", lambda: MZ(sp.simplify((A0 * t).exp() - P0 * (sp.diag(2, -1) * t).exp() * P0.inv())))],
    "la.expderiv": [("d/dt e^{At} = Ae^{At} (예)", lambda: MZ(sp.simplify(sp.diff((A0 * t).exp(), t) - A0 * (A0 * t).exp())))],
    "la.expcommute": [("교환하면 e^{A+B} = e^Ae^B, 아니면 다름 (예)", lambda: MZ(sp.simplify((sp.diag(1, 2) + sp.diag(3, 1)).exp() - sp.diag(1, 2).exp() * sp.diag(3, 1).exp()))
        and not MZ(sp.simplify((sp.Matrix([[0, 1], [0, 0]]) + sp.Matrix([[0, 0], [1, 0]])).exp() - sp.Matrix([[0, 1], [0, 0]]).exp() * sp.Matrix([[0, 0], [1, 0]]).exp()))),
                      ("(A + B)² = A² + AB + BA + B²", lambda: MZ((A2 + B2) ** 2 - (A2**2 + A2 * B2 + B2 * A2 + B2**2)))],
    "la.sylvester": [("ax² + bxy + cy² = a(x + b/2a·y)² + (4ac − b²)/4a·y²", lambda: Z(a * (x + b / (2 * a) * y) ** 2 + (4 * a * c - b**2) / (4 * a) * y**2 - (a * x**2 + b * x * y + c * y**2))),
                     ("det [[a, b/2], [b/2, c]] = ac − b²/4", lambda: Z(sp.Matrix([[a, b / 2], [b / 2, c]]).det() - (a * c - b**2 / 4)))],
    "la.expat": [("X = e^{At}: X′ = AX, X(0) = I (예)", lambda: (lambda X: MZ(sp.simplify(sp.diff(X, t) - A0 * X)) and MZ(X.subs(t, 0) - sp.eye(2)))((A0 * t).exp()))],
    "la.paxes": [("q = λ₁X² + λ₂Y² (예)", lambda: CHECKS["la.definite"][0][1]())],
    # ---------------- 6장
    "ode.mu": [("μ = e^{∫p dx} ⇒ μ′ = pμ, μ(y′ + py) = (μy)′", lambda: (lambda P, Y: (lambda mu: Z(sp.diff(mu, x) - P * mu) and Z(mu * (sp.diff(Y, x) + P * Y) - sp.diff(mu * Y, x)))(
        sp.exp(sp.Integral(P, x))))(sp.Function("p")(x), f(x)))],
    "ode.sepgen": [("y = Ce^{∫f dx} ⇒ y′ = f y", lambda: (lambda F: Z(sp.diff(C * sp.exp(sp.Integral(F, x)), x) - F * C * sp.exp(sp.Integral(F, x))))(sp.Function("g")(x)))],
    "ode.exactk": [("F_x = M, F_y = N ⇒ M_y = N_x", lambda: (lambda F: Z(sp.diff(sp.diff(F, x), y) - sp.diff(sp.diff(F, y), x)))(sp.Function("F")(x, y)))],
    "ode.exactcond": [("F_x = M, F_y = N ⇒ M_y = N_x", lambda: (lambda F: Z(sp.diff(sp.diff(F, x), y) - sp.diff(sp.diff(F, y), x)))(sp.Function("F")(x, y)))],
    "ode.linformula": [("y = (1/μ)(∫μq dx + C)는 y′ + py = q를 만족", lambda: (lambda P, Q: (lambda mu: (lambda Y: Z(sp.simplify(sp.diff(Y, x) + P * Y - Q)))(
        (sp.Integral(mu * Q, x) + C) / mu))(sp.exp(sp.Integral(P, x))))(sp.Function("p")(x), sp.Function("q")(x)))],
    "ode.bernoulli": [("v = y^{1−n}: v′ + (1−n)pv − (1−n)q = (1−n)y^{−n}(y′ + py − qyⁿ)", lambda: (lambda Y, P, Q: Z(sp.simplify(
        sp.diff(Y ** (1 - n_), x) + (1 - n_) * P * Y ** (1 - n_) - (1 - n_) * Q - (1 - n_) * Y ** (-n_) * (sp.diff(Y, x) + P * Y - Q * Y**n_))))(f(x), sp.Function("p")(x), sp.Function("q")(x)))],
    "ode.existence": [("y = 0과 y = x²/4가 모두 y′ = √y, y(0) = 0의 해 (x ≥ 0)", lambda: (lambda xp: Z(sp.diff(xp**2 / 4, xp) - sp.sqrt(xp**2 / 4)))(sp.Symbol("xp", positive=True)))],
    "ode.linear": [("(e^{ax}y)′ = e^{ax}(y′ + ay)", lambda: Z(sp.diff(sp.exp(a * x) * f(x), x) - sp.exp(a * x) * (sp.diff(f(x), x) + a * f(x))))],
    "ode.separable": [("게임의 네 가족에서 H′(y) = 1/g(y), F′(x) = f(x) (적분이 맞음)", lambda: all(
        Z(sp.diff(H, y) - 1 / g) and Z(sp.diff(F, x) - fx) for H, g, F, fx in [
            (-1 / y, y**2, k * x**2 / 2, k * x), (y**2 / 2, 1 / y, x**2 / 2, x),
            (sp.log(y), y, x**2 / 2 + a * x, x + a), (y**2 / 2, 1 / y, sp.exp(x), sp.exp(x))])),
                      ("예: y′ = xy², −1/y = x²/2 + C 의 해 y = −1/(x²/2 + C)가 방정식을 만족", lambda: (lambda yy: Z(sp.diff(yy, x) - x * yy**2))(-1 / (x**2 / 2 + C)))],
    "ode.exact": [("F = ∫M dx + h(y) ⇒ F_x = M (예: M = 2xy, N = x² + 2y)", lambda: (lambda F: Z(sp.diff(F, x) - 2 * x * y) and Z(sp.diff(F, y) - (x**2 + 2 * y)))(
        sp.integrate(2 * x * y, x) + y**2))],
    # ---------------- 7장
    "ode2.form": [("L[e^{rx}] = (r² + pr + q)e^{rx}", lambda: Z(sp.diff(sp.exp(r * x), x, 2) + p * sp.diff(sp.exp(r * x), x) + q * sp.exp(r * x) - (r**2 + p * r + q) * sp.exp(r * x))),
                  ("중근(p = −2r, q = r²)이면 xe^{rx}도 해", lambda: Z(sp.diff(x * sp.exp(r * x), x, 2) - 2 * r * sp.diff(x * sp.exp(r * x), x) + r**2 * x * sp.exp(r * x))),
                  ("e^{αx}cos βx, e^{αx}sin βx가 해 (p = −2α, q = α² + β²)", lambda: all(Z(sp.diff(g, x, 2) - 2 * al * sp.diff(g, x) + (al**2 + be**2) * g)
                                                                                  for g in (sp.exp(al * x) * sp.cos(be * x), sp.exp(al * x) * sp.sin(be * x))))],
    "ode2.trial": [("a가 특성근(q = −a² − pa)이면 L[e^{ax}] = 0, L[xe^{ax}] = (2a + p)e^{ax}", lambda: (lambda qq: Z(sp.diff(sp.exp(a * x), x, 2) + p * sp.diff(sp.exp(a * x), x) + qq * sp.exp(a * x))
        and Z(sp.diff(x * sp.exp(a * x), x, 2) + p * sp.diff(x * sp.exp(a * x), x) + qq * x * sp.exp(a * x) - (2 * a + p) * sp.exp(a * x)))(-a**2 - p * a))],
    "ode2.wronskian": [("W(e^{ax}, e^{bx}) = (b − a)e^{(a+b)x}", lambda: Z(sp.wronskian([sp.exp(a * x), sp.exp(b * x)], x) - (b - a) * sp.exp((a + b) * x)))],
    "ode2.varparam": [("u₁′ = −y₂R/W, u₂′ = y₁R/W 가 두 조건을 만족", lambda: (lambda y1, y2, R: (lambda W: Z(-y2 * R / W * y1 + y1 * R / W * y2)
        and Z(-y2 * R / W * sp.diff(y1, x) + y1 * R / W * sp.diff(y2, x) - R))(y1 * sp.diff(y2, x) - sp.diff(y1, x) * y2))(sp.Function("y1")(x), sp.Function("y2")(x), sp.Function("R")(x))),
                      ("예: y″ + y = x 에 공식 적용 → L[y_p] = x", lambda: (lambda yp: Z(sp.diff(yp, x, 2) + yp - x))(
                          -sp.cos(x) * sp.integrate(sp.sin(x) * x, x) + sp.sin(x) * sp.integrate(sp.cos(x) * x, x)))],
    "ode2.eulerform": [("x²(xʳ)″ + ax(xʳ)′ + bxʳ = (r(r − 1) + ar + b)xʳ", lambda: Z(x**2 * sp.diff(x**r, x, 2) + a * x * sp.diff(x**r, x) + b * x**r - (r * (r - 1) + a * r + b) * x**r))],
    "ode2.reduction": [("y = v y₁ 대입, L[y₁] = 0 ⇒ y₁v″ + (2y₁′ + py₁)v′", lambda: (lambda y1, V: Z(sp.expand(sp.diff(V * y1, x, 2) + p * sp.diff(V * y1, x) + q * V * y1
        - V * (sp.diff(y1, x, 2) + p * sp.diff(y1, x) + q * y1) - (y1 * sp.diff(V, x, 2) + (2 * sp.diff(y1, x) + p * y1) * sp.diff(V, x)))))(sp.Function("y1")(x), sp.Function("v")(x))),
                       ("v′ = e^{−∫p}/y₁² 가 그 1계식을 만족", lambda: (lambda y1, P: (lambda vp: Z(sp.simplify(y1 * sp.diff(vp, x) + (2 * sp.diff(y1, x) + P * y1) * vp)))(
                           sp.exp(-sp.Integral(P, x)) / y1**2))(sp.Function("y1")(x), sp.Function("p")(x))),
                       ("중근: y₁ = e^{rx}, p = −2r ⇒ v′ = 1", lambda: Z(sp.simplify(sp.exp(-sp.integrate(-2 * r, x)) / sp.exp(r * x) ** 2 - 1)))],
    "ode2.superpos": [("L 선형: L[y − y_p] = L[y] − L[y_p]", lambda: (lambda Y1, Y2: Z((sp.diff(Y1 - Y2, x, 2) + p * sp.diff(Y1 - Y2, x) + q * (Y1 - Y2))
        - ((sp.diff(Y1, x, 2) + p * sp.diff(Y1, x) + q * Y1) - (sp.diff(Y2, x, 2) + p * sp.diff(Y2, x) + q * Y2))))(f(x), sp.Function("g")(x)))],
    "ode2.const": [("C₁, C₂ 연립 (예: y″ − y = 0, y(0)=1, y′(0)=0 → cosh x)", lambda: (lambda sol: Z(sol[sp.Symbol("C1")] * sp.exp(x) + sol[sp.Symbol("C2")] * sp.exp(-x) - sp.cosh(x)))(
        sp.solve([sp.Symbol("C1") + sp.Symbol("C2") - 1, sp.Symbol("C1") - sp.Symbol("C2")], sp.symbols("C1 C2"))))],
    "ode2.undet": [("예: y″ − 3y′ + 2y = 4e^{3x}, y_p = Ae^{3x} → A = 2", lambda: (lambda A_: Z(sp.diff(A_ * sp.exp(3 * x), x, 2) - 3 * sp.diff(A_ * sp.exp(3 * x), x) + 2 * A_ * sp.exp(3 * x) - 4 * sp.exp(3 * x)))(2))],
    "ode2.euler": [("x = eᵗ: x dy/dx = dy/dt, x²y″ = ÿ − ẏ (예: Y = e³ᵗ + te⁻ᵗ)", lambda: (lambda tr, xp: (lambda Yt: (lambda yx: Z(sp.simplify((xp * sp.diff(yx, xp)).subs(xp, sp.exp(tr)) - sp.diff(Yt, tr)))
        and Z(sp.simplify((xp**2 * sp.diff(yx, xp, 2)).subs(xp, sp.exp(tr)) - (sp.diff(Yt, tr, 2) - sp.diff(Yt, tr)))))(Yt.subs(tr, sp.log(xp))))(sp.exp(3 * tr) + tr * sp.exp(-tr)))(
        sp.Symbol("t", real=True), sp.Symbol("x", positive=True))),
                   ("x = eᵗ 치환 결과 ÿ + (a − 1)ẏ + by = 0 의 해 eʳᵗ = xʳ (r(r−1) + ar + b = 0)", lambda: Z(sp.expand(r**2 + (a - 1) * r + b - (r * (r - 1) + a * r + b))))],
    # ---------------- 10장
    "lap.exp": [("∫₀^∞ e^{at}e^{−st} dt = 1/(s − a)", lambda: Z(L(sp.exp(a * t)) - 1 / (s - a)))],
    "lap.pow": [("ℒ{tⁿ} = (n/s)ℒ{tⁿ⁻¹}, ℒ{tⁿ} = n!/sⁿ⁺¹ (n = 1..5)", lambda: all(Z(L(t**m) - sp.Integer(m) / s * L(t ** (m - 1))) and Z(L(t**m) - sp.factorial(m) / s ** (m + 1)) for m in range(1, 6)))],
    "lap.sin": [("(1/2i)(1/(s − ib) − 1/(s + ib)) = b/(s² + b²)", lambda: Z((1 / (2 * sp.I)) * (1 / (s - sp.I * b) - 1 / (s + sp.I * b)) - b / (s**2 + b**2)))],
    "lap.cos": [("(1/2)(1/(s − ib) + 1/(s + ib)) = s/(s² + b²)", lambda: Z(sp.Rational(1, 2) * (1 / (s - sp.I * b) + 1 / (s + sp.I * b)) - s / (s**2 + b**2)))],
    "lap.sinh": [("(1/2)(1/(s − b) − 1/(s + b)) = b/(s² − b²)", lambda: Z(sp.Rational(1, 2) * (1 / (s - b) - 1 / (s + b)) - b / (s**2 - b**2)))],
    "lap.cosh": [("(1/2)(1/(s − b) + 1/(s + b)) = s/(s² − b²)", lambda: Z(sp.Rational(1, 2) * (1 / (s - b) + 1 / (s + b)) - s / (s**2 - b**2)))],
    "lap.texp": [("ℒ{teᵃᵗ} = 1/(s − a)²", lambda: Z(L(t * sp.exp(a * t)) - 1 / (s - a) ** 2))],
    "lap.expsin": [("ℒ{eᵃᵗ sin bt} = b/((s − a)² + b²)", lambda: Z(L(sp.exp(a * t) * sp.sin(be * t)) - be / ((s - a) ** 2 + be**2)))],
    "lap.expcos": [("ℒ{eᵃᵗ cos bt} = (s − a)/((s − a)² + b²)", lambda: Z(L(sp.exp(a * t) * sp.cos(be * t)) - (s - a) / ((s - a) ** 2 + be**2)))],
    "lap.tsin": [("−d/ds b/(s² + b²) = 2bs/(s² + b²)²", lambda: Z(-sp.diff(b / (s**2 + b**2), s) - 2 * b * s / (s**2 + b**2) ** 2)),
                 ("= ℒ{t sin bt}", lambda: Z(L(t * sp.sin(be * t)) - 2 * be * s / (s**2 + be**2) ** 2))],
    "lap.step": [("ℒ{u(t − c)} = e^{−cs}/s", lambda: Z(L(sp.Heaviside(t - cc)) - sp.exp(-cc * s) / s))],
    "lap.delta": [("ℒ{δ(t − c)} = e^{−cs}", lambda: Z(L(sp.DiracDelta(t - cc)) - sp.exp(-cc * s)))],
    "lap.deriv1": [("ℒ{y′} = sY − y(0) (예: y = e^{2t}cos t)", lambda: (lambda Y: Z(L(sp.diff(Y, t)) - (s * L(Y) - Y.subs(t, 0))))(sp.exp(2 * t) * sp.cos(t)))],
    "lap.deriv2": [("ℒ{y″} = s²Y − sy(0) − y′(0) (예)", lambda: (lambda Y: Z(L(sp.diff(Y, t, 2)) - (s**2 * L(Y) - s * Y.subs(t, 0) - sp.diff(Y, t).subs(t, 0))))(sp.exp(-t) * sp.sin(3 * t) + t**2))],
    # ---------------- M3.6 새 풀이 뼈대 (유도의 예를 그대로 확인)
    "ode.homog": [("y' = y/x + y²/x², y(1) = 1 → y = −x/(ln x − 1)", lambda: (lambda Y_: Z(sp.diff(Y_, x) - Y_ / x - Y_**2 / x**2) and Z(Y_.subs(x, 1) - 1))(-x / (sp.log(x) - 1)))],
    "ode.bernoulli.solve": [("y' + y = y², y(0) = 2 → y = −2/(eˣ − 2)", lambda: (lambda Y_: Z(sp.diff(Y_, x) + Y_ - Y_**2) and Z(Y_.subs(x, 0) - 2))(-2 / (sp.exp(x) - 2))),
                            ("v = y^{1−n}이면 v' + (1 − n)Pv = (1 − n)Q (일반 n)", lambda: (lambda Yf: Z(sp.diff(Yf**(1 - n_), x) + (1 - n_) * p * Yf**(1 - n_)
                                                                                           - (1 - n_) * Yf**(-n_) * (sp.diff(Yf, x) + p * Yf)))(f(x)))],
    "ode.intfactor": [("(2y + 3x)dx + x dy: μ = x로 완전, F = x²y + x³", lambda: (lambda M_, N_, mu: Z(sp.diff(mu * M_, y) - sp.diff(mu * N_, x)) and Z(sp.diff(x**2 * y + x**3, x) - mu * M_)
                                                                                                and Z(sp.diff(x**2 * y + x**3, y) - mu * N_) and Z((sp.diff(M_, y) - sp.diff(N_, x)) / N_ - 1 / x))(2 * y + 3 * x, x, x))],
    "ode2.varparam.solve": [("y'' + y = sec x → y_p = cos x ln|cos x| + x sin x", lambda: (lambda Yp: Z(sp.diff(Yp, x, 2) + Yp - 1 / sp.cos(x)))(sp.cos(x) * sp.log(sp.cos(x)) + x * sp.sin(x)))],
    "ode2.reduction.solve": [("x²y'' − xy' + y = 0, y₁ = x → y₂ = x ln x", lambda: (lambda Y_: Z(x**2 * sp.diff(Y_, x, 2) - x * sp.diff(Y_, x) + Y_))(x * sp.log(x))),
                             ("p = −1/x면 e^{−∫p} = x, v' = x/x² = 1/x", lambda: Z(sp.exp(-sp.integrate(-1 / x, x)) - x) and Z(x / x**2 - 1 / x))],
    "ode2.forced": [("y'' + 2y' + 5y = 10 cos t → y_p = 2 cos t + sin t", lambda: (lambda Yp: Z(sp.diff(Yp, t, 2) + 2 * sp.diff(Yp, t) + 5 * Yp - 10 * sp.cos(t)))(2 * sp.cos(t) + sp.sin(t))),
                    ("공명: y'' + ω²y = F cos ωt → y_p = F t sin ωt/(2ω)", lambda: (lambda Yp: Z(sp.diff(Yp, t, 2) + w**2 * Yp - a * sp.cos(w * t)))(a * t * sp.sin(w * t) / (2 * w)))],
    "lap.ivp.step": [("ℒ{u(t − c)} = e^{−cs}/s", lambda: Z(L(sp.Heaviside(t - cc)) - sp.exp(-cc * s) / s)),
                     ("y' + ay = Ku(t − c) → y = (K/a)u(t − c)(1 − e^{−a(t−c)})", lambda: (lambda A_, K_, c_: Z(L(sp.Heaviside(t - c_) * K_ / A_ * (1 - sp.exp(-A_ * (t - c_)))) - K_ * sp.exp(-c_ * s) / (s * (s + A_))))(2, 3, 1))],
    "lap.convsolve": [("∫₀ᵗ sin(t − τ)dτ = 1 − cos t, 그리고 y'' + y = 1 만족", lambda: (lambda T_: Z(sp.integrate(sp.sin(t - T_), (T_, 0, t)) - (1 - sp.cos(t)))
                                                                                    and Z(sp.diff(1 - sp.cos(t), t, 2) + 1 - sp.cos(t) - 1))(sp.Symbol("tau")))],
    "lap.system": [("x' = x + 2y, y' = 2x + y, x(0) = 1, y(0) = 0 → x = (e^{3t} + e^{−t})/2", lambda: (lambda X_, Y_: Z(sp.diff(X_, t) - X_ - 2 * Y_) and Z(sp.diff(Y_, t) - 2 * X_ - Y_)
                                                                                                      and Z(X_.subs(t, 0) - 1) and Z(Y_.subs(t, 0)))((sp.exp(3 * t) + sp.exp(-t)) / 2, (sp.exp(3 * t) - sp.exp(-t)) / 2))],
    "lap.volterra": [("y = 1 + ∫₀ᵗ (t − τ)y(τ)dτ → y = cosh t", lambda: (lambda T_: Z(sp.cosh(t) - 1 - sp.integrate((t - T_) * sp.cosh(T_), (T_, 0, t))))(sp.Symbol("tau")))],
    "lap.csqinv": [("(as + b)/((s − α)² + β²) = ℒ{e^{αt}(a cos βt + (b + aα)/β sin βt)}",
                    lambda: (lambda A_, B_, al_, b_: Z(L(sp.exp(al_ * t) * (A_ * sp.cos(b_ * t) + (B_ + A_ * al_) / b_ * sp.sin(b_ * t)))
                                                     - (A_ * s + B_) / ((s - al_) ** 2 + b_**2)))(2, 3, -1, 2))],
    "lap.sshift": [("ℒ{eᵃᵗf} = F(s − a) (예: f = t² + cos t)", lambda: (lambda F_: Z(L(sp.exp(a * t) * F_) - L(F_).subs(s, s - a)))(t**2 + sp.cos(t)))],
    "lap.tshift": [("ℒ{u(t − c)f(t − c)} = e^{−cs}F(s) (예: f = t e^{−t})", lambda: Z(L(sp.Heaviside(t - cc) * (t - cc) * sp.exp(-(t - cc))) - sp.exp(-cc * s) * L(t * sp.exp(-t))))],
    "lap.conv": [("ℒ{f*g} = FG (예: f = e^{−t}, g = sin t)", lambda: (lambda tau: Z(L(sp.integrate(sp.exp(-tau) * sp.sin(t - tau), (tau, 0, t))) - L(sp.exp(-t)) * L(sp.sin(t))))(sp.Symbol("tau")))],
    "lap.tmult": [("F′(s) = −ℒ{tf} (예: f = e^{−2t}cos t)", lambda: (lambda F_: Z(sp.diff(L(F_), s) + L(t * F_)))(sp.exp(-2 * t) * sp.cos(t)))],
    "lap.integral": [("ℒ{∫₀ᵗ f} = F/s (예: f = t e^{t})", lambda: (lambda tau: Z(L(sp.integrate((tau * sp.exp(tau)), (tau, 0, t))) - L(t * sp.exp(t)) / s))(sp.Symbol("tau")))],
    "lap.ivp1": [("sY − y₀ + aY = Q ⇒ Y = (y₀ + Q)/(s + a)", lambda: (lambda Q, Y_, y0: Z(sp.solve(s * Y_ - y0 + a * Y_ - Q, Y_)[0] - (y0 + Q) / (s + a)))(*sp.symbols("Q Y y0")))],
    "lap.ivp2.real": [("s²Y − sy₀ − v₀ + p(sY − y₀) + qY = 0 ⇒ Y = (y₀s + v₀ + py₀)/(s² + ps + q)", lambda: (lambda Y_, y0, v0: Z(sp.solve(s**2 * Y_ - s * y0 - v0 + p * (s * Y_ - y0) + q * Y_, Y_)[0]
        - (y0 * s + v0 + p * y0) / (s**2 + p * s + q)))(*sp.symbols("Y y0 v0"))),
                      ("덮개법 A = N(r₁)/(r₁ − r₂) (예: (2s + 9)/((s + 1)(s + 2)))", lambda: Z(sp.apart((2 * s + 9) / ((s + 1) * (s + 2)), s) - (7 / (s + 1) - 5 / (s + 2))))],
    "lap.ivp2.repeated": [("p = −2r: y₀s + v₀ + py₀ = y₀(s − r) + K, K = v₀ − ry₀", lambda: (lambda y0, v0: Z(y0 * s + v0 - 2 * r * y0 - (y0 * (s - r) + (v0 - r * y0))))(*sp.symbols("y0 v0"))),
                          ("ℒ⁻¹{1/(s − r)²} = teʳᵗ", lambda: Z(L(t * sp.exp(r * t)) - 1 / (s - r) ** 2))],
    "lap.ivp2.complex": [("ℒ⁻¹{A(s − α)/((s − α)² + β²) + (C/β)·β/((s − α)² + β²)} = e^{αt}(A cos βt + (C/β) sin βt)", lambda: (lambda A_, C_: Z(
        L(sp.exp(al * t) * (A_ * sp.cos(be * t) + C_ / be * sp.sin(be * t))) - (A_ * (s - al) + C_) / ((s - al) ** 2 + be**2)))(*sp.symbols("A C")))],
    "lap.ivp2.impulse": [("변환 후 Y = (sy₀ + v₀)/(s² + ω²) + e^{−cs}/(s² + ω²)", lambda: (lambda Y_, y0, v0: Z(sp.solve(s**2 * Y_ - s * y0 - v0 + w**2 * Y_ - sp.exp(-cc * s), Y_)[0]
        - ((s * y0 + v0) / (s**2 + w**2) + sp.exp(-cc * s) / (s**2 + w**2))))(*sp.symbols("Y y0 v0"))),
                         ("ℒ{u(t − c) sin ω(t − c)/ω} = e^{−cs}/(s² + ω²)", lambda: Z(L(sp.Heaviside(t - cc) * sp.sin(w * (t - cc)) / w) - sp.exp(-cc * s) / (s**2 + w**2)))],
}

CONCEPT = {
    "la.rank": "수식 주장 없음 (행 연산과 계수의 관계를 말로 설명)",
}


def main():
    units = []
    for fpath in sorted(glob.glob("content/ch*/derivations.yaml")):
        units += list((yaml.safe_load(open(fpath, encoding="utf-8")) or {}).keys())
    fails, passed, n = [], 0, 0
    for uid in units:
        if uid in CONCEPT:
            print(f"  개념  {uid}: {CONCEPT[uid]}")
            continue
        if uid not in CHECKS:
            fails.append(f"{uid}: 검사 없음")
            continue
        for desc, fn in CHECKS[uid]:
            n += 1
            try:
                ok = bool(fn())
            except Exception as e:  # noqa: BLE001
                ok = False
                desc += f"  [오류 {type(e).__name__}: {str(e)[:80]}]"
            if ok:
                passed += 1
            else:
                fails.append(f"{uid}: {desc}")
            print(f"  {'통과' if ok else '실패'}  {uid}: {desc}")
    print(f"\n단위 {len(units)}개, 검사 {n}개 중 {passed}개 통과, 개념 설명만 있는 단위 {len(CONCEPT)}개")
    if fails:
        print("\n실패:\n" + "\n".join(fails))
        sys.exit(1)


if __name__ == "__main__":
    main()
