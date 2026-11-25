// 게임 본체: 홈(오늘 세션·스킬 지도), 장 상세, 세션, 요약.
import { loadIndex, loadBuiltPacks } from './packs.js';
import * as store from './store.js';
import { makeSync } from './sync.js';
import * as E from './engine.js';
import * as S from './session.js';
import { playMcq, playOrder, clearKeys, escapeHtml, shuffle } from './modes.js';
import { rich, setRich, html, renderPrompt, renderProblem, fit, shrink } from './tex.js';

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

// ------------------------------------------------------------------ 기기 동기화
const SYNC = makeSync(store);
let syncing = null;

function ago(ts) {
  if (!ts) return '아직 없음';
  const m = Math.round((Date.now() - ts) / 60000);
  return m < 1 ? '방금' : m < 60 ? `${m}분 전` : m < 1440 ? `${Math.round(m / 60)}시간 전` : `${Math.round(m / 1440)}일 전`;
}

async function showSync(msg) {
  const cfg = await SYNC.config();
  $('#sync-off').hidden = !!cfg;
  $('#sync-on').hidden = !cfg;
  if (cfg) {
    const link = cfg.url ? ` · <a href="${cfg.url}" target="_blank" rel="noopener">Gist 보기</a>` : '';
    $('#sync-status').innerHTML = `${escapeHtml(cfg.login || '')} 계정에 연결됨 · 기기 ${escapeHtml(await store.deviceId())} · 마지막 동기화 ${ago(cfg.last)}${link}` +
      (msg ? `<br>${escapeHtml(msg)}` : '');
  }
  $('#sync-msg').textContent = cfg ? '' : msg || '';
}

/** 동기화 한 번. 다른 기기 기록이 들어오면 상태를 다시 계산하고 화면을 새로 그린다. */
async function syncNow({ quiet = false } = {}) {
  if (syncing) return syncing;
  syncing = (async () => {
    try {
      const r = await SYNC.syncNow();
      if (!r) return null;
      if (r.pulled) {
        await reload();
        if (!$('#home').hidden) renderHome();
      }
      await showSync(quiet ? '' : `받음 ${r.pulled}개 · 올림 ${r.pushed}개`);
      return r;
    } catch (e) {
      await showSync(e.kind === 'network' ? '오프라인이라 다음에 다시 시도합니다.' : `동기화 실패: ${e.message}`);
      return null;
    } finally {
      syncing = null;
    }
  })();
  return syncing;
}

function bindSync() {
  $('#sync-connect').addEventListener('click', async () => {
    const token = $('#sync-token').value;
    if (!token.trim()) return;
    $('#sync-connect').disabled = true;
    try {
      const { created } = await SYNC.connect(token);
      $('#sync-token').value = '';
      await showSync(created ? '새 비밀 Gist를 만들었습니다.' : '기존 기록 Gist에 연결했습니다.');
      await syncNow();
    } catch (e) {
      await showSync(`연결 실패: ${e.message}`);
    } finally {
      $('#sync-connect').disabled = false;
    }
  });
  $('#sync-now').addEventListener('click', () => syncNow());
  $('#sync-disconnect').addEventListener('click', async () => {
    await SYNC.disconnect();
    await showSync('연결을 해제했습니다. 이 기기의 기록은 그대로 남아 있습니다.');
  });
  // 앱으로 돌아올 때마다 받아 온다 (폰에서 하다가 맥을 열 때 등)
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') syncNow({ quiet: true }); });
}

async function reload() {
  G.log = await store.allAttempts();
  G.states = E.replay(G.log);
}

const hintHtml = (t) => rich(t);

const errName = (id) => G.errName[id] || (id === 'timeout' ? '시간 초과' : id || '');

