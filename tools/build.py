#!/usr/bin/env python3
"""콘텐츠 원본(content/) → 검증된 팩(packs/*.json).

사용법:  python3 tools/build.py            # 모든 장
         python3 tools/build.py 10 6       # 지정한 장만

검증 (생성기와 독립적인 경로로 확인한다):
  - 변환쌍 원자: F(s₀) ≈ ∫₀^∞ f(t)e^{−s₀t}dt 를 수치적분으로 확인
  - 오답 보기:   정답과 여러 표본점에서 값이 달라야 통과
  - 풀이 뼈대:   해 y가 미분방정식·초기조건을 만족하는지 수치로 확인,
                 Y_ref(s₀) ≈ ∫ y e^{−s₀t}dt 확인,
                 각 단계가 Y_ref 또는 y와 같은지, 각 오답 블록은 달라야 통과
실패한 사례는 팩에서 빼고 tools/reports/chNN.md에 남긴다.
"""
import datetime
import importlib
import itertools
import json
import math
import random
import sys
from pathlib import Path

import sympy as sp
import yaml
from scipy.integrate import quad

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from texkit import t, s, Y, tex  # noqa: E402

FORMAT = 0
MAX_PER_TIER = 30          # 뼈대·단계별 사례 상한 (부족하면 Claude에게 더 생성 요청)
S_PTS = [6.5, 8.25, 11.0]  # 모든 극점보다 오른쪽
T_PTS = [0.37, 1.13, 1.71, 2.59, 3.83]  # 정수가 아닌 t (계단함수 불연속점 회피)
NS = {"t": t, "s": s, "Heaviside": sp.Heaviside, "DiracDelta": sp.DiracDelta}


# ------------------------------------------------------------------ 수치 비교
def num(e, var, x):
    v = complex(sp.sympify(e).subs(var, x).evalf(30))
    return v


def same(a, b, var, pts):
    for x in pts:
        va, vb = num(a, var, x), num(b, var, x)
        if not (math.isfinite(abs(va)) and math.isfinite(abs(vb))):
            return False
        if abs(va - vb) > 1e-8 * max(abs(va), abs(vb)) + 1e-15:
            return False
    return True


def laplace_num(f, s0):
    """∫₀^∞ f(t)e^{−s₀t}dt. δ 함수 항은 해석적으로 처리."""
    f = sp.expand(sp.sympify(f))
    total = 0.0
    rest = 0
    for term in sp.Add.make_args(f):
        if term.has(sp.DiracDelta):
            d = [a for a in term.atoms(sp.DiracDelta)][0]
            c = sp.solve(d.args[0], t)[0]
            coeff = term / d
            total += float((coeff * sp.exp(-s0 * t)).subs(t, c)) if c >= 0 else 0.0
        else:
            rest += term
    if rest != 0:
        g = sp.lambdify(t, rest * sp.exp(-s0 * t), modules=[{"Heaviside": lambda x, h=0.5: 1.0 * (x > 0)}, "numpy"])
        brk = sorted({float(h.args[0].subs(t, 0)) * -1 for h in sp.sympify(rest).atoms(sp.Heaviside)})
        pts = [p for p in brk if p > 0] or None
        val, _ = quad(lambda x: float(g(x)), 0, 60, points=pts, limit=400, epsabs=1e-15, epsrel=1e-11)
        total += val
    return total


def laplace_same(f, F, s_pts=S_PTS):
    for s0 in s_pts:
        a, b = laplace_num(f, s0), float(sp.sympify(F).subs(s, s0))
        if abs(a - b) > 1e-6 * max(abs(a), abs(b)) + 1e-13:
            return False
    return True


def solve_Y(expr):
    expr = sp.expand(expr)
    A = expr.coeff(Y)
    return -(expr - A * Y) / A


# ------------------------------------------------------------------ 원자
def _closure_risk(fn):
    """생성기 파일 안에서 만든 판정 함수가 바깥 변수를 늦게 묶으면(late binding) 위험.
    기본 인자로 값을 묶지 않은 자유 변수가 있으면 True."""
    code = getattr(fn, "__code__", None)
    if code is None or "templates" not in code.co_filename:
        return False
    return bool(code.co_freevars)


FLOAT = __import__("re").compile(r"\d\.\d{4,}")


