import os

from flask import Flask, jsonify, render_template, request

import po_store
import preview
import validators

app = Flask(__name__)
app.json.ensure_ascii = False


def entry_payload(file_name, block):
    entry = po_store.get_entry(file_name, block)
    check = validators.validate(entry['msgid'], entry['msgstr'])
    return {
        **entry,
        'issues': check['issues'],
        'metrics': check['metrics'],
        'pages': check['pages'],
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
    check = validators.validate(mid, tr)
    return jsonify({**check, 'preview': preview.render(tr)})


@app.post('/api/save')
def api_save():
    data = request.get_json(force=True)
    file_name = data.get('file', '')
    block = int(data.get('block', 0))
    tr = data.get('msgstr', '')
    mid = data.get('msgid', '')
    check = validators.validate(mid, tr)
    errors = [x for x in check['issues'] if x['severity'] == 'error']
    if errors:
        return jsonify({'error': '存在错误，未保存', 'issues': check['issues']}), 400
    try:
        po_store.save_entry(file_name, block, tr)
        return jsonify(entry_payload(file_name, block))
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.post('/api/reindex')
def api_reindex():
    try:
        n = po_store.rebuild_index()
        return jsonify({'ok': True, 'entries': n})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


if __name__ == '__main__':
    po_store.ensure_index()
    port = int(os.environ.get('RYONA_PORT', '5010'))
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
