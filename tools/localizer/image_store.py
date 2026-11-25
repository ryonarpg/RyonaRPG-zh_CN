import io
import json
import os
import re
import struct
import subprocess
import sys
import threading
import time
import uuid
import zlib
from pathlib import Path

from PIL import Image, ImageChops

import po_store

REPO_ROOT = Path(po_store.REPO_ROOT)
LANG_DIR = Path(po_store.LANG_DIR)
IMAGE_DIR = REPO_ROOT / 'tools' / 'images'
DATA_DIR = Path(__file__).resolve().parent / 'data'
CONFIG_PATH = DATA_DIR / 'image_config.json'
IMAGE_EXTS = {'.png', '.bmp', '.xyz'}
MAX_PIXELS = 20_000_000

FAMILIES = [
    ('Menu', '菜单图片', 'Picture/Menu/'),
    ('Pict_op', '选人界面', 'Picture/Pict_op/'),
    ('SkillName', '技能名', 'Picture/SkillName/'),
    ('Interface', '界面/状态', 'Picture/Interface/'),
    ('Ending', '结局', 'Picture/Ending/'),
    ('Mini_game', '小游戏', 'Picture/Mini_game/'),
    ('All', '全部覆盖图', 'Picture/'),
]
FAMILY_MAP = {key: {'id': key, 'label': label, 'prefix': prefix}
              for key, label, prefix in FAMILIES}

CUSTOM_GENERATORS = {
    'Pict_op': 'charselect_overrides.py',
    'SkillName': 'skillname_overrides.py',
    'Interface': 'interface_overrides.py',
    'Ending': 'ending_overrides.py',
    'Mini_game': 'minigame_overrides.py',
}
MENU_KINDS = ('all', 'items', 'skills', 'abl', 'ex', 'itm', 'labels',
              'menu_rest', 'mn_main', 'br_pages', 'sub_lists', 'cat_menu',
              'status_panel', 'sub_000200')

DEFAULT_CONFIG = {
    'game_dir': '',
    'edb_path': '',
    'lcf2xml': '',
    'font': '',
}

JOBS = {}
JOBS_LOCK = threading.Lock()


def _normalize_path(value):
    return str(value or '').strip().strip('"')


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    cfg['game_dir'] = os.environ.get('RYONA_GAME_DIR', '')
    cfg['edb_path'] = os.environ.get('RYONA_EDB', '')
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
            for key in cfg:
                if isinstance(data.get(key), str):
                    cfg[key] = data[key]
        except (OSError, ValueError):
            pass
    cfg['game_dir'] = _normalize_path(cfg['game_dir'])
    cfg['edb_path'] = _normalize_path(cfg['edb_path'])
    cfg['lcf2xml'] = _normalize_path(cfg['lcf2xml'])
    cfg['font'] = _normalize_path(cfg['font'])
    return cfg


def save_config(payload):
    cfg = load_config()
    for key in cfg:
        if key in payload:
            cfg[key] = _normalize_path(payload.get(key))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8', newline='\n')
    return get_config()


def game_status(cfg=None):
    cfg = cfg or load_config()
    root = Path(cfg['game_dir']) if cfg['game_dir'] else None
    edb = Path(cfg['edb_path']) if cfg['edb_path'] else None
    return {
        'game_dir': cfg['game_dir'],
        'edb_path': cfg['edb_path'],
        'game_exists': bool(root and root.is_dir()),
        'has_ldb': bool(root and (root / 'RPG_RT.ldb').is_file()),
        'has_picture': bool(root and (root / 'Picture').is_dir()),
        'edb_exists': bool(edb and edb.is_file()),
    }


def get_config():
    cfg = load_config()
    families = []
    for key, label, prefix in FAMILIES:
        families.append({
            'id': key,
            'label': label,
            'prefix': prefix,
            'generator': generator_name(key) is not None,
        })
    return {
        'config': cfg,
        'status': game_status(cfg),
        'families': families,
        'menu_kinds': list(MENU_KINDS),
    }


