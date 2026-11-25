"""문제별 해설을 팩에 붙인다.

각 장의 templates/exN.py 에 EXPLAIN = {단위 id: 함수} 를 둔다.
함수는 (P, item) 을 받는다. P는 생성기 params를 SymPy로 되살린 것, item은 팩의 문제.
돌려주는 값: 해설 줄 목록, 또는 (줄 목록, 검사 목록).
  - 줄: 문장($…$ 안은 TeX) 또는 $$…$$ 수식 블록
  - 검사: (a, b) 쌍. SymPy로 a == b 인지 확인한다. 하나라도 틀리면 그 문제의 해설은 버리고 보고서에 남긴다.
해설이 없는 문제는 앱에서 단위의 핵심(hint)과 유도로 대신한다.

사용: python3 tools/explain.py [장 번호 ...]   (빌드 없이 팩에만 다시 붙인다)
"""
import importlib
import json
import sys
from pathlib import Path

import sympy as sp

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from checks import same  # noqa: E402

LOCALS = {k: sp.Symbol(k) for k in "xyzrst"}
LOCALS.update(E=sp.E, I=sp.I, pi=sp.pi, Matrix=sp.Matrix)


def revive(v):
    """build._jp 로 문자열이 된 params 를 SymPy 값으로."""
    if isinstance(v, dict):
        return {k: revive(x) for k, x in v.items()}
    if isinstance(v, list):
        return [revive(x) for x in v]
    if isinstance(v, str):
        try:
            return sp.sympify(v, locals=LOCALS)
        except (sp.SympifyError, TypeError, SyntaxError):
            return v
    if isinstance(v, int) and not isinstance(v, bool):
        return sp.Integer(v)
    return v


def _check(a, b):
    try:
        if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
            return all(_check(x, y) for x, y in zip(a, b)) and len(a) == len(b)
        return bool(same(a, b))
    except Exception:  # noqa: BLE001
        return False


def registry(chdir):
    tdir = chdir / "templates"
    mods = sorted(tdir.glob("ex*.py"))
    reg = {}
    if not mods:
        return reg
    if str(tdir) not in sys.path:
        sys.path.insert(0, str(tdir))
    for m in mods:
        reg.update(getattr(importlib.import_module(m.stem), "EXPLAIN", {}))
    return reg


def apply(cid, report=None):
    chdir = next(d for d in (ROOT / "content").iterdir() if d.is_dir() and d.name.startswith(f"ch{cid:02d}"))
    pp = ROOT / "packs" / f"ch{cid:02d}.json"
    pack = json.loads(pp.read_text())
    reg = registry(chdir)
    report = report if report is not None else []
    added = failed = 0
    for it in pack["items"]:
        fn = reg.get(it["unit"])
        if it["type"] != "mcq" or not fn or "params" not in it:
            continue
        try:
            out = fn(revive(it["params"]), it)
        except Exception as e:  # noqa: BLE001
            report.append(f"- 해설 오류 {it['id']}: {e!r}"[:300])
            it.pop("explain", None)
            failed += 1
            continue
        lines, checks = out if isinstance(out, tuple) else (out, [])
        bad = [k for k, (a, b) in enumerate(checks) if not _check(a, b)]
        if bad:
            report.append(f"- 해설 검사 실패 {it['id']}: {bad}")
            it.pop("explain", None)
            failed += 1
            continue
        it["explain"] = [str(x) for x in lines]
        added += 1
    pp.write_text(json.dumps(pack, ensure_ascii=False, separators=(",", ":")))
    mcq = sum(1 for it in pack["items"] if it["type"] == "mcq")
    have = sum(1 for it in pack["items"] if it["type"] == "mcq" and it.get("explain"))
    print(f"ch{cid:02d} 해설: 새로 {added}, 실패 {failed}, 객관식 {mcq}개 중 {have}개에 해설")
    return report


if __name__ == "__main__":
    ids = [int(a) for a in sys.argv[1:]] or sorted(int(p.stem[2:]) for p in (ROOT / "packs").glob("ch*.json"))
    rep = []
    for c in ids:
        apply(c, rep)
    if rep:
        print("\n".join(rep[:60]))
        if len(rep) > 60:
            print(f"… 외 {len(rep) - 60}건")
