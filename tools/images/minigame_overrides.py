#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Mini_game 中 BlackJack 策略表的中文覆盖图。"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_FONT = r"C:\Windows\Fonts\simhei.ttf"
FALLBACK_FONTS = [
    r"C:\Windows\Fonts\simsun.ttc",
    r"C:\Windows\Fonts\unifont-all.ttf",
]

HEADER = ("2张牌合计", "抽第3张时")
ROWS = [
    ("9、8", "停牌"),
    ("7", "停牌"),
    ("6", "闲家第3张为6、7"),
    ("5", "闲家第3张为4～7"),
    ("4", "闲家第3张为2～7"),
    ("3", "闲家第3张为0～7、9"),
    ("0、1、2", "全部抽牌"),
]

# 原图 280x108：表头 y2..13，之后每行约 13px；竖线在 x=1 和 x=84。
HEADER_BOXES = [(3, 2, 83, 14), (86, 2, 279, 14)]
ROW_Y = [(16, 28), (29, 41), (42, 54), (56, 68), (69, 81), (82, 94), (96, 108)]


def font(path, size):
    for candidate in [path] + FALLBACK_FONTS:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render(src, dst, font_path):
    src_im = Image.open(src).convert("P")
    rgb = src_im.convert("RGB")
    header_bg = (230, 230, 230)
    body_bg = (255, 255, 255)
    draw = ImageDraw.Draw(rgb)
    fnt = font(font_path, 8)

    for (box, text) in zip(HEADER_BOXES, HEADER):
        x0, y0, x1, y1 = box
        draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=header_bg)
        draw.text((x0 + 1, y0 + 1), text, font=fnt, fill=(85, 149, 117))

    for (y0, y1), (left, right) in zip(ROW_Y, ROWS):
        draw.rectangle([3, y0, 83, y1 - 1], fill=body_bg)
        draw.rectangle([86, y0, 279, y1 - 1], fill=body_bg)
        draw.text((4, y0 + 1), left, font=fnt, fill=(85, 149, 117))
        draw.text((87, y0 + 1), right, font=fnt, fill=(85, 149, 117))

    out = rgb.quantize(palette=src_im, dither=Image.Dither.NONE)
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
    ap.add_argument("--out", default="language/zh_CN/Picture/Mini_game")
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    game = Path(args.game_dir)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    src = game / "Picture" / "Mini_game" / "Baccarat.png"
    dst = out / "Baccarat.png"
    if not src.exists():
        print("missing source: " + str(src))
        return 1
    if not args.check:
        render(src, dst, args.font)
    problems = validate(src, dst)
    if problems:
        print("FAIL: " + "; ".join(problems))
        return 1
    print("OK: Baccarat.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