def generator_name(family):
    if family == 'Menu':
        return 'build.py' if (IMAGE_DIR / 'build.py').is_file() else None
    script = CUSTOM_GENERATORS.get(family)
    if script and (IMAGE_DIR / script).is_file():
        return script
    return None


def _safe_rel(rel):
    rel = str(rel or '').replace('\\', '/').lstrip('/')
    parts = [p for p in rel.split('/') if p]
    if not parts or parts[0] != 'Picture':
        raise ValueError('only Picture/ paths are allowed')
    if any(p in ('..', '.') for p in parts):
        raise ValueError('invalid image path')
    return '/'.join(parts)


def _base_for(side, cfg):
    if side == 'source':
        if not cfg['game_dir']:
            return None
        return Path(cfg['game_dir'])
    return LANG_DIR


def resolve_path(rel, side, cfg=None):
    cfg = cfg or load_config()
    rel = _safe_rel(rel)
    base = _base_for(side, cfg)
    if base is None:
        raise FileNotFoundError('game directory is not configured')
    path = (base / rel).resolve()
    root = base.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError('invalid image path')
    if path.suffix.lower() not in IMAGE_EXTS:
        raise ValueError('unsupported image type')
    return path


def _is_transparent_key(rel):
    rel = rel.replace('\\', '/')
    if rel.startswith('Picture/Pict_op/Noel_text_'):
        return False
    if rel.lower().endswith(('.xyz',)):
        return False
    if rel in (
        'Picture/Interface/bossbutton_text.png',
        'Picture/Interface/bossbutton_heng.png',
        'Picture/Mini_game/Baccarat.png',
    ):
        return False
    return True


def _decode_xyz(path):
    data = path.read_bytes()
    if data[:4] != b'XYZ1':
        raise ValueError('invalid xyz file')
    w, h = struct.unpack('<HH', data[4:8])
    if w * h > MAX_PIXELS:
        raise ValueError('image is too large')
    raw = zlib.decompress(data[8:])
    if len(raw) < 768 + w * h:
        raise ValueError('short xyz payload')
    im = Image.frombytes('P', (w, h), raw[768:768 + w * h])
    im.putpalette(raw[:768])
    return im.convert('RGB')


def _to_png_bytes(im):
    buf = io.BytesIO()
    im.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _transparency_mask(im):
    raw = im.tobytes()
    return Image.frombytes('L', im.size, bytes(0 if value == 0 else 255 for value in raw))


def preview_bytes(rel, side, alpha=True, cfg=None):
    path = resolve_path(rel, side, cfg)
    if path.suffix.lower() == '.xyz':
        im = _decode_xyz(path)
        return _to_png_bytes(im)

    im = Image.open(path)
    if getattr(im, 'is_animated', False):
        im.seek(0)
    if im.mode == 'P' and alpha and _is_transparent_key(rel):
        rgba = im.convert('RGBA')
        rgba.putalpha(_transparency_mask(im))
        return _to_png_bytes(rgba)
    if im.mode in ('RGBA', 'LA'):
        return _to_png_bytes(im.convert('RGBA'))
    return _to_png_bytes(im.convert('RGB'))


def _scan(base, prefix):
    root = Path(base)
    path = root / prefix.rstrip('/')
    if not path.is_dir():
        return set()
    return {p.relative_to(root).as_posix()
            for p in path.rglob('*')
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS}


