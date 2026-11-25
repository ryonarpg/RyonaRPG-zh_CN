import os
from PIL import Image, ImageDraw, ImageFont

from common_env import GAME_DIR, OUT, FONT
SRC = os.path.join(GAME_DIR, 'Picture', 'Menu')
STAGE = OUT


OKEY = (255, 156, 0)
OUTLINE = (29, 29, 30)
FILL = (155, 220, 255)

PAGES = {
    'MN_Main_000001.png': [
        (104, 8, 162, 15, '武器类型：'),
        (104, 42, 150, 49, '武器属性：'),
        (105, 59, 150, 66, '属性防御'),
        (110, 76, 120, 84, '炎'), (176, 76, 185, 84, '冰'), (242, 76, 252, 84, '雷'),
        (110, 93, 119, 101, '圣'), (176, 93, 185, 101, '咒'), (242, 93, 264, 101, '吸收'),
        (110, 110, 132, 121, '毒'), (176, 110, 186, 121, '酸'), (242, 110, 276, 121, '力'),
        (110, 127, 132, 138, '米索'), (176, 127, 186, 138, '水'), (242, 127, 276, 138, '等离子'),
        (104, 144, 150, 153, '状态附加：'),
        (104, 161, 150, 169, '状态抗性'),
        (111, 178, 140, 190, '毒'), (146, 178, 168, 190, '黑暗'), (183, 178, 204, 190, '沉默'),
        (219, 178, 240, 190, '麻痹'), (254, 178, 276, 190, '倒地'), (291, 178, 307, 190, '出血'),
        (112, 195, 132, 207, '捕获'), (146, 195, 168, 207, '黏液'), (182, 195, 201, 207, '恐惧'),
        (218, 195, 240, 207, '冻结'), (255, 195, 274, 207, '昏厥'),
    ],
    'MN_Main_000002.png': [
        (104, 8, 126, 15, '状态'),
        (146, 25, 200, 36, '保护'), (222, 25, 300, 36, '加速'),
        (146, 42, 200, 53, '魔法护盾'), (222, 42, 300, 53, '再生'),
        (146, 59, 200, 70, '屏障'), (222, 59, 300, 70, '浮游'),
        (104, 93, 162, 100, '自然回复率'),
        (216, 110, 292, 122, '回复量：'), (216, 127, 292, 139, '回复量：'),
    ],
    'MN_Main_000003.png': [
        (104, 25, 125, 32, '魅力'),
        (104, 110, 136, 122, '身高'), (104, 127, 136, 139, '胸围'), (249, 127, 282, 139, '罩杯'),
        (104, 144, 135, 153, '腰围'), (104, 161, 138, 170, '臀围'),
    ],
    'MN_Main_000051.png': [
        (116, 25, 138, 32, '性感'),
        (118, 42, 150, 49, 'B感觉'), (214, 42, 246, 49, 'N感觉'),
        (117, 59, 150, 66, 'V感觉'), (214, 59, 246, 66, 'U感觉'),
        (119, 76, 150, 83, 'A感觉'),
        (117, 110, 150, 121, 'B适性'), (214, 110, 246, 121, 'N适性'),
        (117, 127, 150, 138, 'V适性'), (214, 127, 246, 138, 'U适性'),
        (119, 144, 150, 152, 'A适性'),
    ],
    'MN_Main_000052.png': [
        (100, 7, 146, 16, '性相关', 2), (180, 7, 280, 16, '◆Shift键查看详情', 4),
    ],
    'MN_Main_000053.png': [
        (100, 7, 157, 16, '性相关', 2), (180, 7, 280, 16, '◆Shift键查看详情', 4),
    ],
    'MN_Main_000054.png': [
        (100, 7, 146, 16, '催眠相关', 2), (180, 7, 280, 16, '◆Shift键查看详情', 4),
    ],
    'MN_Main_000055.png': [
        (101, 7, 157, 16, '贞操带相关', 2), (180, 7, 280, 16, '◆Shift键查看详情', 4),
    ],
    'MN_Main_000100.png': [
        (8, 42, 30, 52, '魔法'), (116, 42, 161, 52, '主要魔法'), (116, 58, 161, 68, '辅助魔法'),
    ],
    'MN_Main_000105.png': [
        (8, 42, 30, 52, '装填'), (116, 42, 126, 52, '枪械'), (116, 58, 135, 68, '子弹'),
        (8, 138, 30, 148, '弹数'), (9, 154, 29, 164, '威力'), (9, 170, 60, 180, '魔力传导'),
    ],
    'MN_Main_001100.png': [
        (8, 42, 30, 52, '内衣'), (141, 42, 150, 52, '上衣'), (117, 58, 132, 68, '下装'),
    ],
    'MN_Main_001300.png': [
        (8, 42, 30, 52, '装填'), (116, 42, 126, 52, '枪械'), (116, 58, 135, 68, '子弹'),
        (8, 138, 30, 148, '弹数'), (9, 154, 29, 164, '威力'), (9, 170, 60, 180, '魔力传导'),
    ],
    'MN_Main_009000.png': [
        (20, 42, 77, 49, '选项'), (32, 59, 102, 66, '难度变更'), (33, 76, 113, 83, '沉浸模式'),
        (33, 93, 125, 100, '夏亚专用模式'), (35, 110, 90, 120, '等级限制'), (32, 127, 126, 134, '回复道具限制'),
        (45, 144, 126, 151, '升级时全回复'), (32, 161, 137, 168, '关于妖精的存在'),
        (33, 178, 114, 185, '随时存档'), (140, 212, 198, 219, '当前设定'),
    ],
    'MN_Main_009001.png': [
        (20, 42, 77, 49, '选项'), (32, 59, 198, 66, '立绘、半身像等显示'), (33, 76, 148, 83, '半身像切换'),
        (32, 93, 185, 100, '种族转生用步行图'), (33, 127, 149, 134, '角色台词'),
    ],
    'MN_Main_009002.png': [
        (20, 42, 77, 49, '选项'), (33, 59, 113, 66, '双击模式'), (32, 76, 78, 83, '技能名显示'),
        (32, 93, 78, 100, '残弹显示'), (32, 110, 101, 120, '低负载模式'), (33, 127, 126, 134, 'Boss HP条显示'),
        (33, 161, 126, 168, '胸围尺寸上限'), (33, 178, 186, 185, '根据胸围限制装备'),
        (32, 195, 173, 202, '因羞耻限制装备（街中）'), (32, 212, 90, 219, '性攻击'),
    ],
    'MN_Main_009003.png': [
        (20, 42, 77, 49, '选项'), (32, 59, 114, 66, '敌人出现抑制范围'),
        (32, 76, 150, 83, '多段伤害合并显示'), (32, 93, 102, 100, '街中移动速度'),
        (32, 178, 78, 188, '改名'), (212, 178, 234, 188, '执行'),
        (32, 195, 126, 202, '通常菜单封印'), (32, 212, 138, 219, '主人公备份'),
    ],
}

