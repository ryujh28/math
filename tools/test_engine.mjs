// 학습 엔진 테스트: node tools/test_engine.mjs
import assert from 'node:assert/strict';
import { replay, gradeFor, retrievability, isMastered, isUnlocked, tierFor, GRADE } from '../app/js/engine.js';

const day = 864e5;
const t0 = Date.parse('2026-11-24T21:00:00+09:00');
let n = 0;
const row = (unit, grade, ts) => ({ id: `r${n++}`, unit, grade, ts, mode: 'mcq' });

// 1. 등급 변환
assert.equal(gradeFor('mcq', { correct: false, ms: 1000 }), GRADE.again);
assert.equal(gradeFor('mcq', { correct: true, ms: 3800 }), GRADE.easy);
assert.equal(gradeFor('mcq', { correct: true, ms: 4500 }), GRADE.good);
assert.equal(gradeFor('mcq', { correct: true, ms: 5500 }), GRADE.good);
assert.equal(gradeFor('mcq', { correct: true, ms: 8900 }), GRADE.good);
assert.equal(gradeFor('order', { checks: 1, ms: 20000, refMs: 30000 }), GRADE.good);
assert.equal(gradeFor('order', { checks: 1, ms: 10000, refMs: 30000 }), GRADE.easy);
assert.equal(gradeFor('order', { checks: 2 }), GRADE.hard);
assert.equal(gradeFor('order', { checks: 1, gaveUp: true }), GRADE.again);
assert.equal(gradeFor('draw', { stars: 3 }), GRADE.easy);

// 2. 재생: 같은 로그는 순서와 중복에 상관없이 같은 상태
const log = [row('a', 3, t0), row('a', 3, t0 + 1 * day), row('a', 3, t0 + 4 * day), row('a', 4, t0 + 15 * day), row('b', 1, t0)];
const s1 = replay(log);
const s2 = replay([...log].reverse().concat(log)); // 섞고 중복
assert.equal(s1.get('a').card.stability, s2.get('a').card.stability);
assert.equal(s1.get('a').attempts, 4);

// 3. 녹슬기: 시간이 지나면 R이 줄어든다
const a = s1.get('a');
const rNow = retrievability(a, new Date(a.lastTs));
const rLater = retrievability(a, new Date(a.lastTs + 120 * day));
assert.ok(rNow > 0.95 && rLater < rNow, `R ${rNow} → ${rLater}`);
assert.equal(retrievability(undefined), 0);

// 4. 숙련: 여러 번 맞히면 안정도 7일 이상
assert.ok(isMastered(a), `stability ${a.card.stability}`);
assert.ok(!isMastered(s1.get('b')));

// 4b. 첫 Easy 한 번으로는 숙련 아님
const once = replay([row('e', 4, t0)]).get('e');
assert.ok(once.card.stability >= 7 && !isMastered(once), 'single Easy must not master');

// 5. 해금
const m = new Map([[3, 0.8], [5, 0.75], [7, 0.4]]);
assert.ok(isUnlocked({ id: 10, prereqs: [], start_open: true }, m));
assert.ok(!isUnlocked({ id: 1, prereqs: [] }, m, { startIds: [6, 7, 10] }));
assert.ok(isUnlocked({ id: 1, prereqs: [] }, new Map([[6, 0.8]]), { startIds: [6, 7, 10] }));
assert.ok(isUnlocked({ id: 4, prereqs: [3] }, m));
assert.ok(!isUnlocked({ id: 8, prereqs: [3, 5, 7] }, m));
assert.ok(isUnlocked({ id: 8, prereqs: [3, 5, 7] }, m, { testMode: true }));

// 6. 난이도 단계
const unit = { tiers: [1, 2, 3] };
assert.equal(tierFor(unit, undefined), 1);
const good = replay(Array.from({ length: 10 }, (_, i) => row('c', 3, t0 + i * day)));
assert.ok(tierFor(unit, good.get('c')) >= 2);

console.log('engine: all tests passed', { stabilityA: a.card.stability.toFixed(1), rNow: rNow.toFixed(3), r120d: rLater.toFixed(3) });

// 미니 튜토리얼 기록: 배운 단위면 '다시 배움' + 복습을 지금으로 당김, 맞히면 표시가 풀린다
{
  const t0 = Date.UTC(2026, 10, 1, 12);
  const base = [{ id: 'a1', ts: t0, unit: 'u', grade: 3 }, { id: 'a2', ts: t0 + 864e5, unit: 'u', grade: 3 }];
  const before = replay(base).get('u');
  assert.ok(before.card.due.getTime() > t0 + 2 * 864e5);
  const tut = { id: 't1', ts: t0 + 2 * 864e5, unit: 'u', kind: 'tutorial' };
  const after = replay([...base, tut]).get('u');
  assert.equal(after.relearn, true);
  assert.equal(after.card.due.getTime(), tut.ts);
  assert.equal(after.attempts, 2, '튜토리얼은 시도로 세지 않음');
  assert.equal(after.card.stability, before.card.stability, '숙련도는 그대로');
  const fixed = replay([...base, tut, { id: 'a3', ts: tut.ts + 6e4, unit: 'u', grade: 3 }]).get('u');
  assert.equal(fixed.relearn, false);
  assert.equal(replay([tut]).size, 0, '안 배운 단위의 튜토리얼은 상태를 만들지 않음');
  console.log('engine: tutorial rows ok');
}