def _has_float(*texs):
    return any(FLOAT.search(t or "") for t in texs)


def _safe(fn):
    if _closure_risk(fn):
        return None
    try:
        return bool(fn())
    except Exception as e:  # 판정 중 오류 = 확인 불가
        return None


def _gen_items(a, uid, gen_ref, report, seed, start):
    """생성기 사례들을 검증해 객관식 문제로. 정답 ok() == True, 오답 ok() == False만 남긴다."""
    mod_name, fn = gen_ref.split(":")
    cases = getattr(importlib.import_module(mod_name), fn)()
    rng = random.Random(f"{seed}:{uid}")
    rng.shuffle(cases)
    per_tier, items, tiers, n = {}, [], set(), start
    for c in cases:
        tr = c.get("tier", a.get("tier", 1))
        if per_tier.get(tr, 0) >= MAX_PER_TIER:
            continue
        tag = f"{uid} {c.get('params', {})}"
        if _has_float(c["prompt"], c["answer"]["tex"], *[w["tex"] for w in c["wrong"]]):
            report.append(f"- 실패 {tag}: TeX에 소수점 근삿값이 섞임")
            continue
        if _safe(c["answer"]["ok"]) is not True:
            report.append(f"- 실패 {tag}: 정답 보기가 판정을 통과하지 못함")
            continue
        wr = []
        for w in c["wrong"]:
            v = _safe(w["ok"])
            if v is None:
                report.append(f"- 오답 제외 {tag}: 판정 오류")
                continue
            if v or w["tex"] == c["answer"]["tex"] or any(w["tex"] == q["tex"] for q in wr):
                continue
            wr.append({"tex": w["tex"], "error": w["error"]})
        if len(wr) < 3:
            report.append(f"- 제외 {tag}: 유효한 오답 {len(wr)}개")
            continue
        if any(it["prompt"] == c["prompt"] and it["answer"] == c["answer"]["tex"] for it in items):
            continue  # 같은 문제·같은 정답이면 중복
        items.append({"id": f"{uid}#{n}", "unit": uid, "type": "mcq", "tier": tr, "dir": c.get("dir", "fwd"),
                      "prompt": c["prompt"], "answer": c["answer"]["tex"], "wrong": wr})
        n += 1
        tiers.add(tr)
        per_tier[tr] = per_tier.get(tr, 0) + 1
    return items, tiers


