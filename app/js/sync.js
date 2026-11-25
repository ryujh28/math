// 기기 간 동기화: 비밀 GitHub Gist 하나에 기기별·월별 기록 파일을 둔다.
//   log-<기기 id>-<YYYYMM>.json  = 그 기기가 그 달에 남긴 시도 기록 배열
// 각 기기는 자기 파일만 쓰고, 모든 파일을 읽어 id 기준으로 합친다.
// 그래서 두 기기가 동시에 플레이해도 덮어쓰기 충돌이 없다. 복습 상태는 합친 기록을 다시 계산해 얻는다.

const API = 'https://api.github.com';
export const DESCRIPTION = "Isn't she lovely — 학습 기록 (자동 생성, 지우지 마세요)";
const FILE_RE = /^log-([A-Za-z0-9]+)-(\d{6})\.json$/;

export function monthKey(ts) {
  const d = new Date(ts);
  return `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
}

/** 이 기기 기록을 달별 파일로 묶는다. */
export function ownFiles(log, device) {
  const by = new Map();
  for (const r of log) {
    if (r.device !== device) continue;
    const name = `log-${device}-${monthKey(r.ts)}.json`;
    if (!by.has(name)) by.set(name, []);
    by.get(name).push(r);
  }
  for (const rows of by.values()) rows.sort((a, b) => a.ts - b.ts || (a.id < b.id ? -1 : 1));
  return by;
}

export class SyncError extends Error {
  constructor(kind, msg) {
    super(msg);
    this.kind = kind; // 'auth' | 'network' | 'notfound' | 'other'
  }
}

/**
 * store: {allAttempts, mergeAttempts, kvGet, kvSet, deviceId}
 * fetchFn: 테스트에서 가짜 Gist 서버를 넣을 수 있게
 */
export function makeSync(store, fetchFn = globalThis.fetch.bind(globalThis)) {
  async function gh(path, opt = {}, token) {
    let res;
    try {
      res = await fetchFn(API + path, {
        ...opt,
        headers: { Accept: 'application/vnd.github+json', Authorization: `Bearer ${token}`, 'X-GitHub-Api-Version': '2022-11-28',
          ...(opt.body ? { 'Content-Type': 'application/json' } : {}) },
      });
    } catch (e) {
      throw new SyncError('network', '네트워크에 연결할 수 없습니다.');
    }
    if (res.status === 401) throw new SyncError('auth', '토큰이 올바르지 않거나 만료되었습니다.');
    if (res.status === 403) throw new SyncError('auth', '토큰에 Gist 권한이 없거나 요청 한도를 넘었습니다.');
    if (res.status === 404) throw new SyncError('notfound', 'Gist를 찾을 수 없습니다.');
    if (!res.ok) throw new SyncError('other', `GitHub 응답 ${res.status}`);
    return res.status === 204 ? null : res.json();
  }

  async function config() {
    return (await store.kvGet('sync', null)) || null;
  }

  /** 토큰으로 연결: 같은 설명의 Gist가 있으면 그것을, 없으면 새 비밀 Gist를 만든다. */
  async function connect(token) {
    token = token.trim();
    const user = await gh('/user', {}, token);
    let gist = null;
    for (let page = 1; page <= 5 && !gist; page++) {
      const list = await gh(`/gists?per_page=100&page=${page}`, {}, token);
      gist = list.find((g) => g.description === DESCRIPTION) || null;
      if (list.length < 100) break;
    }
    let created = false;
    if (!gist) {
      gist = await gh('/gists', {
        method: 'POST',
        body: JSON.stringify({
          description: DESCRIPTION, public: false,
          files: { 'README.md': { content: "# Isn't she lovely 기록\n\nryujh28.github.io/math 가 자동으로 관리하는 파일입니다. 기기마다 `log-<기기>-<월>.json`을 씁니다.\n" } },
        }),
      }, token);
      created = true;
    }
    const cfg = { token, gistId: gist.id, login: user.login, url: gist.html_url, pushed: {}, seen: {}, last: null };
    await store.kvSet('sync', cfg);
    return { created, cfg };
  }

  async function disconnect() {
    await store.kvSet('sync', null);
  }

  /** 한 번 동기화: 받아서 합치고, 이 기기 파일 중 바뀐 달만 올린다. {pulled, pushed} */
  async function syncNow() {
    const cfg = await config();
    if (!cfg) return null;
    const device = await store.deviceId();
    // 1) 받기
    const gist = await gh(`/gists/${cfg.gistId}`, {}, cfg.token);
    let pulled = 0;
    const seen = { ...(cfg.seen || {}) };
    for (const [name, f] of Object.entries(gist.files || {})) {
      if (!FILE_RE.test(name)) continue;
      const sig = `${f.size}`;
      if (seen[name] === sig) continue; // 지난번 이후 안 바뀐 파일
      let text = f.content;
      if (f.truncated || text == null) {
        try {
          const r = await fetchFn(f.raw_url);
          text = await r.text();
        } catch (e) {
          throw new SyncError('network', '기록 파일을 내려받지 못했습니다.');
        }
      }
      let rows = [];
      try { rows = JSON.parse(text); } catch (e) { continue; }
      if (Array.isArray(rows)) pulled += await store.mergeAttempts(rows);
      seen[name] = sig;
    }
    // 2) 올리기: 이 기기 기록 중 개수가 달라진 달만
    const mine = ownFiles(await store.allAttempts(), device);
    const pushedMap = { ...(cfg.pushed || {}) };
    const files = {};
    for (const [name, rows] of mine) {
      const remote = gist.files?.[name];
      if (pushedMap[name] === rows.length && remote) continue;
      files[name] = { content: JSON.stringify(rows) };
    }
    let pushed = 0;
    if (Object.keys(files).length) {
      const out = await gh(`/gists/${cfg.gistId}`, { method: 'PATCH', body: JSON.stringify({ files }) }, cfg.token);
      for (const name of Object.keys(files)) {
        pushed += mine.get(name).length - (pushedMap[name] || 0);
        pushedMap[name] = mine.get(name).length;
        const f = out?.files?.[name];
        if (f) seen[name] = `${f.size}`; // 내가 방금 쓴 파일은 다시 받을 필요 없음
      }
    }
    const next = { ...cfg, seen, pushed: pushedMap, last: Date.now() };
    await store.kvSet('sync', next);
    return { pulled, pushed: Math.max(0, pushed), cfg: next };
  }

  return { config, connect, disconnect, syncNow };
}
