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
