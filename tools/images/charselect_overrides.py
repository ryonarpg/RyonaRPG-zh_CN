#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成选人界面的中文 Type 标签和 Noel 天赋说明，并生成界面模拟图。"""
import argparse
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_FONT = r"C:\Windows\Fonts\unifont-all.ttf"
FALLBACK_FONTS = [
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
]

TYPE_TEXTS = [
    ("Type0", "战士"),
    ("Type1", "魔法"),
    ("Type2", "魔法战士"),
    ("Type3", "其他"),
]

NOEL_1 = [
    "天赋　「链式左轮」",
    "攻击中有20%概率回避攻击。",
    "获得最多可持续8连击的连击发生机会。",
    "连击从最后一次攻击起持续5秒，击破敌人时持续7秒。",
    "",
    "连击发生、持续条件",
    "　周围2格以内的敌人普通攻击、",
    "　或单体攻击魔法命中。",
    "",
    "连击结束条件",
    "　未满足持续条件的攻击　辅助魔法的使用",
    "　受到伤害　疲劳状态中",
    "　？？？状态经过一段时间",
]

NOEL_2 = [
    "天赋　「链式左轮」",
    "连击发生中，获得以下效果。",
    "　共通：蓄力速度上升　普通攻击硬直无效",
    "　特殊：解锁必杀技",
    "　仅枪械：自动装填　暴击发生机会",
    "　　　　　解锁必杀技",
    "",
    "以下任一操作发动特殊必杀技。",
    "　攻击键＋Shift键同时按下",
    "　蓄力完成时按下Shift键",
    "",
    "特殊必杀技发动中必定回避攻击。",
]


def font(path, size):
    for candidate in [path] + FALLBACK_FONTS:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def to_rgba(path, key=None):
    src = Image.open(path)
    im = src.convert("RGBA")
    if key is None:
        if src.mode == "P":
            palette = src.getpalette() or []
            if palette:
                key = tuple(palette[0:3])
    if key:
        px = im.load()
        for y in range(im.height):
            for x in range(im.width):
                r, g, b, a = px[x, y]
                if (r, g, b) == key:
                    px[x, y] = (r, g, b, 0)
    return im