def build_atoms(atoms, report, tdir=None, seed="v0"):
    if tdir is not None:
        sys.path.insert(0, str(tdir))
    units, items = [], []
    for a in atoms:
        uid = a["id"]
        tiers = set()
        n = 0
        if a["kind"] == "gen":
            got, tiers_g = _gen_items(a, uid, a["generator"], report, seed, 0)
            items += got
            tiers |= tiers_g
            n = len(got)
        elif a["kind"] == "formula":
            # 추상 공식 문제 + 손으로 쓴 변형(variants) + 구체적 적용 문제 생성기(generator)
            for v in [a] + a.get("variants", []):
                wrong = [{"tex": w["tex"], "error": w["error"]} for w in v["wrong"]]
                items.append({"id": f"{uid}#{n}", "unit": uid, "type": "mcq", "tier": v.get("tier", a["tier"]), "dir": "fwd",
                              "prompt": v["prompt"], "answer": v["answer"], "wrong": wrong, "verified": "hand"})
                tiers.add(v.get("tier", a["tier"]))
                n += 1
            if a.get("generator"):
                got, tiers_g = _gen_items(a, uid, a["generator"], report, seed, n)
                items += got
                tiers |= tiers_g
                n += len(got)
        else:
            keys = list(a["params"])
            for combo in itertools.product(*[a["params"][k] for k in keys]):
                env = dict(NS, **{k: sp.Integer(v) for k, v in zip(keys, combo)})
                f = sp.sympify(a["f"], locals=env)
                F = sp.sympify(a["F"], locals=env)
                tag = f"{uid} {dict(zip(keys, combo))}"
                if not laplace_same(f, F):
                    report.append(f"- 실패 {tag}: ℒ{{f}} ≠ F")
                    continue
                # 정변환 문제
                wr = []
                for w in a.get("wrong_F", []):
                    Fw = sp.sympify(w["F"], locals=env)
                    if same(Fw, F, s, S_PTS) or any(x["tex"] == tex(Fw) for x in wr) or tex(Fw) == tex(F):
                        continue
                    wr.append({"tex": tex(Fw), "error": w["error"]})
                if len(wr) >= 3:
                    items.append({"id": f"{uid}#{n}", "unit": uid, "type": "mcq", "tier": a["tier"], "dir": "fwd",
                                  "prompt": r"\mathcal{L}\left\{" + tex(f) + r"\right\}", "answer": tex(F), "wrong": wr})
                    n += 1
                    tiers.add(a["tier"])
                else:
                    report.append(f"- 제외 {tag} 정변환: 유효한 오답 {len(wr)}개")
                # 역변환 문제
                wr = []
                for w in a.get("wrong_f", []):
                    fw = sp.sympify(w["f"], locals=env)
                    if laplace_same(fw, F) or any(x["tex"] == tex(fw) for x in wr):
                        continue
                    wr.append({"tex": tex(fw), "error": w["error"]})
                if len(wr) >= 3:
                    items.append({"id": f"{uid}#{n}", "unit": uid, "type": "mcq", "tier": a["inverse_tier"], "dir": "inv",
                                  "prompt": r"\mathcal{L}^{-1}\left\{" + tex(F) + r"\right\}", "answer": tex(f), "wrong": wr})
                    n += 1
                    tiers.add(a["inverse_tier"])
                else:
                    report.append(f"- 제외 {tag} 역변환: 유효한 오답 {len(wr)}개")
        if a.get("pace") and a["pace"] not in ("light", "compute", "heavy", "epic"):
            raise SystemExit(f"{uid}: pace는 light·compute·heavy·epic 중 하나 (없으면 기억형)")
        units.append({"id": uid, "kind": "atom", "title": a["title"], "hint": a.get("hint", ""), "tiers": sorted(tiers),
                      **({"pace": a["pace"]} if a.get("pace") else {})})
    return units, items


# ------------------------------------------------------------------ 풀이 뼈대
def check_solution(v):
    """해 y가 방정식·초기조건을 만족하는지 수치로 확인."""
    y = sp.sympify(v["y"])
    co = v["coeffs"]
    ders = [y, sp.diff(y, t), sp.diff(y, t, 2)]
    order = len(co)
    lhs = ders[order] + sum(c * ders[order - 1 - i] for i, c in enumerate(co))
    resid = lhs - v["rhs"]
    for x in T_PTS:
        r = num(resid.subs(sp.DiracDelta(t - v.get("impulse", -99)), 0), t, x)
        if abs(r) > 1e-8:
            return "방정식 불만족"
    for k, val in enumerate(v["ics"]):
        if abs(num(ders[k], t, 0) - val) > 1e-9:
            return f"초기조건 {k} 불만족"
    if v.get("impulse") is not None:
        c = v["impulse"]
        d1 = sp.diff(y, t).subs(sp.DiracDelta(t - c), 0)
        jump = num(d1, t, c + 1e-9) - num(d1, t, c - 1e-9)
        cont = num(y, t, c + 1e-9) - num(y, t, c - 1e-9)
        if abs(jump - 1) > 1e-6 or abs(cont) > 1e-6:
            return "충격 조건(y′ 도약 1, y 연속) 불만족"
    return None


def Y_reference(v):
    """도함수 변환 공식으로 만든 Y. 수치 Laplace 적분으로 따로 확인한다."""
    co, ics = v["coeffs"], v["ics"]
    y = sp.sympify(v["y"])
    rhs = sp.sympify(v["rhs"])
    R = sp.laplace_transform(rhs, t, s, noconds=True) if rhs != 0 else 0
    if v.get("impulse") is not None:
        R += sp.exp(-v["impulse"] * s)
    if len(co) == 1:
        Yr = (ics[0] + R) / (s + co[0])
    else:
        p, q = co
        Yr = (s * ics[0] + ics[1] + p * ics[0] + R) / (s**2 + p * s + q)
    if not laplace_same(y, Yr):   # 수치 적분으로 독립 확인
        return None
    return Yr


