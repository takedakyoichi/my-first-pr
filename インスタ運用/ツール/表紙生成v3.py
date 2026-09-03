# 挽肉と米 表紙v3（手書き看板風: Yusei Magic・縦書き東京＋エリア名＋関西弁キャッチ）
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙元.jpg"
OUT = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙-v3.png"
FONT = "/private/tmp/claude-501/-Users-kyoichi-Claud-/530534c3-7cef-47d6-ace3-7d83da216441/scratchpad/YuseiMagic-Regular.ttf"

W, H = 1080, 1350
WHITE = (255, 255, 255, 255)
SHADOW = (0, 0, 0, 165)

img = Image.open(SRC)
sw, sh = img.size
crop_h = int(sw * 1.25)
y0 = 1020
img = img.crop((0, y0, sw, y0 + crop_h)).resize((W, H), Image.LANCZOS).convert("RGBA")

f_catch = ImageFont.truetype(FONT, 76)
f_big = ImageFont.truetype(FONT, 175)
f_area = ImageFont.truetype(FONT, 62)

shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ds, dt = ImageDraw.Draw(shadow), ImageDraw.Draw(text)

def put(x, y, s, f):
    ds.text((x + 6, y + 7), s, font=f, fill=SHADOW)
    dt.text((x, y), s, font=f, fill=WHITE)

# 上部キャッチ（中央寄せ）
catch = "肉汁でキマッテシマイマシタ"
cw = dt.textlength(catch, font=f_catch)
put((W - cw) / 2, 52, catch, f_catch)

# 左に縦書き「東京」＋エリア名
x, ytop, gap = 52, 240, 12
for i, c in enumerate(["東", "京"]):
    put(x, ytop + i * (175 + gap), c, f_big)
put(x + 6, ytop + 2 * (175 + gap) + 24, "吉祥寺", f_area)

shadow = shadow.filter(ImageFilter.GaussianBlur(6))
img = Image.alpha_composite(Image.alpha_composite(img, shadow), text)
img.convert("RGB").save(OUT)
print("saved", OUT)
