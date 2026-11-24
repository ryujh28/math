// M0 점검 화면. M1에서 실제 게임 화면(홈·세션)으로 바뀐다.
import { loadIndex, loadBuiltPacks } from './packs.js';
import * as store from './store.js';
import * as E from './engine.js';
import { render, html, validatePack, renderProblem } from './tex.js';

const $ = (s) => document.querySelector(s);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};
const shuffle = (a) => {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
};

let index, packs, states = new Map(), testMode = false;
let selCh = 10, selUnit = null, cur = null, errName = {};

// ------------------------------------------------------------ 점검
function check(label, ok, detail) {
  const li = el('li', ok ? 'ok' : 'fail');
  const body = el('div', null, label);
  if (detail) body.appendChild(el('small', null, detail));
  li.appendChild(body);
  $('#check-list').appendChild(li);
  return ok;
}

async function runChecks() {
  $('#check-list').textContent = '';
  check('팩 목록(index.json)', !!index, `${index.chapters.length}개 장, 만들어진 장: ${index.chapters.filter((c) => c.file).map((c) => c.id).join(', ') || '없음'}`);
  for (const [id, p] of packs) {
    check(`${id}장 팩`, p.units.length > 0 && p.items.length > 0, `단위 ${p.units.length}개, 문제 ${p.items.length}개 (빌드 ${p.built})`);
    const v = validatePack(p);
    check(`${id}장 수식 렌더링 (KaTeX)`, v.bad.length === 0,
      v.bad.length ? `${v.total}개 중 ${v.bad.length}개 실패: ${v.bad.slice(0, 2).map((b) => b.where + ' ' + b.msg).join(' / ')}` : `${v.total}개 수식 모두 렌더링됨`);
  }
  const persistent = await store.persistent();
  await store.kvSet('selftest', 42);
  const back = await store.kvGet('selftest');
  check('기기 저장소 (IndexedDB)', persistent && back === 42, persistent ? '쓰기·읽기 확인' : 'IndexedDB를 쓸 수 없어 메모리에 저장 중 (새로고침하면 사라짐)');
  const t0 = Date.now() - 30 * 864e5;
  const fake = [3, 3, 3].map((g, i) => ({ id: 'x' + i, unit: 'u', grade: g, ts: t0 + i * 3 * 864e5 }));
  const st = E.replay(fake).get('u');
  const r1 = E.retrievability(st, new Date(st.lastTs + 864e5));
  const r2 = E.retrievability(st, new Date(st.lastTs + 60 * 864e5));
  check('복습 엔진 (FSRS)', r1 > r2 && r2 > 0, `안정도 ${st.card.stability.toFixed(1)}일, R: 1일 뒤 ${(r1 * 100).toFixed(0)}% → 60일 뒤 ${(r2 * 100).toFixed(0)}%`);
}

// ------------------------------------------------------------ 지도
function masteryMap() {
  const m = new Map();
  for (const [id, p] of packs) m.set(id, E.chapterMastery(p, states));
  return m;
}

function drawMap() {
  const map = $('#map');
  map.textContent = '';
  const mm = masteryMap();
  const parts = [...new Set(index.chapters.map((c) => c.part))];
  for (const part of parts) {
    map.appendChild(el('div', 'part', part));
    const g = el('div', 'tiles');
    for (const c of index.chapters.filter((x) => x.part === part)) {
      const open = E.isUnlocked(c, mm, { testMode, startIds: index.chapters.filter((x) => x.start_open).map((x) => x.id) });
      const b = el('button', 'tile ' + (c.file ? (open ? 'open' : 'locked') : 'unbuilt') + (c.id === selCh ? ' sel' : ''));
      b.appendChild(el('b', null, `${c.id}장 · ${c.file ? (open ? '열림' : '잠김') : '준비 중'}`));
      b.appendChild(el('span', null, c.title));
      const bar = el('div', 'bar');
      const fill = el('i');
      fill.style.width = `${Math.round((mm.get(c.id) || 0) * 100)}%`;
      bar.appendChild(fill);
      b.appendChild(bar);
      if (c.file) b.addEventListener('click', () => { selCh = c.id; selUnit = null; drawMap(); drawChapter(); });
      else b.disabled = true;
      g.appendChild(b);
    }
    map.appendChild(g);
  }
}

