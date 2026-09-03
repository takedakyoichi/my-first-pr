# 挽肉と米 表紙v4（non.gourmet_参考: 白タグ明朝エリア名＋細ペン字の斜めキャッチ2行）
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙元.jpg"
OUT = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙-v4.png"
PEN = "/private/tmp/claude-501/-Users-kyoichi-Claud-/530534c3-7cef-47d6-ace3-7d83da216441/scratchpad/ZenKurenaido-Regular.ttf"
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

# 2) 細ペン字の斜めキャッチ2行（白＋うっすら影・-4度回転・2行目を字下げ）
f_pen = ImageFont.truetype(PEN, 57)
layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dl, dsl = ImageDraw.Draw(layer), ImageDraw.Draw(sl)
lines = [("焼きたてハンバーグと炊き立ての米", 84, 240), ("肉汁でキマッテシマイマシタ", 250, 328)]
for s, lx, ly in lines:
    dsl.text((lx + 4, ly + 5), s, font=f_pen, fill=(0, 0, 0, 150))
    dl.text((lx, ly), s, font=f_pen, fill=WHITE)
sl = sl.filter(ImageFilter.GaussianBlur(5))
rot_s = sl.rotate(4, resample=Image.BICUBIC, center=(W / 2, 300))
rot_t = layer.rotate(4, resample=Image.BICUBIC, center=(W / 2, 300))
img = Image.alpha_composite(Image.alpha_composite(img, rot_s), rot_t)

img.convert("RGB").save(OUT)
print("saved", OUT)
