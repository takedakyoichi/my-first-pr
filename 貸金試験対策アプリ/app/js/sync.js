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