// ------------------------------------------------------------ 장 상세
function dueText(st) {
  if (!st) return '—';
  const d = st.card.due.getTime() - Date.now();
  if (d <= 0) return '지금';
  const m = d / 6e4;
  if (m < 60) return `${Math.ceil(m)}분 후`;
  if (m < 1440) return `${Math.round(m / 60)}시간 후`;
  return `${Math.round(m / 1440)}일 후`;
}

function statusText(st) {
  if (!st) return '새 단위';
  if (E.isMastered(st)) return '숙련';
  if (E.isDue(st)) return '복습 필요';
  return '학습 중';
}

function drawChapter() {
  const p = packs.get(selCh);
  if (!p) return;
  const c = index.chapters.find((x) => x.id === selCh);
  const open = E.isUnlocked(c, masteryMap(), { testMode, startIds: index.chapters.filter((x) => x.start_open).map((x) => x.id) });
  $('#chapter').hidden = false;
  $('#ch-title').textContent = `${p.chapter.id}장 ${p.chapter.title}`;
  $('#ch-meta').textContent = `${p.chapter.part} · ${p.chapter.level} · ${open ? '열림' : '잠김 (테스트 모드에서 열 수 있음)'} · 숙련 ${Math.round(E.chapterMastery(p, states) * 100)}%`;
  $('#ch-summary').textContent = p.chapter.summary;
  const counts = {};
  p.items.forEach((it) => (counts[it.unit] = (counts[it.unit] || 0) + 1));
  const tb = $('#unit-rows');
  tb.textContent = '';
  for (const u of p.units) {
    const st = states.get(u.id);
    const tr = el('tr', u.id === selUnit ? 'sel' : '');
    tr.appendChild(el('td', null, u.title));
    tr.appendChild(el('td', null, u.kind === 'atom' ? '사실 원자' : '풀이 뼈대'));
    tr.appendChild(el('td', null, u.tiers.join('·')));
    tr.appendChild(el('td', 'num', String(counts[u.id] || 0)));
    tr.appendChild(el('td', null, statusText(st)));
    const td = el('td');
    const r = el('span', 'rust');
    const fill = el('i');
    fill.style.width = `${Math.round(E.retrievability(st) * 100)}%`;
    r.appendChild(fill);
    r.title = st ? `기억 유지 확률 ${Math.round(E.retrievability(st) * 100)}%` : '아직 안 배움';
    td.appendChild(r);
    tr.appendChild(td);
    tr.appendChild(el('td', null, dueText(st)));
    tr.addEventListener('click', () => { selUnit = u.id; drawChapter(); showSample(); });
    tb.appendChild(tr);
  }
}

// ------------------------------------------------------------ 샘플 문제
function showSample() {
  const p = packs.get(selCh);
  const u = p.units.find((x) => x.id === selUnit);
  if (!u) return;
  const st = states.get(u.id);
  const tier = E.tierFor(u, st);
  const pool = p.items.filter((it) => it.unit === u.id);
  const atTier = pool.filter((it) => it.tier === tier);
  const item = (atTier.length ? atTier : pool)[Math.floor(Math.random() * (atTier.length || pool.length))];
  cur = { unit: u, item, t0: performance.now(), done: false };
  $('#sample').hidden = false;
  $('#sample-title').textContent = `${u.title} · 단계 ${item.tier}`;
  $('#sample-msg').textContent = u.hint ? '힌트: ' + u.hint : '';
  const body = $('#sample-body');
  body.textContent = '';
  if (item.type === 'mcq') {
    const pr = el('div', 'prompt');
    render(pr, item.prompt, true);
    body.appendChild(pr);
    const opts = shuffle([{ tex: item.answer, ok: true }, ...shuffle(item.wrong).slice(0, 3)]);
    const box = el('div', 'opts');
    opts.forEach((o) => {
      const b = el('button', 'opt');
      b.innerHTML = html(o.tex);
      b.addEventListener('click', () => answerMcq(o, b, box, opts));
      box.appendChild(b);
    });
    body.appendChild(box);
  } else {
    const pr = el('div', 'prompt');
    renderProblem(pr, item.problem);
    body.appendChild(pr);
    body.appendChild(el('p', 'note', '정답 단계 (순서 맞추기 화면은 M1에서 만듭니다):'));
    const list = el('div', 'steps');
    item.steps.forEach((s, i) => {
      const d = el('div', 'step');
      d.appendChild(el('small', null, `${i + 1}단계`));
      const m = el('div');
      render(m, s);
      d.appendChild(m);
      list.appendChild(d);
    });
    body.appendChild(list);
    body.appendChild(el('p', 'note', '오답 블록 후보:'));
    const dl = el('div', 'steps');
    item.decoys.forEach((dc) => {
      const d = el('div', 'step dec');
      d.appendChild(el('small', null, `${errName[dc.error] || dc.error} · ${dc.why}`));
      const m = el('div');
      render(m, dc.tex);
      d.appendChild(m);
      dl.appendChild(d);
    });
    body.appendChild(dl);
  }
}

