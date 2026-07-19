function pickSrs(a, b) {
  const aHas = a && typeof a.box === "number";
  const bHas = b && typeof b.box === "number";
  if (!aHas && !bHas) return null;
  if (aHas && !bHas) return { box: a.box, due: a.due };
  if (bHas && !aHas) return { box: b.box, due: b.due };
  if (a.box !== b.box) return a.box > b.box ? { box: a.box, due: a.due } : { box: b.box, due: b.due };
  return (a.due ?? "") >= (b.due ?? "") ? { box: a.box, due: a.due } : { box: b.box, due: b.due };
}

function pickNote(a, b) {
  const an = a && typeof a.note === "string" && a.note !== "" ? a.note : undefined;
  if (an !== undefined) return an;
  const bn = b && typeof b.note === "string" && b.note !== "" ? b.note : undefined;
  return bn;
}

export function mergeStates(local, remote) {
  const lp = local.pages ?? {};
  const rp = remote.pages ?? {};
  const ids = new Set([...Object.keys(lp), ...Object.keys(rp)]);
  const pages = {};
  for (const id of ids) {
    const a = lp[id];
    const b = rp[id];
    const entry = {};
    if ((a && a.read) || (b && b.read)) entry.read = true;
    const srs = pickSrs(a, b);
    if (srs) { entry.box = srs.box; entry.due = srs.due; }
    const note = pickNote(a, b);
    if (note !== undefined) entry.note = note;
    pages[id] = entry;
  }
  const dates = new Set([...(local.activityDates ?? []), ...(remote.activityDates ?? [])]);
  return { pages, activityDates: [...dates].sort() };
}
