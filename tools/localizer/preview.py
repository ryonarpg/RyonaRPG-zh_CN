import base64
import io
import os
import re

from PIL import Image, ImageDraw, ImageFont

W, H = 320, 80
PAD_X, PAD_Y, LINE_H = 8, 4, 16

CODE = re.compile(
    r'\\[nN]\[\\[vV]\[\d+\]\]|\\[nN]\[\d+\]|\[\\[vV]\[\d+\]\]|'
    r'\\[A-Za-z]+\[\d+\]|\\[\\|.!<>^]|\\[A-Za-z]|\$[A-Za-z]'
)


def preview_text(s):
    s = re.sub(r'\\[nN]\[\\[vV]\[\d+\]\]', '[名字]', s)
    s = re.sub(r'\\[nN]\[\d+\]', '[名字]', s)
    s = re.sub(r'\[\\[vV]\[\d+\]\]', '[值]', s)
    s = re.sub(r'\\[vV]\[\d+\]', '[值]', s)
    s = CODE.sub('', s)
    s = s.replace('\\n', ' ')
    return s


def font():
    for path in (r'C:\Windows\Fonts\simsun.ttc', r'C:\Windows\Fonts\msyh.ttc'):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, 12)
            except Exception:
                pass
    return ImageFont.load_default()


def render(tr):
    text = preview_text(tr)
    lines = text.split('\n')
    if not lines:
        lines = ['']
    pages = [lines[i:i + 4] for i in range(0, len(lines), 4)]
    f = font()
    out = []
    for page in pages:
        im = Image.new('RGB', (W, H), (8, 8, 64))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W - 1, H - 1), outline=(180, 180, 200))
        d.rectangle((2, 2, W - 3, H - 3), outline=(60, 60, 120))
        for i, line in enumerate(page[:4]):
            d.text((PAD_X, PAD_Y + i * LINE_H), line, font=f, fill=(255, 255, 255))
        buf = io.BytesIO()
        im.save(buf, format='PNG')
        out.append('data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii'))
    return out
