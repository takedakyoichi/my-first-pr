# 貸金試験対策アプリ — Plan A: 画像教材リーダー Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** スクショ教材画像をページめくりで読み、既読/要復習/SRS復習/メモ/学習記録で反復学習できる、完全無料・オフライン動作の静的PWAを作る（AI・API・OCRは一切使わない）。

**Architecture:** Python の `build_manifest.py` が `app/pages/` の画像から目次 `manifest.json` を生成。PWA本体は素のHTML/CSS/JS(ESM)。学習ロジックは DOM 非依存の純粋関数モジュール（`srs.js` / `progress.js` / `store.js` / `reader.flattenPages`）に切り出して `node --test` でユニットテスト。UI（`reader.js`/`app.js`）はブラウザプレビューで検証。進捗は localStorage（KV同期は Plan B）。

**Tech Stack:** Python 3（標準ライブラリのみ, pytest）, Vanilla JS (ESM), `node --test`（Node 18+）, PWA（Service Worker + webmanifest）。

## Global Constraints

- AI/API/OCR/ネットワーク推論を一切使わない（完全無料・オフライン）。
- 学習ロジック（SRS・進捗・永続化・flattenPages）は DOM/localStorage をモジュール読み込み時に触らない純粋関数にし、`node --test` で検証する。UI描画のみ DOM に依存。
- SRS は Leitner ボックス。間隔（日）box 0..5 = `[1, 2, 4, 8, 16, 32]`。「覚えた」→box+1（上限5）、「まだ」→box=0。期限 `due` ≤ 今日 が復習対象。
- 日付は `"YYYY-MM-DD"` 文字列。日付計算は UTC 基準（`new Date(iso+"T00:00:00Z")`）でタイムゾーン揺れを避ける。
- 進捗データモデル（localStorage / 後のKV共通）: `{ pages: { [pageId]: { read?, box?, due?, note? } }, activityDates: [ "YYYY-MM-DD" ] }`。
- manifest 形: `{ version, chapters: [ { id, title, pages: [ { id, image } ] } ] }`。`page.id` は画像ファイル名から決定的（`p-<stem>`）。
- コミットは必ずパス指定 `git add <path>`。`git add -A` / `git add .` 禁止（ワークスペースに他アプリの埋め込みgitリポジトリが同居）。
- Python テストは既存 venv で実行: `cd 貸金試験対策アプリ && .venv/bin/python -m pytest`。JS テストは `cd 貸金試験対策アプリ && node --test app/js/tests/`。
- 実画像（`app/pages/` の本物のスクショ）は著作物。サンプル以外はコミットしない（`.gitignore` で `app/pages/*` を無視し、サンプルのみ明示追加）。

---

## File Structure

- `貸金試験対策アプリ/build_manifest.py` — 画像走査→manifest生成/更新（stdlibのみ）
- `貸金試験対策アプリ/tests/__init__.py`, `貸金試験対策アプリ/tests/test_build_manifest.py` — pytest
- `貸金試験対策アプリ/app/package.json` — `{"type":"module"}`（nodeがjsをESM扱いにするため）
- `貸金試験対策アプリ/app/js/srs.js` — Leitner スケジューリング（純粋）
- `貸金試験対策アプリ/app/js/progress.js` — 既読/ストリーク/メモ/進捗%（純粋）
- `貸金試験対策アプリ/app/js/store.js` — 永続化（localStorage、storage注入可）
- `貸金試験対策アプリ/app/js/reader.js` — flattenPages（純粋）＋ DOM描画
- `貸金試験対策アプリ/app/js/app.js` — 起動・イベント配線
- `貸金試験対策アプリ/app/js/tests/*.test.js` — node:test
- `貸金試験対策アプリ/app/index.html`, `貸金試験対策アプリ/app/style.css`
- `貸金試験対策アプリ/app/manifest.webmanifest`, `貸金試験対策アプリ/app/sw.js`
- `貸金試験対策アプリ/app/pages/` — 画像（サンプルのみコミット）
- `貸金試験対策アプリ/app/manifest.json` — build_manifest.py が生成

---

### Task 1: manifest 生成スクリプト（build_manifest.py）

**Files:**
- Create: `貸金試験対策アプリ/build_manifest.py`
- Create: `貸金試験対策アプリ/tests/__init__.py`
- Create: `貸金試験対策アプリ/tests/test_build_manifest.py`
- Modify: `貸金試験対策アプリ/.gitignore`（`app/pages/*` を追記）

**Interfaces:**
- Produces:
  - `IMAGE_EXTS: set[str]`
  - `scan_images(pages_dir: Path) -> list[str]`（`"pages/<name>"` をファイル名昇順で）
  - `page_id(image_path: str) -> str`（`"p-<stem>"`）
  - `build_manifest(images: list[str], existing: dict | None) -> dict`
    - 既存章の画像割り当てを保持。未割り当て画像は末尾の `未分類`(id=`ch-uncat`) に集約。空章は除去。

- [ ] **Step 1: .gitignore に実画像除外を追記** — `貸金試験対策アプリ/.gitignore` の末尾に追加:

```
app/pages/*
!app/pages/sample-*.png
```

- [ ] **Step 2: 失敗するテストを書く** — `貸金試験対策アプリ/tests/test_build_manifest.py`