def list_images(family='Menu', query='', offset=0, limit=100):
    if family not in FAMILY_MAP:
        raise ValueError('invalid family')
    cfg = load_config()
    fam = FAMILY_MAP[family]
    prefix = fam['prefix']
    rels = set()
    if family == 'All':
        rels |= _scan(LANG_DIR, 'Picture/')
    else:
        rels |= _scan(LANG_DIR, prefix)
        if cfg['game_dir'] and Path(cfg['game_dir']).is_dir():
            rels |= _scan(Path(cfg['game_dir']), prefix)
    needle = query.strip().lower()
    if needle:
        rels = {rel for rel in rels if needle in rel.lower()}
    ordered = sorted(rels)
    total = len(ordered)
    offset = max(0, int(offset))
    limit = min(max(1, int(limit)), 200)
    page = ordered[offset:offset + limit]
    items = []
    for rel in page:
        src = Path(cfg['game_dir']) / rel if cfg['game_dir'] else None
        ovr = LANG_DIR / rel
        source_ok = bool(src and src.is_file())
        override_ok = ovr.is_file()
        items.append({
            'path': rel,
            'name': Path(rel).name,
            'dir': str(Path(rel).parent).replace('\\', '/'),
            'ext': Path(rel).suffix.lower(),
            'source': source_ok,
            'override': override_ok,
            'source_size': src.stat().st_size if source_ok else None,
            'override_size': ovr.stat().st_size if override_ok else None,
            'source_mtime': src.stat().st_mtime if source_ok else None,
            'override_mtime': ovr.stat().st_mtime if override_ok else None,
        })
    return {
        'family': fam,
        'total': total,
        'offset': offset,
        'limit': limit,
        'items': items,
    }


def _rgba_image(path, rel):
    if path.suffix.lower() == '.xyz':
        return _decode_xyz(path).convert('RGBA')
    im = Image.open(path)
    if im.mode == 'P' and _is_transparent_key(rel):
        rgba = im.convert('RGBA')
        rgba.putalpha(_transparency_mask(im))
        return rgba
    return im.convert('RGBA')


def _open_native(path, rel):
    if path.suffix.lower() == '.xyz':
        return _decode_xyz(path)
    return Image.open(path)


def compare(rel):
    cfg = load_config()
    src = resolve_path(rel, 'source', cfg)
    ovr = resolve_path(rel, 'override', cfg)
    if not src.is_file() or not ovr.is_file():
        raise ValueError('both source and override images are required')
    a_im = _open_native(src, rel)
    b_im = _open_native(ovr, rel)
    if a_im.size != b_im.size:
        return {
            'same_size': False,
            'source': {'mode': a_im.mode, 'size': list(a_im.size)},
            'override': {'mode': b_im.mode, 'size': list(b_im.size)},
            'diff_pixels': None,
            'total_pixels': None,
            'ratio': None,
        }
    if a_im.width * a_im.height > MAX_PIXELS:
        raise ValueError('image is too large to compare')
    a = _rgba_image(src, rel)
    b = _rgba_image(ovr, rel)
    diff = ImageChops.difference(a, b)
    gray = diff.convert('L')
    hist = gray.histogram()
    changed = sum(hist[1:])
    total = a.width * a.height
    return {
        'same_size': True,
        'source': {'mode': a_im.mode, 'size': list(a.size)},
        'override': {'mode': b_im.mode, 'size': list(b.size)},
        'diff_pixels': changed,
        'total_pixels': total,
        'ratio': changed / total if total else 0,
        'bbox': list(gray.getbbox()) if gray.getbbox() else None,
    }


def _pick_dialog(kind, title):
    code = r'''
import sys
import tkinter as tk
from tkinter import filedialog
kind = sys.argv[1]
title = sys.argv[2]
root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
root.update()
if kind == "dir":
    path = filedialog.askdirectory(parent=root, title=title)
else:
    path = filedialog.askopenfilename(
        parent=root, title=title,
        filetypes=[("RPG Maker LDB XML", "*.edb"),
                   ("Windows executable", "*.exe"),
                   ("All files", "*.*")])
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
print(path or "")
root.destroy()
'''
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        proc = subprocess.run(
            [sys.executable, '-c', code, kind, title],
            capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=300, env=env,
        )
    except Exception as exc:
        raise RuntimeError('无法打开文件选择器：%s' % exc)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or '').strip()
        raise RuntimeError(detail or '文件选择器已取消')
    return proc.stdout.strip()


def pick_path(kind='dir', title='选择路径'):
    if kind not in ('dir', 'file'):
        raise ValueError('invalid picker kind')
    return _pick_dialog(kind, title)