def build_schemas(schemas, tdir, report, seed):
    sys.path.insert(0, str(tdir))
    units, items = [], []
    for sc in schemas:
        mod_name, fn = sc["generator"].split(":")
        mod = importlib.import_module(mod_name)
        cases = getattr(mod, fn)()
        rng = random.Random(f"{seed}:{sc['id']}")
        by_tier = {}
        for c in cases:
            by_tier.setdefault(c["tier"], []).append(c)
        n = 0
        tiers = set()
        for tier, lst in sorted(by_tier.items()):
            rng.shuffle(lst)
            kept = 0
            for c in lst:
                if kept >= MAX_PER_TIER:
                    break
                tag = f"{sc['id']} {c['params']}"
                if "ok" in c["steps"][0]:
                    it = _generic_schema_item(c, tag, report)
                    if it:
                        items.append({"id": f"{sc['id']}#{n}", "unit": sc["id"], "type": "order", "tier": tier, **it})
                        n += 1
                        kept += 1
                        tiers.add(tier)
                    continue
                err = check_solution(c["verify"])
                if err:
                    report.append(f"- 실패 {tag}: {err}")
                    continue
                y = sp.sympify(c["verify"]["y"])
                Yr = Y_reference(c["verify"])
                if Yr is None:
                    report.append(f"- 실패 {tag}: Y 기준값 불일치")
                    continue
                ok = True
                for i, st in enumerate(c["steps"]):
                    if not _matches(st, Yr, y):
                        report.append(f"- 실패 {tag}: {i + 1}단계 불일치 ({st['kind']})")
                        ok = False
                        break
                texs = [st["tex"] for st in c["steps"]]
                if ok and len(set(texs)) != len(texs):
                    report.append(f"- 실패 {tag}: 같은 단계 TeX 중복")
                    ok = False
                if not ok:
                    continue
                dec = []
                for d in c["decoys"]:
                    if d["tex"] in texs or any(d["tex"] == x["tex"] for x in dec):
                        continue
                    if _matches(d, Yr, y):
                        report.append(f"- 오답 제외 {tag}: '{d['error']}' 블록이 실제로는 정답과 같음")
                        continue
                    dec.append({"tex": d["tex"], "error": d["error"], "why": d["why"], "pos": d["pos"]})
                if len(dec) < 2:
                    report.append(f"- 제외 {tag}: 유효한 오답 블록 {len(dec)}개")
                    continue
                items.append({"id": f"{sc['id']}#{n}", "unit": sc["id"], "type": "order", "tier": tier,
                              "problem": c["problem"], "steps": texs, "decoys": dec})
                n += 1
                kept += 1
                tiers.add(tier)
        units.append({"id": sc["id"], "kind": "schema", "title": sc["title"], "hint": sc.get("hint", ""),
                      "steps": sc.get("steps", []), "tiers": sorted(tiers)})
    return units, items


def _generic_schema_item(c, tag, report):
    v = c.get("verify")
    if v is not None:
        try:
            err = v()
        except Exception as e:
            err = f"검증 오류 {e!r}"[:120]
        if err:
            report.append(f"- 실패 {tag}: {err}")
            return None
    for i, st in enumerate(c["steps"]):
        if _safe(st["ok"]) is not True:
            report.append(f"- 실패 {tag}: {i + 1}단계 판정 실패")
            return None
    texs = [st["tex"] for st in c["steps"]]
    if len(set(texs)) != len(texs):
        report.append(f"- 실패 {tag}: 같은 단계 TeX 중복")
        return None
    if _has_float(c["problem"], *texs):
        report.append(f"- 실패 {tag}: TeX에 소수점 근삿값이 섞임")
        return None
    dec = []
    for d in c["decoys"]:
        if d["tex"] in texs or any(d["tex"] == q["tex"] for q in dec) or _has_float(d["tex"]):
            continue
        ok = _safe(d["ok"])
        if ok is None:
            report.append(f"- 오답 제외 {tag}: '{d['error']}' 판정 오류")
            continue
        if ok:
            report.append(f"- 오답 제외 {tag}: '{d['error']}' 블록이 실제로는 맞음")
            continue
        dec.append({"tex": d["tex"], "error": d["error"], "why": d["why"], "pos": d["pos"]})
    if len(dec) < 2:
        report.append(f"- 제외 {tag}: 유효한 오답 블록 {len(dec)}개")
        return None
    return {"problem": c["problem"], "steps": texs, "decoys": dec}


