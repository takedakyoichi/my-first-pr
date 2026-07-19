from __future__ import annotations

import json
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def scan_images(pages_dir: Path) -> list[str]:
    names = sorted(p.name for p in pages_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    return [f"pages/{name}" for name in names]


def page_id(image_path: str) -> str:
    return f"p-{Path(image_path).stem}"


def build_manifest(images: list[str], existing: dict | None) -> dict:
    existing = existing or {"version": 1, "chapters": []}
    assigned = {
        pg["image"]: ch["id"]
        for ch in existing.get("chapters", [])
        for pg in ch.get("pages", [])
    }
    chapters = [
        {"id": c["id"], "title": c["title"], "pages": []}
        for c in existing.get("chapters", [])
    ]
    by_id = {c["id"]: c for c in chapters}

    unassigned: list[str] = []
    for img in images:
        cid = assigned.get(img)
        if cid and cid in by_id:
            by_id[cid]["pages"].append({"id": page_id(img), "image": img})
        else:
            unassigned.append(img)

    if unassigned:
        uncat = by_id.get("ch-uncat")
        if uncat is None:
            uncat = {"id": "ch-uncat", "title": "未分類", "pages": []}
            chapters.append(uncat)
            by_id["ch-uncat"] = uncat
        for img in unassigned:
            uncat["pages"].append({"id": page_id(img), "image": img})

    chapters = [c for c in chapters if c["pages"]]
    return {"version": 1, "chapters": chapters}


def main() -> None:
    app_dir = Path(__file__).parent / "app"
    pages_dir = app_dir / "pages"
    manifest_path = app_dir / "manifest.json"
    pages_dir.mkdir(parents=True, exist_ok=True)

    images = scan_images(pages_dir)
    existing = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else None
    )
    manifest = build_manifest(images, existing)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total = sum(len(c["pages"]) for c in manifest["chapters"])
    print(f"manifest.json: {len(manifest['chapters'])} chapters, {total} pages")


if __name__ == "__main__":
    main()
