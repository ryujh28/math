// 동기화 검사: 가짜 Gist 서버 + 기기 두 대 (각자 메모리 저장소)
import assert from 'node:assert/strict';
import { makeSync, ownFiles, DESCRIPTION } from '../app/js/sync.js';

// ---------- 가짜 GitHub
function fakeGitHub({ token = 'ghp_ok', truncateOver = Infinity } = {}) {
  const gists = new Map();
  let n = 0;
  const calls = [];
  const view = (g) => ({
    id: g.id, description: g.description, html_url: `https://gist.github.com/${g.id}`,
    files: Object.fromEntries(Object.entries(g.files).map(([k, v]) => {
      const big = v.content.length > truncateOver;
      return [k, { filename: k, size: Buffer.byteLength(v.content), truncated: big, content: big ? v.content.slice(0, truncateOver) : v.content,
        raw_url: `https://gist.githubusercontent.com/raw/${g.id}/${k}` }];
    })),
  });
  const json = (status, body) => ({ status, ok: status < 300, json: async () => body, text: async () => JSON.stringify(body) });
  async function fetch(url, opt = {}) {
    calls.push(`${opt.method || 'GET'} ${url.replace('https://api.github.com', '')}`);
    if (url.startsWith('https://gist.githubusercontent.com/raw/')) {
      const [, , , , id, name] = url.split('/');
      return { status: 200, ok: true, text: async () => gists.get(id).files[name].content };
    }
    if (opt.headers?.Authorization !== `Bearer ${token}`) return json(401, { message: 'Bad credentials' });
    const path = url.replace('https://api.github.com', '');
    const body = opt.body ? JSON.parse(opt.body) : null;
    if (path === '/user') return json(200, { login: 'ryujh28' });
    if (path.startsWith('/gists?')) return json(200, [...gists.values()].map((g) => ({ id: g.id, description: g.description, html_url: '' })));
    if (path === '/gists' && opt.method === 'POST') {
      const id = `g${++n}`;
      gists.set(id, { id, description: body.description, public: body.public, files: Object.fromEntries(Object.entries(body.files).map(([k, v]) => [k, { content: v.content }])) });
      return json(201, view(gists.get(id)));
    }
    const m = path.match(/^\/gists\/(\w+)$/);
    if (m) {
      const g = gists.get(m[1]);
      if (!g) return json(404, {});
      if (opt.method === 'PATCH') for (const [k, v] of Object.entries(body.files)) g.files[k] = { content: v.content };
      return json(200, view(g));
    }
    return json(404, {});
  }
  return { fetch, gists, calls };
}

// ---------- 메모리 저장소 (store.js와 같은 모양)
function memStore(device) {
  const log = new Map();
  const kv = new Map([['device', device]]);
  let t = Date.UTC(2026, 10, 25, 12);
  return {
    async allAttempts() { return [...log.values()]; },
    async mergeAttempts(rows) { let k = 0; for (const r of rows) if (r?.id && !log.has(r.id)) { log.set(r.id, r); k++; } return k; },
    async kvGet(k, d = null) { return kv.has(k) ? structuredClone(kv.get(k)) : d; },
    async kvSet(k, v) { kv.set(k, structuredClone(v)); },
    async deviceId() { return device; },
    add(unit, dt = 60e3) { t += dt; const r = { id: `${device}-${log.size}`, ts: t, device, unit, grade: 3 }; log.set(r.id, r); return r; },
    setTime(x) { t = x; },
    log,
  };
}

const gh = fakeGitHub();
const phone = memStore('phone1');
const mac = memStore('mac0001');
const P = makeSync(phone, gh.fetch);
const M = makeSync(mac, gh.fetch);

// 1. 잘못된 토큰
await assert.rejects(() => P.connect('nope'), (e) => e.kind === 'auth');
assert.equal(await P.config(), null);

