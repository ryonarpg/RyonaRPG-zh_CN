#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查新游戏本体相对 compat.json / 旧游戏目录的变化，给更新翻译提供分流建议。"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COMPAT = ROOT / 'compat.json'
LANG_DIR = ROOT / 'language' / 'zh_CN'
IMAGE_EXTS = {'.png', '.bmp', '.xyz'}
IMAGE_FAMILIES = {
    'Menu': 'Picture/Menu',
    'Pict_op': 'Picture/Pict_op',
    'SkillName': 'Picture/SkillName',
    'Interface': 'Picture/Interface',
    'Ending': 'Picture/Ending',
    'Mini_game': 'Picture/Mini_game',
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def file_info(path, hash_file=True):
    st = path.stat()
    info = {'size': st.st_size, 'mtime': st.st_mtime}
    if hash_file:
        info['sha256'] = sha256(path)
    return info


def collect_maps(game):
    game = Path(game)
    return {
        p.name: file_info(p)
        for p in sorted(game.glob('Map*.lmu'))
        if p.is_file()
    }


def collect_images(game):
    game = Path(game)
    out = {}
    for family, prefix in IMAGE_FAMILIES.items():
        root = game / prefix
        if not root.is_dir():
            out[family] = {}
            continue
        out[family] = {
            p.relative_to(game).as_posix(): file_info(p)
            for p in sorted(root.rglob('*'))
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        }
    return out


def collect_snapshot(game):
    game = Path(game)
    ldb = game / 'RPG_RT.ldb'
    lmt = game / 'RPG_RT.lmt'
    ini = game / 'RPG_RT.ini'
    return {
        'ldb': file_info(ldb) if ldb.is_file() else None,
        'lmt': file_info(lmt) if lmt.is_file() else None,
        'ini': file_info(ini) if ini.is_file() else None,
        'maps': collect_maps(game),
        'images': collect_images(game),
    }


def diff_manifest(old, new):
    old_keys = set(old)
    new_keys = set(new)
    changed = sorted(k for k in old_keys & new_keys
                     if old[k].get('sha256') != new[k].get('sha256'))
    return {
        'added': sorted(new_keys - old_keys),
        'removed': sorted(old_keys - new_keys),
        'changed': changed,
    }


def diff_images(old, new):
    result = {}
    for family in IMAGE_FAMILIES:
        result[family] = diff_manifest(old.get(family, {}), new.get(family, {}))
    return result


def _summary(diff):
    return len(diff['added']) + len(diff['removed']) + len(diff['changed'])


def check(game_dir, old_game_dir=None, compat_path=DEFAULT_COMPAT):
    game = Path(game_dir).expanduser().resolve()
    if not game.is_dir():
        raise FileNotFoundError('游戏目录不存在: %s' % game)
    if not (game / 'RPG_RT.ldb').is_file():
        raise FileNotFoundError('目录中没有 RPG_RT.ldb: %s' % game)

    compat = {}
    compat_path = Path(compat_path)
    if compat_path.is_file():
        compat = json.loads(compat_path.read_text(encoding='utf-8'))

    new = collect_snapshot(game)
    expected = compat.get('game_ldb_sha256')
    ldb_sha = new['ldb']['sha256'] if new['ldb'] else None
    ldb_matches = bool(expected and ldb_sha == expected)

    old = None
    maps_diff = None
    images_diff = None
    ldb_changed = False
    lmt_changed = False
    if old_game_dir:
        old_path = Path(old_game_dir).expanduser().resolve()
        if not old_path.is_dir():
            raise FileNotFoundError('旧游戏目录不存在: %s' % old_path)
        old = collect_snapshot(old_path)
        old_ldb = old['ldb']['sha256'] if old.get('ldb') else None
        new_ldb = new['ldb']['sha256'] if new.get('ldb') else None
        ldb_changed = old_ldb != new_ldb
        old_lmt = old['lmt']['sha256'] if old.get('lmt') else None
        new_lmt = new['lmt']['sha256'] if new.get('lmt') else None
        lmt_changed = old_lmt != new_lmt
        maps_diff = diff_manifest(old['maps'], new['maps'])
        images_diff = diff_images(old['images'], new['images'])

    recommendations = []
    if old is None:
        recommendations.append(
            '未提供 --old-game-dir，只能核对 compat.json 的 LDB 哈希；'
            '无法判断地图和图片变化。')
    else:
        if ldb_changed:
            recommendations.append(
                'RPG_RT.ldb 已变化：重新导出数据库 XML/PO，检查物品、技能、'
                '状态、公共事件，并重生成数据库相关图片。')
        if lmt_changed:
            recommendations.append('RPG_RT.lmt 已变化：重新导出 LMT 并合并地图树/战斗文本。')
        if maps_diff and _summary(maps_diff):
            recommendations.append(
                '地图文件有变化：重新导出对应 Map*.lmu，按消息合并旧 PO；'
                '重点检查新增/变更事件和连续 10110 分页。')
        for family, diff in (images_diff or {}).items():
            if _summary(diff):
                recommendations.append(
                    '%s 图片有变化：重新生成该图片组覆盖图并更新 manifest。'
                    % family)

    if not ldb_matches:
        recommendations.append(
            '新 LDB 哈希与 compat.json 不一致：完成核对后更新 compat.json '
            '的 game_version / game_ldb_sha256。')
    if old is not None and not ldb_changed and not lmt_changed and not any(
            _summary(d) for d in [maps_diff] + list((images_diff or {}).values())):
        recommendations.append(
            '未发现 LDB/LMT/地图/图片结构变化；仍建议跑 QA、更新版本并实机回归。')

    po_files = sorted(LANG_DIR.glob('*.po')) if LANG_DIR.is_dir() else []
    return {
        'game_dir': str(game),
        'old_game_dir': str(Path(old_game_dir).expanduser().resolve())
        if old_game_dir else None,
        'compat': {
            'game_version': compat.get('game_version'),
            'translation_version': compat.get('translation_version'),
            'expected_ldb_sha256': expected,
        },
        'ldb': {
            'sha256': ldb_sha,
            'matches_compat': ldb_matches,
            'size': new['ldb']['size'] if new['ldb'] else None,
        },
        'lmt': new['lmt'],
        'counts': {
            'maps': len(new['maps']),
            'images': {
                family: len(files)
                for family, files in new['images'].items()
            },
            'po_files': len(po_files),
        },
        'changes': {
            'ldb': ldb_changed,
            'lmt': lmt_changed,
            'maps': maps_diff,
            'images': images_diff,
        },
        'recommendations': recommendations,
        'has_changes': bool(
            ldb_changed or lmt_changed or
            (maps_diff and _summary(maps_diff)) or
            any(_summary(d) for d in (images_diff or {}).values())),
    }


def render_text(data, limit=20):
    lines = [
        '游戏目录: %s' % data['game_dir'],
        'compat: %s / translation %s' % (
            data['compat']['game_version'] or '?',
            data['compat']['translation_version'] or '?'),
        'LDB SHA-256: %s' % (data['ldb']['sha256'] or 'missing'),
        'LDB 与 compat 一致: %s' % ('yes' if data['ldb']['matches_compat'] else 'NO'),
        '地图: %d | PO: %d' % (data['counts']['maps'], data['counts']['po_files']),
    ]
    images = data['counts']['images']
    lines.append('图片: ' + ', '.join('%s=%d' % (k, v) for k, v in images.items()))
    changes = data['changes']
    if data['old_game_dir'] is None:
        lines.append('旧游戏目录: 未提供（无法做文件级比较）')
    else:
        lines.append('旧游戏目录: %s' % data['old_game_dir'])
        lines.append('LDB 变化: %s | LMT 变化: %s' % (
            'yes' if changes['ldb'] else 'no',
            'yes' if changes['lmt'] else 'no'))
        maps = changes.get('maps') or {}
        lines.append('地图变化: +%d / -%d / ~%d' % (
            len(maps.get('added', [])), len(maps.get('removed', [])),
            len(maps.get('changed', []))))
        if maps.get('changed'):
            lines.append('  变更: ' + ', '.join(maps['changed'][:limit]))
        for family, diff in (changes.get('images') or {}).items():
            count = _summary(diff)
            if count:
                lines.append('图片 %s: +%d / -%d / ~%d' % (
                    family, len(diff['added']), len(diff['removed']),
                    len(diff['changed'])))
    lines.append('建议:')
    for item in data['recommendations']:
        lines.append('  - ' + item)
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(
        description='检查新游戏本体相对旧版本/compat.json 的变化，'
                    '判断需要重做哪些翻译和图片。')
    ap.add_argument('--game-dir', required=True, help='新游戏根目录')
    ap.add_argument('--old-game-dir', help='旧游戏根目录（用于文件级差异）')
    ap.add_argument('--compat', default=str(DEFAULT_COMPAT))
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--limit', type=int, default=20,
                    help='文本输出中每类变更最多列出的文件名数')
    args = ap.parse_args()
    try:
        data = check(args.game_dir, args.old_game_dir, args.compat)
    except Exception as exc:
        print('error: %s' % exc, file=sys.stderr)
        return 2
    if args.json:
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_text(data, args.limit))
    if data['has_changes'] or not data['ldb']['matches_compat']:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
