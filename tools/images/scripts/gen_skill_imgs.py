import os, re
from PIL import Image, ImageDraw, ImageFont

from common_env import GAME_DIR, OUT, PO, EDB, FONT
SRC = os.path.join(GAME_DIR, 'Picture', 'Menu', 'Skill')
DEST = os.path.join(OUT, 'Skill')


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

tr = {}
s = open(PO, encoding='utf-8-sig', errors='replace').read()
for b in re.split(r'\n\s*\n', s):
    m = re.search(r'(?m)^msgid ("(?:.*)(?:\n"(?:.*))*")', b)
    n = re.search(r'(?m)^msgstr ("(?:.*)(?:\n"(?:.*))*")', b)
    if m and n:
        tr[unesc(cat(m.group(1)))] = unesc(cat(n.group(1)))

edb = open(EDB, encoding='utf-8', errors='replace').read()
skills = {}
for m in re.finditer(r'<Skill id="(\d+)">(.*?)</Skill>', edb, re.S):
    sid = int(m.group(1)); b = m.group(2)
    nm = re.search(r'<name>(.*?)</name>', b, re.S)
    ds = re.search(r'<description>(.*?)</description>', b, re.S)
    skills[sid] = (nm.group(1) if nm else '', ds.group(1) if ds else '')

def render(text, W, H, top=2):
    im = Image.new('RGB', (W, H), OKEY)
    px = im.load()
    zh = text.replace('\n', '')
    size = 12
    while size > 6:
        f = ImageFont.truetype(FONT, size)
        b = f.getbbox(zh)
        if b[2] - b[0] <= W - 2 and b[3] - b[1] <= H - top:
            break
        size -= 1
    f = ImageFont.truetype(FONT, size)
    b = f.getbbox(zh)
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).text((-b[0], top - b[1]), zh, font=f, fill=255)
    mask = mask.point(lambda v: 255 if v >= 110 else 0)
    mp = mask.load()
    for y in range(H):
        for x in range(W):
            if mp[x, y]:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < W and 0 <= ny < H and not mp[nx, ny]:
                            px[nx, ny] = OUTLINE
    for y in range(H):
        for x in range(W):
            if mp[x, y]:
                px[x, y] = FILL
    pal = [0] * 768
    pal[0:3] = list(OKEY)
    colors = {}; idx = 1; data = bytearray()
    for y in range(H):
        for x in range(W):
            c = px[x, y]
            if c not in colors:
                colors[c] = idx; pal[idx * 3:idx * 3 + 3] = list(c); idx += 1
            data.append(0 if c == OKEY else colors[c])
    out = Image.frombytes('P', (W, H), bytes(data))
    out.putpalette(pal)
    return out

made = miss = 0
for sub, w, h, key in [('Name', 136, 16, 0), ('Desc', 304, 16, 1)]:
    srcdir = os.path.join(SRC, sub)
    outdir = os.path.join(DEST, sub)
    os.makedirs(outdir, exist_ok=True)
    for fn in sorted(os.listdir(srcdir)):
        m = re.match(r'(\d+)\.png$', fn)
        if not m:
            continue
        sid = int(m.group(1))
        if sid not in skills:
            miss += 1
            continue
        jp = skills[sid][key]
        if not jp.strip():
            miss += 1
            continue
        zh = tr.get(jp)
        if not zh:
            alt = tr.get(jp.strip())
            zh = alt if alt else None
        if not zh:
            miss += 1
            continue
        render(zh, w, h).save(os.path.join(outdir, fn))
        made += 1
print('skill images generated', made, 'skipped', miss)
