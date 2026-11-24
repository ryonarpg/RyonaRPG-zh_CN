import re
import unicodedata

TOKEN = re.compile(
    r'\\[nN]\[\\[vV]\[\d+\]\]|\\[nN]\[\d+\]|\[\\[vV]\[\d+\]\]|'
    r'\\[A-Za-z]+\[\d+\]|\\[\\|.!<>^]|\\[A-Za-z]|\$[A-Za-z]'
)
BAD_START = set('，。、；：」』）】…')
BAD_END = set('「『（【')
KANA = re.compile(r'[\u3040-\u30ff]')
LITERAL_ACTOR = re.compile(r'\[(?:10[0-9]|1[1-9][0-9]|20[0-9])\]')


def literal_actor_ids(text):
    out = []
    for m in LITERAL_ACTOR.finditer(text):
        i = m.start()
        if i >= 2 and text[i - 2] == '\\' and text[i - 1].isalpha():
            continue
        out.append(m.group(0))
    return out



def token_width(tok):
    if tok[0] == '$':
        return 2
    if tok[0] == '\\':
        return 0
    if tok[0] == '[':
        return 2
    return 2 if unicodedata.east_asian_width(tok[0]) in ('W', 'F') else 1


def cells(s):
    n = 0
    i = 0
    while i < len(s):
        m = TOKEN.match(s, i)
        if m:
            n += token_width(m.group(0))
            i = m.end()
            continue
        n += 2 if unicodedata.east_asian_width(s[i]) in ('W', 'F') else 1
        i += 1
    return n


def code_tokens(s):
    return TOKEN.findall(s)


def validate(mid, tr, ctx=''):
    issues = []
    metrics = []

    def add(severity, code, message, line=0):
        issues.append({
            'severity': severity,
            'code': code,
            'message': message,
            'line': line,
        })

    if not tr.strip():
        add('error', 'empty', '译文为空', 0)
        return {'issues': issues, 'metrics': metrics, 'pages': 1, 'lines': []}

    lines = tr.split('\n')
    for i, line in enumerate(lines, 1):
        c = cells(line)
        metrics.append({'line': i, 'cells': c, 'text': line})
        st = line.strip()
        if not st:
            continue
        if c > 50:
            add('error', 'width_error', '第 %d 行 %d 单元，超过 50 上限' % (i, c), i)
        elif c > 46:
            add('warning', 'width_warn', '第 %d 行 %d 单元，超过 46 建议值（仍在 50 内）' % (i, c), i)
        if len(st) > 1 and st[0] in BAD_START:
            if st[0] == '…':
                add('info', 'line_start_ellipsis', '第 %d 行以省略号开头' % i, i)
            elif not (ctx == 'actors.name' and st[0] == '、'):
                add('error', 'line_start_punct', '第 %d 行以标点开头：%s' % (i, st[0]), i)
        if st and st[-1] in BAD_END:
            add('error', 'line_end_open', '第 %d 行以开引号/括号结尾：%s' % (i, st[-1]), i)
        if re.search(r'\\[A-Za-z]+\[[^\]\n]*$', line):
            add('error', 'unclosed_code', '第 %d 行控制符未闭合：%s' % (i, line[-24:]), i)
        if i < len(lines) and (
            line.endswith('\\') or re.search(r'\\[A-Za-z]+$', line)
        ) and lines[i].lstrip().startswith('['):
            add('error', 'split_code', '第 %d 行控制符跨行断开，下一行以 [ 开头' % i, i)
    if '。。' in tr or '，，' in tr:
        add('warning', 'dup_punct', '存在重复标点 。。 或 ，，', 0)
    if '“' in tr or '”' in tr:
        add('warning', 'curly_quote', '建议将弯引号统一为「」', 0)
    if re.search(r'(?<!\\)\$(?:\n|[ 　]+)[A-Za-z]', tr):
        add('error', 'exfont_split', 'ExFont 控制符 $x 被换行/空格拆开', 0)
    if KANA.search(tr):
        add('warning', 'kana', '译文含日文假名，请确认是否为有意保留', 0)

    src_codes = code_tokens(mid)
    dst_codes = code_tokens(tr)
    src_set = set(src_codes)
    for code in sorted(set(dst_codes) - src_set):
        add('warning', 'extra_code', '译文出现源文没有的控制符：%s' % code, 0)
    if any(code.startswith('\\n[') for code in src_codes) and not any(
            code.startswith('\\n[') for code in dst_codes):
        add('warning', 'missing_actor_code', '源文含角色名控制符 \\n[...]，译文未保留', 0)
    src_literals = set(literal_actor_ids(mid))
    for literal in sorted(set(literal_actor_ids(tr)) - src_literals):
        add('warning', 'actor_code_literal', '译文含未转义的角色名/文字列编号：%s' % literal, 0)
    if re.search(r'\\[nN](?!\[)', tr) and re.search(r'\[\\[vV]\[', tr):
        add('warning', 'actor_code_misplaced', '可能有角色名控制符错位：\\n/\\N 后未接 [...]，而后面出现 [\\v...]', 0)
    if re.search(r'(?<!\\n)(?<!\\N)\[\\[vV]\[', tr):
        add('warning', 'unbound_var', '存在未绑定到 \\n/\\N 的 [\\v...] 字面文本，可能显示为 [62]', 0)

    pages = max(1, (len(lines) + 3) // 4)
    return {'issues': issues, 'metrics': metrics, 'pages': pages, 'lines': lines}
