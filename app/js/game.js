// 게임 본체: 홈(오늘 세션·스킬 지도), 장 상세, 세션, 요약.
import { loadIndex, loadBuiltPacks } from './packs.js';
import * as store from './store.js';
import * as E from './engine.js';
import * as S from './session.js';
import { playMcq, playOrder, clearKeys, escapeHtml, shuffle } from './modes.js';

const $ = (s) => document.querySelector(s);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};

const G = { index: null, packs: null, meta: null, log: [], states: new Map(), settings: { ...S.DEFAULTS }, errName: {}, quit: false };

function show(view) {
  for (const v of ['home', 'chapter', 'session', 'summary']) $('#' + v).hidden = v !== view;
  window.scrollTo(0, 0);
}

async function reload() {
  G.log = await store.allAttempts();
  G.states = E.replay(G.log);
}

/** 힌트 문장 안의 ^{…}, _{…}를 위·아래첨자로. */
function hintHtml(t) {
  return escapeHtml(t).replace(/\^\{([^}]*)\}/g, '<sup>$1</sup>').replace(/_\{([^}]*)\}/g, '<sub>$1</sub>');
}

const errName = (id) => G.errName[id] || (id === 'timeout' ? '시간 초과' : id || '');

// ------------------------------------------------------------------ 홈
function renderHome() {
  const st = S.streak(G.log);
  $('#streak').textContent = st.count ? `연속 ${st.count}일${st.doneToday ? '' : ' · 오늘 아직'}` : '오늘 첫 세션을 시작해 보세요';
  const plan = S.planSession({ index: G.index, packs: G.packs, states: G.states, log: G.log, settings: G.settings });
  const t = $('#today');
  t.textContent = '';
  if (plan.queue.length) {
    t.appendChild(el('div', 'today-nums', ''));
    const nums = t.firstChild;
    [['복습', plan.dueCount], ['새 단위', plan.newCount], ['예상', `${plan.estMin}분`]].forEach(([k, v]) => {
      const d = el('div', 'num');
      d.appendChild(el('b', null, String(v)));
      d.appendChild(el('span', null, k));
      nums.appendChild(d);
    });
    const b = el('button', 'btn big', '오늘 세션 시작');
    b.addEventListener('click', () => runSession(null));
    t.appendChild(b);
  } else {
    t.appendChild(el('p', null, '오늘 복습할 단위가 없고, 새 단위도 오늘 몫을 다 배웠습니다. 스킬 지도에서 장을 골라 더 연습할 수 있습니다.'));
  }
  renderMap($('#map'));
  show('home');
}

function chapterStats(cid) {
  const p = G.packs.get(cid);
  if (!p) return null;
  const learned = p.units.filter((u) => G.states.has(u.id));
  const mastered = p.units.filter((u) => E.isMastered(G.states.get(u.id)));
  const R = learned.length ? learned.reduce((a, u) => a + E.retrievability(G.states.get(u.id)), 0) / learned.length : 0;
  return { total: p.units.length, learned: learned.length, mastered: mastered.length, R };
}

function masteryMap() {
  const mm = new Map();
  for (const [id, p] of G.packs) mm.set(id, E.chapterMastery(p, G.states));
  return mm;
}

function renderMap(box) {
  box.textContent = '';
  const mm = masteryMap();
  const parts = [...new Set(G.index.chapters.map((c) => c.part))];
  for (const part of parts) {
    box.appendChild(el('div', 'part', part));
    const g = el('div', 'tiles');
    for (const c of G.index.chapters.filter((x) => x.part === part)) {
      const built = G.packs.has(c.id);
      const open = built && E.isUnlocked(c, mm, { testMode: G.settings.testMode, startIds: G.index.chapters.filter((x) => x.start_open).map((x) => x.id) });
      const s = chapterStats(c.id);
      const b = el('button', 'ch-tile ' + (!built ? 'unbuilt' : open ? 'open' : 'locked'));
      b.appendChild(el('b', null, `${c.id}장 · ${!built ? '준비 중' : open ? (s.learned ? `숙련 ${s.mastered}/${s.total}` : '열림') : '잠김'}`));
      b.appendChild(el('span', null, c.title));
      if (built && !open) b.appendChild(el('small', null, c.prereqs.length ? `선수: ${c.prereqs.join(', ')}장` : '시작 장 하나를 숙련하면 열림'));
      if (built && s.learned) {
        const bar = el('div', 'rustbar');
        const fill = el('i');
        fill.style.width = `${Math.round(s.R * 100)}%`;
        bar.appendChild(fill);
        bar.title = `기억 유지 평균 ${Math.round(s.R * 100)}%`;
        b.appendChild(bar);
      }
      if (built) b.addEventListener('click', () => renderChapter(c.id));
      else b.disabled = true;
      g.appendChild(b);
    }
    box.appendChild(g);
  }
}

