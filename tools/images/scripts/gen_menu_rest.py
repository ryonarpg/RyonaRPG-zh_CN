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
    if im.mode != 'P':
        return im.convert('RGB'), pal
    data = list(im.getdata()); base = Image.new('RGB', im.size); px = base.load()
    for y in range(im.height):
        for x in range(im.width):
            i = data[y * im.width + x]
            px[x, y] = tuple(pal[i * 3:i * 3 + 3])
    return base, pal

def is_text(c):
    r, g, b = c
    if r >= 235 and g >= 235:
        return False
    return (r >= 100 and g >= 100) or (g >= 140 and b >= 190)

def fill_box(px, w, h, x0, y0, x1, y1, mode):
    if mode == 'okey':
        for y in range(max(0, y0), min(h, y1 + 1)):
            for x in range(max(0, x0), min(w, x1 + 1)):
                px[x, y] = OKEY
        return
    for y in range(max(0, y0), min(h, y1 + 1)):
        bg = (5, 35, 110)
        found = False
        for sx in list(range(x1 + 3, min(w - 2, x1 + 40))) + list(range(max(1, x0 - 3), max(1, x0 - 40), -1)):
            c = px[sx, y]
            if c != OKEY and not is_text(c) and 50 <= max(c) <= 160:
                bg = c; found = True; break
        for x in range(max(0, x0), min(w, x1 + 1)):
            if px[x, y] != OKEY:
                px[x, y] = bg

def draw_text(px, w, h, x0, y0, text, outline=True):
    f = ImageFont.truetype(FONT, 12)
    b = f.getbbox(text)
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).text((x0 - b[0], y0 - b[1]), text, font=f, fill=255)
    mask = mask.point(lambda v: 255 if v >= 110 else 0)
    mp = mask.load()
    if outline:
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

# rel, mode, entries (x0,y0,x1,y1,text,outline)
JOBS = {
    'ItemSelector/MN_ItemInfo.png': ('bg', [
        (32, 90, 65, 100, '攻击力', True), (32, 106, 65, 116, '防御力', True),
        (33, 122, 53, 132, '魔力', True), (32, 138, 54, 148, '精神', True),
    ]),
    'ItemSelector/MN_ItemSelector_Status.png': ('bg', [
        (16, 154, 50, 164, '攻击力', True), (16, 170, 50, 180, '防御力', True),
        (17, 186, 40, 196, '魔力', True), (16, 202, 40, 212, '精神', True),
    ]),
    'ItemSelector/MN_Shop_Select.png': ('bg', [(207, 105, 247, 116, '所持数', True)]),
    'ItemSelector/MN_Shop_Value.png': ('bg', [(207, 105, 247, 116, '所持数', True)]),
    'CraftMenu/MaterialList.png': ('bg', [
        (128, 42, 150, 52, '材料', True), (256, 42, 315, 52, '持有/需要', True),
    ]),
    'aptSet.png': ('bg', [
        (20, 8, 88, 18, '适性分配', True),
        (58, 41, 97, 51, 'B适性', True), (188, 41, 210, 51, '确定', True),
        (57, 57, 97, 66, 'V适性', True),
        (59, 73, 97, 83, 'A适性', True), (188, 73, 233, 83, '重来', True),
        (58, 89, 97, 98, 'N适性', True),
        (58, 105, 97, 114, 'U适性', True),
        (20, 137, 97, 145, '剩余点数', True),
    ]),
    'cvSet.png': ('bg', [
        (9, 10, 66, 20, '语音设定', False),
        (20, 42, 65, 50, '确定键', False),
        (20, 58, 71, 66, '取消键', False),
        (110, 58, 191, 66, '不修改直接结束', False),
    ]),
    'cvSetX0.png': ('okey', [
        (80, 26, 102, 35, '确定', False), (111, 42, 157, 47, '更改设定', False),
    ]),
    'cvSetX1.png': ('okey', [
        (80, 26, 102, 35, '确定', False), (111, 42, 168, 47, '试听语音', False),
    ]),
    'aptSetX1.png': ('okey', [(25, 4, 94, 13, '全部自动', False)]),
    'aptSetX2.png': ('okey', [(24, 4, 82, 13, '取消自动', False)]),
    'MN_MSG_000003.png': ('bg', [(36, 10, 165, 20, '需要身体检查器', False)]),
}

# Shop serif
serifs = {
    'MN_Shop_Serif01_0.png': [(15, 10, 90, 20, '「欢迎光临」'), (20, 26, 119, 36, '你需要什么？')],
    'MN_Shop_Serif01_1.png': [(15, 10, 131, 20, '「要买几个？」')],
    'MN_Shop_Serif02_0.png': [(15, 10, 119, 20, '「欢迎光临」')],
    'MN_Shop_Serif02_1.png': [(15, 10, 155, 20, '「您需要几个？」')],
    'MN_Shop_Serif03_0.png': [(15, 10, 150, 20, '「章鱼烧店」创业90年'), (21, 26, 167, 36, '目标是日本第一的章鱼烧店！')],
    'MN_Shop_Serif03_1.png': [(15, 10, 143, 20, '「多买点带走吧」')],
    'MN_Shop_Serif04_0.png': [(15, 10, 64, 20, '「嘘——！」'), (20, 26, 121, 36, '别这么大声！'), (20, 42, 83, 52, '有什么事？')],
    'MN_Shop_Serif04_1.png': [(15, 10, 131, 20, '「需要几个？」')],
    'MN_Shop_Serif05_0.png': [(15, 10, 155, 20, '「要购买哪种子弹？」')],
    'MN_Shop_Serif05_1.png': [(15, 10, 143, 20, '「要购买多少？」')],
}
for n, lines in serifs.items():
    JOBS['ItemSelector/' + n] = ('bg', [(x0, y0, x1, y1, t, False) for x0, y0, x1, y1, t in lines])

for rel, (mode, entries) in JOBS.items():
    src = os.path.join(SRC, rel)
    if not os.path.exists(src):
        print('missing', rel); continue
    base, pal = load_rgb(src)
    px = base.load(); w, h = base.size
    for x0, y0, x1, y1, text, outline in entries:
        fill_box(px, w, h, x0 - 5, y0 - 3, x1 + 8, y0 + 13, mode)
        draw_text(px, w, h, x0, y0, text, outline)
    save_paletted(base, pal, os.path.join(STAGE, rel))
    print('done', rel, len(entries))
