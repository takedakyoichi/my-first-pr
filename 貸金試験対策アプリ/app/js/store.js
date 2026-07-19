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
