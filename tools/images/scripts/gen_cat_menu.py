from PIL import Image, ImageDraw, ImageFont
import os

from common_env import GAME_DIR, OUT, FONT, TMP
SRC = os.path.join(GAME_DIR, 'Picture', 'Menu', 'MN_Sub_001100.png')
DEST = os.path.join(OUT, 'MN_Sub_001100.png')


OKEY = (255, 156, 0)
OUTLINE = (29, 29, 30)
FILL = (240, 250, 255)

orig = Image.open(SRC)
palette = orig.getpalette()
base = orig.convert('RGB')
px = base.load(); w, h = base.size

bands = [(42, 49), (58, 65), (74, 81), (90, 97), (106, 113)]
labels = ['恢复', '道具', '其他', '重要物品', '列表']

def is_text(c):
    r, g, b = c
    return r > 180 and g > 200 and b > 230

# erase text rows
for (y0, y1) in bands:
    for y in range(max(0, y0 - 5), min(h, y1 + 6)):
        samples = [px[x, y] for x in range(104, 110) if not is_text(px[x, y]) and px[x, y] != OKEY]
        if not samples:
            continue
        col = max(set(samples), key=samples.count)
        for x in range(14, 113):
            px[x, y] = col

font = ImageFont.truetype(FONT, 12)

def render(xy, text, maxw=100):
    f = font; size = 12
    while size > 8:
        f = ImageFont.truetype(FONT, size)
        b = f.getbbox(text)
        if b[2] - b[0] <= maxw:
            break
        size -= 1
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).text(xy, text, font=f, fill=255)
    mask = mask.point(lambda v: 255 if v >= 110 else 0)
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            if mp[x, y]:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and not mp[nx, ny]:
                            px[nx, ny] = OUTLINE
    for y in range(h):
        for x in range(w):
            if mp[x, y]:
                px[x, y] = FILL

for (y0, y1), lab in zip(bands, labels):
    render((20, y0 - 2), lab, 92)

# map to palette
pal = {}
for i in range(256):
    pal.setdefault(tuple(palette[i * 3:i * 3 + 3]), i)
data = bytearray()
for y in range(h):
    for x in range(w):
        c = px[x, y]
        idx = pal.get(c)
        if idx is None:
            best = 0; bd = 10 ** 9
            for i in range(256):
                pr, pg, pb = palette[i * 3:i * 3 + 3]
                d2 = (pr - c[0]) ** 2 + (pg - c[1]) ** 2 + (pb - c[2]) ** 2
                if d2 < bd:
                    bd = d2; best = i
                idx = best; pal[c] = idx
        data.append(idx)
out = Image.frombytes('P', (w, h), bytes(data))
out.putpalette(palette)
os.makedirs(os.path.dirname(DEST), exist_ok=True)
out.save(DEST)
out.convert('RGB').resize((w * 4, h * 4), Image.NEAREST).save(os.path.join(TMP, 'mnsub001100_zh.png'))
print('saved', DEST)
