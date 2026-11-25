import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent / 'scripts'
LANG = ROOT / 'language' / 'zh_CN'
DEFAULT_OUT = LANG / 'Picture' / 'Menu'
DEFAULT_MANIFEST = LANG / '_img_manifest.json'
DEFAULT_PO = LANG / 'RPG_RT.ldb.po'
DEFAULT_ITM_LIST = Path(__file__).resolve().parent / 'data' / 'itm_magic_ids.txt'
OKEY = (255, 156, 0)

KINDS = {
    'items': ['gen_item_imgs.py'],
    'skills': ['gen_skill_imgs.py'],
    'abl': ['gen_abl_imgs.py'],
    'ex': ['gen_ex_imgs.py'],
    'itm': ['gen_itm_imgs.py', 'gen_itm_manual.py'],
    'labels': ['gen_menu_labels.py'],
    'menu_rest': ['gen_menu_rest.py'],
    'mn_main': ['gen_mn_main.py'],
    'br_pages': ['gen_br_pages.py'],
    'sub_lists': ['gen_sub_lists.py'],
    'cat_menu': ['gen_cat_menu.py'],
    'status_panel': ['gen_status_panel.py'],
    'sub_000200': ['menu_pilot.py'],
}
KIND_ORDER = list(KINDS)
NEEDS_EDB = {'items', 'skills'}


def selected_kinds(kind):
    if kind == 'all':
        return KIND_ORDER
    out = []
    for name in (x.strip() for x in kind.split(',')):
        if name not in KINDS:
            raise SystemExit('unknown kind: %s (choose from %s, all)' % (
                name, ', '.join(KIND_ORDER)))
        out.append(name)
    return out


def default_font():
    if os.name == 'nt':
        return r'C:\Windows\Fonts\simsun.ttc'
    return ''


def game_value(args, name, default=''):
    return str(getattr(args, name) or default)


def prepare_edb(args, tmp_dir):
    if args.edb:
        return str(Path(args.edb).resolve())
    if not args.lcf2xml:
        raise SystemExit(
            'items/skills need --edb (or --lcf2xml to generate it). '
            'See tools/images/README.md.')
    game = Path(args.game_dir)
    out = Path(tmp_dir) / 'RPG_RT.edb'
    lcf = str(Path(args.lcf2xml).resolve()) if Path(args.lcf2xml).exists() else args.lcf2xml
    cmd = [lcf, '--2k', '--encoding', '932', str(game / 'RPG_RT.ldb')]
    subprocess.run(cmd, cwd=tmp_dir, check=True)
    if not out.exists():
        raise SystemExit('lcf2xml did not produce RPG_RT.edb in %s' % tmp_dir)
    return str(out)


def env_for(args, out_dir, tmp_dir, edb=''):
    env = os.environ.copy()
    env.update({
        'RYONA_REPO': str(ROOT),
        'RYONA_GAME_DIR': str(Path(args.game_dir).resolve()),
        'RYONA_OUT': str(Path(out_dir).resolve()),
        'RYONA_STAGE': str(Path(out_dir).resolve()),
        'RYONA_PO': str(Path(args.po).resolve()),
        'RYONA_EDB': edb,
        'RYONA_FONT': str(Path(args.font).resolve()) if args.font else default_font(),
        'RYONA_TMP': str(Path(tmp_dir).resolve()),
        'RYONA_ITM_LIST': str(Path(args.itm_list).resolve()),
        'PYTHONIOENCODING': 'utf-8',
    })
    return env


def run_scripts(kinds, env):
    for kind in kinds:
        for script in KINDS[kind]:
            print('run', kind, script)
            subprocess.run(
                [sys.executable, str(SCRIPTS / script)],
                cwd=str(SCRIPTS), env=env, check=True,
            )


def pngs(root):
    root = Path(root)
    if not root.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): p
        for p in sorted(root.rglob('*.png'))
        if p.is_file()
    }


def signature(path):
    im = Image.open(path)
    im.load()
    if im.mode != 'P':
        return ('mode', im.mode, im.size)
    palette = im.getpalette() or []
    rgb = im.convert('RGB').tobytes()
    return (im.size, tuple(palette[0:3]), hashlib.sha256(rgb).hexdigest())


