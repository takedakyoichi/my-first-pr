# 挽肉と米 表紙生成（表紙の型: えりログ型4点構成 — ロゴ以外の3点）
from PIL import Image, ImageDraw, ImageFont

SRC = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙元.jpg"
OUT = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙-v1.png"
FONT = "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"

W, H = 1080, 1350
WHITE = (255, 255, 255)
INK = (32, 27, 24)

img = Image.open(SRC)
sw, sh = img.size  # 4590 x 8160
crop_h = int(sw * 1.25)
y0 = 1020
img = img.crop((0, y0, sw, y0 + crop_h)).resize((W, H), Image.LANCZOS)
d = ImageDraw.Draw(img)

def font(size, index=1):
    return ImageFont.truetype(FONT, size, index=index)

def center_text(y, text, size, stroke=6):
    f = font(size)
    tw = d.textlength(text, font=f)
    d.text(((W - tw) / 2, y), text, font=f, fill=WHITE,
           stroke_width=stroke, stroke_fill=INK)

# 1) 上部キャッチ（13字・白1色＋黒縁）
center_text(64, "肉汁でキマッテシマイマシタ", 76)

# 2) 右上・縦書き「吉祥寺」白座布団
chars = "吉祥寺"
cf = font(58)
pad, gap = 18, 10
ch = 58
bw = 58 + pad * 2
bh = pad * 2 + ch * len(chars) + gap * (len(chars) - 1)
bx2, by1 = W - 36, 210
bx1, by2 = bx2 - bw, by1 + bh
d.rounded_rectangle((bx1, by1, bx2, by2), radius=14, fill=WHITE)
cy = by1 + pad
for c in chars:
    tw = d.textlength(c, font=cf)
    d.text((bx1 + (bw - tw) / 2, cy - 6), c, font=cf, fill=INK)
    cy += ch + gap

# 3) 下部: 店名＋【メニュー ¥実額】（実額はダミー、確定後差し替え）
center_text(1146, "挽肉と米", 46, stroke=5)
center_text(1216, "【挽肉と米定食 ¥0,000】", 62)

img.save(OUT)
print("saved", OUT, img.size)