def load_rgb(path):
    im = Image.open(path)
    palette = im.getpalette()
    if im.mode != 'P':
        return im.convert('RGB'), palette
    data = list(im.getdata())
    base = Image.new('RGB', im.size); px = base.load()
    for y in range(im.height):
        for x in range(im.width):
            idx = data[y * im.width + x]
            px[x, y] = tuple(palette[idx * 3:idx * 3 + 3])
    return base, palette

def row_bg(px, w, y, ex0, ex1):
    for x in range(min(w - 9, ex1 + 4), max(8, ex1 - 40), -1):
        c = px[x, y]
        if c != OKEY and not (c[0] >= 100 and c[1] >= 100) and 50 <= max(c) <= 140:
            return c
    for x in range(max(8, ex0 - 4), min(w - 9, ex0 + 40)):
        c = px[x, y]
        if c != OKEY and not (c[0] >= 100 and c[1] >= 100) and 50 <= max(c) <= 140:
            return c
    return (5, 35, 103)

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

for fn, entries in PAGES.items():
    base, palette = load_rgb(os.path.join(SRC, fn))
    px = base.load(); w, h = base.size
    for e in entries:
        x0, y0, x1, y1, text = e[0], e[1], e[2], e[3], e[4]
        pad = e[5] if len(e) > 5 else 10
        ex0 = max(0, x0 - 6); ex1 = min(w - 1, x1 + pad)
        ey0 = max(0, y0 - 3); ey1 = min(h - 1, y0 + 14)
        for y in range(ey0, ey1 + 1):
            bg = row_bg(px, w, y, ex0, ex1)
            for x in range(ex0, ex1 + 1):
                if px[x, y] != OKEY:
                    px[x, y] = bg
        draw_text(px, w, h, x0, y0, text)
    dst = os.path.join(STAGE, fn)
    save_paletted(base, palette, dst)
    print('done', fn, len(entries))
