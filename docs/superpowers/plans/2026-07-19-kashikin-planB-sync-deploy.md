# 貸金試験対策アプリ — Plan B: Cloudflare同期＋デプロイ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Plan A の画像リーダーの学習進捗を Cloudflare Pages Functions + KV で PC⇄スマホ同期し、Cloudflare Access で本人限定にして配信する。オフラインファースト（ネットが無くても localStorage で動作、復帰時に同期）。

**Architecture:** `functions/api/state.js`（Pages Function, KV の GET/PUT）を追加。アプリは起動時に「ローカル読込→リモート取得→フィールド単位マージ→ローカル保存＋リモート送信」。保存のたびにデバウンス送信。デプロイは Cloudflare Pages（プライベートGitHub連携）＋KV名前空間バインド＋Access。コードは私が実装/テスト、Cloudflare/GitHub のアカウント作業はユーザーが手順書に沿って実施。

**Tech Stack:** Cloudflare Pages Functions（`onRequestGet`/`onRequestPut`, ESM）, Cloudflare KV, Cloudflare Access。テスト: `node --test`（関数ハンドラ・マージ・同期をモックcontext/fetchで検証）。ローカル検証: 依存ゼロの node 製モック同期サーバ。

## Global Constraints

- AI/API/OCR は引き続き一切使わない（同期は自前のKVのみ）。
- オフラインファースト: リモート取得/送信が失敗してもアプリは localStorage で正常動作する（例外を投げてUIを止めない）。
- マージはデータ喪失を避けるフィールド単位: `read` は OR、`activityDates` は和集合、SRS は「box が大きい方／同点は due が後の方」、`note` は**ローカル優先**（今いる端末で打ったメモを勝たせる）。
- KV バインド名は `STATE_KV`。保存キーは Access 認証メール（ヘッダ `Cf-Access-Authenticated-User-Email`）、無ければ `"default"`。
- 進捗データ形は Plan A と同一: `{ pages: {[id]:{read?,box?,due?,note?}}, activityDates: [] }`。
- 画像・進捗は教材由来/個人データ。配信は必ず **Cloudflare Access 保護のプライベート**。公開URLで無認証配信しない。
- コミットは必ずパス指定 `git add <path>`。`git add -A`/`git add .` 禁止。
- JS テストは `node --test app/js/tests/*.test.js`（ディレクトリ引数不可）。関数テストは `node --test functions/tests/*.test.js`。

---

## File Structure

- `貸金試験対策アプリ/functions/api/state.js` — Pages Function（KV GET/PUT）
- `貸金試験対策アプリ/functions/tests/state.test.js` — ハンドラの node:test（mock context）
- `貸金試験対策アプリ/app/js/merge.js` — `mergeStates`（純粋）
- `貸金試験対策アプリ/app/js/sync.js` — `pullRemote`/`pushRemote`/`syncOnBoot`（fetch注入）
- `貸金試験対策アプリ/app/js/tests/merge.test.js`, `sync.test.js`
- `貸金試験対策アプリ/app/js/app.js` — 同期配線を追記
- `貸金試験対策アプリ/tools/mock_sync_server.mjs` — ローカル検証用の同期モック（node http・依存ゼロ）
- `貸金試験対策アプリ/DEPLOY.md` — Cloudflare Pages + KV + Access + プライベートGitHub の手順書
- `貸金試験対策アプリ/functions/package.json` — `{"type":"module"}`（node が functions の .js を ESM 扱いに）

---

### Task 1: 同期API（functions/api/state.js）

**Files:**
- Create: `貸金試験対策アプリ/functions/package.json`
- Create: `貸金試験対策アプリ/functions/api/state.js`
- Create: `貸金試験対策アプリ/functions/tests/state.test.js`

