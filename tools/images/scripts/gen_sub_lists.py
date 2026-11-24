from PIL import Image, ImageDraw, ImageFont
import os

from common_env import GAME_DIR, OUT, FONT, TMP
MENU = os.path.join(GAME_DIR, 'Picture', 'Menu')
DEST = OUT


OKEY = (255, 156, 0)
OUTLINE = (29, 29, 30)
BLUE = (136, 202, 250)

JOBS = {
    'MN_Sub_000100.png': ['装备', '魔法', '内衣', '穿孔', '装填'],
    'MN_Sub_003100.png': ['武器', '盾/箭', '防具', '头盔', '装饰'],
    'MN_Sub_004100.png': ['通常魔法', '赋予魔法', '反应魔法', '辅助魔法', '快捷键'],
    'MN_Sub_005100.png': ['正面-中央', '正面-上', '正面-右', '正面-下', '正面-左',
                          '背面-中央', '背面-上', '背面-右', '背面-下', '背面-左'],
}

def is_text(c):
    r, g, b = c
    return r > 120 and g > 160 and b > 200

for fname, labels in JOBS.items():
    orig = Image.open(os.path.join(MENU, fname))
    palette = orig.getpalette()
    base = orig.convert('RGB')
    px = base.load(); w, h = base.size

    # interior bounds: content bbox of non-orange
    xs = []; ys = []
    for y in range(h):
        for x in range(w):
            if px[x, y] != OKEY:
                xs.append(x); ys.append(y)
    bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
    ix0, ix1 = bx0 + 4, bx1 - 4
    iy0, iy1 = by0 + 4, by1 - 4
    # background sample column (right interior)
    bgx = ix1 - 2

    rows = []
    for y in range(iy0, iy1):
        xr = [x for x in range(ix0, ix1) if is_text(px[x, y])]
        if xr:
            rows.append((y, min(xr), max(xr)))
    bands = []; cur = []; prev = None
    for r in rows:
        if prev is not None and r[0] != prev + 1:
            bands.append(cur); cur = []
        cur.append(r); prev = r[0]
    if cur:
        bands.append(cur)
    merged = []
    for b in bands:
        if merged and b[0][0] - merged[-1][-1][0] <= 3:
            merged[-1].extend(b)
        else:
            merged.append(b)
    bands = merged
    if len(bands) != len(labels):
        print(fname, 'bands', len(bands), 'labels', len(labels), 'SKIP')
        continue

    def bg(y):
        return px[bgx, y]

    for band, lab in zip(bands, labels):
        ty = band[0][0]
        tx = min(r[1] for r in band)
        by = band[-1][0]
        for y in range(max(iy0, ty - 6), min(iy1, by + 8)):
            c0 = bg(y)
            for x in range(ix0, ix1):
                if px[x, y] != OKEY:
                    px[x, y] = c0
        size = 12
        while size > 8:
            f = ImageFont.truetype(FONT, size)
            b = f.getbbox(lab)
            if b[2] - b[0] <= ix1 - tx - 2 and b[3] - b[1] <= 12:
                break
            size -= 1
        f = ImageFont.truetype(FONT, size)
        b = f.getbbox(lab)
        mask = Image.new('L', (w, h), 0)
        ImageDraw.Draw(mask).text((tx - b[0], ty - b[1]), lab, font=f, fill=255)
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
                    px[x, y] = BLUE

    pal_list = [tuple(palette[i * 3:i * 3 + 3]) for i in range(min(256, len(palette) // 3))]
    while len(pal_list) < 256:
        pal_list.append((0, 0, 0))
    for need in (BLUE, OUTLINE):
        if need not in pal_list:
            for i in range(len(pal_list) - 1, -1, -1):
                if pal_list[i] == (0, 0, 0):
                    pal_list[i] = need
                    break
    exact = {}
    for i, c in enumerate(pal_list):
        exact.setdefault(c, i)
    data = bytearray()
    for y in range(h):
        for x in range(w):
            col = px[x, y]
            idx = exact.get(col)
            if idx is None:
                best = 0; bd = 10 ** 9
                for i, pc in enumerate(pal_list):
                    d2 = (pc[0] - col[0]) ** 2 + (pc[1] - col[1]) ** 2 + (pc[2] - col[2]) ** 2
                    if d2 < bd:
                        bd = d2; best = i
                idx = best
            data.append(idx)
    flat = []
    for c in pal_list:
        flat.extend(c)
    out = Image.frombytes('P', (w, h), bytes(data))
    out.putpalette(flat)
    os.makedirs(DEST, exist_ok=True)
    out.save(os.path.join(DEST, fname))
    prev = out.convert('RGB'); pp = prev.load()
    for y in range(h):
        for x in range(w):
            if pp[x, y] == OKEY:
                pp[x, y] = (60, 60, 60)
    prev.resize((w * 3, h * 3), Image.NEAREST).save(os.path.join(TMP, fname.replace('.png', '_zh.png')))
    print('done', fname, 'bands', len(bands))
