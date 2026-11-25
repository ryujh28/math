// 팩 안의 모든 수식과 문장($…$)을 KaTeX로 실제 렌더링해 본다: node tools/check_tex.mjs
// - 문제·보기·단계: TeX 전체를 엄격 모드로 렌더링
// - 힌트·제목·오답 설명·장 요약·연결 카드: $ 짝, $ 구간 렌더링, $ 밖에 남은 TeX 흔적이나 유니코드 위첨자
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const katex = require('../app/vendor/katex/katex.min.js');
const root = new URL('../packs/', import.meta.url);
const index = JSON.parse(readFileSync(new URL('index.json', root)));

const bad = [];
let nTex = 0, nRich = 0;
const tryTex = (tex, where) => {
  nTex++;
  try { katex.renderToString(tex, { throwOnError: true, strict: 'ignore' }); }
  catch (e) { bad.push(`${where}: 수식 렌더링 실패 — ${String(e.message).slice(0, 100)} — ${tex.slice(0, 80)}`); }
};
const LEFTOVER = /\\[a-zA-Z]+|\^\{|_\{|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻ᵀⁿᵢⱼₖ₀₁₂₃]/;
const tryRich = (text, where) => {
  if (!text) return;
  nRich++;
  const n = (text.match(/\$/g) || []).length;
  if (n % 2) { bad.push(`${where}: $ 짝이 맞지 않음 — ${text.slice(0, 80)}`); return; }
  text.split(/(\$\$[^$]+\$\$|\$[^$]+\$)/g).forEach((part) => {
    if (part.startsWith('$$') && part.endsWith('$$') && part.length > 4) tryTex(part.slice(2, -2), where);
    else if (part.startsWith('$') && part.endsWith('$') && part.length > 2) tryTex(part.slice(1, -1), where);
    else if (LEFTOVER.test(part)) bad.push(`${where}: $ 밖에 수식 흔적 — "${part.match(LEFTOVER)[0]}" in ${part.slice(0, 60)}`);
  });
};

for (const c of index.chapters.filter((x) => x.file)) {
  const p = JSON.parse(readFileSync(new URL(c.file, root)));
  tryRich(p.chapter.summary, `ch${c.id} 요약`);
  p.chapter.connections.forEach((t, i) => tryRich(t, `ch${c.id} 연결${i}`));
  for (const u of p.units) {
    tryRich(u.title, `${u.id} 제목`);
    tryRich(u.hint, `${u.id} 힌트`);
    if (!u.derivation || !u.derivation.length) bad.push(`${u.id}: 유도 없음`);
    // 문장 규칙: 핵심(hint)은 완결된 문장이어야 한다 (수식만 나열하거나 수식 끝에 바로 다른 수식을 붙이지 않는다)
    if (u.hint && !/다[.:]/.test(u.hint)) bad.push(`${u.id}: 핵심이 문장이 아님 (…다. 로 맺는 서술이 없음)`);
    if (u.table) u.table.forEach((t) => tryTex(t, `${u.id} 변환표`));
    if (!u.derivation_goal) bad.push(`${u.id}: 유도의 문제 상황(goal) 없음`);
    else tryRich(u.derivation_goal, `${u.id} 문제 상황`);
    (u.derivation || []).forEach((line, i) => tryRich(line, `${u.id} 유도${i + 1}`));
  }
  const whys = new Set();
  for (const it of p.items) {
    if (it.type === 'mcq') {
      [it.prompt, it.answer, ...it.wrong.map((w) => w.tex)].forEach((t) => tryTex(t, it.id));
      (it.explain || []).forEach((line, i) => tryRich(line, `${it.id} 해설${i + 1}`));
    }
    else {
      [it.problem, ...it.steps, ...it.decoys.map((d) => d.tex)].forEach((t) => tryTex(t, it.id));
      if (it.graph) { tryTex('y = ' + it.graph.sol, it.id + ' 그래프 해'); it.graph.wrong.forEach((w) => { if (!whys.has(w.why)) { whys.add(w.why); tryRich(w.why, `${it.unit} 그래프 오답 설명`); } }); }
      it.decoys.forEach((d) => { if (!whys.has(d.why)) { whys.add(d.why); tryRich(d.why, `${it.unit} 오답 설명`); if (!/다[.:]/.test(d.why)) bad.push(`${it.unit}: 오답 설명이 문장이 아님: ${d.why}`); } });
    }
  }
}
if (bad.length) {
  console.log(bad.slice(0, 40).join('\n'));
  console.log(`실패 ${bad.length}건 (수식 ${nTex}개, 문장 ${nRich}개 검사)`);
  process.exit(1);
}
console.log(`tex: 모두 통과 (수식 ${nTex}개, 문장 ${nRich}개)`);
