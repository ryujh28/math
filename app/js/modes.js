// 게임 모드: 미니멀 훈련(mcq), 순서 맞추기(order).
// 각 모드는 화면을 그리고, 플레이어가 끝내면 결과를 resolve하는 Promise를 돌려준다.
import { render, html, renderProblem, renderPrompt, rich, fit } from './tex.js';

const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};
export const shuffle = (a) => {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
};

let keyHandler = null;
function onKey(fn) {
  if (keyHandler) removeEventListener('keydown', keyHandler);
  keyHandler = fn;
  if (fn) addEventListener('keydown', fn);
}
export const clearKeys = () => onKey(null);

/** 다음으로 넘어가는 버튼 (Enter로도). */
function nextButton(box, label = '다음', extra = null) {
  return new Promise((resolve) => {
    const b = el('button', 'btn', `${label} (Enter)`);
    b.addEventListener('click', () => { onKey(null); resolve(); });
    if (extra) {
      const row = el('div', 'row');
      row.append(b, extra());
      box.appendChild(row);
    } else box.appendChild(b);
    b.focus({ preventScroll: true });
    onKey((e) => { if (e.key === 'Enter') { e.preventDefault(); onKey(null); resolve(); } });
  });
}

// ------------------------------------------------------------------ 미니멀 훈련
/** 객관식 화면(문제·시간 막대·보기)을 그린다. 채점 흐름과 분리해 두어 레이아웃만 따로 검사할 수 있다. */
export function mcqBody(root, item) {
  root.textContent = '';
  const pr = el('div', 'prompt');
  renderPrompt(pr, item.prompt);
  root.appendChild(pr);
  const bar = el('div', 'tbar');
  const fill = el('i');
  bar.appendChild(fill);
  root.appendChild(bar);
  const opts = shuffle([{ tex: item.answer, ok: true }, ...shuffle(item.wrong).slice(0, 3)]);
  const box = el('div', 'opts');
  const btns = opts.map((o, i) => {
    const b = el('button', 'opt');
    b.innerHTML = `<small>${i + 1}</small>` + html(o.tex);
    box.appendChild(b);
    return b;
  });
  root.appendChild(box);
  fit(root);
  return { pr, fill, opts, btns, box };
}

export function playMcq(root, item, ctx) {
  return new Promise((resolve) => {
    const limit = item.tier >= 3 || item.verified === 'hand' ? 15000 : item.tier === 2 ? 12000 : 9000;
    const { fill, opts, btns } = mcqBody(root, item);
    btns.forEach((b, i) => b.addEventListener('click', () => choose(i)));
    const fb = el('div', 'fb');
    root.appendChild(fb);
    const t0 = performance.now();
    let done = false;
    const tick = setInterval(() => {
      const f = 1 - (performance.now() - t0) / limit;
      fill.style.width = `${Math.max(0, f * 100)}%`;
      if (f <= 0) choose(-1);
    }, 50);
    onKey((e) => { if ('1234'.includes(e.key) && e.key) choose(+e.key - 1); });

    async function choose(i) {
      if (done) return;
      done = true;
      clearInterval(tick);
      onKey(null);
      const ms = Math.round(performance.now() - t0);
      const o = i >= 0 ? opts[i] : null;
      const correct = !!(o && o.ok);
      btns.forEach((b, k) => { b.disabled = true; if (opts[k].ok) b.classList.add('good'); });
      if (o && !o.ok) btns[i].classList.add('bad');
      const result = { correct, ms, error: o && !o.ok ? o.error : i < 0 ? 'timeout' : null };
      if (correct) {
        fb.innerHTML = `<div><b class="ok">정답</b> · ${(ms / 1000).toFixed(1)}초</div>`;
        ctx.onCorrect?.(fb);
        setTimeout(() => resolve(result), ctx.extraPause ? 1600 : 650);
      } else {
        fb.innerHTML = `<div><b class="no">${i < 0 ? '시간 초과' : '오답'}</b>` +
          (o ? ` · ${ctx.errName(o.error)}` : '') + '</div>' + (ctx.hint ? `<p class="hint">${ctx.hintHtml || escapeHtml(ctx.hint)}</p>` : '');
        await nextButton(fb, '다음', ctx.derivButton);
        resolve(result);
      }
    }
  });
}

