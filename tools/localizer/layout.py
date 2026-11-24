import re

import po_store

BRACKET_TITLE = re.compile(r'^[\[［].*[\]］]$')
DANGER_LABEL = re.compile(r'^危険度')
BULLET_LINE = re.compile(r'^[・※](?!・)')
FIELD_LINE = re.compile(r'^[A-Za-z][A-Za-z0-9 _-]*\s*:')


def _lines(text):
    return [line for line in text.split('\n') if line.strip()]


def _is_field_lines(src, dst):
    src_fields = sum(bool(FIELD_LINE.match(line.strip())) for line in src)
    dst_fields = sum(bool(FIELD_LINE.match(line.strip())) for line in dst)
    return src_fields > dst_fields or (src_fields and len(src) > len(dst))


def _is_bullet_lines(src, dst):
    src_bullets = sum(bool(BULLET_LINE.match(line.strip())) for line in src)
    dst_bullets = sum(bool(BULLET_LINE.match(line.strip())) for line in dst)
    return src_bullets >= 2 and dst_bullets < src_bullets


def _is_class_fields(src):
    lines = [line.strip() for line in src]
    return (
        any(line.startswith('Class:') for line in lines) and
        any(line.startswith('Name ') for line in lines) and
        any(line.startswith('Type ') for line in lines)
    )


def _is_control_lines(src, dst):
    src_lines = [line.strip() for line in src]
    dst_lines = [line.strip() for line in dst]
    if not any(line == r'\>' for line in src_lines):
        return False
    return (
        sum(line.startswith(r'\>') for line in src_lines) >
        sum(line.startswith(r'\>') for line in dst_lines)
    )


def _classify(mid, tr):
    src = _lines(mid)
    dst = _lines(tr)
    if len(src) > len(dst) and _is_class_fields(src):
        return 'class_fields'
    if _is_bullet_lines(src, dst):
        return 'bullet_lines'
    if len(src) > len(dst) and _is_field_lines(src, dst):
        return 'field_lines'
    if len(src) > len(dst) and _is_control_lines(src, dst):
        return 'control_lines'
    if len(src) <= len(dst):
        return None
    if not BRACKET_TITLE.match(src[0].strip()):
        return None
    if len(src) > 1 and DANGER_LABEL.match(src[1].strip()):
        return 'danger_label'
    return 'bracket_title'


def check_entry(mid, tr):
    kind = _classify(mid, tr)
    if kind == 'danger_label':
        return [{
            'severity': 'warning',
            'code': 'layout_merge_danger',
            'message': '原文的标题与危险度分成两行，译文被合并为一行',
            'line': 0,
        }]
    if kind == 'class_fields':
        return [{
            'severity': 'warning',
            'code': 'layout_merge_class',
            'message': '原文的 Name/Class/Type 字段分行，译文被合并为一行',
            'line': 0,
        }]
    if kind == 'bullet_lines':
        return [{
            'severity': 'warning',
            'code': 'layout_merge_bullet',
            'message': '原文的多条项目符号分行，译文被合并或丢失项目符号',
            'line': 0,
        }]
    if kind == 'field_lines':
        return [{
            'severity': 'warning',
            'code': 'layout_merge_field',
            'message': '原文的字段标签与说明分行，译文被合并为一行',
            'line': 0,
        }]
    return []


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
