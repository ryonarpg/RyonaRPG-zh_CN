import glob
import os
import re
import shutil
import sqlite3
import time
import unicodedata

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(TOOL_DIR))
DEFAULT_LANG_DIR = os.path.join(REPO_ROOT, 'language', 'zh_CN')
LANG_DIR = os.environ.get('RYONA_LANG_DIR', DEFAULT_LANG_DIR)
DB_PATH = os.path.join(TOOL_DIR, 'data', 'index.db')
BACKUP_DIR = os.path.join(TOOL_DIR, 'backups')

CODE_TOKEN = re.compile(
    r'\\[nN]\[\\[vV]\[\d+\]\]|\\[nN]\[\d+\]|\[\\[vV]\[\d+\]\]|'
    r'\\[A-Za-z]+\[\d+\]|\\[\\|.!<>^]|\\[A-Za-z]|\$[A-Za-z]'
)


def unescape_po(s):
    out = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            c = s[i + 1]
            if c == 'n':
                out.append('\n')
            elif c == '"':
                out.append('"')
            elif c == '\\':
                out.append('\\')
            else:
                out.append('\\' + c)
            i += 2
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


def concat_po_strings(expr):
    return ''.join(re.findall(r'"(.*)"', expr))


def escape_po(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def format_msgstr(lines):
    if len(lines) == 1:
        return 'msgstr "%s"' % escape_po(lines[0])
    body = '\n'.join('"%s\\n"' % escape_po(line) for line in lines[:-1])
    return 'msgstr ""\n%s\n"%s"' % (body, escape_po(lines[-1]))


def normalize_search(s):
    s = CODE_TOKEN.sub('', s)
    s = unicodedata.normalize('NFKC', s).lower()
    return re.sub(r'[\s\u3000]+', '', s)


def clean_for_display(s):
    s = CODE_TOKEN.sub('', s)
    s = s.replace('\\n', ' ').replace('\n', ' ')
    return re.sub(r'[\s\u3000]+', ' ', s).strip()


def split_parts(text):
    return re.split(r'(\n\s*\n)', text)


def parse_entries(text):
    parts = split_parts(text)
    entries = []
    seq = 0
    for pi in range(0, len(parts), 2):
        chunk = parts[pi]
        if not chunk.strip():
            continue
        ctx_m = re.search(r'(?m)^msgctxt "(.*)"', chunk)
        id_m = re.search(r'(?m)^msgid ("(?:.*)(?:\n"(?:.*))*")', chunk)
        str_m = re.search(r'(?m)^msgstr ("(?:.*)(?:\n"(?:.*))*")', chunk)
        if not id_m or not str_m:
            continue
        mid = unescape_po(concat_po_strings(id_m.group(1)))
        if not mid.strip():
            continue
        ctx = unescape_po(ctx_m.group(1)) if ctx_m else ''
        tr = unescape_po(concat_po_strings(str_m.group(1)))
        comments = [x for x in chunk.split('\n') if x.startswith('#')]
        entries.append({
            'seq': seq,
            'part_index': pi,
            'ctx': ctx,
            'msgid': mid,
            'msgstr': tr,
            'comments': comments,
        })
        seq += 1
    return entries, parts


def po_files():
    return sorted(glob.glob(os.path.join(LANG_DIR, '*.po')))


def safe_file_path(file_name):
    if os.path.basename(file_name) != file_name:
        raise ValueError('invalid file name')
    path = os.path.join(LANG_DIR, file_name)
    if not os.path.isfile(path):
        raise FileNotFoundError(file_name)
    return path


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def init_db(con):
    con.executescript('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
            file TEXT NOT NULL,
            block INTEGER NOT NULL,
            ctx TEXT,
            msgid TEXT,
            msgstr TEXT,
            jp_norm TEXT,
            cn_norm TEXT,
            comment TEXT,
            UNIQUE(file, block)
        );
        CREATE INDEX IF NOT EXISTS idx_entries_file ON entries(file);
        CREATE INDEX IF NOT EXISTS idx_entries_ctx ON entries(ctx);
        CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
            jp_norm, cn_norm, file, ctx,
            content='entries', content_rowid='id', tokenize='trigram'
        );
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    ''')


def rebuild_index():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = connect()
    try:
        init_db(con)
        con.execute('DELETE FROM entries')
        con.execute('DELETE FROM entries_fts')
        total = 0
        for path in po_files():
            fn = os.path.basename(path)
            text = open(path, encoding='utf-8-sig', errors='replace').read()
            entries, _ = parse_entries(text)
            rows = []
            for e in entries:
                rows.append((
                    fn, e['seq'], e['ctx'], e['msgid'], e['msgstr'],
                    normalize_search(e['msgid']), normalize_search(e['msgstr']),
                    '\n'.join(e['comments']),
                ))
            con.executemany(
                'INSERT INTO entries(file, block, ctx, msgid, msgstr, jp_norm, cn_norm, comment) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)', rows)
            total += len(rows)
        con.commit()
        con.execute("INSERT INTO entries_fts(entries_fts) VALUES('rebuild')")
        con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('lang_dir', ?)", (LANG_DIR,))
        con.commit()
        return total
    finally:
        con.close()


def ensure_index():
    if not os.path.exists(DB_PATH):
        return rebuild_index()
    con = connect()
    try:
        init_db(con)
        row = con.execute("SELECT value FROM meta WHERE key = 'lang_dir'").fetchone()
        lang_dir = row['value'] if row else None
        n = con.execute('SELECT COUNT(*) AS n FROM entries').fetchone()['n']
    finally:
        con.close()
    if n == 0 or lang_dir != LANG_DIR:
        return rebuild_index()
    return n


def _fts_query(q):
    return '"' + q.replace('"', '""') + '"'


def search(q, mode='both', limit=200):
    q = normalize_search(q)
    if not q:
        return {'items': [], 'total': 0, 'query': q}
    con = connect()
    try:
        init_db(con)
        like = '%' + q + '%'
        where = []
        params = []
        if mode == 'jp':
            where.append('jp_norm LIKE ?')
            params.append(like)
        elif mode == 'cn':
            where.append('cn_norm LIKE ?')
            params.append(like)
        else:
            where.append('(jp_norm LIKE ? OR cn_norm LIKE ? OR lower(file) LIKE ?)')
            params.extend([like, like, like])

        total = con.execute(
            'SELECT COUNT(*) AS n FROM entries WHERE ' + ' AND '.join(where), params
        ).fetchone()['n']

        rows = []
        used_fts = False
        if len(q) >= 3:
            try:
                fts = _fts_query(q)
                sql = ('SELECT e.* FROM entries e JOIN entries_fts f ON f.rowid = e.id '
                       'WHERE entries_fts MATCH ?')
                fparams = [fts]
                if mode == 'jp':
                    sql += ' AND e.jp_norm LIKE ?'
                    fparams.append(like)
                elif mode == 'cn':
                    sql += ' AND e.cn_norm LIKE ?'
                    fparams.append(like)
                else:
                    sql += ' AND (e.jp_norm LIKE ? OR e.cn_norm LIKE ? OR lower(e.file) LIKE ?)'
                    fparams.extend([like, like, like])
                sql += ' ORDER BY e.file, e.block LIMIT ?'
                fparams.append(limit)
                rows = con.execute(sql, fparams).fetchall()
                used_fts = bool(rows)
            except sqlite3.Error:
                rows = []
        if not used_fts:
            sql = ('SELECT * FROM entries WHERE ' + ' AND '.join(where) +
                   ' ORDER BY file, block LIMIT ?')
            rows = con.execute(sql, params + [limit]).fetchall()

        items = []
        for r in rows:
            display = r['msgstr'] if (mode != 'jp' and q in r['cn_norm']) else r['msgid']
            snippet = clean_for_display(display)
            if len(snippet) > 160:
                snippet = snippet[:160] + '…'
            items.append({
                'file': r['file'],
                'block': r['block'],
                'ctx': r['ctx'] or '',
                'msgid': r['msgid'],
                'msgstr': r['msgstr'],
                'snippet': snippet,
            })
        return {'items': items, 'total': total, 'query': q, 'used_fts': used_fts}
    finally:
        con.close()


BROWSE_DIMS = (
    ('maps', '地图'),
    ('actors', '角色'),
    ('items', '物品'),
    ('skills', '技能'),
    ('database', '状态/术语'),
    ('files', 'PO 文件'),
)
BROWSE_DIM_LABELS = dict(BROWSE_DIMS)


def _browse_filter(dim):
    if dim == 'maps':
        return "file LIKE 'Map%.po'", []
    if dim == 'actors':
        return "ctx IN ('actors.name', 'actors.title')", []
    if dim == 'items':
        return "ctx IN ('items.name', 'items.description')", []
    if dim == 'skills':
        return "ctx IN ('skills.name', 'skills.description')", []
    if dim == 'database':
        return "(ctx = 'states.name' OR ctx = 'enemies.name' OR ctx LIKE 'terms.%')", []
    if dim == 'files':
        return '1 = 1', []
    raise ValueError('invalid browse dimension')


def _browse_group_filter(dim, group):
    if dim in ('maps', 'files'):
        return 'file = ?', [group]
    if dim in ('actors', 'items', 'skills'):
        return 'ctx = ?', [group]
    if dim == 'database':
        if group == 'states':
            return "ctx = 'states.name'", []
        if group == 'terms':
            return "ctx LIKE 'terms.%'", []
        if group == 'enemies':
            return "ctx = 'enemies.name'", []
    raise ValueError('invalid browse group')


def _browse_group_label(dim, group):
    if dim == 'maps':
        return group[:-3] if group.endswith('.po') else group
    if dim == 'files':
        return group
    if dim == 'actors':
        return {'actors.name': '角色名', 'actors.title': '角色称号'}.get(group, group)
    if dim == 'items':
        return {'items.name': '物品名', 'items.description': '物品说明'}.get(group, group)
    if dim == 'skills':
        return {'skills.name': '技能名', 'skills.description': '技能说明'}.get(group, group)
    if dim == 'database':
        return {'states': '状态', 'terms': '系统术语', 'enemies': '敌人'}.get(group, group)
    return group


def _browse_group_section(dim, group):
    if dim == 'maps':
        return '地图'
    if dim == 'files':
        return '地图' if group.startswith('Map') else '数据库与公共事件'
    return ''


def _browse_categories(con):
    row = con.execute(
        "SELECT "
        "COALESCE(SUM(file LIKE 'Map%.po'), 0) AS maps, "
        "COALESCE(SUM(ctx IN ('actors.name', 'actors.title')), 0) AS actors, "
        "COALESCE(SUM(ctx IN ('items.name', 'items.description')), 0) AS items, "
        "COALESCE(SUM(ctx IN ('skills.name', 'skills.description')), 0) AS skills, "
        "COALESCE(SUM(ctx = 'states.name' OR ctx = 'enemies.name' OR ctx LIKE 'terms.%'), 0) AS database, "
        "COUNT(*) AS files "
        "FROM entries"
    ).fetchone()
    return [{'id': key, 'label': label, 'count': row[key]} for key, label in BROWSE_DIMS]


def _browse_groups(con, dim):
    where, params = _browse_filter(dim)
    if dim in ('maps', 'files'):
        order = ("CASE WHEN file LIKE 'Map%' THEN 1 ELSE 0 END, file"
                 if dim == 'files' else 'file')
        rows = con.execute(
            'SELECT file AS g, COUNT(*) AS n FROM entries WHERE ' + where +
            ' GROUP BY file ORDER BY ' + order, params
        ).fetchall()
    elif dim in ('actors', 'items', 'skills'):
        rows = con.execute(
            'SELECT ctx AS g, COUNT(*) AS n FROM entries WHERE ' + where +
            ' GROUP BY ctx ORDER BY ctx', params
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT CASE WHEN ctx = 'states.name' THEN 'states' "
            "WHEN ctx LIKE 'terms.%' THEN 'terms' ELSE 'enemies' END AS g, "
            "COUNT(*) AS n FROM entries WHERE " + where +
            " GROUP BY g ORDER BY CASE g WHEN 'states' THEN 0 WHEN 'terms' THEN 1 ELSE 2 END",
            params
        ).fetchall()
    return [{
        'id': r['g'],
        'label': _browse_group_label(dim, r['g']),
        'section': _browse_group_section(dim, r['g']),
        'count': r['n'],
    } for r in rows]


def _browse_snippet(text, limit=160):
    text = clean_for_display(text)
    if len(text) > limit:
        return text[:limit] + '…'
    return text


def browse(dim='maps', group='', offset=0, limit=50):
    if dim not in BROWSE_DIM_LABELS:
        raise ValueError('invalid browse dimension')
    offset = max(0, int(offset))
    limit = min(max(1, int(limit)), 200)
    con = connect()
    try:
        init_db(con)
        categories = _browse_categories(con)
        if not group:
            groups = _browse_groups(con, dim)
            return {
                'dim': dim,
                'label': BROWSE_DIM_LABELS[dim],
                'categories': categories,
                'groups': groups,
                'entry_count': sum(g['count'] for g in groups),
            }

        where, params = _browse_group_filter(dim, group)
        total = con.execute(
            'SELECT COUNT(*) AS n FROM entries WHERE ' + where, params
        ).fetchone()['n']
        rows = con.execute(
            'SELECT file, block, ctx, msgid, msgstr FROM entries WHERE ' + where +
            ' ORDER BY file, block LIMIT ? OFFSET ?', params + [limit, offset]
        ).fetchall()
        items = [{
            'file': r['file'],
            'block': r['block'],
            'ctx': r['ctx'] or '',
            'source': _browse_snippet(r['msgid']),
            'translation': _browse_snippet(r['msgstr']),
        } for r in rows]
        return {
            'dim': dim,
            'label': BROWSE_DIM_LABELS[dim],
            'group': group,
            'group_label': _browse_group_label(dim, group),
            'categories': categories,
            'total': total,
            'offset': offset,
            'limit': limit,
            'items': items,
        }
    finally:
        con.close()


def get_entry(file_name, block):
    con = connect()
    try:
        init_db(con)
        r = con.execute(
            'SELECT * FROM entries WHERE file = ? AND block = ?', (file_name, int(block))
        ).fetchone()
        if not r:
            raise FileNotFoundError('entry not found')
        return {
            'file': r['file'],
            'block': r['block'],
            'ctx': r['ctx'] or '',
            'msgid': r['msgid'],
            'msgstr': r['msgstr'],
            'comments': (r['comment'] or '').split('\n') if r['comment'] else [],
        }
    finally:
        con.close()


def save_entry(file_name, block, new_msgstr):
    path = safe_file_path(file_name)
    old_text = open(path, encoding='utf-8-sig', errors='replace').read()
    entries, parts = parse_entries(old_text)
    target = next((e for e in entries if e['seq'] == int(block)), None)
    if target is None:
        raise FileNotFoundError('entry not found')
    if target['msgstr'] == new_msgstr:
        return get_entry(file_name, block)

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = time.strftime('%Y%m%d_%H%M%S')
    backup = os.path.join(BACKUP_DIR, '%s_%s' % (stamp, file_name))
    shutil.copy2(path, backup)

    chunk = parts[target['part_index']]
    m = re.search(r'(?m)^msgstr ("(?:.*)(?:\n"(?:.*))*")', chunk)
    if not m:
        raise ValueError('msgstr block not found')
    chunk = chunk[:m.start()] + format_msgstr(new_msgstr.split('\n')) + chunk[m.end():]
    parts[target['part_index']] = chunk
    with open(path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(''.join(parts))

    con = connect()
    try:
        init_db(con)
        con.execute(
            'UPDATE entries SET msgstr = ?, cn_norm = ? WHERE file = ? AND block = ?',
            (new_msgstr, normalize_search(new_msgstr), file_name, int(block))
        )
        con.commit()
        con.execute("INSERT INTO entries_fts(entries_fts) VALUES('rebuild')")
        con.commit()
    finally:
        con.close()
    return get_entry(file_name, block)


def status():
    con = connect()
    try:
        init_db(con)
        n = con.execute('SELECT COUNT(*) AS n FROM entries').fetchone()['n']
        files = con.execute('SELECT COUNT(DISTINCT file) AS n FROM entries').fetchone()['n']
    finally:
        con.close()
    return {
        'entries': n,
        'files': files,
        'lang_dir': LANG_DIR,
        'backup_dir': BACKUP_DIR,
    }
