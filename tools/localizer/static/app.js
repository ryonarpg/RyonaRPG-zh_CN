(() => {
  const $ = (id) => document.getElementById(id);
  const state = {
    current: null,
    dirty: false,
    searchTimer: null,
    checkTimer: null,
    searchSeq: 0,
  };

  const els = {
    status: $('status'),
    reindex: $('reindexBtn'),
    search: $('searchInput'),
    mode: $('searchMode'),
    searchCount: $('searchCount'),
    searchMeta: $('searchMeta'),
    results: $('results'),
    entryFile: $('entryFile'),
    entryMeta: $('entryMeta'),
    dirty: $('dirtyFlag'),
    save: $('saveBtn'),
    source: $('sourceText'),
    translation: $('translation'),
    lineHint: $('lineHint'),
    issues: $('issues'),
    metrics: $('metrics'),
    preview: $('preview'),
    pageCount: $('pageCount'),
    toast: $('toast'),
  };

  function toast(message, isError = false) {
    els.toast.textContent = message;
    els.toast.classList.toggle('error', !!isError);
    els.toast.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => els.toast.classList.remove('show'), 2600);
  }

  async function jsonFetch(url, options = {}) {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    let data = null;
    try { data = await res.json(); } catch (_) { /* ignore */ }
    if (!res.ok) {
      const err = new Error((data && data.error) || ('HTTP ' + res.status));
      err.data = data;
      throw err;
    }
    return data;
  }

  function setDirty(value) {
    state.dirty = value;
    els.dirty.textContent = value ? '未保存' : '已保存';
    els.dirty.classList.toggle('on', value);
    els.dirty.classList.toggle('off', !value);
  }

  function setStatus(data) {
    els.status.textContent = `${data.entries.toLocaleString()} 条 · ${data.files} 个 PO`;
    els.status.title = data.lang_dir;
  }

  async function loadStatus() {
    try {
      setStatus(await jsonFetch('/api/status'));
    } catch (e) {
      els.status.textContent = '索引不可用';
    }
  }

  function renderSnippet(text, query) {
    const frag = document.createDocumentFragment();
    if (!query) {
      frag.appendChild(document.createTextNode(text));
      return frag;
    }
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx < 0) {
      frag.appendChild(document.createTextNode(text));
      return frag;
    }
    frag.appendChild(document.createTextNode(text.slice(0, idx)));
    const mark = document.createElement('mark');
    mark.textContent = text.slice(idx, idx + query.length);
    frag.appendChild(mark);
    frag.appendChild(document.createTextNode(text.slice(idx + query.length)));
    return frag;
  }

  function renderResults(data) {
    els.results.textContent = '';
    els.searchCount.textContent = data.total ? `${data.total.toLocaleString()} 条` : '';
    els.searchMeta.textContent = data.query
      ? (data.total > data.items.length
          ? `显示前 ${data.items.length} 条，共 ${data.total.toLocaleString()} 条`
          : `找到 ${data.total.toLocaleString()} 条`)
      : '';
    if (!data.items.length) {
      const d = document.createElement('div');
      d.className = 'empty';
      d.textContent = data.query ? '没有匹配的条目' : '输入关键词开始全库搜索';
      els.results.appendChild(d);
      return;
    }
    for (const item of data.items) {
      const div = document.createElement('div');
      div.className = 'result';
      div.dataset.file = item.file;
      div.dataset.block = String(item.block);
      if (state.current && state.current.file === item.file && state.current.block === item.block) {
        div.classList.add('active');
      }

      const top = document.createElement('div');
      top.className = 'result-top';
      const f = document.createElement('span');
      f.className = 'result-file';
      f.textContent = item.file;
      const c = document.createElement('span');
      c.className = 'result-ctx';
      c.textContent = item.ctx || '消息';
      top.append(f, c);

      const snippet = document.createElement('div');
      snippet.className = 'result-snippet';
      snippet.appendChild(renderSnippet(item.snippet, data.query));

      div.append(top, snippet);
      div.addEventListener('click', () => loadEntry(item.file, item.block));
      els.results.appendChild(div);
    }
  }

  async function runSearch() {
    const q = els.search.value.trim();
    if (!q) {
      renderResults({ items: [], total: 0, query: '' });
      return;
    }
    const seq = ++state.searchSeq;
    els.searchMeta.textContent = '搜索中…';
    try {
      const data = await jsonFetch(
        `/api/search?q=${encodeURIComponent(q)}&mode=${encodeURIComponent(els.mode.value)}`
      );
      if (seq === state.searchSeq) renderResults(data);
    } catch (e) {
      if (seq === state.searchSeq) toast(e.message, true);
    }
  }

  function scheduleSearch() {
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(runSearch, 240);
  }

  function renderIssues(issues) {
    els.issues.textContent = '';
    if (!issues || !issues.length) {
      const ok = document.createElement('div');
      ok.className = 'issue ok';
      ok.textContent = '校验通过，没有发现问题。';
      els.issues.appendChild(ok);
      return;
    }
    for (const issue of issues) {
      const div = document.createElement('div');
      div.className = 'issue ' + (issue.severity === 'error' ? 'error' : 'warning');
      const t = document.createElement('div');
      t.className = 'issue-title';
      t.textContent = issue.severity === 'error' ? '错误' : '提示';
      div.appendChild(t);
      div.appendChild(document.createTextNode(issue.message));
      els.issues.appendChild(div);
    }
  }

  function renderMetrics(metrics) {
    els.metrics.textContent = '';
    if (!metrics || !metrics.length) {
      els.metrics.className = 'metrics empty';
      els.metrics.textContent = '暂无数据';
      return;
    }
    els.metrics.className = 'metrics';
    for (const m of metrics) {
      const row = document.createElement('div');
      row.className = 'metric-row' + (m.cells > 50 ? ' bad' : (m.cells > 46 ? ' warn' : ''));
      const num = document.createElement('span');
      num.className = 'num';
      num.textContent = String(m.line);
      const cells = document.createElement('span');
      cells.className = 'cells';
      cells.textContent = `${m.cells} 单元`;
      const text = document.createElement('span');
      text.className = 'text';
      text.textContent = m.text;
      row.append(num, cells, text);
      els.metrics.appendChild(row);
    }
  }

  function renderPreview(pages) {
    els.preview.textContent = '';
    if (!pages || !pages.length) {
      els.preview.className = 'preview empty';
      els.preview.textContent = '暂无预览';
      els.pageCount.textContent = '';
      return;
    }
    els.preview.className = 'preview';
    pages.forEach((src, i) => {
      const wrap = document.createElement('div');
      wrap.className = 'preview-page';
      const label = document.createElement('div');
      label.className = 'preview-label';
      label.textContent = `第 ${i + 1} 页`;
      const img = document.createElement('img');
      img.src = src;
      img.alt = `消息预览第 ${i + 1} 页`;
      wrap.append(label, img);
      els.preview.appendChild(wrap);
    });
    els.pageCount.textContent = `${pages.length} 页`;
  }

  function renderEntry(data) {
    state.current = data;
    els.entryFile.textContent = `${data.file} · #${data.block}`;
    els.entryMeta.textContent = data.ctx ? `上下文：${data.ctx}` : '事件消息';
    els.source.textContent = data.msgid || '';
    els.source.classList.toggle('empty', !data.msgid);
    els.translation.disabled = false;
    els.translation.value = data.msgstr || '';
    els.save.disabled = false;
    els.lineHint.textContent = `${(data.metrics || []).length} 行`;
    renderIssues(data.issues);
    renderMetrics(data.metrics);
    renderPreview(data.preview);
    setDirty(false);
    history.replaceState(null, '', `#${encodeURIComponent(data.file)}/${data.block}`);

    for (const el of els.results.querySelectorAll('.result')) {
      el.classList.toggle('active',
        el.dataset.file === data.file && Number(el.dataset.block) === data.block);
    }
  }

  async function loadEntry(file, block) {
    if (state.dirty && !confirm('当前条目有未保存修改，确定切换吗？')) return;
    els.translation.disabled = true;
    els.save.disabled = true;
    els.source.textContent = '加载中…';
    try {
      const data = await jsonFetch(
        `/api/entry?file=${encodeURIComponent(file)}&block=${encodeURIComponent(block)}`
      );
      renderEntry(data);
    } catch (e) {
      toast(e.message, true);
      els.source.textContent = '加载失败';
    }
  }

  function scheduleCheck() {
    if (!state.current) return;
    clearTimeout(state.checkTimer);
    state.checkTimer = setTimeout(runCheck, 320);
  }

  async function runCheck() {
    if (!state.current) return;
    try {
      const data = await jsonFetch('/api/check', {
        method: 'POST',
        body: JSON.stringify({
          msgid: state.current.msgid,
          msgstr: els.translation.value,
        }),
      });
      renderIssues(data.issues);
      renderMetrics(data.metrics);
      renderPreview(data.preview);
      els.lineHint.textContent = `${data.metrics.length} 行`;
      const hasError = data.issues.some((x) => x.severity === 'error');
      els.save.classList.toggle('primary', !hasError);
    } catch (e) {
      toast(e.message, true);
    }
  }

  async function save() {
    if (!state.current) return;
    clearTimeout(state.checkTimer);
    els.save.disabled = true;
    try {
      const data = await jsonFetch('/api/save', {
        method: 'POST',
        body: JSON.stringify({
          file: state.current.file,
          block: state.current.block,
          msgid: state.current.msgid,
          msgstr: els.translation.value,
        }),
      });
      renderEntry(data);
      toast('已保存，并已更新索引');
      runSearch();
    } catch (e) {
      if (e.data && e.data.issues) {
        renderIssues(e.data.issues);
        const first = e.data.issues.find((x) => x.severity === 'error');
        toast(first ? first.message : e.message, true);
      } else {
        toast(e.message, true);
      }
    } finally {
      els.save.disabled = false;
    }
  }

  async function reindex() {
    if (!confirm('重建全库搜索索引？这不会修改译文。')) return;
    els.reindex.disabled = true;
    try {
      const data = await jsonFetch('/api/reindex', { method: 'POST', body: '{}' });
      toast(`索引已重建：${data.entries.toLocaleString()} 条`);
      await loadStatus();
      runSearch();
    } catch (e) {
      toast(e.message, true);
    } finally {
      els.reindex.disabled = false;
    }
  }

  els.search.addEventListener('input', scheduleSearch);
  els.mode.addEventListener('change', runSearch);
  els.translation.addEventListener('input', () => {
    setDirty(true);
    scheduleCheck();
  });
  els.save.addEventListener('click', save);
  els.reindex.addEventListener('click', reindex);

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      save();
    }
  });

  window.addEventListener('beforeunload', (e) => {
    if (!state.dirty) return;
    e.preventDefault();
    e.returnValue = '';
  });

  (async function init() {
    await loadStatus();
    const m = location.hash.match(/^#([^/]+)\/(\d+)$/);
    if (m) loadEntry(decodeURIComponent(m[1]), Number(m[2]));
  })();
})();
