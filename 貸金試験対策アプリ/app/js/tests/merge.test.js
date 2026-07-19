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
