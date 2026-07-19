from pathlib import Path
from build_manifest import scan_images, page_id, build_manifest


def test_scan_images_sorted(tmp_path):
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "002.png").write_bytes(b"x")
    (pages / "001.png").write_bytes(b"x")
    (pages / "note.txt").write_bytes(b"x")  # 非画像は無視
    assert scan_images(pages) == ["pages/001.png", "pages/002.png"]


def test_page_id_stable():
    assert page_id("pages/001.png") == "p-001"
    assert page_id("pages/003.jpg") == "p-003"


def test_build_manifest_empty_existing():
    m = build_manifest(["pages/001.png", "pages/002.png"], None)
    assert m["version"] == 1
    assert len(m["chapters"]) == 1
    assert m["chapters"][0]["title"] == "未分類"
    assert [p["id"] for p in m["chapters"][0]["pages"]] == ["p-001", "p-002"]


def test_build_manifest_preserves_assignment():
    existing = {
        "version": 1,
        "chapters": [{"id": "ch-1", "title": "第1章", "pages": [
            {"id": "p-001", "image": "pages/001.png"}]}],
    }
    m = build_manifest(["pages/001.png", "pages/002.png"], existing)
    # 001 は ch-1 に残り、002 は 未分類 に入る
    ch1 = next(c for c in m["chapters"] if c["id"] == "ch-1")
    uncat = next(c for c in m["chapters"] if c["id"] == "ch-uncat")
    assert [p["image"] for p in ch1["pages"]] == ["pages/001.png"]
    assert [p["image"] for p in uncat["pages"]] == ["pages/002.png"]
