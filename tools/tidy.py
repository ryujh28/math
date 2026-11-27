"""마지막 표기 다듬기: 생성기가 기계적으로 끼워 넣어 생긴 군더더기를 걷어낸다.

검증은 SymPy 식으로 끝났으므로 여기서는 화면에 보이는 TeX만 바꾼다. 바꾸는 것은 뜻이 같은 것뿐이다.
    y^{1} → y        e^{0}·(…) → (…)      + 0r → (지움)
    \\frac{2}{1} → 2   -1\\mathbf{v} → -\\mathbf{v}   - 1\\left( → - \\left(
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES = [
    (re.compile(r"(?<=[a-zA-Z])\^\{1\}"), ""),
    (re.compile(r"\)\s*e\^\{0\}"), ")"),
    (re.compile(r"e\^\{0\}"), "1"),
    (re.compile(r"\s*\+\s*0\s?([a-z])(?![\w{^])"), ""),
    (re.compile(r"\\frac\{(-?\d+)\}\{1\}"), r"\1"),
    (re.compile(r"(?<![\d.])(-?)1\s*\\mathbf"), r"\1\\mathbf"),
    (re.compile(r"([+-]\s*)1\s*\\left\("), r"\1\\left("),
]


def tidy(s):
    if not isinstance(s, str):
        return s
    for pat, rep in RULES:
        s = pat.sub(rep, s)
    return s


def _item(it):
    for k in ("prompt", "answer", "problem"):
        if k in it:
            it[k] = tidy(it[k])
    for w in it.get("wrong", []):
        w["tex"] = tidy(w["tex"])
    if "steps" in it:
        it["steps"] = [tidy(x) if isinstance(x, str) else {**x, "tex": tidy(x.get("tex"))} for x in it["steps"]]
    for d in it.get("decoys", []):
        d["tex"] = tidy(d["tex"])
    if it.get("explain"):
        it["explain"] = [tidy(x) for x in it["explain"]]


def apply(cid):
    pp = ROOT / "packs" / f"ch{cid:02d}.json"
    pack = json.loads(pp.read_text())
    for it in pack["items"]:
        _item(it)
    pp.write_text(json.dumps(pack, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    for t, want in [("v' = 2y^{1}y'", "v' = 2yy'"), ("(-2 - 2)e^{0} = -4", "(-2 - 2) = -4"), ("r(r - 1) + 0r + \\left(-2\\right)", "r(r - 1) + \\left(-2\\right)"),
                    ("\\mathbf{v}_2 - \\frac{2}{1}\\mathbf{u}_1", "\\mathbf{v}_2 - 2\\mathbf{u}_1"), ("= -1\\mathbf{v}", "= -\\mathbf{v}"),
                    ("x^{10} + 10\\mathbf{v}", "x^{10} + 10\\mathbf{v}"), ("- 1\\left(-1,\\ 0\\right)", "- \\left(-1,\\ 0\\right)"), ("x + 0", "x + 0")]:
        assert tidy(t) == want, (t, tidy(t))
    print("tidy ok")
