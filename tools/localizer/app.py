import os

from flask import Flask, Response, jsonify, render_template, request

import image_store
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


@app.get('/api/whitelist')
def api_whitelist():
    try:
        entries = qa_store.whitelist_entries()
        return jsonify({'entries': entries, 'total': len(entries)})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.post('/api/whitelist')
def api_whitelist_add():
    data = request.get_json(force=True)
    issue_id = data.get('id', '')
    note = data.get('note', '')
    try:
        entries = qa_store.add_whitelist(issue_id, note)
        return jsonify({'ok': True, 'entries': entries, 'total': len(entries)})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.post('/api/whitelist/remove')
def api_whitelist_remove():
    data = request.get_json(force=True)
    entry_id = data.get('id', '')
    try:
        entries = qa_store.remove_whitelist(entry_id)
        return jsonify({'ok': True, 'entries': entries, 'total': len(entries)})
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


@app.get('/images')
def images_page():
    return render_template('images.html')


@app.get('/api/image/config')
def api_image_config():
    try:
        return jsonify(image_store.get_config())
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.post('/api/image/config')
def api_image_config_save():
    try:
        return jsonify(image_store.save_config(request.get_json(force=True)))
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.post('/api/image/pick')
def api_image_pick():
    data = request.get_json(force=True)
    kind = data.get('kind', 'dir')
    title = data.get('title', '选择路径')
    try:
        path = image_store.pick_path(kind, title)
        return jsonify({'path': path})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.get('/api/image/list')
def api_image_list():
    try:
        offset = int(request.args.get('offset', '0'))
        limit = int(request.args.get('limit', '100'))
        data = image_store.list_images(
            request.args.get('family', 'Menu'),
            request.args.get('q', ''), offset, limit)
        return jsonify(data)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.get('/api/image/preview')
def api_image_preview():
    try:
        alpha = request.args.get('alpha', '1') != '0'
        data = image_store.preview_bytes(
            request.args.get('path', ''),
            request.args.get('side', 'override'), alpha)
        return Response(data, mimetype='image/png')
    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 404
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.get('/api/image/compare')
def api_image_compare():
    try:
        return jsonify(image_store.compare(request.args.get('path', '')))
    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 404
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.post('/api/image/export-edb')
def api_image_export_edb():
    try:
        return jsonify({'job_id': image_store.start_edb_export()})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.post('/api/image/generate')
def api_image_generate():
    data = request.get_json(force=True)
    try:
        job_id = image_store.start_job(
            data.get('family', 'Menu'),
            data.get('mode', 'check'),
            data.get('kind', 'all'))
        return jsonify({'job_id': job_id})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.get('/api/image/job/<job_id>')
def api_image_job(job_id):
    try:
        return jsonify(image_store.get_job(job_id))
    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 404


if __name__ == '__main__':
    po_store.ensure_index()
    port = int(os.environ.get('RYONA_PORT', '5010'))
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
