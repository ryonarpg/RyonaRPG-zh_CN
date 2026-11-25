#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Ending 文本幻灯片的 .xyz 中文覆盖文件。"""
import argparse
import struct
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_FONT = r"C:\Windows\Fonts\simhei.ttf"
FALLBACK_FONTS = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\unifont-all.ttf",
]

LISTS = {
    "Ending04.xyz": range(1, 11),
    "Ending05.xyz": range(11, 21),
    "Ending06.xyz": range(21, 31),
    "Ending07.xyz": range(31, 41),
    "Ending08.xyz": range(41, 49),
}

ENDING = {
    "Ending02.xyz": ["任务「通往异世界之门」开发", "Scientist"],
    "Ending03.xyz": ["RyonaRPG开发"],
    "Ending09.xyz": ["新RyonaSaga自主制作·扩展帖"]
    + ["新RyonaSaga自主制作·扩展帖 Part.%d" % i for i in range(2, 12)],
    "Ending10.xyz": ["特别鸣谢"],
    "Ending11.xyz": [
        "RyonaRPG原作者",
        "各素材提供者",
        "参与开发的各位",
        "RyonaSaga开发室Disco部各位",
        "RyonaRPG非官方wiki",
    ],
    "Ending12.xyz": ["还有", "身为玩家的你", "致所有参与RyonaRPG的人", "THANK YOU !"],
}

for name, nums in LISTS.items():
    lines = []
    for i in nums:
        suffix = "" if i == 1 else str(i)
        lines.append("RyonaSaga自主制作·扩展帖" + suffix)
    ENDING[name] = lines


def font(path, size):
    for candidate in [path] + FALLBACK_FONTS:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def decode(path):
    data = path.read_bytes()
    if data[:4] != b"XYZ1":
        raise ValueError("%s: bad magic" % path)
    w, h = struct.unpack("<HH", data[4:8])
    raw = zlib.decompress(data[8:])
    if len(raw) < 768 + w * h:
        raise ValueError("%s: short payload" % path)
    return w, h, raw[:768], raw[768:768 + w * h]


def encode(path, w, h, palette, indices):
    path.write_bytes(b"XYZ1" + struct.pack("<HH", w, h) +
                     zlib.compress(palette + indices, 9))


def bands(im):
    rgb = im.convert("RGB")
    bg = rgb.getpixel((0, 0))
    rows = []
    for y in range(im.height):
        rows.append(any(rgb.getpixel((x, y)) != bg for x in range(im.width)))
    out = []
    start = None
    for y, has in enumerate(rows):
        if has and start is None:
            start = y
        if not has and start is not None:
            out.append((start, y - 1))
            start = None
    if start is not None:
        out.append((start, im.height - 1))
    return out


def render(src, dst, lines, font_path, preview_dir=None):
    w, h, palette, indices = decode(src)
    src_im = Image.frombytes("P", (w, h), indices)
    src_im.putpalette(palette)
    spans = bands(src_im)
    if len(spans) != len(lines):
        raise SystemExit("%s: expected %d text lines, found %d" %
                         (src.name, len(lines), len(spans)))
    bg = tuple(palette[:3])
    canvas = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(canvas)
    fnt = font(font_path, 16)
    for (y0, y1), text in zip(spans, lines):
        if fnt.getlength(text) > w - 8:
            raise SystemExit("%s: text too wide: %s" % (src.name, text))
        draw.text((w // 2, (y0 + y1 + 1) // 2), text, font=fnt,
                  anchor="mm", fill=(247, 247, 247))
    out_im = canvas.quantize(palette=src_im, dither=Image.Dither.NONE)
    indices = out_im.tobytes()
    if len(indices) != w * h:
        raise SystemExit("%s: bad index length" % src.name)
    encode(dst, w, h, bytes(palette), indices)
    if preview_dir:
        preview_dir.mkdir(parents=True, exist_ok=True)
        out_im.convert("RGB").save(preview_dir / (src.name + ".png"))


def check(src, dst):
    if not dst.exists():
        return ["missing output"]
    try:
        w, h, palette, indices = decode(dst)
    except Exception as exc:
        return [str(exc)]
    problems = []
    sw, sh, spalette, _ = decode(src)
    if (w, h) != (sw, sh):
        problems.append("size is %sx%s, expected %sx%s" % (w, h, sw, sh))
    if palette != spalette:
        problems.append("palette differs from source")
    if len(indices) != w * h:
        problems.append("index length %d, expected %d" % (len(indices), w * h))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-dir", required=True)
    ap.add_argument("--out", default="language/zh_CN/Picture/Ending")
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--preview-dir", default="build/ending_preview_zh")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    game = Path(args.game_dir)
    src_dir = game / "Picture" / "Ending"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    failures = []
    for name, lines in ENDING.items():
        src = src_dir / name
        if not src.exists():
            failures.append("%s: missing source" % name)
            continue
        dst = out / name
        if not args.check:
            render(src, dst, lines, args.font, Path(args.preview_dir))
        problems = check(src, dst)
        if problems:
            failures.append("%s: %s" % (name, "; ".join(problems)))
    if failures:
        print("failures: %d" % len(failures))
        for item in failures:
            print("  " + item)
        return 1
    print("OK: %d endings" % len(ENDING))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
