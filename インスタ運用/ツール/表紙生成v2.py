# 挽肉と米 表紙v2（rn_gohanlog参考: 縦書き大「東京」＋エリア名・全面写真ミニマル型）
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙元.jpg"
OUT = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙-v2.png"
GOTHIC = "/System/Library/Fonts/ヒラギノ角ゴシック W9.ttc"

W, H = 1080, 1350
WHITE = (255, 255, 255, 255)
SHADOW = (0, 0, 0, 150)

img = Image.open(SRC)
sw, sh = img.size
crop_h = int(sw * 1.25)
y0 = 1020
img = img.crop((0, y0, sw, y0 + crop_h)).resize((W, H), Image.LANCZOS).convert("RGBA")

f_big = ImageFont.truetype(GOTHIC, 190)
f_area = ImageFont.truetype(GOTHIC, 64)

shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ds, dt = ImageDraw.Draw(shadow), ImageDraw.Draw(text)

x, ytop, gap = 48, 96, 14
for i, c in enumerate(["東", "京"]):
    cy = ytop + i * (190 + gap)
    ds.text((x + 6, cy + 8), c, font=f_big, fill=SHADOW)
    dt.text((x, cy), c, font=f_big, fill=WHITE)

ay = ytop + 2 * (190 + gap) + 26
ds.text((x + 8, ay + 6), "吉祥寺", font=f_area, fill=SHADOW)
dt.text((x + 4, ay), "吉祥寺", font=f_area, fill=WHITE)

shadow = shadow.filter(ImageFilter.GaussianBlur(7))
img = Image.alpha_composite(Image.alpha_composite(img, shadow), text)
img.convert("RGB").save(OUT)
print("saved", OUT)
