// 세션 구성: 오늘 무엇을 얼마나 낼지 정한다. DOM을 쓰지 않는다 (node 테스트 가능).
import * as E from './engine.js';

export const DEFAULTS = { minutes: 10, capMinutes: 15, newPerDay: 5, testMode: false, v: 2 };

/** 저장된 설정을 현재 판으로 올린다. 예전 기본값(하루 새 단위 3개)은 새 기본값 5개로. */
export function migrateSettings(saved = {}) {
  const s = { ...DEFAULTS, ...saved };
  if (!saved.v || saved.v < 2) {
    if (saved.newPerDay === 3 || saved.newPerDay == null) s.newPerDay = DEFAULTS.newPerDay;
    s.v = 2;
  }
  return s;
}
export const EXTRA = { minutes: 5, bonusNew: 2 };
const EST = { mcq: 10, order: 75, hunt: 40, graph: 35, intro: 45 }; // 초 (intro = 미니 튜토리얼)
// 계산 문제는 실제로 걸리는 시간이 길어서 세션 계획에 그만큼 반영한다 (대략 제한시간의 40%).
const EST_PACE = { light: 12, compute: 20, heavy: 30, epic: 50 };
const estOf = (u, mode) => (mode === 'mcq' && EST_PACE[u.pace]) || EST[mode];

const dayKey = (ts) => new Date(ts).toLocaleDateString('sv-SE'); // YYYY-MM-DD (로컬)

/** 오늘 처음 배운 단위 수. */
export function newToday(log, now = Date.now()) {
  const first = new Map();
  for (const r of log) if (r.unit && (!first.has(r.unit) || r.ts < first.get(r.unit))) first.set(r.unit, r.ts);
  const today = dayKey(now);
  return [...first.values()].filter((ts) => dayKey(ts) === today).length;
}

/** 연속 기록: 세션을 한 날을 센다. 7일 안에 하루까지는 빠져도 이어진다(유지권). */
export function streak(log, now = Date.now()) {
  const days = new Set(log.filter((r) => r.kind === 'session' && r.n > 0).map((r) => dayKey(r.ts)));
  const day = 864e5;
  let d = now;
  if (!days.has(dayKey(d))) d -= day; // 오늘 아직 안 했으면 어제부터
  let count = 0, lastFreeze = -Infinity, i = 0, doneToday = days.has(dayKey(now));
  while (i < 3650) {
    if (days.has(dayKey(d))) count++;
    else if (i - lastFreeze >= 7 && count > 0 && days.has(dayKey(d - day))) lastFreeze = i;
    else break;
    d -= day;
    i++;
  }
  return { count, doneToday };
}

export function unitMeta(packs) {
  const meta = new Map();
  for (const [cid, p] of packs) {
    p.units.forEach((u, i) => meta.set(u.id, { unit: u, chapter: cid, order: i, items: p.items.filter((it) => it.unit === u.id) }));
  }
  return meta;
}

export function openChapters(index, packs, states, settings) {
  const mm = new Map();
  for (const [id, p] of packs) mm.set(id, E.chapterMastery(p, states));
  return index.chapters.filter((c) => packs.has(c.id) && E.isUnlocked(c, mm, { testMode: settings.testMode, startIds: index.chapters.filter((x) => x.start_open).map((x) => x.id) })).map((c) => c.id);
}

const modeOf = (u) => (u.kind === 'schema' ? 'order' : 'mcq');

/**
 * 복습할 때의 모드. 풀이 뼈대는 순서 맞추기를 두 번 이상 맞힌 뒤부터
 * 오류 사냥과 순서 맞추기를 번갈아 낸다 (풀이를 외워 버리지 않고, 검증하는 눈을 기르게).
 */
export const HUNT_AFTER = 2;
export function reviewMode(u, st, log) {
  if (u.kind !== 'schema') return 'mcq';
  if (!st || st.correct < HUNT_AFTER) return 'order';
  let last = null;
  for (let i = log.length - 1; i >= 0; i--) if (log[i].unit === u.id && log[i].mode) { last = log[i].mode; break; }
  // 순서 맞추기 → 오류 사냥 → (그래프가 있는 단위면) 그래프 예측 → 순서 맞추기 …
  const cycle = u.graph ? ['order', 'hunt', 'graph'] : ['order', 'hunt'];
  const k = cycle.indexOf(last);
  return cycle[(k + 1) % cycle.length];
}

