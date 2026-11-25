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
    line.className = 'mline';
    renderPrompt(line, part);
    el.appendChild(line);
  }
  return el;
}

/** 일반 문장 안의 $…$ 구간만 KaTeX로 그린 HTML. 나머지는 이스케이프한다. */
export function rich(text) {
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  return String(text ?? '').split(/(\$\$[^$]+\$\$|\$[^$]+\$)/g).map((part) => {
    if (part.length > 4 && part.startsWith('$$') && part.endsWith('$$'))
      return window.katex.renderToString(part.slice(2, -2), { throwOnError: false, displayMode: true, strict: 'ignore' });
    if (part.length > 2 && part.startsWith('$') && part.endsWith('$'))
      return window.katex.renderToString(part.slice(1, -1), { throwOnError: false, displayMode: false, strict: 'ignore' });
    return esc(part);
  }).join('');
}

export function setRich(el, text) {
  el.innerHTML = rich(text);
  return el;
}

// ------------------------------------------------------------------ 좁은 화면 대응
/**
 * 문제 TeX를 '글자'와 '수식 조각'으로 나눈다. 최상위의 \text{…}는 HTML 글자로 빼서 자연스럽게 줄바꿈되게 하고,
 * 수식은 최상위 쉼표 구분(,\  ,\quad  \qquad)에서 잘라 조각마다 따로 그린다. 괄호·\left…\right·\begin…\end 안은 자르지 않는다.
 */
export function splitPrompt(tex) {
  const parts = [];
  let math = '', depth = 0, i = 0;
  const flush = () => {
    const m = math.replace(/^(\s|\\[ ;,!]|\\q?quad)+|(\s|\\[ ;,!]|\\q?quad|,)+$/g, '');
    if (m) parts.push({ math: m });
    math = '';
  };
  const text = (t) => {
    const last = parts[parts.length - 1];
    if (last && last.text != null) last.text += t; else parts.push({ text: t });
  };
  while (i < tex.length) {
    const rest = tex.slice(i);
    if (depth === 0 && rest.startsWith('\\text{')) {
      let j = i + 6, d = 1;
      while (j < tex.length && d) { if (tex[j] === '{') d++; else if (tex[j] === '}') d--; j++; }
      flush();
      text(tex.slice(i + 6, j - 1));
      i = j;
      continue;
    }
    let m;
    if (depth === 0 && (m = rest.match(/^(,\s*\\(?: |quad|qquad)\s*|\\qquad\s*)/))) {
      flush();
      text(rest.startsWith(',') ? ', ' : ' ');
      i += m[0].length;
      continue;
    }
    if ((m = rest.match(/^\\(left|begin)\b/))) depth++;
    else if ((m = rest.match(/^\\(right|end)\b/))) depth--;
    else if (rest[0] === '\\' && rest.length > 1) { math += rest.slice(0, 2); i += 2; continue; }
    else if (rest[0] === '{') depth++;
    else if (rest[0] === '}') depth--;
    math += rest[0];
    i++;
  }
  flush();
  // 앞뒤 글자의 남는 공백 정리
  for (const p of parts) if (p.text != null) p.text = p.text.replace(/\s+/g, ' ');
  return parts;
}

/** 줄바꿈되는 문제 표시: 글자는 그대로, 수식 조각은 한 덩어리씩. */
export function renderPrompt(el, tex) {
  el.textContent = '';
  el.classList.add('flow');
  for (const p of splitPrompt(tex)) {
    if (p.text != null) {
      el.appendChild(document.createTextNode(p.text));
    } else {
      const s = document.createElement('span');
      s.className = 'mchunk';
      render(s, p.math);
      el.appendChild(s);
    }
  }
  return el;
}

/** 상자보다 넓은 수식은 글자 크기를 줄여 맞춘다 (최소 55%). 그래도 넓으면 그 상자 안에서만 가로 스크롤. */
export function shrink(box, min = 0.55) {
  const k = box.querySelector('.katex');
  if (!k || !box.clientWidth) return;
  k.style.fontSize = '';
  let f = 1;
  for (let n = 0; n < 4 && box.scrollWidth > box.clientWidth + 1; n++) {
    f = Math.max(min, f * (box.clientWidth / box.scrollWidth) * 0.97);
    k.style.fontSize = `${(1.21 * f).toFixed(3)}em`;
    if (f === min) break;
  }
}

/** 카드 안의 수식들을 화면 폭에 맞춘다. 보기 하나라도 넘치면 보기를 한 줄에 하나씩. */
export function fit(root) {
  const opts = root.querySelector('.opts');
  if (opts) {
    opts.classList.remove('one');
    const btns = [...opts.querySelectorAll('.opt')];
    btns.forEach((b) => { const k = b.querySelector('.katex'); if (k) k.style.fontSize = ''; });
    if (btns.some((b) => b.scrollWidth > b.clientWidth + 1)) opts.classList.add('one');
  }
  root.querySelectorAll('.mchunk, .opt, .blk, .step, .mline').forEach((b) => shrink(b));
}
