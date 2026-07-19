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
