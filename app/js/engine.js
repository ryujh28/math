// 학습 엔진: 로그 → 단위별 FSRS 상태, 녹슬기, 숙련도, 해금.
// 이 모듈은 DOM을 쓰지 않는다 (node에서 테스트 가능).
import { fsrs, createEmptyCard, generatorParameters, Rating, State } from '../vendor/ts-fsrs/ts-fsrs.mjs';

export const SETTINGS = {
  retention: 0.9,       // 목표 기억 유지율
  masteredDays: 7,      // 안정도 7일 이상 = 숙련
  unlockRatio: 0.7,     // 선수 장의 숙련 단위 비율
  newPerDay: 3,         // 하루 새 단위 수
};

const scheduler = fsrs(generatorParameters({ enable_fuzz: false, request_retention: SETTINGS.retention }));

export const GRADE = { again: Rating.Again, hard: Rating.Hard, good: Rating.Good, easy: Rating.Easy };
export const GRADE_NAME = { 1: 'Again', 2: 'Hard', 3: 'Good', 4: 'Easy' };

/** 모드별 시도 결과 → FSRS 등급 (계획 문서의 표와 같다). */
export function gradeFor(mode, r) {
  switch (mode) {
    case 'mcq':
      if (!r.correct) return GRADE.again;
      if (r.ms > 6000) return GRADE.hard;
      if (r.ms < 2000) return GRADE.easy;
      return GRADE.good;
    case 'order':
      if (r.gaveUp || r.checks >= 3) return GRADE.again;
      if (r.checks === 2) return GRADE.hard;
      if (r.refMs && r.ms < r.refMs / 2) return GRADE.easy;
      return GRADE.good;
    case 'hunt':
      if (!r.lineOk) return GRADE.again;
      if (!r.typeOk) return GRADE.hard;
      return r.fast ? GRADE.easy : GRADE.good;
    case 'draw':
      return [GRADE.again, GRADE.hard, GRADE.good, GRADE.easy][Math.max(0, Math.min(3, r.stars))];
    default:
      throw new Error('unknown mode ' + mode);
  }
}

/** 로그를 시간순으로 다시 재생해 단위별 상태를 만든다. */
export function replay(log) {
  const rows = [...new Map(log.map((r) => [r.id, r])).values()]
    .filter((r) => r.unit && r.grade >= 1 && r.grade <= 4)
    .sort((a, b) => a.ts - b.ts || (a.id < b.id ? -1 : 1));
  const states = new Map();
  for (const r of rows) {
    const now = new Date(r.ts);
    let st = states.get(r.unit);
    if (!st) {
      st = { card: createEmptyCard(now), attempts: 0, correct: 0, recent: [], days: new Set(), firstTs: r.ts, lastTs: r.ts, relearn: false };
      states.set(r.unit, st);
    }
    st.card = scheduler.next(st.card, now, r.grade).card;
    st.attempts += 1;
    if (r.grade >= 2) {
      st.correct += 1;
      st.days.add(new Date(r.ts).toDateString());
    }
    st.recent.push(r.grade >= 2 ? 1 : 0);
    if (st.recent.length > 10) st.recent.shift();
    st.lastTs = r.ts;
    st.relearn = false;
  }
  return states;
}

export function retrievability(st, now = new Date()) {
  if (!st || st.card.state === State.New) return 0;
  return scheduler.get_retrievability(st.card, now, false);
}

export const rust = (st, now) => (st ? 1 - retrievability(st, now) : 1);
// 숙련: 안정도 7일 이상 + 서로 다른 날 2번 이상 맞힘 (첫 Easy 한 번으로 숙련되는 것 방지)
export const isMastered = (st) => !!st && st.card.stability >= SETTINGS.masteredDays && st.days.size >= 2;
export const isDue = (st, now = new Date()) => !!st && st.card.due.getTime() <= now.getTime();

/** 단위의 현재 문제 난이도 단계: 최근 정답률로 올리고 내린다 (목표 85%). */
export function tierFor(unit, st) {
  const tiers = unit.tiers.length ? unit.tiers : [1];
  if (!st || st.recent.length < 5) return tiers[0];
  const acc = st.recent.reduce((a, b) => a + b, 0) / st.recent.length;
  const base = Math.min(tiers.length - 1, Math.floor(st.attempts / 8));
  let idx = base;
  if (acc > 0.9) idx = Math.min(tiers.length - 1, base + 1);
  if (acc < 0.7) idx = Math.max(0, base - 1);
  return tiers[idx];
}

/** 장의 숙련 비율 (숙련 단위 수 / 전체 단위 수). */
export function chapterMastery(pack, states) {
  if (!pack || !pack.units.length) return 0;
  const m = pack.units.filter((u) => isMastered(states.get(u.id))).length;
  return m / pack.units.length;
}

/** 장이 열렸는지. index의 장 항목과, 장 id → 숙련 비율 맵을 받는다. */
export function isUnlocked(ch, masteryById, opts = {}) {
  if (opts.testMode) return true;
  if (ch.start_open) return true;
  if (opts.placementPassed && opts.placementPassed.has(ch.id)) return true;
  if (!ch.prereqs.length) {
    // 선수 장이 없는 장(1, 11, 22장 등)은 시작 장 중 하나가 숙련 70%에 이르면 열린다
    const starts = opts.startIds || [];
    return starts.some((s) => (masteryById.get(s) || 0) >= SETTINGS.unlockRatio);
  }
  return ch.prereqs.every((p) => (masteryById.get(p) || 0) >= SETTINGS.unlockRatio);
}

export { State, Rating };