/** 아직 배우지 않은 단위를 장끼리 번갈아 가며, 장 안에서는 쉬운 것부터. */
export function newCandidates(meta, open, states) {
  const byCh = new Map(open.map((c) => [c, []]));
  for (const [id, m] of meta) if (byCh.has(m.chapter) && !states.has(id) && m.items.length) byCh.get(m.chapter).push(m);
  for (const l of byCh.values()) l.sort((a, b) => (a.unit.tiers[0] || 1) - (b.unit.tiers[0] || 1) || (a.unit.kind === 'schema') - (b.unit.kind === 'schema') || a.order - b.order);
  const out = [];
  const lists = [...byCh.values()];
  for (let k = 0; lists.some((l) => l.length > k); k++) for (const l of lists) if (l[k]) out.push(l[k]);
  return out;
}

/**
 * 오늘 세션 계획.
 * 반환: { queue: [{unit, chapter, mode, isNew, intro}], dueCount, newCount, estMin }
 */
export function planSession({ index, packs, states, log, settings = DEFAULTS, now = Date.now(), chapter = null }) {
  const meta = unitMeta(packs);
  let open = openChapters(index, packs, states, settings);
  if (chapter != null) open = open.filter((c) => c === chapter);
  const budget = settings.minutes * 60;
  const nowD = new Date(now);

  const learned = [...meta.values()].filter((m) => open.includes(m.chapter) && states.has(m.unit.id));
  let due = learned.filter((m) => E.isDue(states.get(m.unit.id), nowD));
  if (chapter != null && due.length === 0) due = learned; // 장 연습: 복습할 게 없으면 배운 것 전부
  due.sort((a, b) => E.retrievability(states.get(a.unit.id), nowD) - E.retrievability(states.get(b.unit.id), nowD));

  const queue = [];
  let est = 0;
  const atoms = due.filter((m) => m.unit.kind === 'atom');
  const schemas = due.filter((m) => m.unit.kind !== 'atom');
  // 워밍업: 원자 2분
  while (atoms.length && est < 120) {
    const m = atoms.shift();
    queue.push({ unit: m.unit.id, chapter: m.chapter, mode: 'mcq', isNew: false });
    est += estOf(m.unit, 'mcq');
  }
  // 나머지 복습: 뼈대와 원자를 섞어서
  const rest = [];
  while (schemas.length || atoms.length) {
    if (schemas.length) rest.push(schemas.shift());
    if (atoms.length) rest.push(atoms.shift());
    if (atoms.length) rest.push(atoms.shift());
  }
  for (const m of rest) {
    const mode = reviewMode(m.unit, states.get(m.unit.id), log);
    const c = estOf(m.unit, mode);
    if (est + c > budget && queue.length) break;
    queue.push({ unit: m.unit.id, chapter: m.chapter, mode, isNew: false });
    est += c;
  }
  const dueCount = queue.length;
  // 새 단위
  const quota = chapter != null ? settings.newPerDay : Math.max(0, settings.newPerDay - newToday(log, now));
  const fresh = newCandidates(meta, open, states).slice(0, quota);
  const later = [];
  for (const m of fresh) {
    const mode = modeOf(m.unit);
    if (est + EST.intro + 2 * estOf(m.unit, mode) > budget * 1.3 && queue.length) break;
    queue.push({ unit: m.unit.id, chapter: m.chapter, mode, isNew: true, intro: true });
    later.push({ unit: m.unit.id, chapter: m.chapter, mode, isNew: true });
    est += EST.intro + 2 * estOf(m.unit, mode);
  }
  // 새 단위의 두 번째 문제는 맨 뒤에 (다른 문제 몇 개를 사이에 두고 다시 떠올리게)
  queue.push(...later);
  return { queue, dueCount, newCount: later.length, estMin: Math.max(1, Math.round(est / 60)) };
}

/**
 * 한 판 더: 세션이 끝난 뒤 바로 이어 하는 짧은 판.
 * 배운 단위 중 기억 확률(R)이 낮은 것부터 약 5분, 그리고 하루 한도를 넘어 새 단위 최대 2개.
 * 보너스 새 단위는 하루 2×newPerDay 까지만 (한 판 더를 연타해도 새 단위가 쏟아지지 않게).
 */