// ------------------------------------------------------------------ 유도 보기
let derivKey = null;
function showDerivation(m) {
  const p = G.packs.get(m.chapter);
  $('#deriv-kicker').textContent = `${m.chapter}장 ${p.chapter.title} · 유도`;
  setRich($('#deriv-title'), m.unit.title);
  const body = $('#deriv-body');
  body.textContent = '';
  // 1) 문제 상황: 무엇이 주어지고 무엇을 구하나
  if (m.unit.derivation_goal) {
    const g = el('div', 'goal');
    g.appendChild(el('div', 'lab', '문제 상황'));
    g.appendChild(setRich(el('p'), m.unit.derivation_goal));
    body.appendChild(g);
  }
  // 2) 이 단위의 실제 문제 하나 (가장 쉬운 단계)
  const ex = exampleItem(m);
  if (ex) {
    const box = el('details', 'example');
    const sum = el('summary');
    sum.appendChild(el('span', 'lab', '예시 문제 · 눌러서 답 보기'));
    const q = el('div', 'ex-q');
    if (ex.type === 'mcq') renderPrompt(q, ex.prompt); else renderProblem(q, ex.problem);
    sum.appendChild(q);
    box.appendChild(sum);
    const a = el('div', 'ex-a');
    if (ex.type === 'mcq') a.innerHTML = '답: ' + html(ex.answer);
    else a.innerHTML = ex.steps.map((t, i) => `<div class="mline"><small>${i + 1}</small> ${html(t)}</div>`).join('');
    box.appendChild(a);
    box.addEventListener('toggle', () => fit(box));
    body.appendChild(box);
  }
  // 3) 유도
  body.appendChild(el('div', 'lab deriv-lab', '유도'));
  for (const line of m.unit.derivation || ['아직 유도가 없습니다.']) {
    const isBlock = line.startsWith('$$') && line.endsWith('$$');
    body.appendChild(setRich(el(isBlock ? 'div' : 'p'), line));
  }
  $('#deriv').hidden = false;
  fit(body);
  body.querySelectorAll('.katex-display').forEach((d) => shrink(d, 0.7));
  $('#deriv-close').focus({ preventScroll: true });
  derivKey = (e) => {
    if (e.key === 'Escape' || e.key === 'Enter') {
      e.preventDefault();
      e.stopImmediatePropagation();
      closeDerivation();
    } else if ('1234'.includes(e.key) && e.key) e.stopImmediatePropagation();
  };
  addEventListener('keydown', derivKey, true);
}
/** 유도 창에 보여 줄 이 단위의 예시 문제: 가장 낮은 단계에서, 열 때마다 같은 것. */
function exampleItem(m) {
  const items = (G.packs.get(m.chapter)?.items || []).filter((it) => it.unit === m.unit.id);
  if (!items.length) return null;
  const low = Math.min(...items.map((it) => it.tier || 1));
  return items.find((it) => (it.tier || 1) === low);
}
function closeDerivation() {
  $('#deriv').hidden = true;
  if (derivKey) removeEventListener('keydown', derivKey, true);
  derivKey = null;
}
function derivButton(m, label = '유도 보기', cls = 'btn ghost') {
  const b = el('button', cls, label);
  b.addEventListener('click', (e) => { e.stopPropagation(); showDerivation(m); });
  return b;
}

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
  setRich($('#ch-summary'), p.chapter.summary);
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
    tr.appendChild(setRich(el('td'), u.title));
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
    const tdb = el('td');
    tdb.appendChild(derivButton(G.meta.get(u.id), '유도', 'btn ghost small'));
    tr.appendChild(tdb);
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
    box.appendChild(setRich(el('h2', 'intro-title'), m.unit.title));
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
    const row = el('div', 'intro-actions');
    row.append(b, derivButton(m));
    box.appendChild(row);
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
  d.appendChild(setRich(el('p'), pick.t));
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

async function runSession(chapter, extra = false) {
  const args = { index: G.index, packs: G.packs, states: G.states, log: G.log, settings: G.settings, chapter };
  const plan = extra ? S.planExtra(args) : S.planSession(args);
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
    setRich($('#s-unit'), `${m.chapter}장 · ${m.unit.title}`);
    if (e.intro) await race(introCard(card, m));
    if (G.quit) break;
    const st = G.states.get(e.unit);
    const item = S.pickItem(m, st, G.log);
    const ctx = {
      hint: m.unit.hint, hintHtml: hintHtml(m.unit.hint), errName, derivButton: () => derivButton(m),
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
  if (done > 0) G.log.push(await store.addAttempt({ kind: 'session', sid, n: done, correct, minutes, chapter, extra }));
  if (done > 0) syncNow({ quiet: true });
  const masteredNow = [...G.states].filter(([u, st]) => E.isMastered(st) && !masteredBefore.has(u)).map(([u]) => u);
  await renderSummary({ done, correct, best, minutes, newUnits: [...newUnits], masteredNow, chapters: [...chaptersSeen], chapter, round: G.round = (extra ? (G.round || 1) + 1 : 1) });
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
  if (r.newUnits.length) box.appendChild(setRich(el('p'), `새로 배운 단위: ${r.newUnits.map(name).join(', ')}`));
  if (r.masteredNow.length) box.appendChild(setRich(el('p'), `숙련된 단위: ${r.masteredNow.map(name).join(', ')}`));
  if (r.chapters.length) await connectionCard(box, r.chapters);
  // 한 판 더
  const more = $('#sum-more');
  const next = S.planExtra({ index: G.index, packs: G.packs, states: G.states, log: G.log, settings: G.settings, chapter: r.chapter });
  more.hidden = !next.queue.length;
  if (next.queue.length) {
    const bonus = next.newCount ? ` · 새 단위 +${next.newCount}` : '';
    more.textContent = `한 판 더 (약 ${next.estMin}분${bonus})`;
    more.onclick = () => runSession(r.chapter, true);
  }
  if (r.round > 1) box.prepend(el('div', 'kicker', `${r.round}판째`));
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
  G.settings = S.migrateSettings(await store.kvGet('settings', {}));
  await reload();
  await bindSettings();
  $('#ch-back').addEventListener('click', renderHome);
  $('#deriv-close').addEventListener('click', closeDerivation);
  $('#deriv').addEventListener('click', (e) => { if (e.target.id === 'deriv') closeDerivation(); });
  $('#sum-home').addEventListener('click', renderHome);
  $('#s-quit').addEventListener('click', () => { G.quit = true; clearKeys(); $('#card').textContent = ''; G.quitR?.(); });
  bindSync();
  await showSync();
  renderHome();
  document.body.dataset.ready = '1';
  syncNow({ quiet: true });
}

main();
