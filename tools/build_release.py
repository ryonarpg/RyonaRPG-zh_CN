import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANG = ROOT / 'language' / 'zh_CN'
DIST = ROOT / 'dist'


def version():
    ref = os.environ.get('GITHUB_REF_NAME', '').strip()
    if ref:
        return ref[1:] if ref.startswith('v') else ref
    return json.loads((ROOT / 'compat.json').read_text(encoding='utf-8')).get('translation_version', 'dev')


def main():
    if not LANG.is_dir():
        raise SystemExit('missing language/zh_CN')
    ver = version()
    staging = DIST / ('RyonaRPG-zh_CN-%s' % ver)
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copytree(LANG, staging / 'language' / 'zh_CN')
    for name in ('启动中文版.bat', '安装说明.txt'):
        shutil.copy2(ROOT / 'launcher' / name, staging / name)
    for name in ('compat.json', 'README.md', 'NOTICE.md', 'CHANGELOG.md'):
        p = ROOT / name
        if p.exists():
            shutil.copy2(p, staging / name)
    zip_path = DIST / ('RyonaRPG-zh_CN-%s.zip' % ver)
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(staging.rglob('*')):
            if p.is_file():
                z.write(p, p.relative_to(DIST))
    print('built', zip_path)


if __name__ == '__main__':
    main()
