// 그래프 예측: 데이터 형식·오답의 구별성·모드 순환·채점
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { reviewMode } from '../app/js/session.js';
import { gradeFor, GRADE } from '../app/js/engine.js';

const idx = JSON.parse(readFileSync(new URL('../packs/index.json', import.meta.url)));
const norm = (y) => { const m = Math.max(...y.map(Math.abs)) || 1; return y.map((v) => v / m); };
const rms = (a, b) => Math.sqrt(a.reduce((s, v, i) => s + (v - b[i]) ** 2, 0) / a.length);
let n = 0;
const lims = {};
for (const c of idx.chapters) {
  if (!c.file) continue;
  const p = JSON.parse(readFileSync(new URL('../packs/' + c.file, import.meta.url)));
  const gu = new Set(p.units.filter((u) => u.graph).map((u) => u.id));
  for (const it of p.items.filter((x) => x.graph)) {
    const g = it.graph;
    n++;
    assert.ok(gu.has(it.unit), `${it.id}: 단위에 graph 표시`);
    assert.equal(g.y.length, 61);
    assert.equal(g.wrong.length, 3);
    assert.ok(['zero', 'const', 'osc', 'grow'].includes(g.lim));
    assert.equal(typeof g.osc, 'boolean');
    if (g.lim === 'osc') assert.equal(g.osc, true, `${it.id}: 진동 유지면 진동함`);
    assert.ok(g.x1 > g.x0);
    const all = [g.y, ...g.wrong.map((w) => w.y)].map(norm);
    for (let i = 0; i < all.length; i++) for (let j = i + 1; j < all.length; j++)
      assert.ok(rms(all[i], all[j]) >= 0.19, `${it.id}: 곡선 ${i}, ${j}가 너무 비슷함`);
    g.wrong.forEach((w) => assert.ok(w.error && w.why));
    lims[g.lim] = (lims[g.lim] || 0) + 1;
  }
}
assert.ok(n > 200, `그래프 문제 ${n}개`);

// 모드 순환: 그래프가 있는 뼈대는 순서 → 사냥 → 그래프 → 순서
const u = { id: 'x', kind: 'schema', graph: true };
const st = { correct: 3 };
assert.equal(reviewMode(u, st, [{ unit: 'x', mode: 'order' }]), 'hunt');
assert.equal(reviewMode(u, st, [{ unit: 'x', mode: 'hunt' }]), 'graph');
assert.equal(reviewMode(u, st, [{ unit: 'x', mode: 'graph' }]), 'order');
assert.equal(reviewMode({ ...u, graph: false }, st, [{ unit: 'x', mode: 'hunt' }]), 'order');

assert.equal(gradeFor('graph', { graphOk: false, featOk: true }), GRADE.again);
assert.equal(gradeFor('graph', { graphOk: true, featOk: false }), GRADE.hard);
assert.equal(gradeFor('graph', { graphOk: true, featOk: true, fast: false }), GRADE.good);
assert.equal(gradeFor('graph', { graphOk: true, featOk: true, fast: true }), GRADE.easy);
console.log(`graph: 모두 통과 (문제 ${n}개, 장기 거동 분포 ${JSON.stringify(lims)})`);
