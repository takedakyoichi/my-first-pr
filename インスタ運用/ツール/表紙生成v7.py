# 挽肉と米 表紙v7（v6軸: エリア表記を位置情報ピン＋太ゴシックに変更）
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙元.jpg"
OUT = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙-v7.png"
PEN = "/Users/kyoichi/Claud用/インスタ運用/ツール/fonts/ZenKurenaido-Regular.ttf"
GOTHIC = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"

W, H = 1080, 1350
WHITE = (255, 255, 255, 255)

img = Image.open(SRC)
sw, sh = img.size
crop_h = int(sw * 1.25)
y0 = 1020
img = img.crop((0, y0, sw, y0 + crop_h)).resize((W, H), Image.LANCZOS).convert("RGBA")

def pin_and_text(color):
    """位置情報ピン＋「吉祥寺」を1レイヤーに描く"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy, r = 80, 116, 30           # ピンの丸
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    d.polygon([(cx - 20, cy + 20), (cx + 20, cy + 20), (cx, cy + 58)], fill=color)
    d.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=(0, 0, 0, 0))  # 穴を抜く
    f = ImageFont.truetype(GOTHIC, 68)
    d.text((cx + 44, cy - 34), "吉祥寺", font=f, fill=color)
    return layer

shadow = pin_and_text((0, 0, 0, 175))
shadow = shadow.transform((W, H), Image.AFFINE, (1, 0, -5, 0, 1, -6))
shadow = shadow.filter(ImageFilter.GaussianBlur(5))
img = Image.alpha_composite(img, shadow)
img = Image.alpha_composite(img, pin_and_text(WHITE))
d = ImageDraw.Draw(img)

# キャッチ（v6と同じ: 2段・斜め・強めの影）
f1 = ImageFont.truetype(PEN, 104)
f2 = ImageFont.truetype(PEN, 96)
layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dl, dsl = ImageDraw.Draw(layer), ImageDraw.Draw(sl)
for s, f, lx, ly in [("肉汁で", f1, 140, 208), ("キマッテシマイマシタ", f2, 96, 344)]:
    dsl.text((lx + 6, ly + 7), s, font=f, fill=(0, 0, 0, 185))
    dl.text((lx, ly), s, font=f, fill=WHITE)
sl = sl.filter(ImageFilter.GaussianBlur(6))
img = Image.alpha_composite(Image.alpha_composite(img, sl.rotate(4, resample=Image.BICUBIC, center=(W / 2, 320))),
                            layer.rotate(4, resample=Image.BICUBIC, center=(W / 2, 320)))
img.convert("RGB").save(OUT)
print("saved", OUT)
