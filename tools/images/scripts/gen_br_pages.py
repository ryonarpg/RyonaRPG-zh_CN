import os
from PIL import Image, ImageDraw, ImageFont

from common_env import GAME_DIR, OUT, FONT
SRC = os.path.join(GAME_DIR, 'Picture', 'Menu')
STAGE = OUT


OKEY = (255, 156, 0)
OUTLINE = (29, 29, 30)
FILL = (155, 220, 255)

def load_rgb(path):
    im = Image.open(path); pal = im.getpalette()
    data = list(im.getdata()); base = Image.new('RGB', im.size); px = base.load()
    for y in range(im.height):
        for x in range(im.width):
            i = data[y * im.width + x]
            px[x, y] = tuple(pal[i * 3:i * 3 + 3])
    return base, pal

def draw_text(px, w, h, x0, y0, text):
    f = ImageFont.truetype(FONT, 12)
    b = f.getbbox(text)
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).text((x0 - b[0], y0 - b[1]), text, font=f, fill=255)
    mask = mask.point(lambda v: 255 if v >= 110 else 0)
    mp = mask.load()
    for yy in range(h):
        for xx in range(w):
            if mp[xx, yy]:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = xx + dx, yy + dy
                        if 0 <= nx < w and 0 <= ny < h and not mp[nx, ny]:
                            px[nx, ny] = OUTLINE
    for yy in range(h):
        for xx in range(w):
            if mp[xx, yy]:
                px[xx, yy] = FILL

def save_paletted(im, palette, path):
    pal_list = [tuple(palette[i * 3:i * 3 + 3]) for i in range(len(palette) // 3)]
    while len(pal_list) < 256:
        pal_list.append((0, 0, 0))
    pal_list[0] = OKEY
    for need in (FILL, OUTLINE):
        if need not in pal_list:
            for i in range(255, 0, -1):
                if pal_list[i] == (0, 0, 0):
                    pal_list[i] = need
                    break
    exact = {}
    for i, c in enumerate(pal_list):
        exact.setdefault(c, i)
    data = bytearray(); px = im.load(); w, h = im.size
    for y in range(h):
        for x in range(w):
            c = px[x, y]
            idx = exact.get(c)
            if idx is None:
                best = 0; bd = 10 ** 9
                for i, pc in enumerate(pal_list):
                    d2 = (pc[0] - c[0]) ** 2 + (pc[1] - c[1]) ** 2 + (pc[2] - c[2]) ** 2
                    if d2 < bd:
                        bd = d2; best = i
                idx = best
            data.append(idx)
    flat = []
    for c in pal_list:
        flat.extend(c)
    out = Image.frombytes('P', (w, h), bytes(data))
    out.putpalette(flat)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out.save(path)

def is_blue(c):
    r, g, b = c
    return b >= 190 and (b - r) >= 50 and g >= 140

# BR0602 labels
base, pal = load_rgb(os.path.join(SRC, 'MN_BR_0602.png'))
px = base.load(); w, h = base.size
for x0, y0, x1, y1, text in [
    (44, 143, 170, 152, '头像显示'),
    (44, 160, 110, 169, '步行时袖白'),
    (44, 177, 175, 186, '台词触发频率 (n/10)'),
    (44, 194, 145, 203, '台词瞬间显示'),
    (44, 211, 160, 220, '男性路人青字台词'),
]:
    for y in range(max(0, y0 - 3), min(h, y0 + 13)):
        for x in range(max(0, x0 - 5), min(w, x1 + 8)):
            px[x, y] = OKEY
    draw_text(px, w, h, x0, y0, text)
save_paletted(base, pal, os.path.join(STAGE, 'MN_BR_0602.png'))
print('BR0602 done')

# BR0440: erase the whole label band and redraw centered
base, pal = load_rgb(os.path.join(SRC, 'MN_BR_0440.png'))
px = base.load(); w, h = base.size
for y in range(72, 88):
    for x in range(30, 291):
        px[x, y] = OKEY
text = '半身像动画'
f = ImageFont.truetype(FONT, 12)
tw = f.getbbox(text)[2] - f.getbbox(text)[0]
draw_text(px, w, h, (w - tw) // 2, 77, text)
save_paletted(base, pal, os.path.join(STAGE, 'MN_BR_0440.png'))
print('BR0440 done')
