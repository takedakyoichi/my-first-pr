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
