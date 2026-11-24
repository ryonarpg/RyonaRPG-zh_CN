import re, os
from PIL import Image, ImageDraw, ImageFont

from common_env import OUT, PO, ITM_LIST, FONT, TMP
DOC = ITM_LIST
DEST = os.path.join(OUT, 'ITM')


OKEY = (255, 156, 0)
FILL = (155, 220, 255)
OUTLINE = (29, 29, 30)

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

tr = {}
s = open(PO, encoding='utf-8-sig', errors='replace').read()
for b in re.split(r'\n\s*\n', s):
    m = re.search(r'(?m)^msgid ("(?:.*)(?:\n"(?:.*))*")', b)
    n = re.search(r'(?m)^msgstr ("(?:.*)(?:\n"(?:.*))*")', b)
    if m and n:
        tr[unesc(cat(m.group(1)))] = unesc(cat(n.group(1)))

pairs = []
for line in open(DOC, encoding='utf-8'):
    m = re.match(r'^(.+?)\t+(\d{4})\s*$', line)
    if m:
        pairs.append((m.group(1).strip(), int(m.group(2))))

os.makedirs(DEST, exist_ok=True)
made = 0
for name, mid in pairs:
    zh = tr.get(name)
    if not zh:
        alt = re.sub(r'\(\d+\)$', '', name)
        zh = tr.get(alt, name)
    zh = zh.replace('\n', '')
    im = Image.new('RGB', (120, 12), OKEY)
    px = im.load()
    size = 12
    while size > 7:
        f = ImageFont.truetype(FONT, size)
        b = f.getbbox(zh)
        if b[2] - b[0] <= 118 and b[3] - b[1] <= 12:
            break
        size -= 1
    f = ImageFont.truetype(FONT, size)
    b = f.getbbox(zh)
    pos = (-b[0], -b[1])
    mask = Image.new('L', (120, 12), 0)
    ImageDraw.Draw(mask).text(pos, zh, font=f, fill=255)
    mask = mask.point(lambda v: 255 if v >= 110 else 0)
    mp = mask.load()
    for y in range(12):
        for x in range(120):
            if mp[x, y]:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < 120 and 0 <= ny < 12 and not mp[nx, ny]:
                            px[nx, ny] = OUTLINE
    for y in range(12):
        for x in range(120):
            if mp[x, y]:
                px[x, y] = FILL
    # palette with index 0 orange
    pal = [0, 0, 0] * 256
    colors = {}
    pal[0:3] = list(OKEY)
    idx = 1
    data = bytearray()
    for y in range(12):
        for x in range(120):
            c = px[x, y]
            if c not in colors and idx < 256:
                colors[c] = idx
                pal[idx * 3:idx * 3 + 3] = list(c)
                idx += 1
            data.append(0 if c == OKEY else colors[c])
    out = Image.frombytes('P', (120, 12), bytes(data))
    out.putpalette(pal)
    out.save(os.path.join(DEST, 'MN_ITM_%04d.png' % mid))
    made += 1
print('generated ITM', made)
