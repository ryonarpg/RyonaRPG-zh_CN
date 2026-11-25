import os
from PIL import Image, ImageDraw, ImageFont

from common_env import OUT, FONT
DEST = os.path.join(OUT, 'ITM')


OKEY = (255, 156, 0)
FILL = (155, 220, 255)
OUTLINE = (29, 29, 30)

PAIRS = [
    ('0136', '盗贼之眼'), ('1401', '奴隶穿孔'), ('1402', '锦之穿孔'),
    ('1403', '精灵银穿孔'), ('1404', '圣女穿孔'), ('1405', '活力穿孔'),
    ('1406', '魔女穿孔'), ('1407', '幸运穿孔'), ('1408', '结界穿孔'),
    ('1409', '雌猪穿孔'), ('1461', '转轮手枪'), ('1464', '古式枪'),
    ('1466', '无限弹仓'), ('1467', '子弹'), ('1468', '强力子弹'),
    ('1469', '更强子弹'), ('1471', 'E0001 火焰'), ('1472', 'E0002 冰暴'),
    ('1473', 'E0003 雷电'), ('s0956', '贞操带'),
]

os.makedirs(DEST, exist_ok=True)
for key, zh in PAIRS:
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
    mask = Image.new('L', (120, 12), 0)
    ImageDraw.Draw(mask).text((-b[0], -b[1]), zh, font=f, fill=255)
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
    pal = [0] * 768
    pal[0:3] = list(OKEY)
    colors = {}
    idx = 1
    data = bytearray()
    for y in range(12):
        for x in range(120):
            c = px[x, y]
            if c not in colors:
                colors[c] = idx
                pal[idx * 3:idx * 3 + 3] = list(c)
                idx += 1
            data.append(0 if c == OKEY else colors[c])
    out = Image.frombytes('P', (120, 12), bytes(data))
    out.putpalette(pal)
    out.save(os.path.join(DEST, 'MN_ITM_%s.png' % key))
print('manual ITM generated', len(PAIRS))
