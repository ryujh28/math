// 오류 사냥: 사례 만들기와 모드 배정 검사 (모든 팩의 순서 문제에 대해)
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { huntCase } from '../app/js/modes.js';
import { reviewMode, HUNT_AFTER } from '../app/js/session.js';
import { gradeFor, GRADE } from '../app/js/engine.js';

const idx = JSON.parse(readFileSync(new URL('../packs/index.json', import.meta.url)));
let n = 0, withFix = 0;
let seed = 7;
const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
for (const c of idx.chapters) {
  if (!c.file) continue;
  const p = JSON.parse(readFileSync(new URL('../packs/' + c.file, import.meta.url)));
  for (const it of p.items.filter((x) => x.type === 'order')) {
    for (let k = 0; k < 3; k++) {
      const { d, lines, chips } = huntCase(it, rand);
      n++;
      assert.equal(lines.length, it.steps.length);
      // 정확히 한 줄만 바뀌고, 그 줄은 원래 단계와 다르다
      const diff = lines.map((l, i) => l !== it.steps[i]).filter(Boolean).length;
      assert.equal(diff, 1, `${it.id}: 바뀐 줄 ${diff}`);
      assert.notEqual(lines[d.pos], it.steps[d.pos]);
      // 고치기 칩: 정답 하나, 지금 틀린 줄과 같은 칩은 없음, 중복 없음
      assert.equal(chips.filter((x) => x.ok).length, 1);
      assert.ok(!chips.some((x) => !x.ok && x.tex === d.tex));
      assert.equal(new Set(chips.map((x) => x.tex)).size, chips.length);
      assert.ok(d.error && d.why, `${it.id}: 오류 종류·이유`);
      if (chips.length > 1) withFix++;
    }
  }
}

// 모드 배정
const u = { id: 'x', kind: 'schema' };
assert.equal(reviewMode({ id: 'a', kind: 'atom' }, null, []), 'mcq');
assert.equal(reviewMode(u, { correct: 1 }, []), 'order');
assert.equal(reviewMode(u, { correct: HUNT_AFTER }, [{ unit: 'x', mode: 'order' }]), 'hunt');
assert.equal(reviewMode(u, { correct: 5 }, [{ unit: 'x', mode: 'hunt' }, { unit: 'y', mode: 'mcq' }]), 'order');

// 채점
assert.equal(gradeFor('hunt', { lineOk: false, typeOk: true }), GRADE.again);
assert.equal(gradeFor('hunt', { lineOk: true, typeOk: false }), GRADE.hard);
assert.equal(gradeFor('hunt', { lineOk: true, typeOk: true, fast: false }), GRADE.good);
assert.equal(gradeFor('hunt', { lineOk: true, typeOk: true, fast: true }), GRADE.easy);
console.log(`hunt: 모두 통과 (사례 ${n}개, 고치기 단계 있는 것 ${withFix}개)`);
