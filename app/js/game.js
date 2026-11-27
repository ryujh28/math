// 게임 본체: 홈(오늘 세션·스킬 지도), 장 상세, 세션, 요약.
import { loadIndex, loadBuiltPacks } from './packs.js';
import * as store from './store.js';
import { makeSync } from './sync.js';
import * as E from './engine.js';
import * as S from './session.js';
import { playMcq, playOrder, playHunt, playGraph, graphSvg, LIM, clearKeys, escapeHtml, shuffle, explainHtml } from './modes.js';
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
// 기억 확률이 이보다 낮은 복습 단위는 되살리기 카드를 먼저 보여 준다
const RUSTY_R = 0.4;

/** 오류 사냥의 '오류 종류' 보기: 그 장의 문제에 실제로 나오는 오류 종류만 (Laplace에 Jacobian이 섞이지 않게). */
const errCache = new Map();
function chapterErrors(ch) {
  if (!errCache.has(ch)) {
    const seen = new Set();
    for (const it of G.packs.get(ch)?.items || []) {
      for (const w of it.wrong || []) if (w.error) seen.add(w.error);
      for (const d of it.decoys || []) if (d.error) seen.add(d.error);
    }
    const ids = G.index.errors.map((x) => x.id).filter((id) => seen.has(id));
    errCache.set(ch, ids.length >= 4 ? ids : G.index.errors.map((x) => x.id));
  }
  return errCache.get(ch);
}

const errName = (id) => G.errName[id] || (id === 'timeout' ? '시간 초과' : id || '');

// ------------------------------------------------------------------ 문제 다시 보기 (세션이 끝난 뒤)
function reviewList(box, list) {
  const sec = el('div', 'review');
  const head = el('div', 'review-head');
  const nWrong = list.filter((x) => x.grade < 2).length;
  head.appendChild(el('h3', null, `문제 다시 보기 (${list.length})`));
  const only = el('label', 'switch small');
  const cb = el('input');
  cb.type = 'checkbox';
  cb.checked = false;
  only.append(cb, document.createTextNode(` 틀린 것만 (${nWrong})`));
  if (nWrong) head.appendChild(only);
  sec.appendChild(head);
  sec.appendChild(el('p', 'note', '눌러서 내 답·정답·해설을 봅니다.'));
  const ul = el('div', 'review-list');
  sec.appendChild(ul);
  const draw = () => {
    ul.textContent = '';
    list.forEach((x, i) => {
      if (cb.checked && x.grade >= 2) return;
      const b = el('button', 'review-row ' + (x.grade >= 2 ? 'ok' : 'no'));
      const mark = x.grade >= 2 ? '✓' : x.result?.error === 'timeout' ? '⏱' : '✗';
      b.appendChild(el('span', 'mark', mark));
      const mid = el('span', 'mid');
      const t = el('span', 'unit');
      setRich(t, `${i + 1}. ${x.m.unit.title}`);
      mid.appendChild(t);
      const q = el('span', 'q');
      if (x.item.type === 'mcq') renderPrompt(q, x.item.prompt); else renderProblem(q, x.item.problem);
      mid.appendChild(q);
      b.appendChild(mid);
      b.appendChild(el('span', 'tm', x.mode === 'mcq' ? `${(x.result.ms / 1000).toFixed(1)}초` : { hunt: '오류 사냥', graph: '그래프', order: '순서' }[x.mode]));
      b.addEventListener('click', () => showReview(x, i));
      ul.appendChild(b);
    });
    fit(ul);
  };
  cb.addEventListener('change', draw);
  box.appendChild(sec);
  draw();
}