**Interfaces:**
- Produces:
  - `onRequestGet(context) -> Response`（KVから保存JSONを返す。無ければ `{pages:{},activityDates:[]}`）
  - `onRequestPut(context) -> Response`（リクエストbodyのJSONをKVに保存し `{ok:true}` を返す）
  - `userKey(request) -> string`（`Cf-Access-Authenticated-User-Email` か `"default"`）
  - context 形: `{ request, env: { STATE_KV: { get(key), put(key, value) } } }`

- [ ] **Step 1: functions/package.json を作成**

`貸金試験対策アプリ/functions/package.json`:
```json
{ "name": "kashikin-functions", "private": true, "type": "module" }
```

- [ ] **Step 2: 失敗するテストを書く** — `貸金試験対策アプリ/functions/tests/state.test.js`

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { onRequestGet, onRequestPut, userKey } from "../api/state.js";

function kvStub(initial = {}) {
  const data = { ...initial };
  return {
    get: async (k) => (k in data ? data[k] : null),
    put: async (k, v) => { data[k] = v; },
    _data: data,
  };
}

function req(headers = {}, body = null) {
  return {
    headers: { get: (h) => headers[h] ?? null },
    json: async () => body,
  };
}

test("userKey uses Access email header, else default", () => {
  assert.equal(userKey(req({ "Cf-Access-Authenticated-User-Email": "a@b.com" })), "a@b.com");
  assert.equal(userKey(req({})), "default");
});

test("GET returns default state when KV empty", async () => {
  const STATE_KV = kvStub();
  const res = await onRequestGet({ request: req(), env: { STATE_KV } });
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { pages: {}, activityDates: [] });
});

test("PUT stores body then GET returns it", async () => {
  const STATE_KV = kvStub();
  const state = { pages: { "p-001": { read: true } }, activityDates: ["2026-07-20"] };
  const putRes = await onRequestPut({ request: req({}, state), env: { STATE_KV } });
  assert.equal(putRes.status, 200);
  assert.deepEqual(await putRes.json(), { ok: true });

  const getRes = await onRequestGet({ request: req(), env: { STATE_KV } });
  assert.deepEqual(await getRes.json(), state);
});

test("per-user isolation by Access email", async () => {
  const STATE_KV = kvStub();
  const s = { pages: { "p-1": { read: true } }, activityDates: [] };
  await onRequestPut({ request: req({ "Cf-Access-Authenticated-User-Email": "a@b.com" }, s), env: { STATE_KV } });
  const other = await onRequestGet({ request: req({ "Cf-Access-Authenticated-User-Email": "z@z.com" }), env: { STATE_KV } });
  assert.deepEqual(await other.json(), { pages: {}, activityDates: [] });
});
```

- [ ] **Step 3: 失敗を確認**

Run: `cd 貸金試験対策アプリ && node --test functions/tests/state.test.js`
Expected: FAIL（`Cannot find module '../api/state.js'`）

- [ ] **Step 4: 実装** — `貸金試験対策アプリ/functions/api/state.js`

```javascript
const EMPTY = { pages: {}, activityDates: [] };

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export function userKey(request) {
  return request.headers.get("Cf-Access-Authenticated-User-Email") || "default";
}

export async function onRequestGet(context) {
  const key = userKey(context.request);
  const raw = await context.env.STATE_KV.get(key);
  if (!raw) return json(EMPTY);
  try {
    return json(JSON.parse(raw));
  } catch {
    return json(EMPTY);
  }
}

export async function onRequestPut(context) {
  const key = userKey(context.request);
  const body = await context.request.json();
  const state = {
    pages: body.pages ?? {},
    activityDates: body.activityDates ?? [],
  };
  await context.env.STATE_KV.put(key, JSON.stringify(state));
  return json({ ok: true });
}
```

- [ ] **Step 5: テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && node --test functions/tests/state.test.js`
Expected: PASS（4件）

- [ ] **Step 6: コミット**

```bash
git add 貸金試験対策アプリ/functions/package.json 貸金試験対策アプリ/functions/api/state.js \
        貸金試験対策アプリ/functions/tests/state.test.js
git commit -m "feat(kashikin/sync): Cloudflare Function 進捗のKV GET/PUT"
```

