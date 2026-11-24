import argparse
import gzip
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'localizer'))
import misalignment  # noqa: E402
import po_store  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Build the compact TM reference used by the misalignment QA check.'
    )
    parser.add_argument('--tm', required=True,
                        help='path to ManualTransFile_translated.json')
    parser.add_argument('--out', default=str(Path(__file__).with_name('tm_reference.json.gz')),
                        help='output .json.gz path')
    parser.add_argument('--lang-dir', help='override language/zh_CN directory')
    args = parser.parse_args(argv)

    if args.lang_dir:
        po_store.LANG_DIR = args.lang_dir

    with open(args.tm, encoding='utf-8-sig') as f:
        tm = json.load(f)
    tm_norm = {}
    for key, value in tm.items():
        if not isinstance(value, str) or key.startswith('MTool_Meta'):
            continue
        norm = misalignment.normalize_key(key)
        if norm:
            tm_norm[norm] = value

    keys = set()
    for path in po_store.po_files():
        text = open(path, encoding='utf-8-sig', errors='replace').read()
        entries, _ = po_store.parse_entries(text)
        for entry in entries:
            for line in entry['msgid'].split('\n'):
                if misalignment.is_label(line):
                    continue
                norm = misalignment.normalize_key(line)
                if norm and norm in tm_norm:
                    keys.add(norm)

    reference = {key: tm_norm[key] for key in sorted(keys)}
    payload = {
        'version': 1,
        'source': os.path.basename(args.tm),
        'count': len(reference),
        'entries': reference,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':')).encode('utf-8')
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'wb') as f:
        with gzip.GzipFile(filename='', fileobj=f, mode='wb', mtime=0, compresslevel=9) as gz:
            gz.write(raw)
    print('wrote %s (%d entries, %.1f KiB)' % (out, len(reference), out.stat().st_size / 1024))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