```python
from pathlib import Path
from build_manifest import scan_images, page_id, build_manifest


def test_scan_images_sorted(tmp_path):
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "002.png").write_bytes(b"x")
    (pages / "001.png").write_bytes(b"x")
    (pages / "note.txt").write_bytes(b"x")  # 非画像は無視
    assert scan_images(pages) == ["pages/001.png", "pages/002.png"]


def test_page_id_stable():
    assert page_id("pages/001.png") == "p-001"
    assert page_id("pages/003.jpg") == "p-003"


def test_build_manifest_empty_existing():
    m = build_manifest(["pages/001.png", "pages/002.png"], None)
    assert m["version"] == 1
    assert len(m["chapters"]) == 1
    assert m["chapters"][0]["title"] == "未分類"
    assert [p["id"] for p in m["chapters"][0]["pages"]] == ["p-001", "p-002"]


def test_build_manifest_preserves_assignment():
    existing = {
        "version": 1,
        "chapters": [{"id": "ch-1", "title": "第1章", "pages": [
            {"id": "p-001", "image": "pages/001.png"}]}],
    }
    m = build_manifest(["pages/001.png", "pages/002.png"], existing)
    # 001 は ch-1 に残り、002 は 未分類 に入る
    ch1 = next(c for c in m["chapters"] if c["id"] == "ch-1")
    uncat = next(c for c in m["chapters"] if c["id"] == "ch-uncat")
    assert [p["image"] for p in ch1["pages"]] == ["pages/001.png"]
    assert [p["image"] for p in uncat["pages"]] == ["pages/002.png"]
```

- [ ] **Step 3: 失敗を確認**

Run: `cd 貸金試験対策アプリ && .venv/bin/python -m pytest tests/test_build_manifest.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'build_manifest'`）

- [ ] **Step 4: 実装** — `貸金試験対策アプリ/tests/__init__.py`（空）、`貸金試験対策アプリ/build_manifest.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def scan_images(pages_dir: Path) -> list[str]:
    names = sorted(p.name for p in pages_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    return [f"pages/{name}" for name in names]


def page_id(image_path: str) -> str:
    return f"p-{Path(image_path).stem}"


def build_manifest(images: list[str], existing: dict | None) -> dict:
    existing = existing or {"version": 1, "chapters": []}
    assigned = {
        pg["image"]: ch["id"]
        for ch in existing.get("chapters", [])
        for pg in ch.get("pages", [])
    }
    chapters = [
        {"id": c["id"], "title": c["title"], "pages": []}
        for c in existing.get("chapters", [])
    ]
    by_id = {c["id"]: c for c in chapters}

    unassigned: list[str] = []
    for img in images:
        cid = assigned.get(img)
        if cid and cid in by_id:
            by_id[cid]["pages"].append({"id": page_id(img), "image": img})
        else:
            unassigned.append(img)

    if unassigned:
        uncat = by_id.get("ch-uncat")
        if uncat is None:
            uncat = {"id": "ch-uncat", "title": "未分類", "pages": []}
            chapters.append(uncat)
            by_id["ch-uncat"] = uncat
        for img in unassigned:
            uncat["pages"].append({"id": page_id(img), "image": img})

    chapters = [c for c in chapters if c["pages"]]
    return {"version": 1, "chapters": chapters}


def main() -> None:
    app_dir = Path(__file__).parent / "app"
    pages_dir = app_dir / "pages"
    manifest_path = app_dir / "manifest.json"
    pages_dir.mkdir(parents=True, exist_ok=True)

    images = scan_images(pages_dir)
    existing = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else None
    )
    manifest = build_manifest(images, existing)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total = sum(len(c["pages"]) for c in manifest["chapters"])
    print(f"manifest.json: {len(manifest['chapters'])} chapters, {total} pages")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && .venv/bin/python -m pytest tests/test_build_manifest.py -v`
Expected: PASS（4件）

- [ ] **Step 6: コミット**

```bash
git add 貸金試験対策アプリ/build_manifest.py 貸金試験対策アプリ/tests/__init__.py \
        貸金試験対策アプリ/tests/test_build_manifest.py 貸金試験対策アプリ/.gitignore
git commit -m "feat(kashikin/reader): 画像→manifest.json 生成スクリプト"
```

---

### Task 2: SRS（Leitner）モジュール（srs.js）

**Files:**
- Create: `貸金試験対策アプリ/app/package.json`
- Create: `貸金試験対策アプリ/app/js/srs.js`
- Create: `貸金試験対策アプリ/app/js/tests/srs.test.js`

**Interfaces:**
- Produces:
  - `INTERVALS = [1,2,4,8,16,32]`
  - `addDays(iso: string, n: number) -> string`（UTC基準, `"YYYY-MM-DD"`）
  - `enterReview(today: string) -> { box: 0, due: string }`
  - `review(entry: {box?:number}, grade: "known"|"again", today: string) -> { box, due }`
  - `isDue(entry, today) -> boolean`（`entry.box`/`entry.due` があり `due <= today`）
  - `duePageIds(pages: object, today: string) -> string[]`（昇順）

- [ ] **Step 1: app/package.json を作成**（node が .js を ESM 扱いにするため）

`貸金試験対策アプリ/app/package.json`:
```json
{
  "name": "kashikin-app",
  "private": true,
  "type": "module"
}
```

- [ ] **Step 2: 失敗するテストを書く** — `貸金試験対策アプリ/app/js/tests/srs.test.js`

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { addDays, enterReview, review, isDue, duePageIds } from "../srs.js";

test("addDays crosses month boundary in UTC", () => {
  assert.equal(addDays("2026-07-31", 1), "2026-08-01");
  assert.equal(addDays("2026-07-01", -1), "2026-06-30");
});