// ------------------------------------------------------------------ 장 상세
function dueText(st) {
  if (!st) return '—';
  const d = st.card.due.getTime() - Date.now();
  if (d <= 0) return '지금';
  const m = d / 6e4;
  if (m < 60) return `${Math.ceil(m)}분 후`;
  if (m < 1440) return `${Math.round(m / 60)}시간 후`;
  return `${Math.round(m / 1440)}일 후`;
}

function renderChapter(cid) {
  const p = G.packs.get(cid);
  const c = G.index.chapters.find((x) => x.id === cid);
  const open = E.isUnlocked(c, masteryMap(), { testMode: G.settings.testMode, startIds: G.index.chapters.filter((x) => x.start_open).map((x) => x.id) });
  const s = chapterStats(cid);
  $('#ch-title').textContent = `${cid}장 ${p.chapter.title}`;
  $('#ch-meta').textContent = `${p.chapter.part} · ${p.chapter.level} · 단위 ${s.total}개 · 배운 단위 ${s.learned} · 숙련 ${s.mastered}`;
  $('#ch-summary').textContent = p.chapter.summary;
  const act = $('#ch-actions');
  act.textContent = '';
  if (open) {
    const b = el('button', 'btn', '이 장만 연습');
    b.addEventListener('click', () => runSession(cid));
    act.appendChild(b);
  } else {
    const mm = masteryMap();
    const need = c.prereqs.length ? c.prereqs.map((q) => `${q}장 숙련 ${Math.round((mm.get(q) || 0) * 100)}%`).join(', ') : '시작 장(6·7·10장) 중 하나가 숙련 70%';
    act.appendChild(el('p', 'note', `잠김: 선수 장이 모두 숙련 70% 이상이면 열립니다 (${need}). 설정의 테스트 모드로 바로 열 수 있습니다.`));
  }
  const tb = $('#ch-units');
  tb.textContent = '';
  for (const u of p.units) {
    const st = G.states.get(u.id);
    const tr = el('tr');
    const n = p.items.filter((it) => it.unit === u.id).length;
    tr.appendChild(el('td', null, u.title));
    tr.appendChild(el('td', null, u.kind === 'atom' ? '미니멀 훈련' : '순서 맞추기'));
    tr.appendChild(el('td', 'num', String(n)));
    tr.appendChild(el('td', null, !st ? '새 단위' : E.isMastered(st) ? '숙련' : E.isDue(st) ? '복습 필요' : '학습 중'));
    const td = el('td');
    const r = el('span', 'rust');
    const f = el('i');
    f.style.width = `${Math.round(E.retrievability(st) * 100)}%`;
    r.appendChild(f);
    td.appendChild(r);
    tr.appendChild(td);
    tr.appendChild(el('td', null, dueText(st)));
    tb.appendChild(tr);
  }
  show('chapter');
}

