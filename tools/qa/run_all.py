import json
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'localizer'))
import po_store  # noqa: E402

BAD_START = set('，。、；：')
LANG = Path(po_store.LANG_DIR)


def cells(line):
    n = 0
    i = 0
    while i < len(line):
        m = po_store.CODE_TOKEN.match(line, i)
        if m:
            n += 2 if m.group(0).startswith('$') else 0
            i = m.end()
            continue
        n += 2 if unicodedata.east_asian_width(line[i]) in ('W', 'F') else 1
        i += 1
    return n


def main():
    total = empty = over50 = over46 = line_start = split = curly = dup = bare_name = 0
    for path in po_store.po_files():
        text = open(path, encoding='utf-8-sig', errors='replace').read()
        entries, _ = po_store.parse_entries(text)
        for e in entries:
            total += 1
            tr = e['msgstr']
            if not tr.strip():
                empty += 1
            if '“' in tr or '”' in tr:
                curly += 1
            if '。。' in tr or '，，' in tr:
                dup += 1
            if re.search(r'\\[nN](?!\[)', tr):
                bare_name += 1
            if re.search(r'(?<!\\)\$(?:\n|[ 　]+)[A-Za-z]', tr):
                split += 1

            lines = tr.split('\n')
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                c = cells(line)
                if c > 50:
                    over50 += 1
                elif c > 46:
                    over46 += 1
                st = line.strip()
                if len(st) > 1 and st[0] in BAD_START:
                    if not (e['ctx'] == 'actors.name' and e['msgid'].strip().startswith('、')):
                        line_start += 1
                if i < len(lines) - 1:
                    nxt = lines[i + 1]
                    if re.search(r'\\[A-Za-z]+\[[^\]\n]*$', line):
                        split += 1
                    elif line.endswith('\\') and nxt.lstrip():
                        split += 1
                    elif re.search(r'\\[A-Za-z]+$', line) and nxt.lstrip().startswith('['):
                        split += 1

    manifest_path = LANG / '_img_manifest.json'
    manifest_count = 0
    missing_images = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest_count = len(manifest.get('files', []))
        for rel in manifest.get('files', []):
            if not (LANG / rel).exists():
                missing_images.append(rel)
    else:
        missing_images.append('_img_manifest.json')

    print('entries %d' % total)
    print('empty %d | lines>46 %d | lines>50 %d' % (empty, over46, over50))
    print('line_start %d | split_codes %d | bare_name_codes %d' % (line_start, split, bare_name))
    print('curly_quotes %d | dup_punct %d' % (curly, dup))
    print('manifest %d | missing_images %d' % (manifest_count, len(missing_images)))
    for rel in missing_images[:20]:
        print('MISSING_IMAGE', rel)

    errors = empty + over50 + line_start + split + bare_name + curly + dup + len(missing_images)
    if errors:
        print('QA FAILED: %d issue(s)' % errors)
        return 1
    print('QA OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
