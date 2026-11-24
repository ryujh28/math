// KaTeX 렌더링 (vendor/katex/katex.min.js가 전역 katex를 제공한다)
export function render(el, tex, display = false) {
  if (!display) tex = '\\displaystyle ' + tex;
  try {
    window.katex.render(tex, el, { throwOnError: false, displayMode: display, strict: 'ignore' });
  } catch (e) {
    el.textContent = tex;
  }
  return el;
}

export function html(tex, display = false) {
  if (!display) tex = '\\displaystyle ' + tex;
  return window.katex.renderToString(tex, { throwOnError: false, displayMode: display, strict: 'ignore' });
}

/** 팩 안의 모든 TeX를 엄격 모드로 렌더해 실패 목록을 돌려준다. */
export function validatePack(pack) {
  const bad = [];
  const tryOne = (tex, where) => {
    try {
      window.katex.renderToString(tex, { throwOnError: true, strict: 'ignore' });
    } catch (e) {
      bad.push({ where, tex, msg: String(e.message || e).slice(0, 120) });
    }
  };
  let n = 0;
  for (const it of pack.items) {
    if (it.type === 'mcq') {
      [it.prompt, it.answer, ...it.wrong.map((w) => w.tex)].forEach((t) => (n++, tryOne(t, it.id)));
    } else if (it.type === 'order') {
      [it.problem, ...it.steps, ...it.decoys.map((d) => d.tex)].forEach((t) => (n++, tryOne(t, it.id)));
    }
  }
  return { total: n, bad };
}

/** 문제 TeX를 ',\quad'에서 나눠 여러 줄로 렌더 (좁은 화면에서 넘치지 않게). */
export function renderProblem(el, tex) {
  el.textContent = '';
  for (const part of tex.split(/,\\quad\s*/)) {
    const line = document.createElement('div');
    render(line, part, true);
    el.appendChild(line);
  }
  return el;
}
