"""dev用: 動作確認用のサンプルページ画像(単色PNG)を app/pages/ に生成する。"""
import struct
import zlib
from pathlib import Path


def write_png(path: Path, width: int, height: int, rgb: tuple[int, int, int]) -> None:
    def chunk(typ: bytes, data: bytes) -> bytes:
        body = typ + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def main() -> None:
    out = Path(__file__).parent.parent / "app" / "pages"
    out.mkdir(parents=True, exist_ok=True)
    colors = [(230, 200, 200), (200, 230, 200), (200, 200, 230)]
    for i, rgb in enumerate(colors, start=1):
        write_png(out / f"sample-{i:03d}.png", 600, 800, rgb)
    print(f"wrote {len(colors)} sample images to {out}")


if __name__ == "__main__":
    main()