export function planExtra({ index, packs, states, log, settings = DEFAULTS, now = Date.now(), chapter = null, extra = EXTRA }) {
  const meta = unitMeta(packs);
  let open = openChapters(index, packs, states, settings);
  if (chapter != null) open = open.filter((c) => c === chapter);
  const nowD = new Date(now);
  const budget = extra.minutes * 60;
  // 이번 판 직전에 푼 단위는 뒤로 미룬다 (방금 본 걸 또 보는 느낌을 줄이려고)
  const lastSid = [...log].reverse().find((r) => r.kind === 'session')?.sid;
  const justSeen = new Set(log.filter((r) => r.sid && r.sid === lastSid && r.unit).map((r) => r.unit));
  const learned = [...meta.values()].filter((m) => open.includes(m.chapter) && states.has(m.unit.id));
  const R = (m) => E.retrievability(states.get(m.unit.id), nowD) + (justSeen.has(m.unit.id) ? 1 : 0);
  learned.sort((a, b) => R(a) - R(b));
  const atoms = learned.filter((m) => m.unit.kind === 'atom');
  const schemas = learned.filter((m) => m.unit.kind !== 'atom');
  const mixed = [];
  while (schemas.length || atoms.length) {
    if (atoms.length) mixed.push(atoms.shift());
    if (atoms.length) mixed.push(atoms.shift());
    if (schemas.length) mixed.push(schemas.shift());
  }
  const queue = [];
  let est = 0;
  for (const m of mixed) {
    const mode = reviewMode(m.unit, states.get(m.unit.id), log);
    const c = estOf(m.unit, mode);
    if (est + c > budget) continue;
    queue.push({ unit: m.unit.id, chapter: m.chapter, mode, isNew: false });
    est += c;
  }
  const reviewCount = queue.length;
  const room = Math.max(0, 2 * settings.newPerDay - newToday(log, now));
  const fresh = newCandidates(meta, open, states).slice(0, Math.min(extra.bonusNew, room));
  const later = [];
  for (const m of fresh) {
    const mode = modeOf(m.unit);
    // 새 단위는 복습 몇 문제 뒤에 소개
    queue.splice(Math.min(2, queue.length), 0, { unit: m.unit.id, chapter: m.chapter, mode, isNew: true, intro: true });
    later.push({ unit: m.unit.id, chapter: m.chapter, mode, isNew: true });
    est += EST.intro + 2 * estOf(m.unit, mode);
  }
  queue.push(...later);
  return { queue, dueCount: reviewCount, newCount: later.length, estMin: Math.max(1, Math.round(est / 60)) };
}

/** 단위에 맞는 문제 하나: 난이도 단계 맞추고, 최근에 낸 문제는 피한다. */
export function pickItem(m, st, log, rand = Math.random, mode = null) {
  const tier = E.tierFor(m.unit, st);
  const recent = new Set(log.filter((r) => r.unit === m.unit.id).slice(-8).map((r) => r.item));
  const all = mode === 'graph' ? m.items.filter((it) => it.graph) : m.items;
  let pool = all.filter((it) => it.tier === tier);
  if (!pool.length) pool = all.filter((it) => it.tier <= tier);
  if (!pool.length) pool = all;
  const fresh = pool.filter((it) => !recent.has(it.id));
  const from = fresh.length ? fresh : pool;
  return from[Math.floor(rand() * from.length)];
}

// ------------------------------------------------------------------ 제한시간
/**
 * 객관식 제한시간 (ms). 단위의 pace로 정한다.
 *   (없음) 기억형: 변환쌍·공식 알아보기 → 단계별 10/13/16초
 *   light   : 한 번의 짧은 계산 (내적, 2×2 행렬식, 적분인자)      → 20초
 *   compute : 몇 단계 계산 (3×3 행렬식, 고유벡터, 도함수 변환)     → 40초
 *   heavy   : 긴 계산 (Wronskian, 행렬지수, 합성곱, 계수 낮추기)   → 60초
 *   epic    : 적분까지 하는 계산 (매개변수 변환법)                  → 120초
 * 문제·보기가 길면 읽는 시간을 더 준다 (최대 +10초).
 */
export const PACE_MS = { light: 20000, compute: 40000, heavy: 60000, epic: 120000 };
export function timeLimit(unit, item) {
  let ms = PACE_MS[unit?.pace] ?? [10000, 10000, 13000, 16000][Math.min(3, item.tier || 1)];
  if (!unit?.pace && item.verified === 'hand') ms += 3000;
  const len = (item.prompt || '').length + (item.answer || '').length + (item.wrong || []).reduce((a, w) => a + w.tex.length, 0);
  ms += Math.min(10000, Math.max(0, Math.ceil((len - 160) / 40)) * 1000);
  return ms;
}
/** Easy로 칠 시간: 4초 또는 제한시간의 1/4 중 긴 쪽. */
export const easyMs = (limit) => Math.max(4000, Math.round(limit / 4));