def render_type(src, dst, text, font_path):
    src_im = Image.open(src).convert("P")
    w, h = src_im.size
    rgb = src_im.convert("RGB")
    px = rgb.load()
    # 按行取左侧留白处的背景色，保留原有的纵向渐变和圆角边框
    for y in range(4, 28):
        bg = px[3, y]
        for x in range(4, w - 5):
            px[x, y] = bg
    del px
    draw = ImageDraw.Draw(rgb)
    fnt = font(font_path, 12)
    draw.text((w // 2 + 1, 17), text, font=fnt, anchor="mm",
              fill=(82, 167, 247))
    draw.text((w // 2, 16), text, font=fnt, anchor="mm",
              fill=(250, 250, 255))
    out = rgb.quantize(palette=src_im, dither=Image.Dither.NONE)
    out.save(dst, optimize=True)


def render_noel(src, dst, lines, font_path):
    src_im = Image.open(src).convert("P")
    w, h = src_im.size
    rgb = src_im.convert("RGB")
    px = rgb.load()
    # 标题条和正文面板分别清理文字，保留中间的双线分隔与四周边框。
    # 每行取出现次数最多的颜色作为背景，避免采到原日文长行的文字像素。
    for y in range(4, 28):
        bg = Counter(px[x, y] for x in range(10, 311)).most_common(1)[0][0]
        for x in range(10, 311):
            px[x, y] = bg
    for y in range(36, 235):
        bg = Counter(px[x, y] for x in range(12, 306)).most_common(1)[0][0]
        for x in range(12, 306):
            px[x, y] = bg
    del px
    draw = ImageDraw.Draw(rgb)
    fnt = font(font_path, 12)

    def line(x, y, text):
        draw.text((x + 1, y + 1), text, font=fnt, fill=(82, 167, 247))
        draw.text((x, y), text, font=fnt, fill=(250, 250, 255))

    line(10, 8, lines[0])
    y = 38
    for text in lines[1:]:
        line(12, y, text)
        y += 16
    out = rgb.quantize(palette=src_im, dither=Image.Dither.NONE)
    out.save(dst, optimize=True)


def draw_window(canvas, skin_path, box, font_path):
    skin = Image.open(skin_path).convert("RGB")
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    win = Image.new("RGB", (w, h))
    bg = skin.crop((0, 0, 32, 32))
    for y in range(0, h, 32):
        for x in range(0, w, 32):
            win.paste(bg, (x, y))
    frame = skin.crop((32, 0, 64, 32))
    for x in (0, w - 8):
        sx = 0 if x == 0 else 24
        for y in range(8, h - 8, 8):
            win.paste(frame.crop((sx, 8, sx + 8, 16)), (x, y))
    for y in (0, h - 8):
        sy = 0 if y == 0 else 24
        for x in range(8, w - 8, 8):
            win.paste(frame.crop((8, sy, 16, sy + 8)), (x, y))
    corners = [(0, 0), (24, 0), (0, 24), (24, 24)]
    for (sx, sy), (x, y) in zip(corners, [(0, 0), (w - 8, 0), (0, h - 8), (w - 8, h - 8)]):
        win.paste(frame.crop((sx, sy, sx + 8, sy + 8)), (x, y))

    canvas.paste(win, (x0, y0))
    draw = ImageDraw.Draw(canvas)
    fnt = font(font_path, 12)
    lines = [
        "Name :诺艾尔",
        "Class:统制机构少尉",
        "Type :战士型",
        "",
    ]
    y = y0 + 8
    for text in lines:
        draw.text((x0 + 16 + 1, y + 1), text, font=fnt, fill=(29, 29, 30))
        draw.text((x0 + 16, y), text, font=fnt, fill=(250, 250, 255))
        y += 16


def make_mock(game, labels_dir, out, font_path):
    bg = Image.open(game / "Panorama" / "CharaSelect.png").convert("RGB")
    bg = bg.resize((320, 240))
    portraits = list((game / "Picture" / "Noel01").glob("*.png"))
    portrait = None
    for p in portraits:
        if "汎用服" in p.name:
            portrait = p
            break
    if portrait is None and portraits:
        portrait = portraits[0]
    canvas = bg.copy()
    if portrait:
        im = to_rgba(portrait, (255, 0, 255))
        im.thumbnail((150, 180), Image.LANCZOS)
        canvas.paste(im, (160 - im.width // 2, 132 - im.height), im)
    label = Image.open(labels_dir / "Type2.png").convert("RGBA")
    # Type 图片使用调色板索引 0 作为透明色
    if label.getpixel((0, 0))[:3] == (255, 0, 0):
        px = label.load()
        for y in range(label.height):
            for x in range(label.width):
                r, g, b, a = px[x, y]
                if (r, g, b) == (255, 0, 0):
                    px[x, y] = (r, g, b, 0)
    canvas.paste(label, (240, 4), label)
    draw_window(canvas, game / "System" / "システムB.png", (0, 160, 320, 240), font_path)

    out.mkdir(parents=True, exist_ok=True)
    canvas.save(out / "chara_select_noel.png")
    for n in (1, 2):
        desc = Image.open(labels_dir / f"Noel_text_{n}.png").convert("RGB")
        overlay = canvas.copy()
        overlay.paste(desc, (0, 0))
        overlay.save(out / f"chara_select_noel_text{n}.png")
        desc.save(out / f"noel_text_{n}_preview.png")


def validate(src_path, dst_path):
    if not dst_path.exists():
        return ["missing output"]
    src = Image.open(src_path)
    dst = Image.open(dst_path)
    problems = []
    if dst.mode != "P":
        problems.append(f"mode is {dst.mode}, expected P")
    if dst.size != src.size:
        problems.append(f"size is {dst.size}, expected {src.size}")
    sp = src.getpalette() or []
    dp = dst.getpalette() or []
    if dp[:3] != sp[:3]:
        problems.append(f"palette[0] is {tuple(dp[:3])}, expected {tuple(sp[:3])}")
    if "transparency" in dst.info:
        problems.append("unexpected transparency chunk")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-dir", required=True)
    ap.add_argument("--out", default="language/zh_CN/Picture/Pict_op")
    ap.add_argument("--mock-dir", default="build/charselect_mock")
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--check", action="store_true",
                    help="只校验目标 PNG 的结构和调色板，不重新生成")
    args = ap.parse_args()
    game = Path(args.game_dir)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    src = game / "Picture" / "Pict_op"
    names = [name for name, _ in TYPE_TEXTS] + ["Noel_text_1", "Noel_text_2"]

    if args.check:
        failed = False
        for name in names:
            problems = validate(src / f"{name}.png", out / f"{name}.png")
            if problems:
                failed = True
                print(f"FAIL {name}: " + "; ".join(problems))
            else:
                print(f"OK   {name}")
        return 1 if failed else 0

    for name, text in TYPE_TEXTS:
        render_type(src / f"{name}.png", out / f"{name}.png", text, args.font)
    render_noel(src / "Noel_text_1.png", out / "Noel_text_1.png", NOEL_1, args.font)
    render_noel(src / "Noel_text_2.png", out / "Noel_text_2.png", NOEL_2, args.font)
    for name in names:
        problems = validate(src / f"{name}.png", out / f"{name}.png")
        if problems:
            raise SystemExit(f"generated {name} failed validation: " + "; ".join(problems))
    make_mock(game, out, Path(args.mock_dir), args.font)
    print("wrote", out)
    print("mock", args.mock_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