// 2. 첫 기기 연결 → 비밀 Gist 생성
for (let i = 0; i < 5; i++) phone.add(`u${i}`);
let c = await P.connect(' ghp_ok \n');
assert.equal(c.created, true);
const gid = c.cfg.gistId;
assert.equal(gh.gists.get(gid).public, false);
assert.equal(gh.gists.get(gid).description, DESCRIPTION);
let r = await P.syncNow();
assert.deepEqual([r.pulled, r.pushed], [0, 5]);
assert.ok(gh.gists.get(gid).files['log-phone1-202611.json']);

// 3. 둘째 기기: 같은 토큰이면 기존 Gist를 찾아 붙는다
for (let i = 0; i < 3; i++) mac.add(`m${i}`);
c = await M.connect('ghp_ok');
assert.equal(c.created, false);
assert.equal(c.cfg.gistId, gid);
r = await M.syncNow();
assert.deepEqual([r.pulled, r.pushed], [5, 3]);
assert.equal(mac.log.size, 8);

// 4. 폰이 다시 동기화 → 맥 기록 3개를 받고, 올릴 것은 없다
const before = gh.calls.length;
r = await P.syncNow();
assert.deepEqual([r.pulled, r.pushed], [3, 0]);
assert.equal(phone.log.size, 8);
assert.ok(!gh.calls.slice(before).some((x) => x.startsWith('PATCH')), '바뀐 게 없으면 올리지 않음');

// 5. 바뀐 게 없으면 받기도 0, 내 파일은 다시 내려받지 않음
r = await P.syncNow();
assert.deepEqual([r.pulled, r.pushed], [0, 0]);

// 6. 동시에 플레이: 두 기기가 각자 쌓은 뒤 동기화해도 잃는 것 없음
phone.add('x1'); phone.add('x2'); mac.add('y1');
await M.syncNow(); await P.syncNow(); await M.syncNow();
assert.equal(phone.log.size, 11);
assert.equal(mac.log.size, 11);
assert.deepEqual([...phone.log.keys()].sort(), [...mac.log.keys()].sort());

// 7. 달이 바뀌면 새 파일, 지난달 파일은 다시 올리지 않음
phone.setTime(Date.UTC(2026, 11, 2, 9));
phone.add('dec');
const b2 = gh.calls.length;
await P.syncNow();
assert.ok(gh.gists.get(gid).files['log-phone1-202612.json']);
const patch = gh.calls.slice(b2).filter((x) => x.startsWith('PATCH'));
assert.equal(patch.length, 1);
assert.equal(JSON.parse(gh.gists.get(gid).files['log-phone1-202612.json'].content).length, 1);
await M.syncNow();
assert.equal(mac.log.size, 12);

// 8. 큰 파일(응답에서 잘림)은 raw_url로 받는다
const gh2 = fakeGitHub({ truncateOver: 200 });
const a = memStore('aaaa'), b = memStore('bbbb');
for (let i = 0; i < 30; i++) a.add(`k${i}`);
const A = makeSync(a, gh2.fetch), B = makeSync(b, gh2.fetch);
await A.connect('ghp_ok'); await A.syncNow();
await B.connect('ghp_ok'); r = await B.syncNow();
assert.equal(r.pulled, 30);
assert.ok(gh2.calls.some((x) => x.includes('gist.githubusercontent.com')));

// 9. 브라우저 데이터를 지운 기기(새 기기 id)도 Gist에서 전부 되살린다
const fresh = memStore('newdev1');
const F = makeSync(fresh, gh.fetch);
await F.connect('ghp_ok');
r = await F.syncNow();
assert.equal(r.pulled, 12);

// 10. ownFiles는 내 기록만, 달별로
const f = ownFiles([...phone.log.values()], 'phone1');
assert.deepEqual([...f.keys()].sort(), ['log-phone1-202611.json', 'log-phone1-202612.json']);

// 11. 연결 해제
await P.disconnect();
assert.equal(await P.config(), null);
assert.equal(await P.syncNow(), null);

console.log('sync: 모두 통과');