async function answerMcq(o, btn, box, opts) {
  if (cur.done) return;
  cur.done = true;
  const ms = Math.round(performance.now() - cur.t0);
  [...box.children].forEach((b, i) => { if (opts[i].ok) b.classList.add('good'); });
  if (!o.ok) btn.classList.add('bad');
  const grade = E.gradeFor('mcq', { correct: !!o.ok, ms });
  await store.addAttempt({ unit: cur.unit.id, item: cur.item.id, mode: 'mcq', grade, ms, result: { correct: !!o.ok }, error: o.ok ? null : o.error });
  $('#sample-msg').textContent = `${o.ok ? '정답' : '오답 (' + (errName[o.error] || o.error) + ')'} · ${(ms / 1000).toFixed(1)}초 → ${E.GRADE_NAME[grade]}로 기록`;
  await refresh();
}

async function manualGrade(g) {
  if (!cur) return;
  await store.addAttempt({ unit: cur.unit.id, item: cur.item.id, mode: 'manual', grade: g, ms: 0, result: {} });
  $('#sample-msg').textContent = `${E.GRADE_NAME[g]}로 기록했습니다. 다음 복습: ${dueText(E.replay(await store.allAttempts()).get(cur.unit.id))}`;
  await refresh();
}

// ------------------------------------------------------------ 기록
async function drawLog() {
  const log = await store.allAttempts();
  const devices = new Set(log.map((r) => r.device));
  $('#log-stats').textContent = `시도 ${log.length}회 · 단위 ${states.size}개 · 기기 ${devices.size}대 · 이 기기 ${await store.deviceId()}`;
}

async function refresh() {
  states = E.replay(await store.allAttempts());
  drawMap();
  drawChapter();
  await drawLog();
}

function bind() {
  $('#sample-next').addEventListener('click', showSample);
  $('#grades').addEventListener('click', (e) => { const g = e.target.closest('[data-g]'); if (g) manualGrade(+g.dataset.g); });
  $('#test-mode').addEventListener('change', async (e) => { testMode = e.target.checked; await store.kvSet('testMode', testMode); drawMap(); drawChapter(); });
  $('#log-copy').addEventListener('click', async () => {
    const txt = JSON.stringify(await store.allAttempts());
    try { await navigator.clipboard.writeText(txt); $('#log-stats').textContent += ' · 복사됨'; }
    catch (e) { $('#import-box').hidden = false; $('#import-text').value = txt; }
  });
  $('#log-import-open').addEventListener('click', () => { $('#import-box').hidden = !$('#import-box').hidden; });
  $('#log-import').addEventListener('click', async () => {
    try {
      const rows = JSON.parse($('#import-text').value);
      const n = await store.mergeAttempts(Array.isArray(rows) ? rows : []);
      $('#import-text').value = '';
      $('#import-box').hidden = true;
      await refresh();
      $('#log-stats').textContent += ` · ${n}개 합침`;
    } catch (e) { $('#log-stats').textContent = '가져오기 실패: JSON 형식이 아닙니다.'; }
  });
  $('#log-reset').addEventListener('click', () => { $('#confirm-box').hidden = false; });
  $('#log-reset-no').addEventListener('click', () => { $('#confirm-box').hidden = true; });
  $('#log-reset-yes').addEventListener('click', async () => { await store.clearLog(); $('#confirm-box').hidden = true; await refresh(); });
}

async function main() {
  bind();
  try {
    index = await loadIndex();
    packs = await loadBuiltPacks(index);
  } catch (e) {
    $('#check-list').textContent = '';
    check('팩 불러오기', false, String(e) + ' — 로컬에서는 파일을 직접 열지 말고 간단한 웹 서버로 여세요 (README 참고).');
    return;
  }
  errName = Object.fromEntries(index.errors.map((x) => [x.id, x.name]));
  testMode = !!(await store.kvGet('testMode', false));
  $('#test-mode').checked = testMode;
  await runChecks();
  await refresh();
  document.body.dataset.ready = '1';
}

main();