def validate_image(path, source_path=None, source_size_value=None, require_key=False):
    issues = []
    try:
        im = Image.open(path)
        im.load()
    except Exception as exc:
        return ['cannot open: %s' % exc]
    if im.mode != 'P':
        issues.append('mode %s is not P' % im.mode)
    palette = im.getpalette()
    if not palette:
        issues.append('missing palette')
    else:
        key = tuple(palette[0:3])
        if key != OKEY:
            has_key = any(
                tuple(palette[i * 3:i * 3 + 3]) == OKEY
                for i in range(min(256, len(palette) // 3))
            )
            source_key = None
            if source_path and Path(source_path).exists():
                try:
                    src = Image.open(source_path)
                    src_pal = src.getpalette()
                    if src.mode == 'P' and src_pal:
                        source_key = tuple(src_pal[0:3])
                except Exception:
                    pass
            if has_key:
                issues.append('palette[0]=%s, but transparent key is not index 0' % (key,))
            elif source_key is not None:
                if source_key != key:
                    issues.append('palette[0]=%s, expected %s' % (key, source_key))
            elif require_key:
                issues.append('palette[0]=%s, expected %s' % (key, OKEY))
    if source_size_value and im.size != source_size_value:
        issues.append('size %sx%s, expected %sx%s' % (im.size + source_size_value))
    return issues


def source_path(game_dir, rel):
    if not game_dir:
        return None
    path = Path(game_dir) / 'Picture' / 'Menu' / rel
    return path if path.exists() else None


def source_size(game_dir, rel):
    rel = Path(rel)
    if rel.parts and rel.parts[0] == 'ABL':
        return (120, 12)
    if rel.parts and rel.parts[0] == 'EX':
        return (96, 12)
    if rel.parts and rel.parts[0] == 'ITM':
        return (120, 12)
    if game_dir:
        src = Path(game_dir) / 'Picture' / 'Menu' / rel
        if src.exists():
            try:
                return Image.open(src).size
            except Exception:
                pass
    return None


def check_manifest(manifest_path, out_dir, extra_check=True):
    issues = []
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        return ['manifest not found: %s' % manifest_path], 0
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    prefix = 'Picture/Menu/'
    files = {
        rel[len(prefix):] if rel.startswith(prefix) else rel
        for rel in data.get('files', [])
    }
    existing = set(pngs(out_dir))
    missing = sorted(files - existing)
    extra = sorted(existing - files) if extra_check else []
    for rel in missing[:20]:
        issues.append('manifest path missing: %s' % rel)
    if len(missing) > 20:
        issues.append('... %d more manifest paths missing' % (len(missing) - 20))
    for rel in extra[:20]:
        issues.append('image not in manifest: %s' % rel)
    if len(extra) > 20:
        issues.append('... %d more images not in manifest' % (len(extra) - 20))
    return issues, len(files)


def validate_tree(args, out_dir):
    out_dir = Path(out_dir)
    issues = []
    images = pngs(out_dir)
    for rel, path in images.items():
        bad = validate_image(
            path,
            source_path(args.game_dir, rel),
            source_size(args.game_dir, rel),
            require_key=rel.startswith(('ABL/', 'EX/', 'ITM/')),
        )
        for item in bad:
            issues.append('%s: %s' % (rel, item))
    manifest_count = 0
    if args.kind == 'all' and Path(out_dir).resolve() == DEFAULT_OUT.resolve():
        manifest_issues, manifest_count = check_manifest(
            args.manifest, out_dir, extra_check=True)
        issues.extend(manifest_issues)
    return {
        'out': str(out_dir),
        'images': len(images),
        'manifest': manifest_count,
        'issues': issues,
    }


def cmd_build(args):
    out_dir = Path(args.out or DEFAULT_OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    kinds = selected_kinds(args.kind)
    with tempfile.TemporaryDirectory(prefix='ryona_img_tmp_') as tmp:
        edb = prepare_edb(args, tmp) if (set(kinds) & NEEDS_EDB or args.kind == 'all') else ''
        env = env_for(args, out_dir, tmp, edb)
        run_scripts(kinds, env)
    result = validate_tree(args, out_dir)
    print('images %d | manifest %d | issues %d' % (
        result['images'], result['manifest'], len(result['issues'])))
    for item in result['issues'][:30]:
        print('IMAGE_ISSUE', item)
    return 1 if result['issues'] else 0


def cmd_check(args):
    repo_out = Path(args.out or DEFAULT_OUT)
    kinds = selected_kinds(args.kind)
    with tempfile.TemporaryDirectory(prefix='ryona_img_check_') as tmp:
        tmp_out = Path(tmp) / 'Menu'
        tmp_out.mkdir(parents=True)
        edb = prepare_edb(args, tmp) if (set(kinds) & NEEDS_EDB or args.kind == 'all') else ''
        env = env_for(args, tmp_out, tmp, edb)
        run_scripts(kinds, env)

        generated = pngs(tmp_out)
        committed = pngs(repo_out)
        stale = []
        missing = []
        invalid = []
        for rel, path in generated.items():
            if rel not in committed:
                missing.append(rel)
                continue
            bad = validate_image(
                path,
                source_path(args.game_dir, rel),
                source_size(args.game_dir, rel),
                require_key=rel.startswith(('ABL/', 'EX/', 'ITM/')),
            )
            if bad:
                invalid.append((rel, bad))
                continue
            if signature(path) != signature(committed[rel]):
                stale.append(rel)
        extra = sorted(set(committed) - set(generated)) if args.kind == 'all' else []

    print('generated %d | stale %d | missing %d | extra %d | invalid %d' % (
        len(generated), len(stale), len(missing), len(extra), len(invalid)))
    for label, items in (('STALE', stale), ('MISSING', missing), ('EXTRA', extra)):
        for rel in items[:30]:
            print(label, rel)
        if len(items) > 30:
            print('%s ... %d more' % (label, len(items) - 30))
    for rel, bad in invalid[:20]:
        print('INVALID', rel, '; '.join(bad))
    return 1 if (stale or missing or extra or invalid) else 0


def cmd_validate(args):
    out_dir = Path(args.out or DEFAULT_OUT)
    result = validate_tree(args, out_dir)
    print('images %d | manifest %d | issues %d' % (
        result['images'], result['manifest'], len(result['issues'])))
    for item in result['issues'][:50]:
        print('IMAGE_ISSUE', item)
    return 1 if result['issues'] else 0


def add_common(parser, require_game=True):
    parser.add_argument('--game-dir', required=require_game,
                        help='原版游戏目录（包含 RPG_RT.ldb 和 Picture/Menu）')
    parser.add_argument('--po', default=str(DEFAULT_PO),
                        help='译文 PO 文件（默认 language/zh_CN/RPG_RT.ldb.po）')
    parser.add_argument('--edb', help='lcf2xml 导出的 RPG_RT.edb')
    parser.add_argument('--lcf2xml', help='lcf2xml 可执行文件；没有 --edb 时自动导出')
    parser.add_argument('--font', default=default_font(),
                        help='CJK 字体路径（默认 Windows simsun.ttc）')
    parser.add_argument('--out', default=str(DEFAULT_OUT),
                        help='输出 Picture/Menu 目录')
    parser.add_argument('--manifest', default=str(DEFAULT_MANIFEST),
                        help='_img_manifest.json 路径')
    parser.add_argument('--itm-list', default=str(DEFAULT_ITM_LIST),
                        help='ITM 图像的 ID 对照表')
    parser.add_argument('--kind', default='all',
                        help='all 或逗号分隔：%s' % ', '.join(KIND_ORDER))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='RyonaRPG 菜单图片生成与校验工具')
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('build', help='生成/覆盖图片')
    add_common(p, require_game=True)
    p.set_defaults(func=cmd_build)

    p = sub.add_parser('check', help='生成到临时目录并检查仓库图片是否需要更新')
    add_common(p, require_game=True)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser('validate', help='只校验现有图片格式、尺寸和 manifest')
    add_common(p, require_game=False)
    p.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    if args.game_dir:
        if not Path(args.game_dir).is_dir():
            parser.error('--game-dir is not a directory: %s' % args.game_dir)
    if args.command in ('build', 'check'):
        if not args.font:
            parser.error('--font is required on this platform')
    if args.font and not Path(args.font).is_file():
        parser.error('--font not found: %s' % args.font)
    if args.edb and not Path(args.edb).is_file():
        parser.error('--edb not found: %s' % args.edb)
    if args.po and not Path(args.po).is_file():
        parser.error('--po not found: %s' % args.po)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
