import argparse
import json
import sys

import layout
import po_store
import qa_store
import validators


def _dump(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _short(text, limit=160):
    text = po_store.clean_for_display(text)
    if len(text) > limit:
        return text[:limit] + '…'
    return text


def _entry_json(file_name, block):
    entry = po_store.get_entry(file_name, block)
    check = validators.validate(entry['msgid'], entry['msgstr'], entry['ctx'])
    issues = check['issues'] + layout.check_entry(entry['msgid'], entry['msgstr'])
    return {
        **entry,
        'issues': issues,
        'metrics': check['metrics'],
        'pages': check['pages'],
    }


def cmd_status(args):
    data = po_store.status()
    if args.qa:
        data['qa'] = qa_store.get_issues(limit=0)['summary']
    if args.json:
        _dump(data)
    else:
        print(f"entries: {data['entries']}")
        print(f"files:   {data['files']}")
        print(f"lang:    {data['lang_dir']}")
        if args.qa:
            q = data['qa']
            print(f"qa:      scanned {q['scanned']}, findings {q['total']}, "
                  f"entries {q['entries']}")
    return 0


def cmd_search(args):
    data = po_store.search(args.query, args.mode, args.limit)
    if args.json:
        _dump(data)
        return 0
    print(f"total: {data['total']}")
    for item in data['items']:
        ctx = item['ctx'] or '事件消息'
        print(f"{item['file']}#{item['block']} [{ctx}]")
        print(f"  原文: {_short(item['msgid'])}")
        print(f"  译文: {_short(item['msgstr'])}")
    return 0


def cmd_browse(args):
    data = po_store.browse(args.dim, args.group or '', args.offset, args.limit)
    if args.json:
        _dump(data)
        return 0
    if not args.group:
        print(f"{data['label']}: {len(data['groups'])} 个分组 · "
              f"{data['entry_count']:,} 条")
        for group in data['groups']:
            section = f"[{group['section']}] " if group['section'] else ''
            print(f"{section}{group['label']}  {group['count']:,}")
        return 0
    print(f"{data['label']} / {data['group_label']} · {data['total']:,} 条")
    for item in data['items']:
        ctx = item['ctx'] or '事件消息'
        print(f"{item['file']}#{item['block']} [{ctx}]")
        print(f"  原文: {_short(item['source'])}")
        print(f"  译文: {_short(item['translation'])}")
    return 0


def cmd_entry(args):
    data = _entry_json(args.file, args.block)
    if args.json:
        _dump(data)
        return 0
    print(f"{data['file']}#{data['block']} [{data['ctx'] or '事件消息'}]")
    print('原文:')
    print(data['msgid'])
    print('译文:')
    print(data['msgstr'])
    print(f"页面: {data['pages']}")
    if not data['issues']:
        print('校验: 未发现问题')
    else:
        for issue in data['issues']:
            print(f"[{issue['severity']}] {issue['code']}: {issue['message']}")
    return 0


def cmd_check(args):
    data = _entry_json(args.file, args.block)
    if args.json:
        _dump(data['issues'])
    elif not data['issues']:
        print('未发现问题')
    else:
        for issue in data['issues']:
            print(f"[{issue['severity']}] {issue['code']}: {issue['message']}")
    return 1 if any(x['severity'] == 'error' for x in data['issues']) else 0


def cmd_issues(args):
    data = qa_store.get_issues(
        args.severity or '', args.code or '', args.offset, args.limit, args.refresh)
    if args.json:
        _dump(data)
        return 0
    summary = data['summary']
    print(f"scan: {summary['scanned']:,} entries · "
          f"{summary['entries']:,} with findings · "
          f"errors {summary['by_severity']['error']} / "
          f"warnings {summary['by_severity']['warning']} / "
          f"info {summary['by_severity']['info']}")
    print(f"selected: {data['total']:,}")
    for item in data['items']:
        ctx = item['ctx'] or '事件消息'
        print(f"[{item['severity']}] {item['file']}#{item['block']} [{ctx}] "
              f"{item['code']}: {item['message']}")
    return 0


def cmd_layout(args):
    findings = layout.scan(args.kind)
    if args.limit:
        findings = findings[:args.limit]
    if args.json:
        _dump({'count': len(findings), 'items': findings})
        return 0
    print(f"layout findings: {len(findings)}")
    for item in findings:
        print(f"[{item['kind']}] {item['file']}#{item['block']}")
        print(f"  原文: {_short(item['source'])}")
        print(f"  译文: {_short(item['translation'])}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog='ryona-localizer',
        description='RyonaRPG 中文翻译本地工具的脚本接口。默认输出人类可读文本，'
                    '使用 --json 输出稳定 JSON。',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('status', help='显示索引和语言目录状态')
    p.add_argument('--qa', action='store_true', help='同时扫描 QA 摘要')
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_status)

    p = sub.add_parser('search', help='全库搜索中日文原文或译文')
    p.add_argument('query')
    p.add_argument('--mode', choices=('both', 'jp', 'cn'), default='both')
    p.add_argument('--limit', type=int, default=20)
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_search)

    p = sub.add_parser('browse', help='按分类浏览条目')
    p.add_argument('dim', choices=tuple(key for key, _ in po_store.BROWSE_DIMS))
    p.add_argument('--group', help='分组 id，省略时列出分组')
    p.add_argument('--offset', type=int, default=0)
    p.add_argument('--limit', type=int, default=50)
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_browse)

    p = sub.add_parser('entry', help='读取单条原文、译文和校验结果')
    p.add_argument('file')
    p.add_argument('block', type=int)
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_entry)

    p = sub.add_parser('check', help='校验指定条目；有 error 时退出码为 1')
    p.add_argument('file')
    p.add_argument('block', type=int)
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_check)

    p = sub.add_parser('issues', help='读取全库 QA 问题和筛选结果')
    p.add_argument('--severity', choices=('error', 'warning', 'info'))
    p.add_argument('--code')
    p.add_argument('--offset', type=int, default=0)
    p.add_argument('--limit', type=int, default=50)
    p.add_argument('--refresh', action='store_true', help='强制重新扫描')
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_issues)

    p = sub.add_parser('layout', help='检查源文换行结构与译文不一致的候选条目')
    p.add_argument('--kind', choices=('all', 'danger_label', 'class_fields',
                                      'bullet_lines', 'field_lines',
                                      'control_lines', 'bracket_title'),
                   default='all')
    p.add_argument('--limit', type=int, default=0)
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_layout)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
