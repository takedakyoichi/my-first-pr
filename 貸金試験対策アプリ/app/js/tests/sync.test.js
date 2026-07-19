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
