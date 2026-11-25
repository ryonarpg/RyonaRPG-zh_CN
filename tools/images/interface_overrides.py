#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Interface 内状态名与武器名的中文覆盖图。"""
import argparse
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_FONT = r"C:\Windows\Fonts\simhei.ttf"
PAGE_FONT = r"C:\Windows\Fonts\unifont-all.ttf"
FALLBACK_FONTS = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\unifont-all.ttf",
]
FILL = (155, 220, 255)
EDGE = (29, 29, 30)

STATUS = {
    "Status_02.png": ("毒", "毒"),
    "Status_03.png": ("暗闇", "黑暗"),
    "Status_04.png": ("沈黙", "沉默"),
    "Status_05.png": ("麻痺", "麻痹"),
    "Status_06.png": ("転倒", "倒地"),
    "Status_07.png": ("出血", "出血"),
    "Status_08.png": ("捕縛", "束缚"),
    "Status_09.png": ("粘液", "黏液"),
    "Status_10.png": ("恐怖", "恐惧"),
    "Status_11.png": ("凍結", "冻结"),
    "Status_12.png": ("気絶", "昏迷"),
    "Status_13.png": ("？？？", "？？？"),
}

NOTIFY = {
    "Status_v1320.png": ("バックドラフト", ["逆流火焰", "已可使用！"]),
}

WEAPON = {
    "wep_v0947_0.png": ("素手", "徒手", 16),
}

PAGES = {
    "bossbutton_text.png": [
        "……所住城市的空气，远比想象中污染严重。",
        "自行渗出的汗水与唾液、无数体液，让莉丝",
        "射精前的膨胀进一步加剧……感知到这一切的女性器官",
        "性感被不断增幅，莉丝的娇态愈发狂乱。",
        "与这个女人的情事，时机绝不会错乱。",
        "回应我的射精，被调教到极致的她的肉体",
        "被强制推向绝顶的顶点。",
        "「呜、啊、啊啊呜呜呜！！」",
        "在精准算计般的时机，肉壶收缩与蠕动，",
        "发出法悦的呻吟，我将强忍的白浊尽情释放。",
        "「唔……要、要去了！……做好觉悟！」",
        "「啊啊、啊嘻咕噜凛沙嘛啊啊～、哇、哇",
        "哇啦嘻、咿呀、啊、咿呀呜呜呜」",
    ],
}


def font(path, size):
    for candidate in [path] + FALLBACK_FONTS:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def palette_key(im):
    pal = im.getpalette() or [255, 156, 0]
    return tuple(pal[:3])


def draw_line(draw, x, y, text, fnt):
    draw.text((x + 1, y + 1), text, font=fnt, fill=EDGE)
    draw.text((x, y), text, font=fnt, fill=FILL)


def render_text_only(src, dst, lines, font_path):
    src_im = Image.open(src).convert("P")
    key = palette_key(src_im)
    rgb = Image.new("RGB", src_im.size, key)
    draw = ImageDraw.Draw(rgb)
    fnt = font(font_path, 12)
    start = 2 if len(lines) == 1 else 1
    for i, text in enumerate(lines):
        draw_line(draw, 2, start + i * 16, text, fnt)
    out = rgb.quantize(palette=src_im, dither=Image.Dither.NONE)
    out.save(dst, optimize=True)


def render_with_icon(src, dst, text, icon_width, font_path):
    src_im = Image.open(src).convert("P")
    key = palette_key(src_im)
    rgb = src_im.convert("RGB")
    px = rgb.load()
    for y in range(rgb.height):
        for x in range(icon_width, rgb.width):
            px[x, y] = key
    del px
    draw = ImageDraw.Draw(rgb)
    fnt = font(font_path, 12)
    draw_line(draw, icon_width + 1, 2, text, fnt)
    out = rgb.quantize(palette=src_im, dither=Image.Dither.NONE)
    out.save(dst, optimize=True)


def render_page(src, dst, lines, font_path):
    src_im = Image.open(src).convert("P")
    rgb = src_im.convert("RGB")
    bg = Counter(rgb.getdata()).most_common(1)[0][0]
    canvas = Image.new("RGB", rgb.size, bg)
    draw = ImageDraw.Draw(canvas)
    fnt = font(PAGE_FONT, 12)
    y = 2
    for text in lines:
        draw.text((7, y + 1), text, font=fnt, fill=(4, 6, 36))
        draw.text((6, y), text, font=fnt, fill=(4, 2, 140))
        y += 16
    out = canvas.quantize(palette=src_im, dither=Image.Dither.NONE)
    out.save(dst, optimize=True)


def validate(src_path, dst_path):
    if not dst_path.exists():
        return ["missing output"]
    src = Image.open(src_path)
    dst = Image.open(dst_path)
    problems = []
    if dst.mode != "P":
        problems.append("mode is %s, expected P" % dst.mode)
    if dst.size != src.size:
        problems.append("size is %s, expected %s" % (dst.size, src.size))
    sp = src.getpalette() or []
    dp = dst.getpalette() or []
    if dp[:3] != sp[:3]:
        problems.append("palette[0] is %s, expected %s" % (tuple(dp[:3]), tuple(sp[:3])))
    if "transparency" in dst.info:
        problems.append("unexpected transparency chunk")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-dir", required=True)
    ap.add_argument("--out", default="language/zh_CN/Picture/Interface")
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    game = Path(args.game_dir)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    src_dir = game / "Picture" / "Interface"

    jobs = []
    for name, (_source, text) in STATUS.items():
        jobs.append((name, "status", [text], None))
    for name, (_source, lines) in NOTIFY.items():
        jobs.append((name, "status", lines, None))
    for name, (_source, text, icon_width) in WEAPON.items():
        jobs.append((name, "icon", text, icon_width))
    for name, lines in PAGES.items():
        jobs.append((name, "page", lines, None))

    failures = []
    for name, kind, data, icon_width in jobs:
        src = src_dir / name
        if not src.exists():
            failures.append("%s: missing source" % name)
            continue
        dst = out / name
        if not args.check:
            if kind == "status":
                render_text_only(src, dst, data, args.font)
            elif kind == "icon":
                render_with_icon(src, dst, data, icon_width, args.font)
            else:
                render_page(src, dst, data, args.font)
        problems = validate(src, dst)
        if problems:
            failures.append("%s: %s" % (name, "; ".join(problems)))
    if failures:
        print("failures: %d" % len(failures))
        for item in failures:
            print("  " + item)
        return 1
    print("OK: %d images" % len(jobs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