---

### Task 2: フィールド単位マージ（merge.js）

**Files:**
- Create: `貸金試験対策アプリ/app/js/merge.js`
- Create: `貸金試験対策アプリ/app/js/tests/merge.test.js`

**Interfaces:**
- Produces:
  - `mergeStates(local, remote) -> state`（純粋。read=OR / activityDates=和集合ソート / SRS=box大きい方,同点due後 / note=ローカル優先）

- [ ] **Step 1: 失敗するテストを書く** — `貸金試験対策アプリ/app/js/tests/merge.test.js`

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { mergeStates } from "../merge.js";

test("read is OR across devices", () => {
  const local = { pages: { "p-1": { read: true } }, activityDates: [] };
  const remote = { pages: { "p-1": { read: false }, "p-2": { read: true } }, activityDates: [] };
  const m = mergeStates(local, remote);
  assert.equal(m.pages["p-1"].read, true);
  assert.equal(m.pages["p-2"].read, true);
});

test("activityDates union sorted unique", () => {
  const local = { pages: {}, activityDates: ["2026-07-20", "2026-07-18"] };
  const remote = { pages: {}, activityDates: ["2026-07-19", "2026-07-20"] };
  assert.deepEqual(mergeStates(local, remote).activityDates,
    ["2026-07-18", "2026-07-19", "2026-07-20"]);
});

test("SRS keeps higher box; tie keeps later due", () => {
  const local = { pages: { "p-1": { box: 2, due: "2026-07-25" }, "p-2": { box: 1, due: "2026-07-21" } }, activityDates: [] };
  const remote = { pages: { "p-1": { box: 1, due: "2026-08-01" }, "p-2": { box: 1, due: "2026-07-28" } }, activityDates: [] };
  const m = mergeStates(local, remote);
  assert.deepEqual(m.pages["p-1"], { box: 2, due: "2026-07-25" }); // 高いbox
  assert.deepEqual(m.pages["p-2"], { box: 1, due: "2026-07-28" }); // 同box→遅いdue
});

test("note prefers local non-empty, falls back to remote", () => {
  const local = { pages: { "p-1": { note: "ローカルメモ" }, "p-2": {} }, activityDates: [] };
  const remote = { pages: { "p-1": { note: "旧メモ" }, "p-2": { note: "リモートメモ" } }, activityDates: [] };
  const m = mergeStates(local, remote);
  assert.equal(m.pages["p-1"].note, "ローカルメモ");
  assert.equal(m.pages["p-2"].note, "リモートメモ");
});

test("page present on only one side is kept", () => {
  const local = { pages: { "p-1": { read: true } }, activityDates: [] };
  const remote = { pages: { "p-9": { read: true, box: 0, due: "2026-07-21" } }, activityDates: [] };
  const m = mergeStates(local, remote);
  assert.equal(m.pages["p-1"].read, true);
  assert.equal(m.pages["p-9"].box, 0);
});
```

- [ ] **Step 2: 失敗を確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/merge.test.js`
Expected: FAIL（`Cannot find module '../merge.js'`）

- [ ] **Step 3: 実装** — `貸金試験対策アプリ/app/js/merge.js`

