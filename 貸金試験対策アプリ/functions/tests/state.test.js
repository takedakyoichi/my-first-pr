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
