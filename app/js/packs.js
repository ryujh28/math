// 콘텐츠 팩 불러오기. 팩은 tools/build.py가 만든 정적 JSON이다.
const cache = new Map();
const BASE = new URL('../../packs/', import.meta.url);

async function getJSON(name) {
  if (cache.has(name)) return cache.get(name);
  const p = fetch(new URL(name, BASE), { cache: 'no-cache' }).then((r) => {
    if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`);
    return r.json();
  });
  cache.set(name, p);
  return p;
}

export const loadIndex = () => getJSON('index.json');
export const loadPack = (file) => getJSON(file);

/** 지금 만들어진 모든 팩을 불러와 장 id → 팩 맵으로. */
export async function loadBuiltPacks(index) {
  const out = new Map();
  await Promise.all(index.chapters.filter((c) => c.file).map(async (c) => out.set(c.id, await loadPack(c.file))));
  return out;
}
