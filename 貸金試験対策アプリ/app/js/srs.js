export const INTERVALS = [1, 2, 4, 8, 16, 32];

export function addDays(iso, n) {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export function enterReview(today) {
  return { box: 0, due: addDays(today, INTERVALS[0]) };
}

export function review(entry, grade, today) {
  const cur = entry && typeof entry.box === "number" ? entry.box : 0;
  const box = grade === "known" ? Math.min(cur + 1, INTERVALS.length - 1) : 0;
  return { box, due: addDays(today, INTERVALS[box]) };
}

export function isDue(entry, today) {
  return !!entry && typeof entry.box === "number" && typeof entry.due === "string" && entry.due <= today;
}

export function duePageIds(pages, today) {
  return Object.keys(pages).filter((id) => isDue(pages[id], today)).sort();
}