def _matches(st, Yr, y):
    k = st["kind"]
    if k == "eqY":
        e = sp.expand(st["expr"])
        if e.coeff(Y) == 0:
            return False
        return same(solve_Y(e), Yr, s, S_PTS)
    if k == "Y":
        return same(st["expr"], Yr, s, S_PTS)
    if k == "y":
        return same(st["expr"], y, t, T_PTS)
    raise ValueError(k)


# ------------------------------------------------------------------ 장 빌드
def build_chapter(cdir, catalog, seed="v0"):
    meta = yaml.safe_load((cdir / "chapter.yaml").read_text())
    cid = meta["id"]
    cat = next(c for c in catalog if c["id"] == cid)
    report = []
    units, items = [], []
    if (cdir / "atoms.yaml").exists():
        u, i = build_atoms(yaml.safe_load((cdir / "atoms.yaml").read_text()), report, cdir / "templates", seed)
        units += u
        items += i
    if (cdir / "schemas.yaml").exists():
        u, i = build_schemas(yaml.safe_load((cdir / "schemas.yaml").read_text()), cdir / "templates", report, seed)
        units += u
        items += i
    dpath = cdir / "derivations.yaml"
    deriv = yaml.safe_load(dpath.read_text()) if dpath.exists() else {}
    for u in units:
        if u["id"] in (deriv or {}):
            d = deriv[u["id"]]
            if not isinstance(d, dict) or not d.get("goal") or not d.get("steps"):
                raise SystemExit(f"{dpath}: {u['id']}에 goal(문제 상황)과 steps가 모두 있어야 합니다")
            u["derivation_goal"] = d["goal"]
            u["derivation"] = d["steps"]
        else:
            report.append(f"- 유도 없음: {u['id']}")
    pack = {"format": FORMAT, "built": datetime.date.today().isoformat(),
            "chapter": {"id": cid, "slug": meta["slug"], "title": meta["title"], "summary": meta.get("summary", ""),
                        "part": cat["part"], "level": cat["level"], "prereqs": cat["prereqs"],
                        "connections": meta.get("connections", [])},
            "units": units, "items": items}
    out = ROOT / "packs" / f"ch{cid:02d}.json"
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=1))
    rdir = ROOT / "tools" / "reports"
    rdir.mkdir(exist_ok=True)
    counts = {}
    for it in items:
        counts[it["unit"]] = counts.get(it["unit"], 0) + 1
    lines = [f"# ch{cid:02d} {meta['title']} 빌드 리포트 ({pack['built']})", "",
             f"- 단위 {len(units)}개, 문제 {len(items)}개", ""]
    lines += [f"- {u['id']}: {counts.get(u['id'], 0)}문제, 단계 {u['tiers']}" for u in units]
    lines += ["", "## 실패·제외", ""] + (report or ["- 없음"])
    (rdir / f"ch{cid:02d}.md").write_text("\n".join(lines) + "\n")
    print(f"ch{cid:02d}: units={len(units)} items={len(items)} issues={len(report)} → {out.relative_to(ROOT)}")
    return pack


def main():
    catalog = yaml.safe_load((ROOT / "content" / "catalog.yaml").read_text())
    errors = yaml.safe_load((ROOT / "content" / "errors.yaml").read_text())
    want = {int(a) for a in sys.argv[1:]}
    dirs = sorted(d for d in (ROOT / "content").iterdir() if d.is_dir() and d.name.startswith("ch"))
    for d in dirs:
        cid = int(d.name[2:4])
        if not want or cid in want:
            build_chapter(d, catalog)
    built = {int(p.stem[2:]): json.loads(p.read_text()) for p in (ROOT / "packs").glob("ch*.json")}
    index = {"format": FORMAT, "game": "Isn't she lovely", "errors": errors, "chapters": []}
    for c in catalog:
        e = dict(c)
        e["start_open"] = bool(c.get("start_open"))
        if c["id"] in built:
            p = built[c["id"]]
            e.update(file=f"ch{c['id']:02d}.json", units=len(p["units"]), items=len(p["items"]), built=p["built"])
        index["chapters"].append(e)
    (ROOT / "packs" / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    print("index.json 갱신")


if __name__ == "__main__":
    main()