```javascript
function pickSrs(a, b) {
  const aHas = a && typeof a.box === "number";
  const bHas = b && typeof b.box === "number";
  if (!aHas && !bHas) return null;
  if (aHas && !bHas) return { box: a.box, due: a.due };
  if (bHas && !aHas) return { box: b.box, due: b.due };
  if (a.box !== b.box) return a.box > b.box ? { box: a.box, due: a.due } : { box: b.box, due: b.due };
  return (a.due ?? "") >= (b.due ?? "") ? { box: a.box, due: a.due } : { box: b.box, due: b.due };
}

function pickNote(a, b) {
  const an = a && typeof a.note === "string" && a.note !== "" ? a.note : undefined;
  if (an !== undefined) return an;
  const bn = b && typeof b.note === "string" && b.note !== "" ? b.note : undefined;
  return bn;
}

export function mergeStates(local, remote) {
  const lp = local.pages ?? {};
  const rp = remote.pages ?? {};
  const ids = new Set([...Object.keys(lp), ...Object.keys(rp)]);
  const pages = {};
  for (const id of ids) {
    const a = lp[id];
    const b = rp[id];
    const entry = {};
    if ((a && a.read) || (b && b.read)) entry.read = true;
    const srs = pickSrs(a, b);
    if (srs) { entry.box = srs.box; entry.due = srs.due; }
    const note = pickNote(a, b);
    if (note !== undefined) entry.note = note;
    pages[id] = entry;
  }
  const dates = new Set([...(local.activityDates ?? []), ...(remote.activityDates ?? [])]);
  return { pages, activityDates: [...dates].sort() };
}
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/merge.test.js`
Expected: PASS（5件）

- [ ] **Step 5: コミット**

```bash
git add 貸金試験対策アプリ/app/js/merge.js 貸金試験対策アプリ/app/js/tests/merge.test.js
git commit -m "feat(kashikin/sync): デバイス間フィールド単位マージ(データ喪失回避)"
```

---

### Task 3: 同期オーケストレーション（sync.js）

**Files:**
- Create: `貸金試験対策アプリ/app/js/sync.js`
- Create: `貸金試験対策アプリ/app/js/tests/sync.test.js`

**Interfaces:**
- Consumes: `mergeStates`（`./merge.js`）
- Produces（fetch を注入可、失敗時はオフライン扱いで例外を投げない）:
  - `ENDPOINT = "api/state"`
  - `pullRemote(fetchImpl) -> state | null`（失敗/非ok は null）
  - `pushRemote(state, fetchImpl) -> boolean`（成功可否）
  - `syncOnBoot(localState, fetchImpl) -> { state, pushed }`（pull→merge→push。pull失敗時は local をそのまま返し push もしない）

- [ ] **Step 1: 失敗するテストを書く** — `貸金試験対策アプリ/app/js/tests/sync.test.js`

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { pullRemote, pushRemote, syncOnBoot, ENDPOINT } from "../sync.js";

function okFetch(remoteState) {
  const calls = [];
  const fn = async (url, opts) => {
    calls.push({ url, opts });
    if (!opts || opts.method === undefined || opts.method === "GET") {
      return { ok: true, json: async () => remoteState };
    }
    return { ok: true, json: async () => ({ ok: true }) };
  };
  fn.calls = calls;
  return fn;
}

function failFetch() {
  return async () => { throw new Error("offline"); };
}

test("pullRemote returns remote state on success", async () => {
  const remote = { pages: { "p-1": { read: true } }, activityDates: [] };
  assert.deepEqual(await pullRemote(okFetch(remote)), remote);
});

test("pullRemote returns null when offline", async () => {
  assert.equal(await pullRemote(failFetch()), null);
});

test("pushRemote returns true on ok, sends PUT to endpoint", async () => {
  const fetchImpl = okFetch({});
  const ok = await pushRemote({ pages: {}, activityDates: [] }, fetchImpl);
  assert.equal(ok, true);
  const put = fetchImpl.calls.find((c) => c.opts && c.opts.method === "PUT");
  assert.equal(put.url, ENDPOINT);
});

test("pushRemote returns false when offline", async () => {
  assert.equal(await pushRemote({ pages: {}, activityDates: [] }, failFetch()), false);
});

test("syncOnBoot merges remote into local and pushes", async () => {
  const local = { pages: { "p-1": { note: "ローカル" } }, activityDates: ["2026-07-20"] };
  const remote = { pages: { "p-2": { read: true } }, activityDates: ["2026-07-19"] };
  const { state, pushed } = await syncOnBoot(local, okFetch(remote));
  assert.equal(pushed, true);
  assert.equal(state.pages["p-1"].note, "ローカル");
  assert.equal(state.pages["p-2"].read, true);
  assert.deepEqual(state.activityDates, ["2026-07-19", "2026-07-20"]);
});