// ------------------------------------------------------------------ 세션
function introCard(box, m) {
  return new Promise((resolve) => {
    box.textContent = '';
    const p = G.packs.get(m.chapter);
    box.appendChild(el('div', 'kicker', `새 단위 · ${m.chapter}장 ${p.chapter.title}`));
    box.appendChild(el('h2', 'intro-title', m.unit.title));
    if (m.unit.hint) {
      const h = el('p', 'intro-hint');
      h.innerHTML = hintHtml(m.unit.hint);
      box.appendChild(h);
    }
    box.appendChild(el('p', 'note', m.unit.kind === 'atom' ? '미니멀 훈련: 제한시간 안에 맞는 보기를 고르세요. 숫자키 1–4로도 고를 수 있습니다.'
      : '순서 맞추기: 블록을 눌러 풀이를 순서대로 쌓고 검사하세요. 그럴듯한 오답 블록이 섞여 있습니다.'));
    const b = el('button', 'btn', '시작 (Enter)');
    const go = () => { removeEventListener('keydown', k); resolve(); };
    const k = (e) => { if (e.key === 'Enter') { e.preventDefault(); go(); } };
    b.addEventListener('click', go);
    addEventListener('keydown', k);
    box.appendChild(b);
  });
}

async function connectionCard(box, chapters) {
  const seen = new Set(await store.kvGet('connSeen', []));
  const all = [];
  for (const c of chapters) (G.packs.get(c)?.chapter.connections || []).forEach((t, i) => all.push({ key: `${c}:${i}`, c, t }));
  if (!all.length) return null;
  const fresh = all.filter((a) => !seen.has(a.key));
  const pick = shuffle(fresh.length ? fresh : all)[0];
  seen.add(pick.key);
  await store.kvSet('connSeen', [...seen]);
  const d = el('div', 'conn');
  d.appendChild(el('b', null, `연결 카드 · ${pick.c}장`));
  d.appendChild(el('p', null, pick.t));
  box.appendChild(d);
  return d;
}

function waitNext(box, label = '계속') {
  return new Promise((resolve) => {
    const b = el('button', 'btn', `${label} (Enter)`);
    const go = () => { removeEventListener('keydown', k); resolve(); };
    const k = (e) => { if (e.key === 'Enter') { e.preventDefault(); go(); } };
    b.addEventListener('click', go);
    addEventListener('keydown', k);
    box.appendChild(b);
  });
}

async function runSession(chapter) {
  const plan = S.planSession({ index: G.index, packs: G.packs, states: G.states, log: G.log, settings: G.settings, chapter });
  if (!plan.queue.length) {
    alertBox('지금 낼 문제가 없습니다.');
    return;
  }
  show('session');
  G.quit = false;
  G.quitP = new Promise((r) => (G.quitR = r));
  const race = (p) => Promise.race([p, G.quitP]);
  const card = $('#card');
  const sid = store.newId();
  const t0 = Date.now();
  const q = plan.queue.slice();
  const masteredBefore = new Set([...G.states].filter(([, st]) => E.isMastered(st)).map(([u]) => u));
  const reasked = new Set();
  const chaptersSeen = new Set();
  let done = 0, correct = 0, combo = 0, best = 0;
  const newUnits = new Set(q.filter((e) => e.isNew).map((e) => e.unit));
  const timer = setInterval(() => {
    const s = Math.floor((Date.now() - t0) / 1000);
    $('#s-time').textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  }, 1000);

  while (q.length && !G.quit) {
    if (Date.now() - t0 > G.settings.capMinutes * 6e4) break;
    const e = q.shift();
    const m = G.meta.get(e.unit);
    chaptersSeen.add(m.chapter);
    $('#s-prog').style.width = `${Math.round((done / (done + q.length + 1)) * 100)}%`;
    $('#s-count').textContent = `${done + 1} / ${done + q.length + 1}`;
    $('#s-combo').textContent = combo >= 2 ? `콤보 ${combo}` : '';
    $('#s-unit').textContent = `${m.chapter}장 · ${m.unit.title}`;
    if (e.intro) await race(introCard(card, m));
    if (G.quit) break;
    const st = G.states.get(e.unit);
    const item = S.pickItem(m, st, G.log);
    const ctx = {
      hint: m.unit.hint, hintHtml: hintHtml(m.unit.hint), errName,
      prefill: e.mode === 'order' && (!st || st.attempts < 2) && item.tier === 1 ? 1 : 0,
    };
    const result = await race((e.mode === 'mcq' ? playMcq : playOrder)(card, item, ctx));
    if (G.quit) break;
    const grade = E.gradeFor(e.mode, result);
    const row = await store.addAttempt({ unit: e.unit, item: item.id, mode: e.mode, grade, ms: result.ms, result, error: result.error || null, sid });
    G.log.push(row);
    G.states = E.replay(G.log);
    done++;
    if (grade >= 2) {
      correct++;
      combo++;
      best = Math.max(best, combo);
      if (combo % 5 === 0) {
        card.textContent = '';
        card.appendChild(el('div', 'kicker', `${combo}콤보`));
        await connectionCard(card, [...chaptersSeen]);
        await race(waitNext(card));
      }
    } else {
      combo = 0;
      if (!reasked.has(e.unit)) {
        reasked.add(e.unit);
        q.splice(Math.min(3, q.length), 0, { ...e, intro: false });
      }
    }
  }
  clearInterval(timer);
  clearKeys();
  const minutes = Math.round((Date.now() - t0) / 6e4 * 10) / 10;
  if (done > 0) G.log.push(await store.addAttempt({ kind: 'session', sid, n: done, correct, minutes, chapter }));
  const masteredNow = [...G.states].filter(([u, st]) => E.isMastered(st) && !masteredBefore.has(u)).map(([u]) => u);
  await renderSummary({ done, correct, best, minutes, newUnits: [...newUnits], masteredNow, chapters: [...chaptersSeen] });
}

