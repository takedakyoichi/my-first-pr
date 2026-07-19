from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from .merge import merge_pages
from .schema import Content
from .vision import extract_from_image

IMAGE_EXTS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def load_content(path: Path) -> Content:
    if path.exists():
        return Content.model_validate_json(path.read_text(encoding="utf-8"))
    return Content(version=1, generatedAt="", topics=[], questions=[])


def run(import_dir: Path, content_path: Path, extractor=extract_from_image, client=None) -> Content:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()

    images = sorted(
        p for p in import_dir.iterdir()
        if p.suffix.lower() in IMAGE_EXTS
    )
    pages = []
    for img in images:
        media_type = IMAGE_EXTS[img.suffix.lower()]
        pages.append(extractor(client, img.read_bytes(), media_type))
        print(f"processed {img.name}")

    content = merge_pages(load_content(content_path), pages)
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_text(
        json.dumps(content.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return content


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Kindle撮影画像→content.json 生成バッチ")
    parser.add_argument("--import-dir", default="import")
    parser.add_argument("--out", default="app/content.json")
    args = parser.parse_args()

    content = run(Path(args.import_dir), Path(args.out))
    print(f"done: topics={len(content.topics)} questions={len(content.questions)} -> {args.out}")


if __name__ == "__main__":
    main()
