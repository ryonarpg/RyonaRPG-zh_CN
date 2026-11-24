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
