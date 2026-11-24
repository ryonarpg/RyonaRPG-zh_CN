from PIL import Image, ImageDraw, ImageFont
import os

from common_env import GAME_DIR, OUT, FONT, TMP
SRC = os.path.join(GAME_DIR, 'Picture', 'Menu', 'MN_Main_000000.png')
DEST = os.path.join(OUT, 'MN_Main_000000.png')


OKEY = (255, 156, 0)
OUTLINE = (29, 29, 30)
BLUE = (136, 202, 250)
GRAY = (201, 201, 205)

orig = Image.open(SRC)
palette = orig.getpalette()
base = orig.convert('RGB')
px = base.load(); w, h = base.size

def bg_at(y):
    return px[305, y]

def text_bbox(x0, y0, x1, y1):
    xs = []; ys = []
    for y in range(y0, y1):
        bg = bg_at(y)
        for x in range(x0, x1):
            c = px[x, y]
            if c != OKEY and c != bg:
                xs.append(x); ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)

def erase_box(bx0, by0, bx1, by1):
    for y in range(max(0, by0 - 1), min(h, by1 + 2)):
        bg = bg_at(y)
        for x in range(max(0, bx0 - 1), min(w, bx1 + 2)):
            if px[x, y] != OKEY:
                px[x, y] = bg

def draw(xy, text, maxw, fill):
    size = 12
    while size > 8:
        f = ImageFont.truetype(FONT, size)
        b = f.getbbox(text)
        if b[2] - b[0] <= maxw:
            break
        size -= 1
    f = ImageFont.truetype(FONT, size)
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
                        if 0 <= nx < w and 0 <= ny < h and not mp[nx, ny] and px[nx, ny] != OKEY:
                            px[nx, ny] = OUTLINE
    for y in range(h):
        for x in range(w):
            if mp[x, y]:
                px[x, y] = fill

labels = ['毒', '黑暗', '沉默', '麻痹', '倒地', '出血', '捕获', '黏液',
          '恐惧', '冻结', '昏厥', '？？', '羞耻', '寄生', '疲劳', '衰弱']
cols = [122, 170, 218, 266]
rows = [127, 144, 161, 178]

tasks = [
    ((152, 59, 199, 70), '攻击力：', BLUE),
    ((236, 59, 283, 70), '魔力：', BLUE),
    ((152, 76, 199, 87), '防御力：', BLUE),
    ((236, 76, 283, 87), '精神：', BLUE),
    ((104, 110, 128, 121), '状态', BLUE),
    ((236, 212, 272, 223), '衰弱值', BLUE),
]
for r, y in enumerate(rows):
    for c, x in enumerate(cols):
        tasks.append(((x - 1, y, x + 24, y + 11), labels[r * 4 + c], GRAY))

def text_bbox(x0, y0, x1, y1):
    xs = []; ys = []
    for y in range(y0, y1):
        bg = bg_at(y)
        for x in range(x0, x1):
            c = px[x, y]
            if c != OKEY and c != bg:
                xs.append(x); ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)

def erase_box(bx0, by0, bx1, by1):
    for y in range(max(0, by0 - 1), min(h, by1 + 2)):
        bg = bg_at(y)
        for x in range(max(0, bx0 - 1), min(w, bx1 + 2)):
            if px[x, y] != OKEY:
                px[x, y] = bg

def draw(xy, text, maxw, fill):
    size = 12
    while size > 8:
        f = ImageFont.truetype(FONT, size)
        b = f.getbbox(text)
        if b[2] - b[0] <= maxw:
            break
        size -= 1
    f = ImageFont.truetype(FONT, size)
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
                        if 0 <= nx < w and 0 <= ny < h and not mp[nx, ny] and px[nx, ny] != OKEY:
                            px[nx, ny] = OUTLINE
    for y in range(h):
        for x in range(w):
            if mp[x, y]:
                px[x, y] = fill

for (x0, y0, x1, y1), text, fill in tasks:
    bb = text_bbox(x0, y0, x1, y1)
    if not bb:
        print('no bbox', text); continue
    bx0, by0, bx1, by1 = bb
    erase_box(bx0, by0, bx1, by1)
    draw((bx0, by0), text, max(12, bx1 - bx0 + 8), fill)

pal = {}
for i in range(256):
    pal.setdefault(tuple(palette[i * 3:i * 3 + 3]), i)
data = bytearray()
for y in range(h):
    for x in range(w):
        col = px[x, y]
        idx = pal.get(col)
        if idx is None:
            best = 0; bd = 10 ** 9
            for i in range(256):
                pr, pg, pb = palette[i * 3:i * 3 + 3]
                d2 = (pr - col[0]) ** 2 + (pg - col[1]) ** 2 + (pb - col[2]) ** 2
                if d2 < bd:
                    bd = d2; best = i
                idx = best; pal[col] = idx
        data.append(idx)
out = Image.frombytes('P', (w, h), bytes(data))
out.putpalette(palette)
os.makedirs(os.path.dirname(DEST), exist_ok=True)
out.save(DEST)
prev = out.convert('RGB').copy(); pp = prev.load()
for y in range(prev.height):
    for x in range(prev.width):
        if pp[x, y] == OKEY:
            pp[x, y] = (50, 50, 50)
prev.resize((w * 4, h * 4), Image.NEAREST).save(os.path.join(TMP, 'mnmain0_zh.png'))
print('saved', DEST)