test("enterReview puts page in box 0 due tomorrow", () => {
  assert.deepEqual(enterReview("2026-07-19"), { box: 0, due: "2026-07-20" });
});

test("review known advances box and extends interval", () => {
  assert.deepEqual(review({ box: 0 }, "known", "2026-07-19"), { box: 1, due: "2026-07-21" });
  assert.deepEqual(review({ box: 4 }, "known", "2026-07-19"), { box: 5, due: "2026-08-20" });
});

test("review known caps at last box", () => {
  assert.deepEqual(review({ box: 5 }, "known", "2026-07-19"), { box: 5, due: "2026-08-20" });
});

test("review again resets to box 0", () => {
  assert.deepEqual(review({ box: 3 }, "again", "2026-07-19"), { box: 0, due: "2026-07-20" });
});

test("isDue and duePageIds", () => {
  const pages = {
    "p-001": { box: 0, due: "2026-07-19" },
    "p-002": { box: 1, due: "2026-07-25" },
    "p-003": { read: true }, // 復習対象外
  };
  assert.equal(isDue(pages["p-001"], "2026-07-19"), true);
  assert.equal(isDue(pages["p-002"], "2026-07-19"), false);
  assert.deepEqual(duePageIds(pages, "2026-07-19"), ["p-001"]);
});
```

- [ ] **Step 3: 失敗を確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/srs.test.js`
Expected: FAIL（`Cannot find module '../srs.js'`）

- [ ] **Step 4: 実装** — `貸金試験対策アプリ/app/js/srs.js`

```javascript
export const INTERVALS = [1, 2, 4, 8, 16, 32];

export function addDays(iso, n) {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export function enterReview(today) {
  return { box: 0, due: addDays(today, INTERVALS[0]) };
}

export function review(entry, grade, today) {
  const cur = entry && typeof entry.box === "number" ? entry.box : 0;
  const box = grade === "known" ? Math.min(cur + 1, INTERVALS.length - 1) : 0;
  return { box, due: addDays(today, INTERVALS[box]) };
}

export function isDue(entry, today) {
  return !!entry && typeof entry.box === "number" && typeof entry.due === "string" && entry.due <= today;
}

export function duePageIds(pages, today) {
  return Object.keys(pages).filter((id) => isDue(pages[id], today)).sort();
}
```

- [ ] **Step 5: テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/srs.test.js`
Expected: PASS（6件）

- [ ] **Step 6: コミット**

```bash
git add 貸金試験対策アプリ/app/package.json 貸金試験対策アプリ/app/js/srs.js \
        貸金試験対策アプリ/app/js/tests/srs.test.js
git commit -m "feat(kashikin/reader): SRS(Leitnerボックス)スケジューリング"
```

---

### Task 3: 進捗・ストリーク・メモ（progress.js）

**Files:**
- Create: `貸金試験対策アプリ/app/js/progress.js`
- Create: `貸金試験対策アプリ/app/js/tests/progress.test.js`

**Interfaces:**
- Consumes: `addDays`（`./srs.js`）
- Produces（すべて state を変更せず新 state を返す純粋関数）:
  - `defaultState() -> { pages: {}, activityDates: [] }`
  - `recordActivity(state, today) -> state`
  - `markRead(state, pageId, today) -> state`
  - `toggleRead(state, pageId, today) -> state`
  - `setNote(state, pageId, text, today) -> state`
  - `setPageSrs(state, pageId, srs, today) -> state`（`srs = {box, due}` を pages[pageId] にマージ）
  - `progressPercent(state, totalPages) -> number`（0..100 整数）
  - `computeStreak(activityDates, today) -> number`（today から連続する日数）

- [ ] **Step 1: 失敗するテストを書く** — `貸金試験対策アプリ/app/js/tests/progress.test.js`

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  defaultState, recordActivity, markRead, toggleRead, setNote,
  setPageSrs, progressPercent, computeStreak,
} from "../progress.js";

test("defaultState is empty", () => {
  assert.deepEqual(defaultState(), { pages: {}, activityDates: [] });
});

test("markRead sets read and records activity without mutating input", () => {
  const s0 = defaultState();
  const s1 = markRead(s0, "p-001", "2026-07-19");
  assert.equal(s1.pages["p-001"].read, true);
  assert.deepEqual(s1.activityDates, ["2026-07-19"]);
  assert.deepEqual(s0, { pages: {}, activityDates: [] }); // 元は不変
});

test("toggleRead flips read", () => {
  let s = markRead(defaultState(), "p-001", "2026-07-19");
  s = toggleRead(s, "p-001", "2026-07-19");
  assert.equal(s.pages["p-001"].read, false);
});

test("setNote and setPageSrs merge into page", () => {
  let s = setNote(defaultState(), "p-001", "メモ", "2026-07-19");
  s = setPageSrs(s, "p-001", { box: 0, due: "2026-07-20" }, "2026-07-19");
  assert.equal(s.pages["p-001"].note, "メモ");
  assert.equal(s.pages["p-001"].box, 0);
  assert.equal(s.pages["p-001"].due, "2026-07-20");
});

test("recordActivity dedupes dates", () => {
  let s = recordActivity(defaultState(), "2026-07-19");
  s = recordActivity(s, "2026-07-19");
  assert.deepEqual(s.activityDates, ["2026-07-19"]);
});

test("progressPercent", () => {
  let s = defaultState();
  s = markRead(s, "p-001", "2026-07-19");
  assert.equal(progressPercent(s, 4), 25);
  assert.equal(progressPercent(defaultState(), 0), 0);
});

test("computeStreak counts consecutive days ending today", () => {
  assert.equal(computeStreak(["2026-07-17", "2026-07-18", "2026-07-19"], "2026-07-19"), 3);
  assert.equal(computeStreak(["2026-07-17", "2026-07-19"], "2026-07-19"), 1); // 18が抜け
  assert.equal(computeStreak(["2026-07-18"], "2026-07-19"), 0); // todayに活動なし
});
```

