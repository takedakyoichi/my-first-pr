# 挽肉と米 表紙v6（v4軸: 白タグ明朝＋細ペン字キャッチのみを大きく・2段斜め）
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙元.jpg"
OUT = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙-v6.png"
PEN = "/Users/kyoichi/Claud用/インスタ運用/ツール/fonts/ZenKurenaido-Regular.ttf"
MINCHO = "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"

W, H = 1080, 1350
WHITE = (255, 255, 255, 255)
INK = (28, 24, 22, 255)

img = Image.open(SRC)
sw, sh = img.size
crop_h = int(sw * 1.25)
y0 = 1020
img = img.crop((0, y0, sw, y0 + crop_h)).resize((W, H), Image.LANCZOS).convert("RGBA")
d = ImageDraw.Draw(img)

# 1) 左上: 白い四角タグ＋黒明朝「吉祥寺」
f_tag = ImageFont.truetype(MINCHO, 66, index=1)
tag = "吉祥寺"
pad_x, pad_y = 22, 14
tw = d.textlength(tag, font=f_tag)
tx, ty = 40, 84
d.rectangle((tx, ty, tx + tw + pad_x * 2, ty + 66 + pad_y * 2), fill=WHITE)
d.text((tx + pad_x, ty + pad_y - 4), tag, font=f_tag, fill=INK)

# 2) キャッチのみ・大きく（2段・斜め・強めの影）
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