test("syncOnBoot offline keeps local and does not push", async () => {
  const local = { pages: { "p-1": { read: true } }, activityDates: [] };
  const { state, pushed } = await syncOnBoot(local, failFetch());
  assert.deepEqual(state, local);
  assert.equal(pushed, false);
});
```

- [ ] **Step 2: 失敗を確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/sync.test.js`
Expected: FAIL（`Cannot find module '../sync.js'`）

- [ ] **Step 3: 実装** — `貸金試験対策アプリ/app/js/sync.js`

```javascript
import { mergeStates } from "./merge.js";

export const ENDPOINT = "api/state";

export async function pullRemote(fetchImpl = fetch) {
  try {
    const res = await fetchImpl(ENDPOINT, { method: "GET" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function pushRemote(state, fetchImpl = fetch) {
  try {
    const res = await fetchImpl(ENDPOINT, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(state),
    });
    return !!res.ok;
  } catch {
    return false;
  }
}

export async function syncOnBoot(localState, fetchImpl = fetch) {
  const remote = await pullRemote(fetchImpl);
  if (remote === null) return { state: localState, pushed: false };
  const merged = mergeStates(localState, remote);
  const pushed = await pushRemote(merged, fetchImpl);
  return { state: merged, pushed };
}
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/sync.test.js`
Expected: PASS（6件）

- [ ] **Step 5: コミット**

```bash
git add 貸金試験対策アプリ/app/js/sync.js 貸金試験対策アプリ/app/js/tests/sync.test.js
git commit -m "feat(kashikin/sync): 同期オーケストレーション(pull/merge/push・オフライン耐性)"
```

---

### Task 4: アプリへ同期を配線（app.js）+ ローカル検証

**Files:**
- Modify: `貸金試験対策アプリ/app/js/app.js`
- Create: `貸金試験対策アプリ/tools/mock_sync_server.mjs`

**Interfaces:**
- Consumes: `syncOnBoot`/`pushRemote`（`./sync.js`）
- 変更点:
  - boot 内で local 読込後に `syncOnBoot(state)` を await → merged state で描画
  - 保存（persist）時にデバウンス（800ms）で `pushRemote(state)` を呼ぶ
  - どの経路も失敗しても UI を止めない（オフラインファースト）

- [ ] **Step 1: app.js に同期を追記** — import に sync を追加し、`persist`/`boot` を差し替える。

`貸金試験対策アプリ/app/js/app.js` の import 群に追加:
```javascript
import { syncOnBoot, pushRemote } from "./sync.js";
```

`persist` 関数を次に置換（デバウンス送信を追加）:
```javascript
let pushTimer = null;
function persist() {
  saveState(state);
  if (pushTimer) clearTimeout(pushTimer);
  pushTimer = setTimeout(() => { pushRemote(state); }, 800);
}
```

`boot` 関数を次に置換（起動時同期を追加）:
```javascript
async function boot() {
  try {
    const res = await fetch("manifest.json");
    manifest = await res.json();
  } catch {
    manifest = { version: 1, chapters: [] };
  }
  pages = flattenPages(manifest);

  // リモート同期（失敗してもローカルで継続）
  const { state: synced } = await syncOnBoot(state);
  state = synced;
  saveState(state);

  renderTOC(els.toc, manifest, state, jump);
  if (pages.length > 0) go(0);
  refreshHeader();
}
```

