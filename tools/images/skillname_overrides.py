#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 SkillName 原图生成中文技能名称覆盖图。"""
import argparse
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_FONT = r"C:\Windows\Fonts\unifont-all.ttf"
FALLBACK_FONTS = [
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
]
WHITE = (250, 250, 255)
SHADOW = (82, 167, 247)


def font(path, size):
    for candidate in [path] + FALLBACK_FONTS:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def image_name(key):
    # 原工具把第一张技能图编号为 001，000 是空模板；
    # 006 另存为 006b，之后编号与原列表一致。
    if key == "006":
        return "SkillName006b.png"
    if key in ("000", "001", "002", "003", "004", "005"):
        return "SkillName%03d.png" % (int(key) + 1)
    if key.startswith("skk"):
        return "SkillName_skk_%s.png" % key[3:]
    return "SkillName%s.png" % key


def load_table(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, rest = line.partition("\t")
        source, _, translation = rest.partition("\t")
        if key and translation:
            rows.append((key, source, translation))
    return rows


def render(src, dst, text, font_path):
    src_im = Image.open(src).convert("P")
    w, h = src_im.size
    rgb = src_im.convert("RGB")
    px = rgb.load()
    for y in range(4, h - 4):
        bg = Counter(px[x, y] for x in range(4, w - 4)).most_common(1)[0][0]
        for x in range(4, w - 4):
            px[x, y] = bg
    del px
    fnt = font(font_path, 12)
    if fnt.getlength(text) > w - 12:
        raise SystemExit("text too wide for %s: %s" % (dst.name, text))
    draw = ImageDraw.Draw(rgb)
    cx, cy = w // 2, h // 2
    draw.text((cx + 1, cy + 1), text, font=fnt, anchor="mm", fill=SHADOW)
    draw.text((cx, cy), text, font=fnt, anchor="mm", fill=WHITE)
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
    ap.add_argument("--table", default="tools/images/skillname_zh.tsv")
    ap.add_argument("--out", default="language/zh_CN/Picture/SkillName")
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    game = Path(args.game_dir)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    src_dir = game / "Picture" / "SkillName"
    rows = load_table(Path(args.table))
    if not rows:
        raise SystemExit("empty translation table")

    missing = []
    failures = []
    for key, _source, translation in rows:
        src = src_dir / image_name(key)
        if not src.exists():
            missing.append(str(src))
            continue
        dst = out / src.name
        if args.check:
            problems = validate(src, dst)
            if problems:
                failures.append("%s: %s" % (src.name, "; ".join(problems)))
        else:
            render(src, dst, translation, args.font)
            problems = validate(src, dst)
            if problems:
                failures.append("%s: %s" % (src.name, "; ".join(problems)))

    if missing:
        print("missing sources: %d" % len(missing))
        for path in missing:
            print("  " + path)
    if failures:
        print("validation failures: %d" % len(failures))
        for item in failures:
            print("  " + item)
    else:
        print("OK: %d images" % (len(rows) - len(missing)))
    return 1 if missing or failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
