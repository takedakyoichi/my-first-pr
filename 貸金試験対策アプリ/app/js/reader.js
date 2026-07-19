import { computeStreak, progressPercent } from "./progress.js";

export function flattenPages(manifest) {
  const flat = [];
  let index = 0;
  for (const ch of manifest.chapters) {
    for (const pg of ch.pages) {
      flat.push({
        id: pg.id,
        image: pg.image,
        chapterId: ch.id,
        chapterTitle: ch.title,
        index: index++,
      });
    }
  }
  return flat;
}

export function renderTOC(navEl, manifest, state, onJump) {
  navEl.innerHTML = "";
  let running = 0;
  for (const ch of manifest.chapters) {
    const h = document.createElement("h3");
    h.textContent = ch.title;
    navEl.appendChild(h);
    for (const pg of ch.pages) {
      const idx = running++;
      const btn = document.createElement("button");
      btn.className = "toc-item";
      const read = state.pages[pg.id]?.read ? "✅" : "⬜";
      btn.textContent = `${read} ${pg.id}`;
      btn.addEventListener("click", () => onJump(idx));
      navEl.appendChild(btn);
    }
  }
}

export function showPage(els, page, state) {
  const entry = state.pages[page.id] ?? {};
  els.image.src = page.image;
  els.image.alt = `${page.chapterTitle} ${page.id}`;
  els.chapterLabel.textContent = page.chapterTitle;
  els.pageIndex.textContent = page.id;
  els.readToggle.textContent = entry.read ? "既読 ✅" : "未読 ⬜";
  els.reviewToggle.textContent = typeof entry.box === "number" ? "復習登録済 🔁" : "要復習に追加";
  els.note.value = entry.note ?? "";
}

export function updateHeader(els, state, total, today) {
  els.streak.textContent = `🔥${computeStreak(state.activityDates, today)}`;
  els.progress.textContent = `${progressPercent(state, total)}%`;
}