async function renderSummary(r) {
  const box = $('#sum-body');
  box.textContent = '';
  const st = S.streak(G.log);
  const nums = el('div', 'today-nums');
  [['푼 문제', r.done], ['정답률', r.done ? `${Math.round((r.correct / r.done) * 100)}%` : '–'], ['최고 콤보', r.best], ['시간', `${r.minutes}분`], ['연속', `${st.count}일`]]
    .forEach(([k, v]) => {
      const d = el('div', 'num');
      d.appendChild(el('b', null, String(v)));
      d.appendChild(el('span', null, k));
      nums.appendChild(d);
    });
  box.appendChild(nums);
  const name = (u) => G.meta.get(u)?.unit.title || u;
  if (r.newUnits.length) box.appendChild(el('p', null, `새로 배운 단위: ${r.newUnits.map(name).join(', ')}`));
  if (r.masteredNow.length) box.appendChild(el('p', null, `숙련된 단위: ${r.masteredNow.map(name).join(', ')}`));
  if (r.chapters.length) await connectionCard(box, r.chapters);
  show('summary');
}

function alertBox(msg) {
  const t = $('#today');
  const p = el('p', 'note', msg);
  t.appendChild(p);
}

// ------------------------------------------------------------------ 설정
async function bindSettings() {
  const s = G.settings;
  $('#set-min').value = String(s.minutes);
  $('#set-new').value = String(s.newPerDay);
  $('#set-test').checked = !!s.testMode;
  const save = async () => {
    s.minutes = +$('#set-min').value;
    s.capMinutes = Math.max(15, s.minutes + 5);
    s.newPerDay = +$('#set-new').value;
    s.testMode = $('#set-test').checked;
    await store.kvSet('settings', s);
    renderHome();
  };
  ['#set-min', '#set-new', '#set-test'].forEach((id) => $(id).addEventListener('change', save));
}

async function main() {
  try {
    G.index = await loadIndex();
    G.packs = await loadBuiltPacks(G.index);
  } catch (e) {
    $('#today').textContent = '콘텐츠 팩을 불러오지 못했습니다. 파일을 직접 열었다면 간단한 웹 서버로 열어 주세요 (README 참고).';
    return;
  }
  G.meta = S.unitMeta(G.packs);
  G.errName = Object.fromEntries(G.index.errors.map((x) => [x.id, x.name]));
  G.settings = { ...S.DEFAULTS, ...(await store.kvGet('settings', {})) };
  await reload();
  await bindSettings();
  $('#ch-back').addEventListener('click', renderHome);
  $('#sum-home').addEventListener('click', renderHome);
  $('#s-quit').addEventListener('click', () => { G.quit = true; clearKeys(); $('#card').textContent = ''; G.quitR?.(); });
  renderHome();
  document.body.dataset.ready = '1';
}

main();
