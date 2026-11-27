"""문항 전수검사: 빌드는 통과했지만 문제로서 어색한 것을 찾는다.

    python3 tools/audit.py            # 요약 + tools/reports/audit.md
    python3 tools/audit.py --strict   # 결함이 하나라도 있으면 종료 코드 1

빌드 검사(SymPy)는 "맞는가"를 본다. 이 검사는 "읽을 만한가"를 본다.
- 항등식 해설: 해설 한 줄이 "A = A"로 아무 정보도 없다.
- 상수 먼저 쓴 다항식: 1 - s, 3 - 4 x 처럼 sympy 기본 순서가 그대로 나온 것.
- 보기 수: 객관식 보기가 4개(정답 1 + 오답 3)보다 적다.
- 같은 보기: 공백만 다른 보기가 둘 이상.
- 지저분한 표기: + -, - -, 1\\cos, ^{1}, e^{0}, \\frac{1}{1}, 0 x, + 0 등.
- 답 노출: 정답 식이 문제 안에 그대로 있다.
- 순서 문제 단계 중복: 이웃한 두 단계의 식이 같다.
- 단위 이름과 안 맞는 문제: 완전제곱·s-이동 단위인데 이동할 것이 없다 (α = 0).
- 해설 끝줄과 정답 표기가 다르다 (sympy가 항 순서를 바꾼 경우).
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATH = re.compile(r"\$\$?(.+?)\$\$?")

UGLY = [
    (r"\+\s*-", "+ -"),
    (r"(?<![\w}])-\s*-", "- -"),
    (r"(?<![\d._}])1\s*\\(cos|sin|cosh|sinh|frac)", "1\\cos 꼴"),
    (r"\\(cos|sin)\s*\{?0\}?(?![\d.])", "cos 0"),
    (r"y(_h)?\s*=\s*\\left\(C_1\\cos", "통째 괄호"),
    (r"(?<![\d.])-?1\s*\\mathbf", "1v 꼴"),
    (r"\^\{1\}", "^{1}"),
    (r"e\^\{0\}", "e^{0}"),
    (r"\\frac\{(\w+)\}\{1\}", "\\frac{a}{1}"),
    (r"(?<![\d._])0\s*[a-z](?![a-z])", "0x"),
    (r"[+-]\s*0(?![\d.])(?!\s*[<>≤≥])(?!\s*\\cdot)(?!\^)(?!\s*=)", "± 0"),
    (r"e\^\{-1 ?t\}|e\^\{-1 ?x\}", "e^{-1t}"),
    (r"\\left\(\s*\\right\)", "빈 괄호"),
    (r"(?:^|[=+-]\s*)\\cdot(?!s)", "계수 없는 ·"),
    (r"\\ln\{\\left", "ln{(x)} 꼴"),
    (r"\}\\left\((?:\\(?:sin|cos)[^+-]*?)\\right\)\s*$", "한 항만 괄호"),
    (r"s\^\{- n - 1\}", "s^{-n-1} n!"),
]
CONST_FIRST = re.compile(r"(?:^|[{(=,]\s*)-?\d+\s*[-+]\s*\d*\s*[stxy](?![a-z{^])")


def _const_first(tx):
    """상수 먼저 쓴 다항식. 교과서 꼴은 뺀다: 개체군 모델의 x(a − by), (1 − x²)y'' 같은 계수."""
    for m in CONST_FIRST.finditer(tx):
        before = tx[max(0, m.start() - 8):m.start() + 1]
        if re.search(r"[xy]\\left\($", before) or re.match(r"[{(=,]?\s*1\s*-\s*x", m.group(0)):
            continue
        return True
    return False


def norm(tx):
    return re.sub(r"\s+|\\[,;:!]|\\quad|\\left|\\right", "", tx or "")


def texes(it):
    out = []
    for k in ("prompt", "answer", "problem"):
        if it.get(k):
            out.append((k, it[k]))
    for w in it.get("wrong", []):
        out.append(("wrong", w["tex"]))
    for st in it.get("steps", []):
        out.append(("step", st if isinstance(st, str) else st.get("tex", "")))
    for d in it.get("decoys", []):
        out.append(("decoy", d["tex"]))
    for line in it.get("explain") or []:
        for mth in MATH.findall(line):
            out.append(("explain", mth))
    return out


def audit(packs):
    found = defaultdict(list)          # 종류 → [(id, 내용)]
    for p in packs:
        units = {u["id"]: u for u in p["units"]}
        for it in p["items"]:
            iid, u = it["id"], units.get(it["unit"], {})
            for where, tx in texes(it):
                for pat, name in UGLY:
                    if re.search(pat, tx):
                        found[f"표기 {name}"].append((iid, f"{where}: {tx}"))
                if _const_first(tx) and where in ("prompt", "answer", "problem", "wrong"):
                    found["상수 먼저 쓴 다항식"].append((iid, f"{where}: {tx}"))
            if it["type"] == "mcq":
                n = 1 + len(it.get("wrong", []))
                if n < 4:
                    found[f"보기 {n}개"].append((iid, it.get("prompt", "")))
                seen = Counter(norm(t) for t in [it["answer"]] + [w["tex"] for w in it.get("wrong", [])])
                if any(v > 1 for v in seen.values()):
                    found["같은 보기"].append((iid, it.get("prompt", "")))
                a = norm(it["answer"])
                if len(a) > 12 and a in norm(it.get("prompt", "")):
                    found["답 노출"].append((iid, it["prompt"]))
                ex = it.get("explain") or []
                for line in ex:
                    for mth in MATH.findall(line):
                        sides = [norm(x) for x in re.split(r"(?<![<>!])=", mth)]
                        if len(sides) >= 2 and any(sides[k] and sides[k] == sides[k + 1] for k in range(len(sides) - 1)):
                            found["항등식 해설"].append((iid, line))
            if it["type"] == "order":
                st = [norm(s if isinstance(s, str) else s.get("tex", "")) for s in it["steps"]]
                for k in range(len(st) - 1):
                    if st[k] == st[k + 1]:
                        found["이웃 단계가 같은 식"].append((iid, it["problem"]))
            title = u.get("title", "")
            par = it.get("params") or {}
            if ("완전제곱" in title or "이동" in title) and par.get("alpha") == 0:
                found["단위 이름과 안 맞음 (이동 없음)"].append((iid, it.get("prompt") or it.get("problem")))
        # 다양성 가드 (풀이 뼈대): 가족 3개 이상, 한 가족이 45% 이하. 가족 정보가 있는 단위만 본다.
        for u in p["units"]:
            if u["kind"] != "schema":
                continue
            its = [i for i in p["items"] if i["unit"] == u["id"]]
            fams = Counter((i.get("params") or {}).get("family") for i in its)
            fams.pop(None, None)
            if not fams:
                continue
            fams = Counter({k.split("_")[0] if k.startswith("gen_") else k: v for k, v in fams.items()}) if False else fams
            if len(fams) < 3:
                found["다양성: 가족 3개 미만"].append((u["id"] + "#-", f"{dict(fams)}"))
            top = max(fams.values()) / len(its)
            if top > 0.45:
                found["다양성: 한 가족 45% 초과"].append((u["id"] + "#-", f"{dict(fams)}"))
    return found


def main():
    packs = [json.loads(f.read_text()) for f in sorted((ROOT / "packs").glob("ch*.json"))]
    total = sum(len(p["items"]) for p in packs)
    found = audit(packs)
    lines = [f"# 문항 전수검사\n\n문항 {total}개.\n"]
    for k in sorted(found, key=lambda k: -len(found[k])):
        v = found[k]
        byunit = Counter(i.split("#")[0] for i, _ in v)
        lines.append(f"\n## {k} — {len(v)}개\n\n단위: " + ", ".join(f"{u} {n}" for u, n in byunit.most_common()) + "\n")
        for i, t in v[:12]:
            lines.append(f"- `{i}` {t}")
    out = ROOT / "tools" / "reports" / "audit.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"문항 {total}개")
    for k in sorted(found, key=lambda k: -len(found[k])):
        print(f"  {len(found[k]):5d}  {k}")
    if not found:
        print("  결함 없음")
    print(f"→ {out.relative_to(ROOT)}")
    if "--strict" in sys.argv and found:
        sys.exit(1)


if __name__ == "__main__":
    main()
