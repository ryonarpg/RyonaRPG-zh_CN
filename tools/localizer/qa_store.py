import os
import threading

import po_store
import layout
import validators

SEVERITY_ORDER = {'error': 0, 'warning': 1, 'info': 2}
ISSUE_LABELS = {
    'empty': '空译',
    'width_error': '行宽超过 50',
    'width_warn': '行宽 47–50',
    'line_start_punct': '行首标点',
    'line_start_ellipsis': '行首省略号',
    'line_end_open': '行尾开引号/括号',
    'unclosed_code': '控制符未闭合',
    'split_code': '控制符跨行',
    'dup_punct': '重复标点',
    'curly_quote': '弯引号',
    'exfont_split': 'ExFont 拆分',
    'kana': '残留假名',
    'extra_code': '多余控制符',
    'missing_actor_code': '角色名控制符丢失',
    'actor_code_literal': '角色编号未转义',
    'actor_code_misplaced': '角色名控制符错位',
    'unbound_var': '变量控制符未绑定',
    'layout_merge_danger': '标题与危险度未分行',
    'layout_merge_class': '职业字段未分行',
    'layout_merge_bullet': '项目符号分行丢失',
    'layout_merge_field': '字段标签与说明未分行',
    'layout_merge_control': '控制符行结构不一致',
}

_LOCK = threading.Lock()
_CACHE = None
_CACHE_KEY = None


def _cache_key():
    try:
        st = os.stat(po_store.DB_PATH)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def _snippet(text, limit=150):
    text = po_store.clean_for_display(text)
    if len(text) > limit:
        return text[:limit] + '…'
    return text


def _sort_issues(issues):
    issues.sort(key=lambda x: (
        SEVERITY_ORDER.get(x['severity'], 9),
        x['file'],
        x['block'],
        x['line'],
        x['code'],
    ))


def _summary(issues, scanned):
    by_severity = {'error': 0, 'warning': 0, 'info': 0}
    by_code = {}
    entries = set()
    for issue in issues:
        by_severity[issue['severity']] = by_severity.get(issue['severity'], 0) + 1
        entries.add((issue['file'], issue['block']))
        code = issue['code']
        if code not in by_code:
            by_code[code] = {
                'code': code,
                'label': ISSUE_LABELS.get(code, code),
                'severity': issue['severity'],
                'count': 0,
            }
        by_code[code]['count'] += 1
    codes = sorted(
        by_code.values(),
        key=lambda x: (SEVERITY_ORDER.get(x['severity'], 9), -x['count'], x['code']),
    )
    return {
        'total': len(issues),
        'entries': len(entries),
        'scanned': scanned,
        'by_severity': by_severity,
        'by_code': codes,
    }


def _entry_issues(row):
    result = validators.validate(row['msgid'], row['msgstr'], row['ctx'] or '')
    result['issues'].extend(layout.check_entry(row['msgid'], row['msgstr']))
    source = _snippet(row['msgid'])
    translation = _snippet(row['msgstr'])
    out = []
    for issue in result['issues']:
        out.append({
            'file': row['file'],
            'block': row['block'],
            'ctx': row['ctx'] or '',
            'severity': issue['severity'],
            'code': issue['code'],
            'label': ISSUE_LABELS.get(issue['code'], issue['code']),
            'message': issue['message'],
            'line': issue['line'],
            'source': source,
            'translation': translation,
        })
    return out


def _build():
    con = po_store.connect()
    try:
        po_store.init_db(con)
        rows = con.execute(
            'SELECT file, block, ctx, msgid, msgstr FROM entries ORDER BY file, block'
        ).fetchall()
    finally:
        con.close()

    issues = []
    for row in rows:
        issues.extend(_entry_issues(row))
    _sort_issues(issues)
    return {
        'issues': issues,
        'summary': _summary(issues, len(rows)),
    }


def ensure(force=False):
    global _CACHE, _CACHE_KEY
    key = _cache_key()
    with _LOCK:
        if force or _CACHE is None or _CACHE_KEY != key:
            _CACHE = _build()
            _CACHE_KEY = key
        return _CACHE


def invalidate():
    global _CACHE, _CACHE_KEY
    with _LOCK:
        _CACHE = None
        _CACHE_KEY = None


def refresh_entry(file_name, block):
    global _CACHE
    with _LOCK:
        if _CACHE is None:
            return
    con = po_store.connect()
    try:
        po_store.init_db(con)
        row = con.execute(
            'SELECT file, block, ctx, msgid, msgstr FROM entries '
            'WHERE file = ? AND block = ?', (file_name, int(block))
        ).fetchone()
    finally:
        con.close()
    with _LOCK:
        if _CACHE is None:
            return
        issues = [
            x for x in _CACHE['issues']
            if not (x['file'] == file_name and x['block'] == int(block))
        ]
        if row:
            issues.extend(_entry_issues(row))
        _sort_issues(issues)
        scanned = _CACHE['summary']['scanned']
        _CACHE = {'issues': issues, 'summary': _summary(issues, scanned)}
        _CACHE_KEY = _cache_key()


def get_issues(severity='', code='', offset=0, limit=50, force=False):
    severity = (severity or '').strip()
    code = (code or '').strip()
    if severity and severity not in SEVERITY_ORDER:
        raise ValueError('invalid severity')
    if code and code not in ISSUE_LABELS:
        raise ValueError('invalid issue code')
    offset = max(0, int(offset))
    limit = min(max(0, int(limit)), 200)

    cache = ensure(force=force)
    issues = cache['issues']
    if severity:
        issues = [x for x in issues if x['severity'] == severity]
    if code:
        issues = [x for x in issues if x['code'] == code]
    total = len(issues)
    items = issues[offset:offset + limit] if limit else []
    return {
        'summary': cache['summary'],
        'severity': severity,
        'code': code,
        'total': total,
        'offset': offset,
        'limit': limit,
        'items': items,
    }