- [ ] **Step 2: JS 全テストが通ることを確認**（回帰確認）

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/*.test.js`
Expected: PASS（Plan A 19 + merge 5 + sync 6 = 30件）

- [ ] **Step 3: ローカル検証用モック同期サーバを作成** — `貸金試験対策アプリ/tools/mock_sync_server.mjs`

```javascript
// 依存ゼロのローカル検証用: app/ を静的配信しつつ /api/state を in-memory KV で GET/PUT。
// 実行: node tools/mock_sync_server.mjs  (http://localhost:8123)
import http from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..", "app");
let stateStore = null; // in-memory "KV"

const TYPES = {
  ".html": "text/html", ".css": "text/css", ".js": "text/javascript",
  ".json": "application/json", ".png": "image/png", ".webmanifest": "application/manifest+json",
};

async function readBody(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  return Buffer.concat(chunks).toString("utf-8");
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  if (url.pathname === "/api/state") {
    if (req.method === "GET") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(stateStore ?? JSON.stringify({ pages: {}, activityDates: [] }));
      return;
    }
    if (req.method === "PUT") {
      stateStore = await readBody(req);
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ ok: true }));
      return;
    }
  }
  // static
  let p = normalize(url.pathname === "/" ? "/index.html" : url.pathname);
  try {
    const data = await readFile(join(ROOT, p));
    res.writeHead(200, { "content-type": TYPES[extname(p)] ?? "application/octet-stream" });
    res.end(data);
  } catch {
    res.writeHead(404); res.end("not found");
  }
});

server.listen(8123, () => console.log("mock sync server on http://localhost:8123"));
```

- [ ] **Step 4: ブラウザで同期を検証**

1. サンプル画像/manifest が無ければ生成: `cd 貸金試験対策アプリ && python3 tools/make_samples.py && python3 build_manifest.py`
2. Run（バックグラウンド）: `cd 貸金試験対策アプリ && node tools/mock_sync_server.mjs`
3. preview_start `{url: "http://localhost:8123/"}`。
4. 検証:
   - read_console_messages でエラーが無いこと
   - read_network_requests に `api/state` の GET（起動時 pull）と、操作後の PUT（デバウンス送信）が記録されること
   - 数ページ閲覧・「要復習に追加」後、javascript_tool で `fetch('api/state').then(r=>r.json())` がサーバ側に保存された進捗（read/box）を返すこと
   - localStorage を消して（`localStorage.clear()`）リロード → サーバから pull され進捗が復元されること（＝端末をまたいだ同期の疑似確認）
5. モックサーバを停止。

- [ ] **Step 5: コミット**

```bash
git add 貸金試験対策アプリ/app/js/app.js 貸金試験対策アプリ/tools/mock_sync_server.mjs
git commit -m "feat(kashikin/sync): アプリに起動時同期＋デバウンス送信を配線"
```

---

### Task 5: デプロイ手順書（DEPLOY.md）

コード変更なし。Cloudflare Pages + KV + Access + プライベートGitHub の手順を、ユーザーが自分のアカウントで実施できる形で文書化する。

**Files:**
- Create: `貸金試験対策アプリ/DEPLOY.md`

- [ ] **Step 1: DEPLOY.md を作成** — `貸金試験対策アプリ/DEPLOY.md`

````markdown
# デプロイ手順（Cloudflare Pages + KV + Access）

画像・学習進捗は教材由来/個人データ。**必ず Access 保護のプライベート配信**にすること。

## 前提
- Cloudflare アカウント（無料）
- GitHub の**プライベート**リポジトリにこのコードを push 済み

## 1. GitHub（プライベート）に push
```
git remote add origin git@github.com:<you>/kashikin-app.git   # プライベートで作成
git push -u origin feature/kashikin-exam-app
```
（画像は `.gitignore` で除外。配信に必要な実画像は Pages 用に別途アップロードするか、
プライベートリポジトリに限り `app/pages/` の除外を外して含める。公開リポジトリには絶対に置かない。）

## 2. Cloudflare Pages プロジェクト作成
1. Cloudflare ダッシュボード → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**。
2. プライベートリポジトリを選択。
3. ビルド設定:
   - Framework preset: **None**
   - Build command: （空）
   - **Build output directory: `貸金試験対策アプリ/app`**
4. デプロイ。`functions/` は Pages が自動でルーティングする（`app` を出力にするため、
   `functions/` を `app/functions/` に置くか、Pages の Root directory を `貸金試験対策アプリ` に設定し
   output を `app` にする。どちらか一方に統一すること）。

> 補足: Pages Functions は「プロジェクトルート直下の `functions/`」を探す。リポジトリ構成に合わせ、
> Pages の **Root directory** を `貸金試験対策アプリ` に設定すると `functions/` と `app/` の関係が素直。

## 3. KV 名前空間を作成してバインド
1. **Workers & Pages → KV → Create namespace**（例: `kashikin-state`）。
2. Pages プロジェクト → **Settings → Functions → KV namespace bindings** →
   **Variable name: `STATE_KV`** ← 作成した名前空間。
3. 再デプロイ。

## 4. Cloudflare Access（本人限定）
1. **Zero Trust → Access → Applications → Add an application → Self-hosted**。
2. アプリのドメイン（`<project>.pages.dev`）を指定。
3. ポリシー: **Allow**、条件 **Emails = 自分のメールアドレス**。
4. 保存。以降このサイトはメールのワンタイムコード認証を通った本人だけがアクセス可能。
   関数は `Cf-Access-Authenticated-User-Email` ヘッダでユーザーを識別し、KV をそのメールで分離する。

## 5. スマホで使う
1. 認証後 `https://<project>.pages.dev` を開く。
2. ブラウザメニュー →「ホーム画面に追加」で PWA としてインストール。
3. PC で進めた進捗が起動時同期で反映され、以降 PC⇄スマホで自動同期される。

## 更新フロー（教材ページを足す）
1. `app/pages/` にスクショ追加 → `python3 build_manifest.py` → `app/manifest.json` 更新。
2. 章名を編集（任意）。
3. `git add` して push → Pages が自動再デプロイ。
````

- [ ] **Step 2: コミット**

```bash
git add 貸金試験対策アプリ/DEPLOY.md
git commit -m "docs(kashikin/sync): Cloudflare Pages+KV+Access デプロイ手順書"
```

---

## Self-Review

**1. Spec coverage（改訂スペック §3 図・§6 同期・§7 functions）:**
- §6 KV に1ユーザー1レコード保存 → Task 1（`userKey` でメール分離）。✓
- §6 進捗/メモ/復習予定を同期 → Task 3/4（state 全体を pull/merge/push）。✓
- §6 オフライン時ローカル、復帰時同期・last-write-wins → Task 2 はLWWより安全なフィールド単位マージで実現（データ喪失回避、spec の意図を上回る）。✓
- §3 図の `/api/state` 経由 KV → Task 1 のパス `api/state`。✓
- §7 認証を Cloudflare Access に寄せる → Task 5（自前認証を書かない）。✓
- 配信のプライベート厳守 → Task 5 冒頭とGlobal Constraintsに明記。✓

**2. Placeholder scan:** TODO/TBD/「適切に」等なし。全コードは実物。✓

**3. Type consistency:**
- 進捗 state 形 `{pages,activityDates}` を function/merge/sync/app で統一。✓
- `ENDPOINT = "api/state"` を sync.js 定義・test・app 配線で一致。関数側ルートも `functions/api/state.js` = `/api/state`。✓
- `mergeStates(local, remote)` の引数順（local優先note）を sync.js の呼び出し `mergeStates(localState, remote)` と一致。✓
- `pushRemote(state, fetchImpl)` / `pullRemote(fetchImpl)` / `syncOnBoot(localState, fetchImpl)` の署名を test と app 呼び出しで一致。✓
- KV バインド名 `STATE_KV` を function（`context.env.STATE_KV`）と DEPLOY.md の binding 設定で一致。✓

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-19-kashikin-planB-sync-deploy.md`.**

Plan B は全2プラン構成の後半。Task 1〜4 はコード（テスト付き・ローカル検証）で私が実装、Task 5 はデプロイ手順書。実際の Cloudflare/GitHub のアカウント操作（KV作成・Access設定・プライベートpush）はユーザーが DEPLOY.md に沿って実施する。
