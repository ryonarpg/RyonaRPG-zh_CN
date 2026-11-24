import os
from PIL import Image, ImageDraw, ImageFont

from common_env import OUT, FONT
DEST = os.path.join(OUT, 'EX')


OKEY = (255, 156, 0)
FILL = (155, 220, 255)
OUTLINE = (29, 29, 30)

PAIRS = [
    ('0296', '双性'), ('0299', '榨精奴隶'), ('0300', '魔乳化'),
    ('0563', '他人变身'), ('0564', '性奴调教史莱姆'), ('0576', '橡胶中毒'),
    ('0577', '橡胶奴隶'), ('0578', '全身橡胶化'), ('0579', '橡胶人偶'),
    ('0587', '兰德雷之母'), ('0589', '娼妇'), ('0590', '天生的受虐狂'),
    ('0591', '露出癖'), ('0593', '施虐狂'), ('0594', '受虐狂'),
    ('0602', '机械人偶'), ('0603', '僵尸化'), ('0606', '无法攻击的暗示'),
    ('0607', '失禁催眠'), ('0608', '露出催眠'), ('0609', '性处理催眠'),
    ('0610', '自慰催眠'), ('0611', '高潮催眠'), ('0612', '无抵抗的暗示'),
    ('0613', '失禁洗脑'), ('0614', '自慰洗脑'), ('0615', '生殖洗脑'),
    ('0616', '忘却催眠'), ('0617', '失禁快感洗脑'), ('0618', '淫乱人格化催眠'),
    ('0631', '贞操带'), ('0632', '奴隶的贞操带'), ('0633', '性奴的贞操带'),
    ('0634', '射精管理'), ('0635', '（胸）贞操带'), ('0636', '（胸）奴隶的贞操带'),
    ('0637', '（胸）性奴的贞操带'), ('0638', '射乳管理'), ('0639', '高潮管理的快感'),
    ('0640', '隶娘的贞操带'), ('0832', '尿道快乐'), ('0834', '乳畜'),
    ('0835', '失禁癖'), ('0836', '母乳分泌'), ('0872', '自慰中毒'),
    ('0873', '榨乳奴隶'), ('0874', '精液中毒'), ('0878', '肛孔狂'),
    ('0893', '排卵异常'), ('0896', '异形苗床'),
    ('AS', 'A敏感'), ('AW', 'A弱点'), ('BS', 'B敏感'), ('BW', 'B弱点'),
    ('NS', 'N敏感'), ('NW', 'N弱点'), ('US', 'U敏感'), ('UW', 'U弱点'),
    ('VS', 'V敏感'), ('VW', 'V弱点'), ('XS', '对快感很弱'),
    ('XW', '全身性感带'), ('v0563', '奇谭经验'), ('0617_B', '失禁快感洗脑不能'),
]

os.makedirs(DEST, exist_ok=True)
W, H = 96, 12
made = 0
for key, zh in PAIRS:
    im = Image.new('RGB', (W, H), OKEY)
    px = im.load()
    size = 12
    while size > 7:
        f = ImageFont.truetype(FONT, size)
        b = f.getbbox(zh)
        if b[2] - b[0] <= W - 2 and b[3] - b[1] <= H:
            break
        size -= 1
    f = ImageFont.truetype(FONT, size)
    b = f.getbbox(zh)
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).text((-b[0], -b[1]), zh, font=f, fill=255)
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
    colors = {}
    idx = 1
    data = bytearray()
    for y in range(H):
        for x in range(W):
            c = px[x, y]
            if c not in colors:
                colors[c] = idx
                pal[idx * 3:idx * 3 + 3] = list(c)
                idx += 1
            data.append(0 if c == OKEY else colors[c])
    out = Image.frombytes('P', (W, H), bytes(data))
    out.putpalette(pal)
    out.save(os.path.join(DEST, 'MN_EX_%s.png' % key))
    made += 1
print('EX generated', made)
