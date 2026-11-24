import hashlib
import json
import os
import threading
import time

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
WHITELIST_PATH = os.environ.get(
    'RYONA_WHITELIST', os.path.join(TOOL_DIR, 'qa_whitelist.json'))

_LOCK = threading.RLock()


def issue_id(file_name, block, code, line, msgid, msgstr):
    raw = '\0'.join((
        file_name or '',
        str(int(block)),
        code or '',
        str(int(line or 0)),
        msgid or '',
        msgstr or '',
    ))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]


def _read():
    if not os.path.exists(WHITELIST_PATH):
        return []
    with open(WHITELIST_PATH, encoding='utf-8') as f:
        data = json.load(f)
    entries = data.get('entries', []) if isinstance(data, dict) else []
    return [x for x in entries if isinstance(x, dict) and x.get('id')]


def _write(entries):
    os.makedirs(os.path.dirname(WHITELIST_PATH) or '.', exist_ok=True)
    tmp = WHITELIST_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'version': 1, 'entries': entries}, f,
                  ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, WHITELIST_PATH)


def cache_key():
    try:
        st = os.stat(WHITELIST_PATH)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return (0, 0)


def entries():
    with _LOCK:
        return _read()


def ids():
    return {x['id'] for x in entries()}


def add(issue, note=''):
    with _LOCK:
        current = _read()
        by_id = {x['id']: x for x in current}
        item = {
            'id': issue['id'],
            'file': issue.get('file', ''),
            'block': issue.get('block', 0),
            'code': issue.get('code', ''),
            'line': issue.get('line', 0),
            'severity': issue.get('severity', ''),
            'label': issue.get('label', ''),
            'message': issue.get('message', ''),
            'note': note or '',
            'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }
        by_id[item['id']] = item
        result = list(by_id.values())
        result.sort(key=lambda x: (x.get('file', ''), x.get('block', 0),
                                   x.get('line', 0), x.get('code', '')))
        _write(result)
        return result


def remove(entry_id):
    with _LOCK:
        current = _read()
        result = [x for x in current if x.get('id') != entry_id]
        if len(result) != len(current):
            _write(result)
        return result