def _generator_command(family, mode, kind, cfg):
    game_dir = cfg['game_dir']
    if not game_dir:
        raise ValueError('请先设置游戏目录')
    if not Path(game_dir).is_dir():
        raise ValueError('游戏目录不存在')
    script = generator_name(family)
    if not script:
        raise ValueError('该图片组没有可用的生成脚本')
    python = sys.executable
    if family == 'Menu':
        cmd = [python, str(IMAGE_DIR / 'build.py'),
               'check' if mode == 'check' else 'build',
               '--game-dir', game_dir]
        if cfg.get('edb_path'):
            cmd += ['--edb', cfg['edb_path']]
        if cfg.get('lcf2xml'):
            cmd += ['--lcf2xml', cfg['lcf2xml']]
        if cfg.get('font'):
            cmd += ['--font', cfg['font']]
        if kind:
            if not re.fullmatch(r'[a-z0-9_,]+', kind):
                raise ValueError('invalid menu kind')
            cmd += ['--kind', kind]
    else:
        cmd = [python, str(IMAGE_DIR / script), '--game-dir', game_dir]
        if mode == 'check':
            cmd.append('--check')
        if cfg.get('font'):
            cmd += ['--font', cfg['font']]
    return cmd


def _start_process_job(family, mode, kind, cmd, cwd, on_success=None):
    job_id = uuid.uuid4().hex[:10]
    job = {
        'id': job_id,
        'family': family,
        'mode': mode,
        'kind': kind,
        'status': 'running',
        'created': time.time(),
        'finished': None,
        'returncode': None,
        'command': cmd,
        'cwd': str(cwd),
        'result_path': None,
        'log': [],
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
        old = sorted(JOBS.items(), key=lambda item: item[1]['created'])
        for old_id, _ in old[:-8]:
            JOBS.pop(old_id, None)

    thread = threading.Thread(
        target=_run_job, args=(job_id, cmd, cwd, on_success), daemon=True)
    thread.start()
    return job_id


def start_job(family, mode='check', kind='all'):
    if mode not in ('check', 'build'):
        raise ValueError('invalid mode')
    cfg = load_config()
    cmd = _generator_command(family, mode, kind, cfg)
    return _start_process_job(family, mode, kind, cmd, REPO_ROOT)


def start_edb_export():
    cfg = load_config()
    game_dir = cfg.get('game_dir')
    lcf2xml = cfg.get('lcf2xml')
    if not game_dir:
        raise ValueError('请先设置游戏目录')
    ldb = Path(game_dir) / 'RPG_RT.ldb'
    if not ldb.is_file():
        raise ValueError('游戏目录中没有 RPG_RT.ldb')
    if not lcf2xml:
        raise ValueError('请先选择 lcf2xml.exe')
    lcf = Path(lcf2xml)
    if not lcf.is_file():
        raise ValueError('lcf2xml.exe 不存在：%s' % lcf2xml)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / 'RPG_RT.edb'
    cmd = [str(lcf), '--2k', '--encoding', '932', str(ldb)]

    def on_success(job):
        if not out.is_file():
            raise RuntimeError('lcf2xml 未生成 RPG_RT.edb')
        save_config({'edb_path': str(out)})
        job['result_path'] = str(out)

    return _start_process_job('EDB', 'export', 'edb', cmd, DATA_DIR, on_success)


def _run_job(job_id, cmd, cwd, on_success=None):
    job = JOBS.get(job_id)
    if not job:
        return
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUNBUFFERED'] = '1'
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(cwd), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding='utf-8',
            errors='replace', env=env, bufsize=1,
        )
        for line in proc.stdout:
            job['log'].append(line.rstrip('\n'))
            if len(job['log']) > 4000:
                del job['log'][:1000]
        job['returncode'] = proc.wait()
        if job['returncode'] == 0 and on_success:
            on_success(job)
        job['status'] = 'ok' if job['returncode'] == 0 else 'failed'
    except Exception as exc:
        job['log'].append('ERROR: %s' % exc)
        job['returncode'] = -1
        job['status'] = 'failed'
    finally:
        job['finished'] = time.time()


def get_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise FileNotFoundError('job not found')
        data = dict(job)
        data['log'] = list(job['log'])
        return data
