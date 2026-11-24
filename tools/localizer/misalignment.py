import gzip
import json
import os
import re
from pathlib import Path

import po_store

DEFAULT_REFERENCE = Path(__file__).resolve().parents[1] / 'qa' / 'tm_reference.json.gz'
REFERENCE_ENV = 'RYONA_TM_REFERENCE'

CJK = re.compile(r'[\u4e00-\u9fff]')
CODE = re.compile(
    r'\\[nN]\[\\[vV]\[\d+\]\]|\\[nN]\[\d+\]|\\[A-Za-z]+\[\d+\]|'
    r'\\[\\|.!<>^]|\\[A-Za-z]|\$[A-Za-z]'
)

SELF_MAX = 0.45
NEIGHBOR_MIN = 0.45
MARGIN_MIN = 0.18
CUR_MIN_CHARS = 4
NEIGHBOR_MIN_CHARS = 6
RUN_MAX_GAP = 2
RUN_MIN = 3


def normalize_key(s):
    s = s.strip()
    s = re.sub(r'^[＊*>＞\s]+', '', s)
    s = re.sub(r'^【[^】]*】', '', s)
    s = CODE.sub('', s)
    s = re.sub(r'[\s\u3000]+', '', s)
    return s


def is_label(line):
    s = line.strip()
    if not s:
        return True
    if s in ('＊', '*', '\\>＊', '\\>*', 'クリア', '\\>クリア', '？？？', '\\>？？？'):
        return True
    if s.startswith('【') and s.endswith('】'):
        return True
    return False


def cn_chars(s):
    return set(CJK.findall(s))


def dice(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return 2.0 * len(a & b) / (len(a) + len(b))


def load_reference(path=None):
    path = path or os.environ.get(REFERENCE_ENV) or DEFAULT_REFERENCE
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    entries = data.get('entries', data) if isinstance(data, dict) else {}
    if not isinstance(entries, dict):
        raise ValueError('invalid TM reference: entries must be an object')
    return {k: v for k, v in entries.items() if isinstance(v, str)}


def tm_text(msgid, reference):
    parts = []
    for line in msgid.split('\n'):
        if is_label(line):
            continue
        key = normalize_key(line)
        if key in reference:
            parts.append(reference[key])
    return ''.join(parts)


def score_sequence(entries, reference):
    texts = [tm_text(e['msgid'], reference) for e in entries]
    chars = [cn_chars(t) for t in texts]
    scores = []
    for i, entry in enumerate(entries):
        dst = cn_chars(entry['msgstr'])
        prev = chars[i - 1] if i > 0 else set()
        nxt = chars[i + 1] if i + 1 < len(entries) else set()
        scores.append({
            'idx': i,
            'seq': entry['seq'],
            'entry': entry,
            'tm': texts[i],
            'self': dice(dst, chars[i]),
            'prev': dice(dst, prev),
            'next': dice(dst, nxt),
            'cur_n': len(chars[i]),
            'prev_n': len(prev),
            'next_n': len(nxt),
        })
    return scores


def find_flags(scores):
    flags = []
    for i, x in enumerate(scores):
        if x['cur_n'] < CUR_MIN_CHARS or x['self'] > SELF_MAX:
            continue
        if x['prev'] >= x['next']:
            direction = 'prev'
            best = x['prev']
            neighbor_n = x['prev_n']
        else:
            direction = 'next'
            best = x['next']
            neighbor_n = x['next_n']
        if neighbor_n < NEIGHBOR_MIN_CHARS:
            continue
        margin = best - x['self']
        if best < NEIGHBOR_MIN or margin < MARGIN_MIN:
            continue
        entry = x['entry']
        flags.append({
            'idx': i,
            'file': '',
            'block': x['seq'],
            'direction': direction,
            'margin': round(margin, 4),
            'self': round(x['self'], 4),
            'best': round(best, 4),
            'source': entry['msgid'],
            'translation': entry['msgstr'],
            'tm': x['tm'],
        })
    return flags


def group_runs(flags):
    runs = []
    run = []
    for flag in flags:
        if run and flag['idx'] - run[-1]['idx'] <= RUN_MAX_GAP + 1 and flag['direction'] == run[-1]['direction']:
            run.append(flag)
        else:
            if len(run) >= 2:
                runs.append(run)
            run = [flag]
    if len(run) >= 2:
        runs.append(run)
    return runs


def scan_file(path, reference):
    text = open(path, encoding='utf-8-sig', errors='replace').read()
    entries, _ = po_store.parse_entries(text)
    file_name = os.path.basename(path)
    flags = find_flags(score_sequence(entries, reference))
    for flag in flags:
        flag['file'] = file_name
    return {
        'file': file_name,
        'entries': len(entries),
        'flags': flags,
        'runs': group_runs(flags),
    }


def scan(paths=None, reference_path=None):
    if paths is None:
        paths = po_store.po_files()
    elif isinstance(paths, (str, os.PathLike)):
        paths = [paths]
    try:
        reference = load_reference(reference_path)
    except FileNotFoundError as exc:
        return {
            'skipped': True,
            'reason': 'TM reference not found: %s' % exc.filename,
            'summary': {
                'files_scanned': 0, 'files_with_flags': 0,
                'flags': 0, 'runs': 0, 'singles': 0,
            },
            'files': [], 'runs': [], 'singles': [],
        }

    files = []
    for path in paths:
        result = scan_file(path, reference)
        if result['flags']:
            files.append(result)

    runs = []
    short_runs = []
    singles = []
    for result in files:
        run_idx = set()
        for run in result['runs']:
            run_idx.update(x['idx'] for x in run)
            item = {
                'file': result['file'],
                'start_block': run[0]['block'],
                'end_block': run[-1]['block'],
                'direction': run[0]['direction'],
                'count': len(run),
                'flags': run,
            }
            if len(run) >= RUN_MIN:
                item['severity'] = 'error'
                runs.append(item)
            else:
                item['severity'] = 'warning'
                short_runs.append(item)
        for flag in result['flags']:
            if flag['idx'] not in run_idx:
                singles.append(flag)

    return {
        'skipped': False,
        'reference': str(reference_path or os.environ.get(REFERENCE_ENV) or DEFAULT_REFERENCE),
        'summary': {
            'files_scanned': len(paths),
            'files_with_flags': len(files),
            'flags': sum(len(x['flags']) for x in files),
            'runs': len(runs),
            'short_runs': len(short_runs),
            'singles': len(singles),
        },
        'files': files,
        'runs': runs,
        'short_runs': short_runs,
        'singles': singles,
    }
