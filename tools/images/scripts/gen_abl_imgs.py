import os
from PIL import Image, ImageDraw, ImageFont

from common_env import OUT, FONT
DEST = os.path.join(OUT, 'ABL')


OKEY = (255, 156, 0)
FILL = (155, 220, 255)
OUTLINE = (29, 29, 30)

# key, chinese, has_lv
PAIRS = [
 ('0001','变身',False),('0002','魔封剑',False),('0003','风之低语',False),('0004','幻兽的加护',False),
 ('0005','精浆容器',False),('0006','灵光一闪',False),('0007','素颜',False),('0008','悟道',False),
 ('0009','气力',False),('0010','浮游',False),('0011','卢卡维',False),('0012','精气吸收',False),
 ('0013','上级妖魔',False),('0015','忍术',False),('0016','链式左轮',False),('0017','斩岩流格斗术',False),
 ('0018','冰之精灵·康露',False),('0019','吸血鬼',False),('0020','薄幸女主角',False),('0021','妖魔',False),
 ('0022','咒言精通',False),('0023','武具熟练',False),('0024','海盗',False),('0025','魅力',False),
 ('0026','武士道',False),('0027','妖魔化',False),('0028','电瞬',False),('0029','虎人',False),
 ('0030','超能力者',False),('0031','灵符师',False),('0032','大打击',False),('0033','箭矢制造',False),
 ('0034','长腿叔叔',False),('0035','大自然的加护',False),('0036','精灵的援助',False),('0042','家庭教师',False),
 ('0042a','拔剑觉醒',False),('0043','女神',False),('0044','枪械精通',False),('0045','尼迪亚人',False),
 ('0046','鹰骑士',False),('0047','艾克斯菲亚',False),('0048','骑士血脉',False),('0049','女仆流节约术',False),
 ('0051','舞娘',False),('0052','铠罗族',False),('0053','人偶使',False),('0055','徒步旅行',False),
 ('0056','刚拳',False),('0057','魅魔',False),('0058','圣剑技',False),('0059','龙之力',False),
 ('0060','苍之剑',False),('0061','太阳的宠儿',False),('0062','才女之杖',False),('0063','历战骑空士',False),
 ('0064','扳机狂',False),('0251','机械白痴',False),('0252','讨厌肌肉男',False),('0253','宠姬',False),
 ('0254','原宠姬',False),('0255','火焰魔术师',False),('0257','魅魔之触',False),('0258','生命吸取',False),
 ('0259','旅之知识',False),('0291','爱用武器登记',False),('0293','武器能力',False),
 ('0301','※魔法治疗',False),('0302','※狂战士',False),('0303','※斩首剑',False),('0304','※水舞',False),
 ('0305','※刃',False),('0306','※皆杀',False),('0307','※炽热重击',False),('0308','※寒冰重击',False),
 ('0309','※雷击',False),('0310','※鲜血杀戮',False),('0311','※格雷姆林效果',False),('0312','※狮鹫抓击',False),
 ('0313','※诅咒',False),('0314','※恐惧之声',False),('0315','※念力网',False),('0316','※大地重击',False),
 ('0317','※针刺',False),('0318','※史莱姆扩散',False),('0319','※邪恶之眼',False),('0320','※催眠',False),
 ('0321','※偷窃',False),('0361','诅咒',False),('0362','烈焰抹消',False),('0363','怪力',False),
 ('0364','毒免疫',False),('0365','麻痹免疫',False),('0366','削弱',False),('0367','死亡粉末',False),
 ('0368','猛虎乱舞',False),('0369','剧毒打击',False),('0370','麻痹之触',False),('0371','恐惧领域',False),
 ('0372','脑部破坏',False),('0373','达加乔',False),('0374','能量吸取',False),('0375','剥皮者',False),
 ('0376','美白',False),('0377','精神冲击波',False),('0378','发生器',False),('0379','精神护盾',False),
 ('0380','武器精通',False),('0381','魔法精通',False),('0382','野武士',False),('0383','野魔法',False),
 ('0407','×火焰',False),('0408','×冰',False),('0409','×电',False),('0411','辅助',False),
 ('0412','超级护甲',False),('0413','精神护甲',False),('0414','移位',False),('0415','法术抗性',False),
 ('0416','大漩涡',False),('0417','肉球',False),('0418','信息素',False),('0419','对火焰的抗性',False),
 ('0420','对寒冷的抗性',False),('0421','对电击的抗性',False),('0422','俊足',False),('0423','浮游',False),
 ('0424','地响',False),('0425','诅咒',False),('0426','恶臭',False),
 ('s0847','通常',False),('s0848','攻击专念',False),('s0849','休息',False),('s0850','警戒',False),
 ('s0851','忍耐快感',False),('s0852','自慰',False),('s0853','切肉断骨',False),('s0854','招架',False),
 ('s0855','魔法剑',False),('s0856','魔法盾',False),('s0857','魔力积蓄',False),('s0858','防御专念',False),
 ('s0859','无抵抗',False),('0290','预约武器登记',False),('v0529','忍耐',True),('v0530','偷窃',True),('v0531','底力',True),('v0532','连续魔法',True),
 ('v0381','乱打',True),('v0382','白刃取',True),('v0383','魔法护盾',True),('v0384','警戒',True),
 ('v0385','蓄力',True),('v0386','踢击',True),
]

os.makedirs(DEST, exist_ok=True)
W, H = 120, 12
made = 0
for key, zh, lv in PAIRS:
    im = Image.new('RGB', (W, H), OKEY)
    px = im.load()
    maxw = 70 if lv else W - 2
    size = 12
    while size > 7:
        f = ImageFont.truetype(FONT, size)
        b = f.getbbox(zh)
        if b[2] - b[0] <= maxw and b[3] - b[1] <= H:
            break
        size -= 1
    f = ImageFont.truetype(FONT, size)
    b = f.getbbox(zh)
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).text((-b[0], -b[1]), zh, font=f, fill=255)
    if lv:
        ImageDraw.Draw(mask).text((92, 0), 'Lv', font=ImageFont.truetype(FONT, 10), fill=255)
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
    out.save(os.path.join(DEST, 'MN_ABL_%s.png' % key))
    made += 1
print('ABL generated', made)
