import argparse
import hashlib
import json
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


def _needs_copy(src, dst):
    if not dst.is_file():
        return True
    s = src.stat()
    d = dst.stat()
    return s.st_size != d.st_size or int(s.st_mtime_ns) != int(d.st_mtime_ns)


def _backup_file(target, backup, rel):
    src = target / rel
    if not src.is_file():
        return False
    dst = backup / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def deploy(game_dir, with_launcher=False, no_backup=False, dry_run=False,
           incremental=False):
    """Copy the repository language layer to a game directory.

    incremental=True only copies files whose size/mtime differ and backs up
    only the files that are about to be overwritten. It is used by the editor's
    save-and-deploy action so saves do not rewrite thousands of unchanged
    images.
    """
    game = Path(game_dir).expanduser().resolve()
    if not game.is_dir():
        raise FileNotFoundError('游戏目录不存在: %s' % game)
    ldb = game / 'RPG_RT.ldb'
    if not ldb.is_file():
        raise FileNotFoundError('缺少 RPG_RT.ldb，请确认游戏目录正确')
    if not LANG_SRC.is_dir():
        raise FileNotFoundError('仓库语言目录不存在: %s' % LANG_SRC)

    warnings = []
    player = game / 'EasyRPG Player.exe'
    if not player.is_file():
        warnings.append('未找到 EasyRPG Player.exe；仍可部署语言文件，但启动脚本可能无法运行。')

    expected = None
    if COMPAT.is_file():
        try:
            expected = json.loads(COMPAT.read_text(encoding='utf-8')).get('game_ldb_sha256')
        except Exception:
            expected = None
    actual = sha256(ldb)
    hash_ok = bool(expected and actual == expected)
    if expected and not hash_ok:
        warnings.append('RPG_RT.ldb 哈希与 compat.json 不一致；游戏版本可能不同，建议先备份并运行 QA。')

    target = game / 'language' / 'zh_CN'
    stamp = time.strftime('%Y%m%d_%H%M%S')
    backup = ROOT / 'backups' / ('deploy_%s_zh_CN' % stamp)
    if not target.exists():
        backup = None
    copied = 0
    backed_up = 0

    files = []
    for src in LANG_SRC.rglob('*'):
        if not src.is_file():
            continue
        rel = src.relative_to(LANG_SRC)
        dst = target / rel
        if incremental and not _needs_copy(src, dst):
            continue
        files.append((src, dst, rel))

    if target.exists() and not no_backup and not dry_run:
        for _src, dst, rel in files:
            if dst.is_file():
                if _backup_file(target, backup, rel):
                    backed_up += 1
        if backed_up == 0:
            backup = None
    elif target.exists() and no_backup:
        warnings.append('已禁用备份，部署将直接覆盖现有文件。')
        backup = None
    elif dry_run:
        backup = backup if target.exists() else None

    if dry_run:
        return {
            'game_dir': str(game),
            'target': str(target),
            'backup': str(backup) if backup else None,
            'copied': len(files),
            'backed_up': backed_up,
            'hash_ok': hash_ok,
            'warnings': warnings,
            'dry_run': True,
        }

    target.mkdir(parents=True, exist_ok=True)
    for src, dst, _rel in files:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1

    launcher_copied = False
    if with_launcher:
        launcher = ROOT / 'launcher' / '启动中文版.bat'
        if launcher.is_file():
            shutil.copy2(launcher, game / '启动中文版.bat')
            launcher_copied = True

    return {
        'game_dir': str(game),
        'target': str(target),
        'backup': str(backup) if backup else None,
        'copied': copied,
        'backed_up': backed_up,
        'hash_ok': hash_ok,
        'warnings': warnings,
        'dry_run': False,
        'launcher_copied': launcher_copied,
    }


def main():
    ap = argparse.ArgumentParser(description='把本仓库的 language/zh_CN 部署到 RyonaRPG 游戏目录')
    ap.add_argument('--game-dir', required=True, help='游戏根目录（含 RPG_RT.ldb 与 EasyRPG Player.exe）')
    ap.add_argument('--with-launcher', action='store_true', help='同时复制启动中文版.bat 到游戏根目录')
    ap.add_argument('--no-backup', action='store_true', help='不备份现有 language/zh_CN（不推荐）')
    ap.add_argument('--dry-run', action='store_true', help='只显示将要执行的操作')
    ap.add_argument('--incremental', action='store_true',
                    help='只复制大小/mtime 变化的文件，并只备份将被覆盖的文件')
    args = ap.parse_args()

    try:
        result = deploy(
            args.game_dir,
            with_launcher=args.with_launcher,
            no_backup=args.no_backup,
            dry_run=args.dry_run,
            incremental=args.incremental,
        )
    except Exception as exc:
        print('错误:', exc)
        return 2

    for warning in result['warnings']:
        print('警告：' + warning)
    if result['backup']:
        print('备份现有翻译到', result['backup'])
    print('部署', LANG_SRC, '->', result['target'])
    if result['dry_run']:
        print('dry-run：将复制 %d 个文件，未写入任何文件' % result['copied'])
        return 0
    if args.with_launcher:
        print('复制启动中文版.bat ->', Path(result['game_dir']) / '启动中文版.bat')
    print('完成：复制 %d 个文件%s。启动游戏时使用 --language zh_CN，或双击启动中文版.bat。' % (
        result['copied'], '，备份 %d 个文件' % result['backed_up'] if result['backed_up'] else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
