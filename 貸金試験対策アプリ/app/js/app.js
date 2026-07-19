import { loadState, saveState } from "./store.js";
import {
  markRead, toggleRead, setNote, setPageSrs,
} from "./progress.js";
import { enterReview, review, duePageIds } from "./srs.js";
import { flattenPages, renderTOC, showPage, updateHeader } from "./reader.js";

const todayISO = () => new Date().toISOString().slice(0, 10);

const els = {
  menuBtn: document.getElementById("menu-btn"),
  toc: document.getElementById("toc"),
  streak: document.getElementById("streak"),
  progress: document.getElementById("progress"),
  image: document.getElementById("page-image"),
  chapterLabel: document.getElementById("chapter-label"),
  pageIndex: document.getElementById("page-index"),
  prev: document.getElementById("prev"),
  next: document.getElementById("next"),
  readToggle: document.getElementById("read-toggle"),
  reviewToggle: document.getElementById("review-toggle"),
  note: document.getElementById("note"),
  startReview: document.getElementById("start-review"),
  dueCount: document.getElementById("due-count"),
  viewer: document.getElementById("viewer"),
  reviewMode: document.getElementById("review-mode"),
  reviewImage: document.getElementById("review-image"),
  reviewProgress: document.getElementById("review-progress"),
  gradeAgain: document.getElementById("grade-again"),
  gradeKnown: document.getElementById("grade-known"),
  reviewExit: document.getElementById("review-exit"),
};

let manifest = { version: 1, chapters: [] };
let pages = [];
let state = loadState();
let current = 0;
let reviewQueue = [];

function persist() {
  saveState(state);
}

function refreshHeader() {
  updateHeader(els, state, pages.length, todayISO());
  els.dueCount.textContent = String(duePageIds(state.pages, todayISO()).length);
}

function go(index) {
  if (pages.length === 0) return;
  current = Math.max(0, Math.min(index, pages.length - 1));
  const page = pages[current];
  // 閲覧で既読化
  state = markRead(state, page.id, todayISO());
  persist();
  showPage(els, page, state);
  refreshHeader();
  renderTOC(els.toc, manifest, state, jump);
}

function jump(index) {
  els.toc.hidden = true;
  go(index);
}

els.menuBtn.addEventListener("click", () => { els.toc.hidden = !els.toc.hidden; });
els.prev.addEventListener("click", () => go(current - 1));
els.next.addEventListener("click", () => go(current + 1));

els.readToggle.addEventListener("click", () => {
  state = toggleRead(state, pages[current].id, todayISO());
  persist();
  showPage(els, pages[current], state);
  refreshHeader();
});

els.reviewToggle.addEventListener("click", () => {
  const id = pages[current].id;
  const entry = state.pages[id] ?? {};
  if (typeof entry.box !== "number") {
    state = setPageSrs(state, id, enterReview(todayISO()), todayISO());
    persist();
    showPage(els, pages[current], state);
    refreshHeader();
  }
});

els.note.addEventListener("change", () => {
  state = setNote(state, pages[current].id, els.note.value, todayISO());
  persist();
});

// --- 復習モード ---
function startReview() {
  reviewQueue = duePageIds(state.pages, todayISO());
  if (reviewQueue.length === 0) return;
  els.viewer.hidden = true;
  els.reviewMode.hidden = false;
  showNextReview();
}

function showNextReview() {
  if (reviewQueue.length === 0) { exitReview(); return; }
  const id = reviewQueue[0];
  const page = pages.find((p) => p.id === id);
  els.reviewImage.src = page ? page.image : "";
  els.reviewProgress.textContent = `残り ${reviewQueue.length} ページ`;
}

function grade(kind) {
  const id = reviewQueue.shift();
  const entry = state.pages[id] ?? {};
  state = setPageSrs(state, id, review(entry, kind, todayISO()), todayISO());
  persist();
  refreshHeader();
  showNextReview();
}

function exitReview() {
  els.reviewMode.hidden = true;
  els.viewer.hidden = false;
  refreshHeader();
}

els.startReview.addEventListener("click", startReview);
els.gradeAgain.addEventListener("click", () => grade("again"));
els.gradeKnown.addEventListener("click", () => grade("known"));
els.reviewExit.addEventListener("click", exitReview);

async function boot() {
  try {
    const res = await fetch("manifest.json");
    manifest = await res.json();
  } catch {
    manifest = { version: 1, chapters: [] };
  }
  pages = flattenPages(manifest);
  renderTOC(els.toc, manifest, state, jump);
  if (pages.length > 0) go(0);
  refreshHeader();
}

boot();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  });
}