- [ ] **Step 2: 失敗を確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/progress.test.js`
Expected: FAIL（`Cannot find module '../progress.js'`）

- [ ] **Step 3: 実装** — `貸金試験対策アプリ/app/js/progress.js`

```javascript
import { addDays } from "./srs.js";

export function defaultState() {
  return { pages: {}, activityDates: [] };
}

function clone(state) {
  return structuredClone(state);
}

function ensurePage(state, pageId) {
  if (!state.pages[pageId]) state.pages[pageId] = {};
  return state.pages[pageId];
}

export function recordActivity(state, today) {
  const s = clone(state);
  if (!s.activityDates.includes(today)) s.activityDates.push(today);
  return s;
}

export function markRead(state, pageId, today) {
  const s = clone(state);
  ensurePage(s, pageId).read = true;
  return recordActivity(s, today);
}

export function toggleRead(state, pageId, today) {
  const s = clone(state);
  const p = ensurePage(s, pageId);
  p.read = !p.read;
  return recordActivity(s, today);
}

export function setNote(state, pageId, text, today) {
  const s = clone(state);
  ensurePage(s, pageId).note = text;
  return recordActivity(s, today);
}

export function setPageSrs(state, pageId, srs, today) {
  const s = clone(state);
  const p = ensurePage(s, pageId);
  p.box = srs.box;
  p.due = srs.due;
  return recordActivity(s, today);
}

export function progressPercent(state, totalPages) {
  if (!totalPages) return 0;
  const read = Object.values(state.pages).filter((p) => p.read).length;
  return Math.round((read / totalPages) * 100);
}

export function computeStreak(activityDates, today) {
  const set = new Set(activityDates);
  let streak = 0;
  let cur = today;
  while (set.has(cur)) {
    streak += 1;
    cur = addDays(cur, -1);
  }
  return streak;
}
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/progress.test.js`
Expected: PASS（7件）

- [ ] **Step 5: コミット**

```bash
git add 貸金試験対策アプリ/app/js/progress.js 貸金試験対策アプリ/app/js/tests/progress.test.js
git commit -m "feat(kashikin/reader): 既読/ストリーク/メモ/進捗% の進捗モデル"
```

---

### Task 4: 永続化（store.js）

**Files:**
- Create: `貸金試験対策アプリ/app/js/store.js`
- Create: `貸金試験対策アプリ/app/js/tests/store.test.js`

**Interfaces:**
- Consumes: `defaultState`（`./progress.js`）
- Produces:
  - `STORAGE_KEY = "kashikin-state"`
  - `loadState(storage?) -> state`（storage 省略時 `globalThis.localStorage`。壊れ/空なら defaultState）
  - `saveState(state, storage?) -> void`

- [ ] **Step 1: 失敗するテストを書く** — `貸金試験対策アプリ/app/js/tests/store.test.js`

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { loadState, saveState, STORAGE_KEY } from "../store.js";

function memStorage(initial = {}) {
  const data = { ...initial };
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v); },
    _data: data,
  };
}

test("loadState returns defaultState when empty", () => {
  assert.deepEqual(loadState(memStorage()), { pages: {}, activityDates: [] });
});

test("saveState then loadState roundtrips", () => {
  const storage = memStorage();
  const state = { pages: { "p-001": { read: true } }, activityDates: ["2026-07-19"] };
  saveState(state, storage);
  assert.equal(typeof storage._data[STORAGE_KEY], "string");
  assert.deepEqual(loadState(storage), state);
});

test("loadState tolerates corrupt JSON", () => {
  const storage = memStorage({ [STORAGE_KEY]: "{not json" });
  assert.deepEqual(loadState(storage), { pages: {}, activityDates: [] });
});

test("loadState fills missing fields", () => {
  const storage = memStorage({ [STORAGE_KEY]: JSON.stringify({ pages: { "p-1": {} } }) });
  assert.deepEqual(loadState(storage), { pages: { "p-1": {} }, activityDates: [] });
});
```

- [ ] **Step 2: 失敗を確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/store.test.js`
Expected: FAIL（`Cannot find module '../store.js'`）

- [ ] **Step 3: 実装** — `貸金試験対策アプリ/app/js/store.js`

```javascript
import { defaultState } from "./progress.js";

export const STORAGE_KEY = "kashikin-state";

export function loadState(storage = globalThis.localStorage) {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return defaultState();
    const parsed = JSON.parse(raw);
    return {
      pages: parsed.pages ?? {},
      activityDates: parsed.activityDates ?? [],
    };
  } catch {
    return defaultState();
  }
}

