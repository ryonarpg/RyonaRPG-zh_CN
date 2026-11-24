import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANG_SRC = ROOT / 'language' / 'zh_CN'
COMPAT = ROOT / 'compat.json'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description='把本仓库的 language/zh_CN 部署到 RyonaRPG 游戏目录')
    ap.add_argument('--game-dir', required=True, help='游戏根目录（含 RPG_RT.ldb 与 EasyRPG Player.exe）')
    ap.add_argument('--with-launcher', action='store_true', help='同时复制启动中文版.bat 到游戏根目录')
    ap.add_argument('--no-backup', action='store_true', help='不备份现有 language/zh_CN（不推荐）')
    ap.add_argument('--dry-run', action='store_true', help='只显示将要执行的操作')
    args = ap.parse_args()

    game = Path(args.game_dir).expanduser().resolve()
    if not game.is_dir():
        raise SystemExit('游戏目录不存在: %s' % game)
    ldb = game / 'RPG_RT.ldb'
    player = game / 'EasyRPG Player.exe'
    if not ldb.exists():
        raise SystemExit('缺少 RPG_RT.ldb，请确认 --game-dir 指向游戏根目录')
    if not player.exists():
        print('警告：未找到 EasyRPG Player.exe；仍可部署语言文件，但启动脚本可能无法运行。')

    try:
        expected = json.loads(COMPAT.read_text(encoding='utf-8')).get('game_ldb_sha256')
    except Exception:
        expected = None
    if expected:
        actual = sha256(ldb)
        if actual != expected:
            print('警告：RPG_RT.ldb 哈希与 compat.json 不一致。')
            print('  expected', expected)
            print('  actual  ', actual)
            print('  游戏版本可能不同，建议先备份并运行 QA。')

    target = game / 'language' / 'zh_CN'
    stamp = time.strftime('%Y%m%d_%H%M%S')
    backup = ROOT / 'backups' / ('deploy_%s_zh_CN' % stamp)
    if target.exists() and not args.no_backup:
        print('备份现有翻译到', backup)
        if not args.dry_run:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(target, backup)
    elif target.exists():
        print('警告：已禁用备份，将直接覆盖', target)

    print('部署', LANG_SRC, '->', target)
    if args.with_launcher:
        print('复制启动中文版.bat ->', game / '启动中文版.bat')
    if args.dry_run:
        print('dry-run：未写入任何文件')
        return

    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(LANG_SRC, target, dirs_exist_ok=True)
    if args.with_launcher:
        shutil.copy2(ROOT / 'launcher' / '启动中文版.bat', game / '启动中文版.bat')
    print('完成。启动游戏时使用 --language zh_CN，或双击启动中文版.bat。')


if __name__ == '__main__':
    main()
