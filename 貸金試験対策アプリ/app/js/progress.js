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