export function saveState(state, storage = globalThis.localStorage) {
  storage.setItem(STORAGE_KEY, JSON.stringify(state));
}
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/store.test.js`
Expected: PASS（4件）

- [ ] **Step 5: コミット**

```bash
git add 貸金試験対策アプリ/app/js/store.js 貸金試験対策アプリ/app/js/tests/store.test.js
git commit -m "feat(kashikin/reader): 永続化(localStorage・storage注入可)"
```

---

### Task 5: リーダーUI一式（reader.js / index.html / style.css / app.js）+ サンプル画像

DOM描画とイベント配線。純粋関数 `flattenPages` のみ node:test、残りはブラウザプレビューで検証（画像表示・TOCジャンプ・前後ナビ・既読/要復習・メモ・復習モード・ストリーク/進捗表示）。

**Files:**
- Create: `貸金試験対策アプリ/app/js/reader.js`
- Create: `貸金試験対策アプリ/app/js/tests/reader.test.js`
- Create: `貸金試験対策アプリ/app/index.html`
- Create: `貸金試験対策アプリ/app/style.css`
- Create: `貸金試験対策アプリ/app/js/app.js`
- Create: `貸金試験対策アプリ/tools/make_samples.py`（サンプル画像生成・dev用）
- Create: `貸金試験対策アプリ/app/pages/sample-001.png` 〜 `sample-003.png`（生成物をコミット）

**Interfaces:**
- Consumes: `loadState`/`saveState`（store）, `markRead`/`toggleRead`/`setNote`/`setPageSrs`/`progressPercent`/`computeStreak`（progress）, `enterReview`/`review`/`duePageIds`（srs）
- Produces:
  - `flattenPages(manifest) -> [{ id, image, chapterId, chapterTitle, index }]`（純粋）
  - DOM描画: `renderTOC(navEl, manifest, state, onJump)`, `showPage(els, page, state)`, `updateHeader(els, state, total, today)`

- [ ] **Step 1: flattenPages の失敗テストを書く** — `貸金試験対策アプリ/app/js/tests/reader.test.js`

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { flattenPages } from "../reader.js";

test("flattenPages linearizes chapters with running index", () => {
  const manifest = {
    version: 1,
    chapters: [
      { id: "ch-1", title: "第1章", pages: [
        { id: "p-001", image: "pages/001.png" },
        { id: "p-002", image: "pages/002.png" }] },
      { id: "ch-2", title: "第2章", pages: [
        { id: "p-003", image: "pages/003.png" }] },
    ],
  };
  const flat = flattenPages(manifest);
  assert.equal(flat.length, 3);
  assert.deepEqual(flat[0], { id: "p-001", image: "pages/001.png", chapterId: "ch-1", chapterTitle: "第1章", index: 0 });
  assert.equal(flat[2].chapterTitle, "第2章");
  assert.equal(flat[2].index, 2);
});

test("flattenPages handles empty manifest", () => {
  assert.deepEqual(flattenPages({ version: 1, chapters: [] }), []);
});
```

- [ ] **Step 2: 失敗を確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/reader.test.js`
Expected: FAIL（`Cannot find module '../reader.js'`）

- [ ] **Step 3: reader.js を実装**（モジュール読み込み時に `document` を触らない） — `貸金試験対策アプリ/app/js/reader.js`

```javascript
import { computeStreak, progressPercent } from "./progress.js";

export function flattenPages(manifest) {
  const flat = [];
  let index = 0;
  for (const ch of manifest.chapters) {
    for (const pg of ch.pages) {
      flat.push({
        id: pg.id,
        image: pg.image,
        chapterId: ch.id,
        chapterTitle: ch.title,
        index: index++,
      });
    }
  }
  return flat;
}

export function renderTOC(navEl, manifest, state, onJump) {
  navEl.innerHTML = "";
  let running = 0;
  for (const ch of manifest.chapters) {
    const h = document.createElement("h3");
    h.textContent = ch.title;
    navEl.appendChild(h);
    for (const pg of ch.pages) {
      const idx = running++;
      const btn = document.createElement("button");
      btn.className = "toc-item";
      const read = state.pages[pg.id]?.read ? "✅" : "⬜";
      btn.textContent = `${read} ${pg.id}`;
      btn.addEventListener("click", () => onJump(idx));
      navEl.appendChild(btn);
    }
  }
}

export function showPage(els, page, state) {
  const entry = state.pages[page.id] ?? {};
  els.image.src = page.image;
  els.image.alt = `${page.chapterTitle} ${page.id}`;
  els.chapterLabel.textContent = page.chapterTitle;
  els.pageIndex.textContent = page.id;
  els.readToggle.textContent = entry.read ? "既読 ✅" : "未読 ⬜";
  els.reviewToggle.textContent = typeof entry.box === "number" ? "復習登録済 🔁" : "要復習に追加";
  els.note.value = entry.note ?? "";
}

export function updateHeader(els, state, total, today) {
  els.streak.textContent = `🔥${computeStreak(state.activityDates, today)}`;
  els.progress.textContent = `${progressPercent(state, total)}%`;
}
```

- [ ] **Step 4: flattenPages テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && node --test app/js/tests/reader.test.js`
Expected: PASS（2件）

- [ ] **Step 5: index.html を作成** — `貸金試験対策アプリ/app/index.html`

