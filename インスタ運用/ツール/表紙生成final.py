# 表紙・確定金型（2026-09-04 オーナー決定のClaudeデザイン案を再現）
# 構成: 黒タグ(ピン＋エリア名) / 手書きキャッチ2段斜め / 右下縦書き店名
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙元.jpg"
OUT = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙-final再現.png"
POP = "/Users/kyoichi/Claud用/インスタ運用/ツール/fonts/YuseiMagic-Regular.ttf"
GOTHIC = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"

AREA, CATCH1, CATCH2, STORE = "吉祥寺", "肉汁で", "キマッテシマイマシタ", "挽肉と米"

W, H = 1080, 1350
WHITE = (255, 255, 255, 255)
BLACK = (22, 20, 18, 235)

img = Image.open(SRC)
sw, sh = img.size
crop_h = int(sw * 1.25)
y0 = 1020
img = img.crop((0, y0, sw, y0 + crop_h)).resize((W, H), Image.LANCZOS).convert("RGBA")
d = ImageDraw.Draw(img)

# 1) 左上: 黒の角丸タグ＋白ピン＋エリア名（太ゴシック）
f_area = ImageFont.truetype(GOTHIC, 54)
aw = d.textlength(AREA, font=f_area)
tx, ty = 48, 88
tag_w = 44 + 34 + 18 + aw + 40
d.rounded_rectangle((tx, ty, tx + tag_w, ty + 82), radius=16, fill=BLACK)
cx, cy, r = tx + 44 + 8, ty + 34, 15
d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE)
d.polygon([(cx - 10, cy + 10), (cx + 10, cy + 10), (cx, cy + 30)], fill=WHITE)
d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=BLACK)
d.text((cx + r + 18, ty + 13), AREA, font=f_area, fill=WHITE)

def shadowed(draws, rotate=None, center=None):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl, dsl = ImageDraw.Draw(layer), ImageDraw.Draw(sl)
    for s, f, lx, ly in draws:
        dsl.text((lx + 6, ly + 8), s, font=f, fill=(0, 0, 0, 190))
        dl.text((lx, ly), s, font=f, fill=WHITE)
    sl = sl.filter(ImageFilter.GaussianBlur(6))
    if rotate:
        sl = sl.rotate(rotate, resample=Image.BICUBIC, center=center)
        layer = layer.rotate(rotate, resample=Image.BICUBIC, center=center)
    return Image.alpha_composite(sl, layer)

# 2) キャッチ2段（手書きPOP体・少し斜め）
f1 = ImageFont.truetype(POP, 108)
f2 = ImageFont.truetype(POP, 94)
img = Image.alpha_composite(img, shadowed(
    [(CATCH1, f1, 64, 268), (CATCH2, f2, 120, 408)], rotate=3, center=(W / 2, 380)))

# 3) 右下: 縦書き店名（太ゴシック）
f_s = ImageFont.truetype(GOTHIC, 74)
draws = []
by = H - 96 - len(STORE) * 82
for c in STORE:
    cw = ImageDraw.Draw(Image.new("RGBA", (10, 10))).textlength(c, font=f_s)
    draws.append((c, f_s, W - 130 + (74 - cw) / 2, by))
    by += 82
img = Image.alpha_composite(img, shadowed(draws))

img.convert("RGB").save(OUT)
print("saved", OUT)
