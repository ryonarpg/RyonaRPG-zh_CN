import re

import po_store

BRACKET_TITLE = re.compile(r'^[\[［].*[\]］]$')
DANGER_LABEL = re.compile(r'^危険度')


def _lines(text):
    return [line for line in text.split('\n') if line.strip()]


def _classify(mid, tr):
    src = _lines(mid)
    dst = _lines(tr)
    if len(src) <= len(dst):
        return None
    if not BRACKET_TITLE.match(src[0].strip()):
        return None
    if len(src) > 1 and DANGER_LABEL.match(src[1].strip()):
        return 'danger_label'
    return 'bracket_title'


def check_entry(mid, tr):
    if _classify(mid, tr) != 'danger_label':
        return []
    return [{
        'severity': 'warning',
        'code': 'layout_merge_danger',
        'message': '原文的标题与危险度分成两行，译文被合并为一行',
        'line': 0,
    }]


def scan(kind='all'):
    con = po_store.connect()
    try:
        po_store.init_db(con)
        rows = con.execute(
            'SELECT file, block, ctx, msgid, msgstr FROM entries ORDER BY file, block'
        ).fetchall()
    finally:
        con.close()

    findings = []
    for row in rows:
        found = _classify(row['msgid'], row['msgstr'])
        if not found:
            continue
        if kind != 'all' and found != kind:
            continue
        findings.append({
            'file': row['file'],
            'block': row['block'],
            'ctx': row['ctx'] or '',
            'kind': found,
            'source': row['msgid'],
            'translation': row['msgstr'],
        })
    return findings
