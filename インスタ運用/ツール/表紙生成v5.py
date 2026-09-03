# 挽肉と米 表紙v5（masaki_gourmet参考: 白ゴシック2行＋下線・右端に縦書き筆文字）
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙元.jpg"
OUT = "/Users/kyoichi/Claud用/インスタ運用/写真/挽肉と米/表紙-v5.png"
GOTHIC = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
BRUSH = "/private/tmp/claude-501/-Users-kyoichi-Claud-/530534c3-7cef-47d6-ace3-7d83da216441/scratchpad/YujiSyuku-Regular.ttf"

W, H = 1080, 1350
WHITE = (255, 255, 255, 255)

img = Image.open(SRC)
sw, sh = img.size
crop_h = int(sw * 1.25)
y0 = 1020
img = img.crop((0, y0, sw, y0 + crop_h)).resize((W, H), Image.LANCZOS).convert("RGBA")

shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ds, dt = ImageDraw.Draw(shadow), ImageDraw.Draw(text)

# 1) 左上: 白ゴシック2行＋各行に白下線
f_g = ImageFont.truetype(GOTHIC, 52)
lines = ["米おかわり自由！", "焼きたてハンバーグ×炊き立て米"]
x, y = 48, 66
for s in lines:
    tw = dt.textlength(s, font=f_g)
    ds.text((x + 4, y + 5), s, font=f_g, fill=(0, 0, 0, 150))
    dt.text((x, y), s, font=f_g, fill=WHITE)
    dt.rectangle((x, y + 62, x + tw, y + 67), fill=WHITE)
    ds.rectangle((x + 4, y + 66, x + tw + 4, y + 71), fill=(0, 0, 0, 150))
    y += 96

# 2) 右端: 縦書き筆文字「肉汁でキマッテシマイマシタ」
f_b = ImageFont.truetype(BRUSH, 90)
bx, by, gap = W - 140, 250, 2
for c in "肉汁でキマッテシマイマシタ":
    cw = dt.textlength(c, font=f_b)
    ds.text((bx + (90 - cw) / 2 + 5, by + 6), c, font=f_b, fill=(0, 0, 0, 160))
    dt.text((bx + (90 - cw) / 2, by), c, font=f_b, fill=WHITE)
    by += 78 + gap

shadow = shadow.filter(ImageFilter.GaussianBlur(6))
img = Image.alpha_composite(Image.alpha_composite(img, shadow), text)
img.convert("RGB").save(OUT)
print("saved", OUT)