function showReview(x, i) {
  const { m, item, result } = x;
  $('#deriv-kicker').textContent = `문제 다시 보기 · ${i + 1}번 · ${m.chapter}장`;
  setRich($('#deriv-title'), m.unit.title);
  const body = $('#deriv-body');
  body.textContent = '';
  const q = el('div', 'goal');
  q.appendChild(el('div', 'lab', '문제'));
  const qq = el('div', 'ex-q');
  if (item.type === 'mcq') renderPrompt(qq, item.prompt); else renderProblem(qq, item.problem);
  q.appendChild(qq);
  body.appendChild(q);
  if (item.type === 'mcq') {
    const a = el('div', 'rv-ans');
    const mine = result.chosen == null ? '<b class="no">시간 초과</b>' : (result.correct ? '<b class="ok">맞힘</b> ' : '<b class="no">내 답</b> ') + html(result.chosen);
    a.innerHTML = `<div>${mine}</div>` + (result.correct ? '' : `<div><b class="ok">정답</b> ${html(item.answer)}</div>`) +
      (!result.correct && result.error && result.error !== 'timeout' ? `<div class="note">오답 종류: ${escapeHtml(errName(result.error))}</div>` : '');
    body.appendChild(a);
    body.appendChild(el('div', 'lab deriv-lab', item.explain?.length ? '해설' : '핵심'));
    const ex = el('div');
    ex.innerHTML = explainHtml(item, { hint: m.unit.hint, hintHtml: hintHtml(m.unit.hint) });
    body.appendChild(ex);
  } else {
    if (x.mode === 'graph' && item.graph) {
      const gr = el('div', 'rv-ans');
      const gg = item.graph;
      gr.innerHTML = `<div class="gplots one">${graphSvg(gg, gg.y)}</div>` +
        `<div class="note">장기 거동: ${LIM[gg.lim]}${result.graph && result.graph.lim !== gg.lim ? ' (내 예측: ' + LIM[result.graph.lim] + ')' : ''} · 진동: ${gg.osc ? '함' : '안 함'}</div>` +
        `<div>${html('y = ' + gg.sol)}</div>`;
      body.appendChild(gr);
    }
    if (x.mode === 'hunt' && result.hunt) {
      const h = el('div', 'rv-ans');
      h.innerHTML = `<div><b class="no">숨은 실수</b> ${result.hunt.pos + 1}번째 줄 ${html(result.hunt.tex)}</div>` +
        `<div class="note">${escapeHtml(errName(result.hunt.error))} — ${rich(result.hunt.why)}</div>`;
      body.appendChild(h);
    }
    body.appendChild(el('div', 'lab deriv-lab', '풀이'));
    const list = el('div', 'steps');
    item.steps.forEach((t, k) => {
      const d = el('div', 'step');
      d.appendChild(el('small', null, `${k + 1}단계`));
      const mm = el('div');
      mm.innerHTML = html(t);
      d.appendChild(mm);
      list.appendChild(d);
    });
    body.appendChild(list);
  }
  const row = el('div', 'row');
  const db = el('button', 'btn ghost', '유도 보기');
  db.addEventListener('click', () => showDerivation(m));
  row.appendChild(db);
  body.appendChild(row);
  $('#deriv').hidden = false;
  fit(body);
  body.querySelectorAll('.katex-display').forEach((d) => shrink(d, 0.7));
  $('#deriv-close').focus({ preventScroll: true });
  modalKeys();
}

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
  const tutRow = el('div', 'row');
  for (const line of m.unit.derivation || ['아직 유도가 없습니다.']) {
    const isBlock = line.startsWith('$$') && line.endsWith('$$');
    body.appendChild(setRich(el(isBlock ? 'div' : 'p'), line));
  }
  if ($('#session').hidden) {
    const tb = el('button', 'btn', '미니 튜토리얼 + 확인 문제');
    tb.addEventListener('click', () => startTutorial(m));
    tutRow.appendChild(tb);
    body.appendChild(tutRow);
  }
  $('#deriv').hidden = false;
  fit(body);
  body.querySelectorAll('.katex-display').forEach((d) => shrink(d, 0.7));
  $('#deriv-close').focus({ preventScroll: true });
  modalKeys();
}
/** 창이 열려 있는 동안 Esc·Enter는 창을 닫고, 숫자키는 뒤의 게임으로 새지 않게. */
function modalKeys() {
  if (derivKey) removeEventListener('keydown', derivKey, true);
  derivKey = (e) => {
    if (e.key === 'Escape' || e.key === 'Enter') {
      e.preventDefault();
      e.stopImmediatePropagation();
      closeDerivation();
    } else if ('1234'.includes(e.key) && e.key) e.stopImmediatePropagation();
  };
  addEventListener('keydown', derivKey, true);
}
/** 장 화면·유도 창에서 직접 여는 미니 튜토리얼: 튜토리얼 → 확인 문제 2개. */
function startTutorial(m) {
  closeDerivation();
  const st = G.states.get(m.unit.id);
  const mode = st ? S.reviewMode(m.unit, st, G.log) : m.unit.kind === 'schema' ? 'order' : 'mcq';
  const e = { unit: m.unit.id, chapter: m.chapter, mode, isNew: !st };
  runSession(null, false, { queue: [{ ...e, intro: true, tutorial: 'open' }, { ...e }, { ...e }], dueCount: 0, newCount: st ? 0 : 1, estMin: 2 });
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
const WD = ['일', '월', '화', '수', '목', '금', '토'];
const pct = (x) => `${Math.round(x * 100)}%`;

/** 지난 7일 문제 정답률 (튜토리얼·세션 기록 제외). 푼 문제가 없으면 null. */
function weekAccuracy(now = Date.now()) {
  const rows = G.log.filter((r) => r.grade != null && r.ts >= now - 7 * 864e5);
  return rows.length ? rows.filter((r) => r.grade >= 2).length / rows.length : null;
}

function openInfo() {
  const mm = masteryMap();
  const startIds = G.index.chapters.filter((x) => x.start_open).map((x) => x.id);
  const isOpen = (c) => G.packs.has(c.id) && E.isUnlocked(c, mm, { testMode: G.settings.testMode, startIds });
  return { mm, isOpen };
}

function renderHome() {
  const st = S.streak(G.log);
  const now = new Date();
  const plan = S.planSession({ index: G.index, packs: G.packs, states: G.states, log: G.log, settings: G.settings });
  const t = $('#today');
  t.textContent = '';
  const date = `${now.getMonth() + 1}월 ${now.getDate()}일 ${WD[now.getDay()]}요일`;
  const streakTxt = st.count ? ` · ${st.count}일째 연속${st.doneToday ? '' : ' (오늘 아직)'}` : '';
  t.appendChild(el('p', 'dateline', date + streakTxt));
  const h = el('h1', 'headline');
  if (plan.queue.length) {
    const parts = [];
    if (plan.dueCount) parts.push(`복습 ${plan.dueCount}개`);
    if (plan.newCount) parts.push(`새 단위 ${plan.newCount}개`);
    h.textContent = `오늘은 ${parts.join(', ')}입니다.`;
  } else h.textContent = '오늘 몫은 끝났습니다.';
  t.appendChild(h);
  // 숫자 세 개
  let total = 0, mastered = 0;
  for (const p of G.packs.values()) {
    total += p.units.length;
    mastered += p.units.filter((u) => E.isMastered(G.states.get(u.id))).length;
  }
  const acc = weekAccuracy();
  const stats = el('div', 'stats');
  [[plan.queue.length ? `${plan.estMin}분` : '–', '예상 시간'], [`${mastered}<small> / ${total}</small>`, '숙련 단위'], [acc == null ? '–' : pct(acc), '지난 7일 정답률']]
    .forEach(([v, k]) => {
      const d = el('div', 'stat');
      const b = el('b');
      b.innerHTML = v;
      d.append(b, el('span', null, k));
      stats.appendChild(d);
    });
  t.appendChild(stats);
  if (!plan.queue.length) t.appendChild(el('p', 'note', '아래 장을 골라 더 연습할 수 있습니다.'));
  const bar = el('div', 'startbar');
  const b = el('button', 'btn big', plan.queue.length ? '오늘 세션 시작' : '한 판 더 하기');
  b.addEventListener('click', () => runSession(null, !plan.queue.length));
  bar.appendChild(b);
  t.appendChild(bar);
  renderOpenList();
  renderMap($('#map'));
  show('home');
}

/** 열린 장 목록과 다음에 열릴 장 안내. */
function renderOpenList() {
  const { mm, isOpen } = openInfo();
  const box = $('#open-list');
  box.textContent = '';
  const open = G.index.chapters.filter(isOpen);
  for (const c of open) {
    const s = chapterStats(c.id);
    const a = el('button', 'chrow');
    a.appendChild(el('span', 'chno', String(c.id)));
    const mid = el('span', 'chmid');
    mid.appendChild(el('span', 'chtitle', c.title));
    const meter = el('span', 'meter');
    const fill = el('i');
    fill.style.width = pct(mm.get(c.id) || 0);
    meter.appendChild(fill);
    mid.appendChild(meter);
    const sub = s.learned ? `${s.mastered}/${s.total} 숙련 · 기억 ${pct(s.R)}` : `${s.total}단위 · 아직 시작 전`;
    mid.appendChild(el('span', 'chsub', sub));
    a.appendChild(mid);
    a.appendChild(el('span', 'chpct', pct(mm.get(c.id) || 0)));
    a.addEventListener('click', () => renderChapter(c.id));
    box.appendChild(a);
  }
  const next = G.index.chapters.filter((c) => G.packs.has(c.id) && !isOpen(c));
  const nx = $('#next-open');
  if (!next.length) { nx.textContent = ''; return; }
  const c = next[0];
  const need = c.prereqs.length ? `${c.prereqs.join('·')}장을 70% 숙련하면 열립니다` : '시작 장 하나를 70% 숙련하면 열립니다';
  nx.textContent = `다음에 열리는 장: ${c.id}장 ${c.title} · ${need}.`;
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
    const chs = G.index.chapters.filter((x) => x.part === part && (G.showUnbuilt || G.packs.has(x.id)));
    if (!chs.length) { box.lastChild.remove(); continue; }
    for (const c of chs) {
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

/**
 * 장 요약 페이지: 변환표 · 핵심 정리 · 풀이 뼈대 모음. 팩의 단위 정보로 자동으로 만든다.
 * 한때 배운 것을 빠르게 되짚는 참고용이라 숙련도에는 영향이 없다.
 */
function chapterSummary(p) {
  const box = $('#ch-sum');
  box.textContent = '';
  box.appendChild(el('h2', null, '장 요약'));
  const table = p.units.filter((u) => u.table);
  const facts = p.units.filter((u) => u.kind === 'atom' && !u.table && u.hint);
  const schemas = p.units.filter((u) => u.kind !== 'atom');
  const sec = (title, open = true) => {
    const d = el('details', 'sumsec');
    d.open = open;
    d.appendChild(el('summary', null, title));
    box.appendChild(d);
    return d;
  };
  if (table.length) {
    const d = sec(`변환표 (${table.length})`);
    const t = el('table', 'ttable');
    t.innerHTML = '<thead><tr><th>' + html('f(t)') + '</th><th>' + html('F(s) = \\mathcal{L}\\{f\\}') + '</th></tr></thead>';
    const tbd = el('tbody');
    for (const u of table) {
      const tr = el('tr');
      tr.innerHTML = `<td>${html(u.table[0])}</td><td>${html(u.table[1])}</td>`;
      tr.title = u.title;
      tbd.appendChild(tr);
    }
    t.appendChild(tbd);
    d.appendChild(t);
  }
  if (facts.length) {
    const d = sec(`핵심 정리 (${facts.length})`);
    for (const u of facts) {
      const it = el('div', 'sumitem');
      it.appendChild(setRich(el('div', 'sumt'), u.title));
      it.appendChild(setRich(el('div', 'sumb'), u.hint));
      d.appendChild(it);
    }
  }
  if (schemas.length) {
    const d = sec(`풀이 뼈대 (${schemas.length})`);
    for (const u of schemas) {
      const it = el('div', 'sumitem');
      it.appendChild(setRich(el('div', 'sumt'), u.title));
      if (u.steps?.length) it.appendChild(el('div', 'sumsteps', u.steps.map((s, i) => `${i + 1}. ${s}`).join('  →  ')));
      if (u.hint) it.appendChild(setRich(el('div', 'sumb'), u.hint));
      d.appendChild(it);
    }
  }
  fit(box);
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
  chapterSummary(p);
  const tb = $('#ch-units');
  tb.textContent = '';
  for (const u of p.units) {
    const st = G.states.get(u.id);
    const tr = el('tr');
    const n = p.items.filter((it) => it.unit === u.id).length;
    const tdt = setRich(el('td'), u.title);
    tdt.appendChild(el('small', 'kind ' + u.kind, u.kind === 'atom' ? '공식' : '풀이'));
    tr.appendChild(tdt);
    tr.appendChild(el('td', null, u.kind === 'atom' ? '미니멀 훈련' : st && st.correct >= S.HUNT_AFTER ? (u.graph ? '순서·사냥·그래프' : '순서·오류 사냥') : '순서 맞추기'));
    tr.appendChild(el('td', 'num', String(n)));
    const [stTxt, stCls] = !st ? ['새 단위', 'new'] : st.relearn ? ['다시 배움', 'due'] : E.isMastered(st) ? ['숙련', 'ok'] : E.isDue(st) ? ['복습 필요', 'due'] : ['학습 중', 'on'];
    const tds = el('td');
    tds.appendChild(el('span', 'state ' + stCls, stTxt));
    tr.appendChild(tds);
    const td = el('td', 'mem');
    if (st) {
      const R = E.retrievability(st);
      const r = el('span', 'meter');
      const f = el('i');
      f.style.width = pct(R);
      if (R < RUSTY_R) f.classList.add('low');
      r.appendChild(f);
      td.append(r, el('span', 'memtxt', pct(R)));
    } else td.textContent = '—';
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
/**
 * 미니 튜토리얼: 문제 상황·핵심 → 풀이 예제 → 빈칸 예제. 그다음 세션이 확인 문제 2개를 낸다.
 * kind: 'new' (새 단위), 'rusty' (많이 녹슨 단위), 'open' (장 화면에서 직접)
 * 돌려주는 값: 'done' | 'skip'
 */
function tutorialCard(box, m, kind = 'new') {
  return new Promise((resolve) => {
    const p = G.packs.get(m.chapter);
    const items = m.items.slice().sort((a, b) => (a.tier || 1) - (b.tier || 1));
    const low = items.filter((it) => (it.tier || 1) === (items[0]?.tier || 1));
    const exA = low[0] || items[0];
    const exB = low.find((it) => it !== exA && (it.type !== 'mcq' || it.explain?.length)) || items.find((it) => it !== exA);
    let page = 0;
    let keyFn = null;
    const setKey = (fn) => {
      if (keyFn) removeEventListener('keydown', keyFn);
      keyFn = fn;
      if (fn) addEventListener('keydown', fn);
    };
    const finish = (how) => { setKey(null); resolve(how); };
    const pages = [pageIntro, pageWorked, pageFaded].filter((f, i) => i === 0 || (i === 1 ? exA : exB));
    const head = (sub) => {
      box.textContent = '';
      const label = { new: '새 단위', rusty: '되살리기', open: '미니 튜토리얼' }[kind];
      box.appendChild(el('div', 'kicker', `${label} · ${m.chapter}장 ${p.chapter.title} · ${page + 1}/${pages.length} ${sub}`));
      box.appendChild(setRich(el('h2', 'intro-title'), m.unit.title));
    };
    const actions = (nextLabel, extra = []) => {
      const row = el('div', 'intro-actions');
      const b = el('button', 'btn', `${nextLabel}`);
      const go = () => { page++; page < pages.length ? pages[page]() : finish('done'); };
      b.addEventListener('click', go);
      setKey((e) => { if (e.key === 'Enter') { e.preventDefault(); go(); } });
      row.append(b, ...extra);
      box.appendChild(row);
      b.focus({ preventScroll: true });
      return b;
    };
    function pageIntro() {
      head('· 무엇을 하나');
      if (m.unit.derivation_goal) {
        const g = el('div', 'goal');
        g.appendChild(el('div', 'lab', '문제 상황'));
        g.appendChild(setRich(el('p'), m.unit.derivation_goal));
        box.appendChild(g);
      }
      if (m.unit.hint) {
        box.appendChild(el('div', 'lab', '핵심'));
        const h = el('p', 'intro-hint');
        h.innerHTML = hintHtml(m.unit.hint);
        box.appendChild(h);
      }
      box.appendChild(el('p', 'note', m.unit.kind === 'atom'
        ? '확인 문제는 미니멀 훈련(제한시간 안에 보기 고르기)입니다. 숫자키 1–4로도 고를 수 있습니다.'
        : '확인 문제는 순서 맞추기(블록을 순서대로 쌓기)입니다. 그럴듯한 오답 블록이 섞여 있습니다.'));
      const skip = el('button', 'btn ghost', kind === 'new' ? '예제 건너뛰기' : '건너뛰기');
      skip.addEventListener('click', () => finish('skip'));
      actions(pages.length > 1 ? '풀이 예제 보기' : '시작', [skip, derivButton(m)]);
      fit(box);
    }
    function pageWorked() {
      head('· 풀이 예제');
      const q = el('div', 'goal');
      q.appendChild(el('div', 'lab', '예제'));
      const qq = el('div', 'ex-q');
      if (exA.type === 'mcq') renderPrompt(qq, exA.prompt); else renderProblem(qq, exA.problem);
      q.appendChild(qq);
      box.appendChild(q);
      box.appendChild(el('div', 'lab', '풀이'));
      if (exA.type === 'mcq') {
        const ex = el('div');
        ex.innerHTML = explainHtml(exA, { hint: m.unit.hint, hintHtml: hintHtml(m.unit.hint) });
        box.appendChild(ex);
        const a = el('div', 'rv-ans');
        a.innerHTML = `<div><b class="ok">답</b> ${html(exA.answer)}</div>`;
        box.appendChild(a);
      } else box.appendChild(stepsList(exA.steps));
      actions(pages.length > 2 ? '빈칸 예제' : '확인 문제로');
      fit(box);
      box.querySelectorAll('.katex-display').forEach((d) => shrink(d, 0.7));
    }
    function pageFaded() {
      head('· 빈칸 예제');
      const q = el('div', 'goal');
      q.appendChild(el('div', 'lab', '예제 (시간 제한 없음)'));
      const qq = el('div', 'ex-q');
      if (exB.type === 'mcq') renderPrompt(qq, exB.prompt); else renderProblem(qq, exB.problem);
      q.appendChild(qq);
      box.appendChild(q);
      let opts, reveal;
      if (exB.type === 'mcq') {
        const all = exB.explain || [];
        // 답이 처음 드러나는 줄부터 가린다
        const norm = (t) => t.replace(/\s+/g, '');
        const ans = norm(exB.answer.replace(/^y = /, ''));
        let cut = all.findIndex((l) => norm(l).includes(ans));
        if (cut < 0) cut = all.length - 1;
        const lines = all.slice(0, cut + 1);
        if (lines.length > 1) {
          const ex = el('div', 'explain');
          ex.innerHTML = lines.slice(0, -1).map((l) => (l.startsWith('$$') ? `<div>${rich(l)}</div>` : `<p>${rich(l)}</p>`)).join('');
          box.appendChild(ex);
        }
        box.appendChild(el('div', 'lab', lines.length > 1 ? '마지막 단계: 답을 고르세요' : '답을 고르세요'));
        opts = shuffle([{ tex: exB.answer, ok: true }, ...shuffle(exB.wrong).slice(0, 2).map((w) => ({ tex: w.tex, ok: false }))]);
        reveal = () => {
          const rest = all.slice(lines.length - 1);
          if (!rest.length) return null;
          const d = el('div', 'explain');
          d.innerHTML = rest.map((l) => (l.startsWith('$$') ? `<div>${rich(l)}</div>` : `<p>${rich(l)}</p>`)).join('');
          return d;
        };
      } else {
        const k = Math.min(exB.steps.length - 1, Math.max(1, Math.floor(exB.steps.length / 2)));
        const list = stepsList(exB.steps, k);
        box.appendChild(list);
        box.appendChild(el('div', 'lab', `${k + 1}단계에 들어갈 줄을 고르세요`));
        const dec = exB.decoys.filter((d) => d.pos === k).slice(0, 2);
        const fill = exB.decoys.filter((d) => d.pos !== k && !dec.includes(d)).slice(0, Math.max(0, 2 - dec.length));
        opts = shuffle([{ tex: exB.steps[k], ok: true }, ...[...dec, ...fill].map((d) => ({ tex: d.tex, ok: false, why: d.why }))]);
        reveal = () => {
          const slot = list.querySelector('.step.blank > div');
          if (slot) { slot.innerHTML = html(exB.steps[k]); slot.parentElement.classList.remove('blank'); }
          return null;
        };
      }
      const grid = el('div', 'opts col');
      const btns = opts.map((o, i) => {
        const b = el('button', 'opt');
        b.innerHTML = `<small>${i + 1}</small>${html(o.tex)}`;
        b.addEventListener('click', () => pick(i));
        grid.appendChild(b);
        return b;
      });
      box.appendChild(grid);
      const fb = el('div', 'fb');
      box.appendChild(fb);
      setKey((e) => { const i = +e.key - 1; if (i >= 0 && i < opts.length) pick(i); });
      let picked = false;
      function pick(i) {
        if (picked) return;
        picked = true;
        btns.forEach((b, j) => { b.disabled = true; if (opts[j].ok) b.classList.add('good'); else if (j === i) b.classList.add('bad'); });
        fb.innerHTML = opts[i].ok ? '<div><b class="ok">맞습니다</b></div>' : `<div><b class="no">아쉽습니다</b>${opts[i].why ? ' · ' + rich(opts[i].why) : ''}</div>`;
        const r = reveal();
        if (r) fb.appendChild(r);
        actions('확인 문제로');
        fit(box);
      }
      fit(box);
    }
    pages[0]();
  });
}

function stepsList(steps, blank = -1) {
  const list = el('div', 'steps');
  steps.forEach((t, k) => {
    const d = el('div', 'step' + (k === blank ? ' blank' : ''));
    d.appendChild(el('small', null, `${k + 1}단계`));
    const mm = el('div');
    mm.innerHTML = k === blank ? '?' : html(t);
    d.appendChild(mm);
    list.appendChild(d);
  });
  return list;
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
    const b = el('button', 'btn', `${label}`);
    const go = () => { removeEventListener('keydown', k); resolve(); };
    const k = (e) => { if (e.key === 'Enter') { e.preventDefault(); go(); } };
    b.addEventListener('click', go);
    addEventListener('keydown', k);
    box.appendChild(b);
  });
}

async function runSession(chapter, extra = false, custom = null) {
  const args = { index: G.index, packs: G.packs, states: G.states, log: G.log, settings: G.settings, chapter };
  const plan = custom || (extra ? S.planExtra(args) : S.planSession(args));
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
  const review = [];
  const rustShown = new Set();
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
    if (e.intro) {
      const how = await race(tutorialCard(card, m, e.tutorial || 'new'));
      if (how === 'done' && G.states.has(e.unit)) G.log.push(await store.addAttempt({ kind: 'tutorial', unit: e.unit, sid }));
    } else {
      // 많이 녹슨 복습 단위는 문제 전에 되살리기 카드를 한 번 (건너뛸 수 있음)
      const st0 = G.states.get(e.unit);
      if (st0 && !rustShown.has(e.unit) && E.retrievability(st0) < RUSTY_R) {
        rustShown.add(e.unit);
        const how = await race(tutorialCard(card, m, 'rusty'));
        if (how === 'done') G.log.push(await store.addAttempt({ kind: 'tutorial', unit: e.unit, sid }));
      }
    }
    if (G.quit) break;
    const st = G.states.get(e.unit);
    const item = S.pickItem(m, st, G.log, Math.random, e.mode);
    const ctx = {
      hint: m.unit.hint, hintHtml: hintHtml(m.unit.hint), errName, derivButton: () => derivButton(m), errorIds: chapterErrors(m.chapter),
      prefill: e.mode === 'order' && (!st || st.attempts < 2) && item.tier === 1 ? 1 : 0,
      limitMs: Math.round(S.timeLimit(m.unit, item) * (G.settings.timeScale || 1)),
    };
    ctx.easyMs = S.easyMs(ctx.limitMs);
    const play = { mcq: playMcq, order: playOrder, hunt: playHunt, graph: playGraph }[e.mode];
    const result = await race(play(card, item, ctx));
    if (G.quit) break;
    const grade = E.gradeFor(e.mode, result);
    const row = await store.addAttempt({ unit: e.unit, item: item.id, mode: e.mode, grade, ms: result.ms, result, error: result.error || null, sid });
    review.push({ m, item, mode: e.mode, result, grade, ctx });
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
  await renderSummary({ done, correct, best, minutes, newUnits: [...newUnits], masteredNow, chapters: [...chaptersSeen], chapter, review, round: G.round = (extra ? (G.round || 1) + 1 : 1) });
}

async function renderSummary(r) {
  const box = $('#sum-body');
  box.textContent = '';
  const st = S.streak(G.log);
  box.appendChild(el('p', 'dateline', `${r.minutes}분 · 연속 ${st.count}일`));
  const nums = el('div', 'stats');
  [['푼 문제', r.done], ['정답률', r.done ? `${Math.round((r.correct / r.done) * 100)}%` : '–'], ['최고 콤보', r.best]]
    .forEach(([k, v]) => {
      const d = el('div', 'stat');
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
  if (r.review?.length) reviewList(box, r.review);
  show('summary');
}

function alertBox(msg) {
  const t = $('#today');
  t.querySelector('.alert')?.remove();
  t.insertBefore(el('p', 'note alert', msg), t.querySelector('.startbar'));
}

// ------------------------------------------------------------------ 설정 창 · 전체 지도
let setKey = null;
function openSettings() {
  $('#settings').hidden = false;
  document.body.classList.add('locked');
  setKey = (e) => { if (e.key === 'Escape') { e.preventDefault(); closeSettings(); } };
  addEventListener('keydown', setKey);
  $('#settings-close').focus({ preventScroll: true });
}
function closeSettings() {
  $('#settings').hidden = true;
  document.body.classList.remove('locked');
  if (setKey) removeEventListener('keydown', setKey);
  setKey = null;
  $('#open-settings').focus({ preventScroll: true });
}
function bindHome() {
  $('#open-settings').addEventListener('click', openSettings);
  $('#settings-close').addEventListener('click', closeSettings);
  $('#settings').addEventListener('click', (e) => { if (e.target.id === 'settings') closeSettings(); });
  $('#map-toggle').addEventListener('click', () => {
    const w = $('#map-wrap');
    w.hidden = !w.hidden;
    $('#map-toggle').setAttribute('aria-expanded', String(!w.hidden));
    $('#map-toggle').textContent = w.hidden ? '전체 지도' : '지도 접기';
  });
  $('#map-unbuilt').addEventListener('change', (e) => { G.showUnbuilt = e.target.checked; renderMap($('#map')); });
}

// ------------------------------------------------------------------ 설정
async function bindSettings() {
  const s = G.settings;
  $('#set-min').value = String(s.minutes);
  $('#set-new').value = String(s.newPerDay);
  $('#set-time').value = String(s.timeScale || 1);
  $('#set-boost').value = s.schemaBoost ? '1' : '0';
  $('#set-test').checked = !!s.testMode;
  const save = async () => {
    s.minutes = +$('#set-min').value;
    s.capMinutes = Math.max(15, s.minutes + 5);
    s.newPerDay = +$('#set-new').value;
    s.timeScale = +$('#set-time').value || 1;
    s.schemaBoost = $('#set-boost').value === '1';
    s.testMode = $('#set-test').checked;
    await store.kvSet('settings', s);
    renderHome();
  };
  ['#set-min', '#set-new', '#set-time', '#set-boost', '#set-test'].forEach((id) => $(id).addEventListener('change', save));
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
  bindHome();
  await showSync();
  renderHome();
  document.body.dataset.ready = '1';
  syncNow({ quiet: true });
}

main();
