from PIL import Image, ImageDraw, ImageFont
import os

from common_env import GAME_DIR, OUT, FONT, TMP
src = os.path.join(GAME_DIR, 'Picture', 'Menu', 'MN_Sub_000200.png')
out_preview = os.path.join(TMP, 'mnsub200_zh.png')
ov = OUT



orig = Image.open(src)
palette = orig.getpalette()
base = orig.convert('RGB')
px = base.load()
w, h = base.size

bands = [(10, 18), (26, 34), (42, 50), (58, 66), (74, 82), (90, 98), (106, 114)]
labels = ['物品', '能力', '装备', '魔法', '快捷键登记', '选项', '存档']

def is_text(c):
    r, g, b = c
    return r > 120 and g > 160 and b > 200

# erase text rows using per-row background color sampled at x 74..80
for (y0, y1) in bands:
    for y in range(max(0, y0 - 5), min(h, y1 + 5)):
        samples = [px[x, y] for x in range(74, 81) if not is_text(px[x, y])]
        if not samples:
            continue
        col = max(set(samples), key=samples.count)
        for x in range(4, 84):
            px[x, y] = col

font = ImageFont.truetype(FONT, 12)
WHITE = (250, 250, 255)
SHADOW = (29, 29, 30)

def draw_text_hard(target, pos, text, color):
    mask = Image.new('L', target.size, 0)
    d = ImageDraw.Draw(mask)
    d.text(pos, text, font=font, fill=255)
    mask = mask.point(lambda v: 255 if v >= 110 else 0)
    target.paste(color, (0, 0), mask)

for (y0, y1), text in zip(bands, labels):
    ty = y0 - 2
    draw_text_hard(base, (9, ty + 1), text, SHADOW)
    draw_text_hard(base, (8, ty), text, WHITE)

# map RGB back to the original palette (index 0 stays orange = transparent)
pal_rgb = {}
for i in range(256):
    pal_rgb.setdefault(tuple(palette[i * 3:i * 3 + 3]), i)

data = bytearray()
for y in range(h):
    for x in range(w):
        c = px[x, y]
        idx = pal_rgb.get(c)
        if idx is None:
            # nearest palette entry
            best = 0; bd = 10 ** 9
            for i in range(256):
                pr, pg, pb = palette[i * 3:i * 3 + 3]
                d2 = (pr - c[0]) ** 2 + (pg - c[1]) ** 2 + (pb - c[2]) ** 2
                if d2 < bd:
                    bd = d2; best = i
            idx = best
            pal_rgb[c] = idx
        data.append(idx)

out = Image.frombytes('P', (w, h), bytes(data))
out.putpalette(palette)
out.save(out_preview)
os.makedirs(ov, exist_ok=True)
out.save(os.path.join(ov, 'MN_Sub_000200.png'))
print('mode', out.mode, 'palette[0]', tuple(palette[0:3]), 'saved')