```html
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>貸金 学習リーダー</title>
  <link rel="stylesheet" href="style.css" />
  <link rel="manifest" href="manifest.webmanifest" />
</head>
<body>
  <header id="topbar">
    <button id="menu-btn" aria-label="目次">☰</button>
    <h1>貸金 学習</h1>
    <span id="streak">🔥0</span>
    <span id="progress">0%</span>
  </header>

  <nav id="toc" hidden></nav>

  <main id="viewer">
    <div id="page-meta">
      <span id="chapter-label"></span>
      <span id="page-index"></span>
    </div>
    <div id="image-wrap">
      <img id="page-image" alt="教材ページ" />
    </div>
    <div id="controls">
      <button id="prev">◀ 前</button>
      <button id="read-toggle">未読 ⬜</button>
      <button id="review-toggle">要復習に追加</button>
      <button id="next">次 ▶</button>
    </div>
    <textarea id="note" placeholder="このページのメモ"></textarea>
    <button id="start-review">今日の復習（<span id="due-count">0</span>）</button>
  </main>

  <section id="review-mode" hidden>
    <p id="review-progress"></p>
    <div id="review-image-wrap"><img id="review-image" alt="復習ページ" /></div>
    <div id="review-controls">
      <button id="grade-again">まだ</button>
      <button id="grade-known">覚えた</button>
    </div>
    <button id="review-exit">復習を終える</button>
  </section>

  <script type="module" src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 6: style.css を作成** — `貸金試験対策アプリ/app/style.css`

```css
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, "Hiragino Sans", "Noto Sans JP", sans-serif;
  background: #f4f4f5;
  color: #1c1c1e;
}
#topbar {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 14px; background: #1c1c1e; color: #fff;
  position: sticky; top: 0; z-index: 10;
}
#topbar h1 { font-size: 16px; margin: 0; flex: 1; }
#topbar span { font-variant-numeric: tabular-nums; font-size: 14px; }
#menu-btn { font-size: 20px; background: none; border: none; color: #fff; cursor: pointer; }

