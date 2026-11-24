// 기기 저장소: 시도 기록을 추가 전용 로그로 쌓는다.
// 복습 상태는 저장하지 않고, 이 로그를 engine.replay()로 다시 계산한다.
// 그래서 기기 간 동기화(M2)는 로그를 id 기준으로 합치기만 하면 된다.

const DB_NAME = 'isl';
const DB_VER = 1;
let dbp = null;
const mem = { log: new Map(), kv: new Map() }; // IndexedDB를 못 쓰는 환경용

function open() {
  if (dbp) return dbp;
  dbp = new Promise((resolve) => {
    try {
      const req = indexedDB.open(DB_NAME, DB_VER);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains('log')) db.createObjectStore('log', { keyPath: 'id' });
        if (!db.objectStoreNames.contains('kv')) db.createObjectStore('kv', { keyPath: 'k' });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    } catch (e) {
      resolve(null);
    }
  });
  return dbp;
}

function tx(db, store, mode, fn) {
  return new Promise((resolve, reject) => {
    const t = db.transaction(store, mode);
    const st = t.objectStore(store);
    const out = fn(st);
    t.oncomplete = () => resolve(out && 'result' in out ? out.result : undefined);
    t.onerror = () => reject(t.error);
  });
}

export async function persistent() {
  return (await open()) !== null;
}

export function newId() {
  if (globalThis.crypto && crypto.randomUUID) return crypto.randomUUID();
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
}

export async function kvGet(k, dflt = null) {
  const db = await open();
  if (!db) return mem.kv.has(k) ? mem.kv.get(k) : dflt;
  const row = await tx(db, 'kv', 'readonly', (st) => st.get(k));
  return row ? row.v : dflt;
}

export async function kvSet(k, v) {
  const db = await open();
  if (!db) return void mem.kv.set(k, v);
  await tx(db, 'kv', 'readwrite', (st) => st.put({ k, v }));
}

export async function deviceId() {
  let id = await kvGet('device');
  if (!id) {
    id = newId().slice(0, 8);
    await kvSet('device', id);
  }
  return id;
}

/** 시도 하나를 기록한다. {unit, item, mode, grade(1–4), ms, result, error?} */
export async function addAttempt(a) {
  const row = { id: newId(), ts: Date.now(), device: await deviceId(), ...a };
  const db = await open();
  if (!db) mem.log.set(row.id, row);
  else await tx(db, 'log', 'readwrite', (st) => st.put(row));
  return row;
}

export async function allAttempts() {
  const db = await open();
  if (!db) return [...mem.log.values()];
  return (await tx(db, 'log', 'readonly', (st) => st.getAll())) || [];
}

/** 다른 기기의 로그를 합친다. 이미 있는 id는 건너뛴다. 추가된 개수를 돌려준다. */
export async function mergeAttempts(rows) {
  const have = new Set((await allAttempts()).map((r) => r.id));
  const fresh = rows.filter((r) => r && r.id && !have.has(r.id));
  const db = await open();
  if (!db) fresh.forEach((r) => mem.log.set(r.id, r));
  else if (fresh.length) await tx(db, 'log', 'readwrite', (st) => fresh.forEach((r) => st.put(r)));
  return fresh.length;
}

export async function clearLog() {
  const db = await open();
  if (!db) return void mem.log.clear();
  await tx(db, 'log', 'readwrite', (st) => st.clear());
}
