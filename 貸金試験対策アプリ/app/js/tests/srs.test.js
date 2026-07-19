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