// ------------------------------------------------------------------ 순서 맞추기
export function playOrder(root, item, ctx) {
  return new Promise((resolve) => {
    root.textContent = '';
    const pr = el('div', 'prompt small');
    renderProblem(pr, item.problem);
    root.appendChild(pr);
    const nDec = Math.min(item.decoys.length, item.steps.length >= 5 ? 3 : 2);
    const decoys = shuffle(item.decoys).slice(0, nDec);
    const prefill = ctx.prefill || 0;
    const blocks = [...item.steps.map((t, i) => ({ tex: t, pos: i })), ...decoys.map((d) => ({ tex: d.tex, decoy: d }))];
    const sol = blocks.filter((b) => b.pos != null && b.pos < prefill).sort((a, b) => a.pos - b.pos).map((b) => ({ ...b, fixed: true }));
    let pool = shuffle(blocks.filter((b) => !(b.pos != null && b.pos < prefill)));
    const cols = el('div', 'cols');
    const left = el('div');
    left.appendChild(el('div', 'lab', '풀이'));
    const solBox = el('div', 'slots');
    left.appendChild(solBox);
    const right = el('div');
    right.appendChild(el('div', 'lab', '블록 (그럴듯한 오답이 섞여 있습니다)'));
    const poolBox = el('div', 'pool');
    right.appendChild(poolBox);
    cols.append(left, right);
    root.appendChild(cols);
    const ctl = el('div', 'row');
    const checkBtn = el('button', 'btn', '검사 (Enter)');
    const giveBtn = el('button', 'btn ghost', '정답 보기');
    ctl.append(checkBtn, giveBtn);
    root.appendChild(ctl);
    const fb = el('div', 'fb');
    root.appendChild(fb);
    const t0 = performance.now();
    let checks = 0, done = false, marks = new Map();

    function tile(b, onClick, extra = '') {
      const t = el('button', 'blk ' + extra + (b.fixed ? ' fixed' : ''));
      t.innerHTML = html(b.tex);
      if (!b.fixed) t.addEventListener('click', onClick);
      else t.disabled = true;
      return t;
    }
    function draw() {
      solBox.textContent = '';
      sol.forEach((b, i) => solBox.appendChild(tile(b, () => { if (done) return; pool.push(...sol.splice(i, 1)); marks.clear(); draw(); }, marks.get(b) || '')));
      if (!sol.length) solBox.appendChild(el('p', 'note', '블록을 눌러 순서대로 쌓으세요'));
      poolBox.textContent = '';
      pool.forEach((b, i) => poolBox.appendChild(tile(b, () => { if (done) return; sol.push(...pool.splice(i, 1)); marks.clear(); draw(); })));
      fit(root);
    }
    draw();

    function finish(gaveUp) {
      done = true;
      onKey(null);
      checkBtn.disabled = giveBtn.disabled = true;
      const ms = Math.round(performance.now() - t0);
      return { checks: Math.max(checks, 1), gaveUp, ms, refMs: item.steps.length * 20000 };
    }

    async function check() {
      if (done) return;
      checks++;
      marks.clear();
      let i = 0;
      while (i < sol.length && i < item.steps.length && sol[i].pos === i) i++;
      if (i === item.steps.length && sol.length === item.steps.length) {
        sol.forEach((b) => marks.set(b, 'done'));
        draw();
        const res = finish(false);
        fb.innerHTML = `<div><b class="ok">완성</b> · 검사 ${checks}회 · ${(res.ms / 1000).toFixed(0)}초</div>`;
        ctx.onCorrect?.(fb);
        await nextButton(fb);
        resolve(res);
        return;
      }
      let msg;
      if (i < sol.length) {
        marks.set(sol[i], 'err');
        const d = sol[i].decoy;
        msg = d ? `${i + 1}번째 줄: ${ctx.errName(d.error)} — ${rich(d.why)}` : `${i + 1}번째 줄의 순서가 맞지 않습니다.`;
      } else msg = `${i}번째 줄까지는 맞습니다. 단계가 더 필요합니다.`;
      draw();
      fb.innerHTML = `<div><b class="no">아직</b> · ${msg}</div>`;
      if (ctx.derivButton) fb.appendChild(ctx.derivButton());
    }

    async function giveUp() {
      if (done) return;
      const res = finish(true);
      fb.innerHTML = '<b class="no">정답</b>';
      const list = el('div', 'steps');
      item.steps.forEach((s, i) => {
        const d = el('div', 'step');
        d.appendChild(el('small', null, `${i + 1}단계`));
        const m = el('div');
        render(m, s);
        d.appendChild(m);
        list.appendChild(d);
      });
      fb.appendChild(list);
      fit(fb);
      if (ctx.hint) {
        const h = el('p', 'hint');
        h.innerHTML = ctx.hintHtml || escapeHtml(ctx.hint);
        fb.appendChild(h);
      }
      await nextButton(fb, '다음', ctx.derivButton);
      resolve(res);
    }

    checkBtn.addEventListener('click', check);
    giveBtn.addEventListener('click', giveUp);
    onKey((e) => { if (e.key === 'Enter' && !done) { e.preventDefault(); check(); } });
  });
}

export function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
