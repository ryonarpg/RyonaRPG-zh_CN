import os, re
from PIL import Image, ImageDraw, ImageFont

from common_env import GAME_DIR, OUT, FONT
SRC = os.path.join(GAME_DIR, 'Picture', 'Menu')
STAGE = OUT


OKEY = (255, 156, 0)
OUTLINE = (29, 29, 30)
FILL = (155, 220, 255)

LABELS = {}
def add(prefix, mapping):
    for k, v in mapping.items():
        LABELS[prefix + k + '.png'] = v

add('MN_Wpn_AT_', {
    '-01': '能力下降', '00': '物理', '01': '炎', '02': '冰', '03': '雷', '04': '圣', '05': '力',
    '06': '吸收', '07': '对甲', '08': '乱物', '09': '地狱', '10': '虹', '11': '毒', '12': '银', '13': '东方',
})
add('MN_Wpn_ST_', {
    '00': '无', '01': '毒', '02': '麻痹', '03': '盲目', '04': '混乱', '05': '魔力流失',
    '06': '衰弱病', '07': '伤', '08': '重伤', '09': '致命伤', '10': '自我再生', '11': '即死',
})
add('MN_Wpn_Type', {
    '01': '格斗', '02': '地雷', '03': '铁球', '04': '投掷', '05': '鞭', '06': '短剑', '07': '剑',
    '08': '锁镰', '09': '大剑', '10': '斧', '11': '小剑', '12': '长枪', '13': '弓', '14': '枪械',
})
add('MN_ST_', {
    '0101': '毒', '0102': '黑暗', '0103': '沉默', '0104': '麻痹', '0105': '倒地', '0106': '出血',
    '0107': '捕获', '0108': '黏液', '0109': '恐惧', '0110': '冻结', '0111': '昏厥', '0112': '？？？',
    '0113': '保护', '0114': '魔法护盾', '0115': '加速', '0116': '再生', '0369': '疲劳', '0422': '屏障',
    '0474': '寄生', '0494': '浮游', '0620': '羞耻', '1455': '幼女', '1471': '蛙', 'v0409': '衰弱',
    'v1239': '弱体', 'v1249': '故障',
})
add('MN_Mode_', {
    '0000': '普通模式', '0014': '苦难模式', '0014B': '狂热模式', '0371': '夏亚专用模式',
    '0374': 'V-MAX模式', '0510': '简单模式',
})
add('MN_OPT_', {
    's0654': '特定', 'v0725_4': '标准速度', 'v0725_5': '二倍速度', 'v0897_00': '选项',
    'v0897_01': '不使用', 'v0897_02': '长按', 'v0897_03': '双击',
})
add('MN_CHM_', {
    'Mask': '？？？度', 'v0662_+': '萝莉度', 'v0662_-': '老太婆度', 'v0663_+': '婊子度',
    'v0663_-': '清纯度', 'v0664_+': '施虐度', 'v0664_-': '受虐度',
})
LABELS['MN_BLK_00.png'] = '待机'
LABELS['MN_PAT_N.png'] = '未对应'
LABELS['MN_Sub_000201.png'] = '页'

def src_bbox(path, w, h):
    im = Image.open(path)
    data = list(im.getdata())
    pts = [(x, y) for y in range(h) for x in range(w) if data[y * w + x] != 0]
    if not pts:
        return 2, max(0, (h - 10) // 2)
    return min(p[0] for p in pts), min(p[1] for p in pts)

def render(text, w, h, ax, ay):
    im = Image.new('RGB', (w, h), OKEY)
    px = im.load()
    f = ImageFont.truetype(FONT, 12)
    b = f.getbbox(text)
    tw = b[2] - b[0]
    gh = b[3] - b[1]
    if w <= 120:
        x = max(0, min(ax - b[0], w - tw))
    else:
        x = max(2, ax - b[0])
    y = max(0, ay - b[1])
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).text((x - b[0], y), text, font=f, fill=255)
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
    pal = [0] * 768
    pal[0:3] = list(OKEY)
    colors = {}; idx = 1; data = bytearray()
    for yy in range(h):
        for xx in range(w):
            c = px[xx, yy]
            if c not in colors:
                colors[c] = idx; pal[idx * 3:idx * 3 + 3] = list(c); idx += 1
            data.append(0 if c == OKEY else colors[c])
    out = Image.frombytes('P', (w, h), bytes(data))
    out.putpalette(pal)
    return out

made = 0
for rel, text in sorted(LABELS.items()):
    src = os.path.join(SRC, rel)
    if not os.path.exists(src):
        print('missing', rel); continue
    im = Image.open(src)
    w, h = im.size
    ax, ay = src_bbox(src, w, h)
    out = render(text, w, h, ax, ay)
    dst = os.path.join(STAGE, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    out.save(dst)
    made += 1
print('generated', made)
