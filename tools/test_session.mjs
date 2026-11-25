// 세션 구성 테스트: node tools/test_session.mjs  (packs/를 디스크에서 읽는다)
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { replay } from '../app/js/engine.js';
import { planSession, planExtra, migrateSettings, pickItem, unitMeta, streak, newToday, DEFAULTS } from '../app/js/session.js';
const NEW = DEFAULTS.newPerDay;

const root = new URL('../packs/', import.meta.url);
const index = JSON.parse(readFileSync(new URL('index.json', root)));
const packs = new Map(index.chapters.filter((c) => c.file).map((c) => [c.id, JSON.parse(readFileSync(new URL(c.file, root)))]));
const meta = unitMeta(packs);
const day = 864e5;
const t0 = Date.parse('2026-11-25T07:00:00+09:00');

// 1. 첫날: 복습 없음, 새 단위 NEW(5)개, 시작 장(6, 7, 10)에서만
let log = [];
let plan = planSession({ index, packs, states: replay(log), log, now: t0 });
assert.equal(plan.dueCount, 0);
assert.equal(plan.newCount, NEW);
const chs = new Set(plan.queue.map((q) => q.chapter));
assert.ok([...chs].every((c) => [6, 7, 10].includes(c)), `chapters ${[...chs]}`);
assert.equal(new Set(plan.queue.filter((q) => q.isNew).map((q) => q.unit)).size, NEW);
assert.equal(plan.queue.filter((q) => q.intro).length, NEW);

// 2. 플레이 시뮬레이션: 계획대로 모두 맞힘 → 다음 날 복습이 생김, 오늘 새 단위 몫은 소진
let n = 0;
const play = (plan, now, grade = 3) => {
  for (const q of plan.queue) {
    const m = meta.get(q.unit);
    const it = pickItem(m, replay(log).get(q.unit), log);
    assert.ok(it && it.unit === q.unit, 'pickItem unit');
    log.push({ id: `a${n++}`, ts: now + n * 30e3, unit: q.unit, item: it.id, mode: q.mode, grade });
  }
  log.push({ id: `s${n++}`, ts: now + n * 30e3, kind: 'session', n: plan.queue.length });
};
play(plan, t0);
assert.equal(newToday(log, t0 + 3600e3), NEW);
plan = planSession({ index, packs, states: replay(log), log, now: t0 + 3600e3 });
assert.equal(plan.newCount, 0, '같은 날 새 단위 몫 소진');

// 2b. 한 판 더: 배운 단위 복습 + 보너스 새 단위 2개, 하루 2×NEW 까지만
let ex = planExtra({ index, packs, states: replay(log), log, now: t0 + 3600e3 });
assert.ok(ex.dueCount > 0, 'extra has reviews');
assert.equal(ex.newCount, 2);
assert.ok(ex.estMin <= 7, `extra est ${ex.estMin}`);
const exNew = ex.queue.filter((q) => q.intro);
assert.equal(exNew.length, 2);
assert.ok(ex.queue.every((q) => q.isNew || replay(log).has(q.unit)), 'reviews are learned units');
{
  const before = log.length;
  play(ex, t0 + 3700e3);                       // 한 판 더 1회 → 오늘 7개
  ex = planExtra({ index, packs, states: replay(log), log, now: t0 + 4000e3 });
  play(ex, t0 + 4100e3);                       // 2회 → 9개
  ex = planExtra({ index, packs, states: replay(log), log, now: t0 + 4400e3 });
  assert.equal(ex.newCount, 1, '하루 2×NEW = 10개에서 멈춤');
  play(ex, t0 + 4500e3);
  ex = planExtra({ index, packs, states: replay(log), log, now: t0 + 4800e3 });
  assert.equal(ex.newCount, 0);
  assert.ok(ex.queue.length > 0, '새 단위가 없어도 복습 판은 있음');
  log = log.slice(0, before);                  // 이후 시나리오는 원래 기록으로
}

// 2c. 설정 이전: 예전 기본값 3 → 5, 사용자가 고른 다른 값은 유지
assert.equal(migrateSettings({ newPerDay: 3, minutes: 10 }).newPerDay, 5);
assert.equal(migrateSettings({ newPerDay: 2 }).newPerDay, 2);
assert.equal(migrateSettings({}).newPerDay, 5);
assert.equal(migrateSettings({ newPerDay: 3, v: 2 }).newPerDay, 3);

// 3. 14일 동안 매일 → 연속 기록, 배운 단위 증가, 테스트 모드 아니면 1–5장은 아직 잠김일 수 있음
for (let d = 1; d <= 14; d++) {
  const now = t0 + d * day;
  plan = planSession({ index, packs, states: replay(log), log, now });
  assert.ok(plan.queue.length > 0, `day ${d} empty`);
  play(plan, now);
}
const st = streak(log, t0 + 14 * day + 7200e3);
assert.equal(st.count, 15);
assert.ok(st.doneToday);
const learned = replay(log).size;
assert.ok(learned >= 40, `learned ${learned}`);

// 4. 하루 빠져도 유지권으로 연속 유지, 이틀 연속 빠지면 끊김
const gapLog = log.filter((r) => !(r.kind === 'session' && r.ts > t0 + 9 * day && r.ts < t0 + 10 * day));
assert.equal(streak(gapLog, t0 + 14 * day + 7200e3).count, 14);
const gap2 = gapLog.filter((r) => !(r.kind === 'session' && r.ts > t0 + 10 * day && r.ts < t0 + 11 * day));
assert.ok(streak(gap2, t0 + 14 * day + 7200e3).count < 10);

// 5. 테스트 모드: 1–5장도 새 단위 후보
plan = planSession({ index, packs, states: new Map(), log: [], settings: { ...DEFAULTS, testMode: true, newPerDay: 5 }, now: t0 });
assert.equal(plan.newCount, 5);
assert.ok(new Set(plan.queue.map((q) => q.chapter)).size >= 3);

// 6. 장 연습: 해당 장 단위만
plan = planSession({ index, packs, states: replay(log), log, now: t0 + 15 * day, chapter: 10 });
assert.ok(plan.queue.length > 0 && plan.queue.every((q) => q.chapter === 10));

// 7. 세션 길이 예산: 복습이 많아도 10분 예산 근처에서 자른다
const est = (p) => p.estMin;
plan = planSession({ index, packs, states: replay(log), log, now: t0 + 60 * day });
assert.ok(est(plan) <= 14, `est ${est(plan)} min, queue ${plan.queue.length}`);

console.log('session: all tests passed', { learned14d: learned, day60queue: plan.queue.length, day60est: plan.estMin });
