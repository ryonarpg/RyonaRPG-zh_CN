import os

from flask import Flask, jsonify, render_template, request

import layout
import po_store
import preview
import qa_store
import validators

app = Flask(__name__)
app.json.ensure_ascii = False


def entry_payload(file_name, block):
    entry = po_store.get_entry(file_name, block)
    check = validators.validate(entry['msgid'], entry['msgstr'], entry['ctx'])
    issues = check['issues'] + layout.check_entry(entry['msgid'], entry['msgstr'])
    return {
        **entry,
        'issues': issues,
        'metrics': check['metrics'],
        'pages': check['pages'],
        'display_msgstr': po_store.clean_for_display(entry['msgstr']),
        'source_preview': preview.render(entry['msgid']),
        'preview': preview.render(entry['msgstr']),
    }


@app.get('/')
def index():
    return render_template('index.html')


@app.get('/api/status')
def api_status():
    return jsonify(po_store.status())


@app.get('/api/search')
def api_search():
    q = request.args.get('q', '')
    mode = request.args.get('mode', 'both')
    try:
        return jsonify(po_store.search(q, mode))
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.get('/api/browse')
def api_browse():
    dim = request.args.get('dim', 'maps')
    group = request.args.get('group', '')
    try:
        offset = int(request.args.get('offset', '0'))
        limit = int(request.args.get('limit', '50'))
    except ValueError:
        return jsonify({'error': 'invalid offset or limit'}), 400
    try:
        return jsonify(po_store.browse(dim, group, offset, limit))
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.get('/api/issues')
def api_issues():
    severity = request.args.get('severity', '')
    code = request.args.get('code', '')
    force = request.args.get('refresh') == '1'
    try:
        offset = int(request.args.get('offset', '0'))
        limit = int(request.args.get('limit', '50'))
    except ValueError:
        return jsonify({'error': 'invalid offset or limit'}), 400
    try:
        return jsonify(qa_store.get_issues(severity, code, offset, limit, force))
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.get('/api/entry')
def api_entry():
    file_name = request.args.get('file', '')
    block = request.args.get('block', '0')
    try:
        return jsonify(entry_payload(file_name, int(block)))
    except Exception as exc:
        return jsonify({'error': str(exc)}), 404


@app.post('/api/check')
def api_check():
    data = request.get_json(force=True)
    mid = data.get('msgid', '')
    tr = data.get('msgstr', '')
    ctx = data.get('ctx', '')
    check = validators.validate(mid, tr, ctx)
    issues = check['issues'] + layout.check_entry(mid, tr)
    return jsonify({**check, 'issues': issues, 'preview': preview.render(tr)})


@app.post('/api/save')
def api_save():
    data = request.get_json(force=True)
    file_name = data.get('file', '')
    block = int(data.get('block', 0))
    tr = data.get('msgstr', '')
    mid = data.get('msgid', '')
    try:
        ctx = po_store.get_entry(file_name, block)['ctx']
    except Exception:
        ctx = ''
    check = validators.validate(mid, tr, ctx)
    errors = [x for x in check['issues'] if x['severity'] == 'error']
    if errors:
        return jsonify({'error': '存在错误，未保存', 'issues': check['issues']}), 400
    try:
        po_store.save_entry(file_name, block, tr)
        qa_store.refresh_entry(file_name, block)
        return jsonify(entry_payload(file_name, block))
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.post('/api/reindex')
def api_reindex():
    try:
        n = po_store.rebuild_index()
        qa_store.invalidate()
        return jsonify({'ok': True, 'entries': n})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


if __name__ == '__main__':
    po_store.ensure_index()
    port = int(os.environ.get('RYONA_PORT', '5010'))
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