#toc {
  position: fixed; top: 46px; left: 0; bottom: 0; width: 80%; max-width: 320px;
  background: #fff; overflow-y: auto; padding: 12px; z-index: 9;
  box-shadow: 2px 0 8px rgba(0,0,0,.15);
}
#toc h3 { font-size: 14px; margin: 12px 0 6px; color: #555; }
.toc-item { display: block; width: 100%; text-align: left; padding: 8px; border: none;
  background: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
.toc-item:hover { background: #eee; }

#viewer { max-width: 900px; margin: 0 auto; padding: 12px; }
#page-meta { display: flex; justify-content: space-between; color: #666; font-size: 13px; margin-bottom: 6px; }
#image-wrap { overflow: auto; background: #fff; border-radius: 8px; text-align: center; }
#page-image { max-width: 100%; height: auto; touch-action: pinch-zoom; }

#controls { display: flex; gap: 8px; margin: 12px 0; flex-wrap: wrap; }
#controls button { flex: 1 1 auto; padding: 12px; border: 1px solid #ccc; border-radius: 8px;
  background: #fff; font-size: 15px; cursor: pointer; }
#controls button:active { background: #eee; }
#note { width: 100%; min-height: 70px; padding: 10px; border: 1px solid #ccc; border-radius: 8px;
  font-size: 15px; resize: vertical; }
#start-review { display: block; width: 100%; margin-top: 12px; padding: 12px; border: none;
  border-radius: 8px; background: #0a84ff; color: #fff; font-size: 15px; cursor: pointer; }

#review-mode { max-width: 900px; margin: 0 auto; padding: 12px; text-align: center; }
#review-image-wrap { overflow: auto; background: #fff; border-radius: 8px; }
#review-image { max-width: 100%; height: auto; }
#review-controls { display: flex; gap: 8px; margin: 12px 0; }
#grade-again { flex: 1; padding: 14px; border: none; border-radius: 8px; background: #ff453a; color: #fff; font-size: 16px; }
#grade-known { flex: 1; padding: 14px; border: none; border-radius: 8px; background: #30d158; color: #fff; font-size: 16px; }
#review-exit { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px; background: #fff; }
[hidden] { display: none !important; }
```

- [ ] **Step 7: app.js を作成**（配線） — `貸金試験対策アプリ/app/js/app.js`

```javascript
import { loadState, saveState } from "./store.js";
import {
  markRead, toggleRead, setNote, setPageSrs, computeStreak, progressPercent,
} from "./progress.js";
import { enterReview, review, duePageIds } from "./srs.js";
import { flattenPages, renderTOC, showPage, updateHeader } from "./reader.js";

const todayISO = () => new Date().toISOString().slice(0, 10);

const els = {
  menuBtn: document.getElementById("menu-btn"),
  toc: document.getElementById("toc"),
  streak: document.getElementById("streak"),
  progress: document.getElementById("progress"),
  image: document.getElementById("page-image"),
  chapterLabel: document.getElementById("chapter-label"),
  pageIndex: document.getElementById("page-index"),
  prev: document.getElementById("prev"),
  next: document.getElementById("next"),
  readToggle: document.getElementById("read-toggle"),
  reviewToggle: document.getElementById("review-toggle"),
  note: document.getElementById("note"),
  startReview: document.getElementById("start-review"),
  dueCount: document.getElementById("due-count"),
  viewer: document.getElementById("viewer"),
  reviewMode: document.getElementById("review-mode"),
  reviewImage: document.getElementById("review-image"),
  reviewProgress: document.getElementById("review-progress"),
  gradeAgain: document.getElementById("grade-again"),
  gradeKnown: document.getElementById("grade-known"),
  reviewExit: document.getElementById("review-exit"),
};

let manifest = { version: 1, chapters: [] };
let pages = [];
let state = loadState();
let current = 0;
let reviewQueue = [];

function persist() {
  saveState(state);
}

function refreshHeader() {
  updateHeader(els, state, pages.length, todayISO());
  els.dueCount.textContent = String(duePageIds(state.pages, todayISO()).length);
}

function go(index) {
  if (pages.length === 0) return;
  current = Math.max(0, Math.min(index, pages.length - 1));
  const page = pages[current];
  // 閲覧で既読化
  state = markRead(state, page.id, todayISO());
  persist();
  showPage(els, page, state);
  refreshHeader();
  renderTOC(els.toc, manifest, state, jump);
}

function jump(index) {
  els.toc.hidden = true;
  go(index);
}

els.menuBtn.addEventListener("click", () => { els.toc.hidden = !els.toc.hidden; });
els.prev.addEventListener("click", () => go(current - 1));
els.next.addEventListener("click", () => go(current + 1));

els.readToggle.addEventListener("click", () => {
  state = toggleRead(state, pages[current].id, todayISO());
  persist();
  showPage(els, pages[current], state);
  refreshHeader();
});

els.reviewToggle.addEventListener("click", () => {
  const id = pages[current].id;
  const entry = state.pages[id] ?? {};
  if (typeof entry.box !== "number") {
    state = setPageSrs(state, id, enterReview(todayISO()), todayISO());
    persist();
    showPage(els, pages[current], state);
    refreshHeader();
  }
});

els.note.addEventListener("change", () => {
  state = setNote(state, pages[current].id, els.note.value, todayISO());
  persist();
});

// --- 復習モード ---
function startReview() {
  reviewQueue = duePageIds(state.pages, todayISO());
  if (reviewQueue.length === 0) return;
  els.viewer.hidden = true;
  els.reviewMode.hidden = false;
  showNextReview();
}

function showNextReview() {
  if (reviewQueue.length === 0) { exitReview(); return; }
  const id = reviewQueue[0];
  const page = pages.find((p) => p.id === id);
  els.reviewImage.src = page ? page.image : "";
  els.reviewProgress.textContent = `残り ${reviewQueue.length} ページ`;
}

function grade(kind) {
  const id = reviewQueue.shift();
  const entry = state.pages[id] ?? {};
  state = setPageSrs(state, id, review(entry, kind, todayISO()), todayISO());
  persist();
  refreshHeader();
  showNextReview();
}

function exitReview() {
  els.reviewMode.hidden = true;
  els.viewer.hidden = false;
  refreshHeader();
}

els.startReview.addEventListener("click", startReview);
els.gradeAgain.addEventListener("click", () => grade("again"));
els.gradeKnown.addEventListener("click", () => grade("known"));
els.reviewExit.addEventListener("click", exitReview);

async function boot() {
  try {
    const res = await fetch("manifest.json");
    manifest = await res.json();
  } catch {
    manifest = { version: 1, chapters: [] };
  }
  pages = flattenPages(manifest);
  renderTOC(els.toc, manifest, state, jump);
  if (pages.length > 0) go(0);
  refreshHeader();
}

boot();
```

- [ ] **Step 8: サンプル画像生成スクリプトを作成** — `貸金試験対策アプリ/tools/make_samples.py`

```python
"""dev用: 動作確認用のサンプルページ画像(単色PNG)を app/pages/ に生成する。"""
import struct
import zlib
from pathlib import Path


def write_png(path: Path, width: int, height: int, rgb: tuple[int, int, int]) -> None:
    def chunk(typ: bytes, data: bytes) -> bytes:
        body = typ + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def main() -> None:
    out = Path(__file__).parent.parent / "app" / "pages"
    out.mkdir(parents=True, exist_ok=True)
    colors = [(230, 200, 200), (200, 230, 200), (200, 200, 230)]
    for i, rgb in enumerate(colors, start=1):
        write_png(out / f"sample-{i:03d}.png", 600, 800, rgb)
    print(f"wrote {len(colors)} sample images to {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 9: サンプル画像とmanifestを生成**

Run:
```
cd 貸金試験対策アプリ
.venv/bin/python tools/make_samples.py
.venv/bin/python build_manifest.py
```
Expected: `app/pages/sample-001.png`〜`003.png` が生成され、`app/manifest.json` に3ページ（1章 未分類）が書かれる。

- [ ] **Step 10: ブラウザプレビューで検証**

1. preview_start `{url: "file://.../貸金試験対策アプリ/app/index.html"}` は fetch(manifest.json) が file:// で CORS 制限に掛かるため、簡易HTTPサーバで配信する:
   Run（バックグラウンド）: `cd 貸金試験対策アプリ/app && python3 -m http.server 8123`
2. preview_start `{url: "http://localhost:8123/"}` でブラウザを開く。
3. 検証（read_page / screenshot / read_console_messages）:
   - 画像が表示され「次 ▶」でページが切り替わる（色が変わる）
   - ☰ で目次が開き、項目クリックでジャンプ、閲覧済みに ✅
   - ヘッダの 🔥ストリークと % が更新される
   - 「要復習に追加」→ ボタン表示が「復習登録済 🔁」に変わり、「今日の復習」件数が増える（enterReview は翌日期限なので当日の due-count は0のままで正しい。ボタン表示の変化を確認）
   - メモ入力→リロード後も保持（localStorage）
   - コンソールにエラーが出ていない
4. 確認できたら http.server を停止。

- [ ] **Step 11: コミット**

```bash
git add 貸金試験対策アプリ/app/js/reader.js 貸金試験対策アプリ/app/js/tests/reader.test.js \
        貸金試験対策アプリ/app/index.html 貸金試験対策アプリ/app/style.css \
        貸金試験対策アプリ/app/js/app.js 貸金試験対策アプリ/tools/make_samples.py \
        貸金試験対策アプリ/app/pages/sample-001.png 貸金試験対策アプリ/app/pages/sample-002.png \
        貸金試験対策アプリ/app/pages/sample-003.png 貸金試験対策アプリ/app/manifest.json
git commit -m "feat(kashikin/reader): 画像リーダーUI・TOC・既読/要復習/メモ/SRS復習モード"
```

---

### Task 6: PWA化（オフライン動作）

**Files:**
- Create: `貸金試験対策アプリ/app/manifest.webmanifest`
- Create: `貸金試験対策アプリ/app/sw.js`
- Modify: `貸金試験対策アプリ/app/js/app.js`（Service Worker 登録を追記）

**Interfaces:**
- Consumes: 既存の app.js
- Produces: オフラインでアプリ殻＋既読済み画像が開ける（Service Worker キャッシュ）

- [ ] **Step 1: webmanifest を作成** — `貸金試験対策アプリ/app/manifest.webmanifest`

```json
{
  "name": "貸金 学習リーダー",
  "short_name": "貸金学習",
  "start_url": ".",
  "display": "standalone",
  "background_color": "#f4f4f5",
  "theme_color": "#1c1c1e",
  "icons": [
    { "src": "pages/sample-001.png", "sizes": "600x800", "type": "image/png" }
  ]
}
```

- [ ] **Step 2: Service Worker を作成** — `貸金試験対策アプリ/app/sw.js`

```javascript
const CACHE = "kashikin-v1";
const SHELL = [
  ".",
  "index.html",
  "style.css",
  "manifest.json",
  "js/app.js",
  "js/reader.js",
  "js/store.js",
  "js/progress.js",
  "js/srs.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// cache-first。取得できた画像/リソースは動的にキャッシュ。
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((hit) => {
      if (hit) return hit;
      return fetch(event.request).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(event.request, copy));
        return res;
      });
    })
  );
});
```

- [ ] **Step 3: app.js に Service Worker 登録を追記** — `貸金試験対策アプリ/app/js/app.js` の末尾（`boot();` の後）に追加:

```javascript
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  });
}
```

- [ ] **Step 4: ブラウザプレビューで検証**

1. Run（バックグラウンド）: `cd 貸金試験対策アプリ/app && python3 -m http.server 8123`
2. preview_start `{url: "http://localhost:8123/"}`。
3. 検証:
   - read_console_messages で SW 登録エラーが無いこと
   - read_network_requests で `sw.js` と shell リソースが取得されていること
   - javascript_tool: `navigator.serviceWorker.controller` が null でない（登録済み）ことを確認
   - 数ページ閲覧後にリロードしても表示される
4. http.server を停止。

- [ ] **Step 5: コミット**

```bash
git add 貸金試験対策アプリ/app/manifest.webmanifest 貸金試験対策アプリ/app/sw.js 貸金試験対策アプリ/app/js/app.js
git commit -m "feat(kashikin/reader): PWA化(オフライン動作・ホーム画面に追加)"
```

---

## Self-Review

**1. Spec coverage（改訂スペック §3〜§7）:**
- §4 manifest 生成（走査・章保持マージ）→ Task 1。✓
- §5 画像リーダー/TOC/既読/メモ → Task 5。✓
- §5 SRS復習（Leitner）→ Task 2（srs.js）+ Task 5（復習モード配線）。✓
- §5 学習記録（ストリーク・進捗%）→ Task 3 + Task 5（ヘッダ表示）。✓
- §6 進捗データモデル（pages/activityDates）→ Task 3/4。✓
- §7 モジュール構成（srs/progress/store/reader/app、node:test、build_manifest pytest）→ 全タスク。✓
- §7 PWA（SW + webmanifest）→ Task 6。✓
- KV同期・Access・デプロイは Plan B（本プラン対象外）。✓

**2. Placeholder scan:** TODO/TBD/「適切に」等なし。全コードは実物。✓

**3. Type consistency:**
- 状態形 `{ pages: {[id]:{read?,box?,due?,note?}}, activityDates:[] }` を progress/store/app/srs で統一。✓
- `review(entry, grade, today)` の grade 値 `"known"|"again"` を srs 定義・app の `grade("known")/grade("again")` で一致。✓
- `setPageSrs(state, id, {box,due}, today)` の srs 形（`enterReview`/`review` の戻り値 `{box,due}`）が一致。✓
- `flattenPages` の要素 `{id,image,chapterId,chapterTitle,index}` を reader.test と showPage/renderTOC 消費で一致。✓
- manifest 形（`chapters[].pages[].{id,image}`）を build_manifest 出力・flattenPages 入力・fetch で統一。✓
- SW キャッシュの shell パスが実ファイル（js/srs.js 等）と一致。✓

**注記:** `enterReview` は翌日期限のため「要復習に追加」した当日は due-count が増えない（翌日から復習対象）。これは仕様通り（Task 5 Step 10 の検証注記に明記）。

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-19-kashikin-planA-reader.md`.**

全2プラン構成の **Plan A（画像リーダー＋学習補助・完全無料/オフライン）**。完了後に Plan B（Cloudflare KV同期＋Access＋デプロイ）を作成・実装します。旧 Plan 1（Vision生成）は休眠資産として保持。
