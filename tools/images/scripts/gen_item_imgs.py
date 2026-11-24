import re, os
from PIL import Image, ImageDraw, ImageFont

from common_env import GAME_DIR, OUT, PO, EDB, FONT
ITEM_IMG = os.path.join(GAME_DIR, 'Picture', 'Menu', 'Item')


OKEY = (255, 156, 0)
OUTLINE = (29, 29, 30)
FILL = (240, 250, 255)

def unesc(s):
    out = []; i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            c = s[i + 1]
            if c == 'n': out.append('\n')
            elif c == '"': out.append('"')
            elif c == '\\': out.append('\\')
            else: out.append('\\' + c)
            i += 2
        else:
            out.append(s[i]); i += 1
    return ''.join(out)

def cat(x):
    return ''.join(re.findall(r'"(.*)"', x))

# translations
tr = {}
s = open(PO, encoding='utf-8-sig', errors='replace').read()
for b in re.split(r'\n\s*\n', s):
    m = re.search(r'(?m)^msgid ("(?:.*)(?:\n"(?:.*))*")', b)
    n = re.search(r'(?m)^msgstr ("(?:.*)(?:\n"(?:.*))*")', b)
    if m and n:
        tr[unesc(cat(m.group(1)))] = unesc(cat(n.group(1)))
tr.pop('', None)  # header block must not answer empty lookups

def translate(text):
    if not text or not text.strip():
        return ''
    t = tr.get(text)
    if not t:
        return text
    t = t.replace('\n', '')
    return t

# database items
edb = open(EDB, encoding='utf-8', errors='replace').read()
items = []
for m in re.finditer(r'<Item id="(\d+)">(.*?)</Item>', edb, re.S):
    iid = int(m.group(1)); block = m.group(2)
    nm = re.search(r'<name>(.*?)</name>', block, re.S)
    ds = re.search(r'<description>(.*?)</description>', block, re.S)
    items.append((iid, nm.group(1) if nm else '', ds.group(1) if ds else ''))
items.sort()
ITEMS = int(os.environ.get('IMG_ITEMS', '99999'))
items = items[:ITEMS]

font_candidates = [12, 11, 10, 9, 8]
def fit_font(text, maxw):
    for size in font_candidates:
        f = ImageFont.truetype(FONT, size)
        w = f.getbbox(text)[2] - f.getbbox(text)[0] if text else 0
        if w <= maxw:
            return f, size
    return ImageFont.truetype(FONT, 8), 8

# simple outline without numpy: paste mask at offsets
def render_text(im_rgb, xy, text, maxw):
    font, size = fit_font(text, maxw)
    mask = Image.new('L', im_rgb.size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=font, fill=255)
    mask = mask.point(lambda v: 255 if v >= 110 else 0)
    w, h = im_rgb.size
    px = im_rgb.load(); mp = mask.load()
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
    return size

def save_paletted(im, palette, path):
    pal = {}
    for i in range(256):
        pal.setdefault(tuple(palette[i * 3:i * 3 + 3]), i)
    px = im.load(); w, h = im.size
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
    o = Image.frombytes('P', (w, h), bytes(data))
    o.putpalette(palette)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    o.save(path)

made = 0
for iid, name, desc in items:
    if iid > 1900:
        continue
    zh_name = translate(name)
    zh_desc = translate(desc)
    # Name image
    src_n = os.path.join(ITEM_IMG, 'Name', '%04d.png' % iid)
    if os.path.exists(src_n):
        base = Image.open(src_n).convert('RGB')
        palette = Image.open(src_n).getpalette()
        px = base.load()
        for y in range(base.height):
            for x in range(16, base.width):
                px[x, y] = OKEY
        render_text(base, (16, 2), zh_name, 136 - 16 - 2)
        out_n = os.path.join(OUT, 'Item', 'Name', '%04d.png' % iid)
        save_paletted(base, palette, out_n)
        made += 1
    # Desc image
    src_d = os.path.join(ITEM_IMG, 'Desc', '%04d.png' % iid)
    if os.path.exists(src_d):
        base = Image.open(src_d).convert('RGB')
        palette = Image.open(src_d).getpalette()
        px = base.load()
        for y in range(base.height):
            for x in range(base.width):
                px[x, y] = OKEY
        render_text(base, (0, 2), zh_desc, 304 - 2)
        out_d = os.path.join(OUT, 'Item', 'Desc', '%04d.png' % iid)
        save_paletted(base, palette, out_d)
        made += 1

print('generated', made, 'images for', len(items), 'items')
