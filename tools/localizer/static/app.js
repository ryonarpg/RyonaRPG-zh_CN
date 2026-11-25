(() => {
  const $ = (id) => document.getElementById(id);
  const state = {
    current: null,
    dirty: false,
    deploying: false,
    searchTimer: null,
    checkTimer: null,
    searchSeq: 0,
    mode: 'browse',
    browse: {
      dim: 'maps',
      label: '地图',
      group: null,
      groupLabel: '',
      categories: [],
      groups: [],
      filter: '',
      items: [],
      total: 0,
      limit: 50,
      loading: false,
      seq: 0,
    },
    issues: {
      loaded: false,
      loading: false,
      severity: '',
      code: '',
      items: [],
      total: 0,
      limit: 50,
      summary: null,
      seq: 0,
    },
    whitelist: {
      loaded: false,
      loading: false,
      entries: [],
      seq: 0,
    },
  };

  const els = {
    status: $('status'),
    reindex: $('reindexBtn'),
    search: $('searchInput'),
    mode: $('searchMode'),
    searchCount: $('searchCount'),
    searchMeta: $('searchMeta'),
    leftModes: $('leftModes'),
    modeBrowse: $('modeBrowse'),
    modeIssues: $('modeIssues'),
    modeWhitelist: $('modeWhitelist'),
    issueBadge: $('issueBadge'),
    browsePanel: $('browsePanel'),
    browseTabs: $('browseTabs'),
    browsePath: $('browsePath'),
    browseFilter: $('browseFilter'),
    browseList: $('browseList'),
    browseFooter: $('browseFooter'),
    issuesPanel: $('issuesPanel'),
    issueSummary: $('issueSummary'),
    issueRefresh: $('issueRefresh'),
    issueSeverity: $('issueSeverity'),
    issueCode: $('issueCode'),
    issueList: $('issueList'),
    issueFooter: $('issueFooter'),
    whitelistPanel: $('whitelistPanel'),
    whitelistSummary: $('whitelistSummary'),
    whitelistRefresh: $('whitelistRefresh'),
    whitelistList: $('whitelistList'),
    results: $('results'),
    entryFile: $('entryFile'),
    entryMeta: $('entryMeta'),
    dirty: $('dirtyFlag'),
    save: $('saveBtn'),
    saveDeploy: $('saveDeployBtn'),
    autoDeploy: $('autoDeploy'),
    source: $('sourceText'),
    translation: $('translation'),
    lineHint: $('lineHint'),
    issues: $('issues'),
    metrics: $('metrics'),
    sourcePreview: $('sourcePreview'),
    sourcePageCount: $('sourcePageCount'),
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

  function renderBrowseTabs() {
    els.browseTabs.textContent = '';
    for (const category of state.browse.categories) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'browse-tab' + (category.id === state.browse.dim ? ' active' : '');
      const label = document.createElement('span');
      label.textContent = category.label;
      const count = document.createElement('span');
      count.className = 'tab-count';
      count.textContent = Number(category.count || 0).toLocaleString();
      btn.append(label, count);
      btn.addEventListener('click', () => switchBrowseDim(category));
      els.browseTabs.appendChild(btn);
    }
  }

  function switchBrowseDim(category) {
    const b = state.browse;
    if (b.dim === category.id && !b.group) return;
    b.dim = category.id;
    b.label = category.label;
    b.group = null;
    b.groupLabel = '';
    b.filter = '';
    b.items = [];
    b.total = 0;
    els.browseFilter.value = '';
    loadBrowseGroups();
  }

  function renderBrowseGroupPath(data) {
    els.browsePath.textContent = '';
    const name = document.createElement('strong');
    name.textContent = data.label;
    const meta = document.createElement('span');
    const groups = data.groups.length;
    const entries = Number(data.entry_count || 0).toLocaleString();
    meta.textContent = `${groups.toLocaleString()} 个分组 · ${entries} 条`;
    els.browsePath.append(name, meta);
  }

  function renderBrowseGroupList() {
    els.browseList.textContent = '';
    const needle = state.browse.filter.trim().toLowerCase();
    const groups = state.browse.groups.filter((g) => {
      if (!needle) return true;
      return `${g.label} ${g.id}`.toLowerCase().includes(needle);
    });
    if (!groups.length) {
      const empty = document.createElement('div');
      empty.className = 'empty';
      empty.textContent = state.browse.filter ? '没有匹配的分组' : '这一分类暂无条目';
      els.browseList.appendChild(empty);
      return;
    }
    let section = null;
    for (const group of groups) {
      if (group.section && group.section !== section) {
        section = group.section;
        const heading = document.createElement('div');
        heading.className = 'browse-section';
        heading.textContent = section;
        els.browseList.appendChild(heading);
      }
      const row = document.createElement('div');
      row.className = 'browse-group';
      const label = document.createElement('span');
      label.className = 'browse-group-label';
      label.textContent = group.label;
      const count = document.createElement('span');
      count.className = 'browse-group-count';
      count.textContent = `${Number(group.count || 0).toLocaleString()} 条`;
      row.append(label, count);
      row.addEventListener('click', () => openBrowseGroup(group));
      els.browseList.appendChild(row);
    }
  }

  function openBrowseGroup(group) {
    const b = state.browse;
    b.group = group.id;
    b.groupLabel = group.label;
    b.filter = '';
    b.items = [];
    b.total = 0;
    els.browseFilter.value = '';
    loadBrowseEntries(false);
  }

  function renderBrowseEntryPath() {
    const b = state.browse;
    els.browsePath.textContent = '';
    const back = document.createElement('button');
    back.type = 'button';
    back.className = 'browse-back';
    back.textContent = '← 分组';
    back.addEventListener('click', () => {
      b.group = null;
      b.groupLabel = '';
      b.items = [];
      b.total = 0;
      loadBrowseGroups();
    });
    const name = document.createElement('strong');
    name.textContent = b.label;
    const meta = document.createElement('span');
    meta.textContent = ` / ${b.groupLabel} · ${Number(b.total || 0).toLocaleString()} 条`;
    els.browsePath.append(back, name, meta);
  }

  function browseLine(tagText, value, emptyText) {
    const row = document.createElement('div');
    row.className = 'browse-text';
    const tag = document.createElement('span');
    tag.className = 'lang-tag ' + (tagText === '原文' ? 'jp' : 'cn');
    tag.textContent = tagText;
    const text = document.createElement('span');
    if (value) {
      text.textContent = value;
    } else {
      text.textContent = emptyText;
      text.className = 'empty-text';
    }
    row.append(tag, text);
    return row;
  }

  function renderBrowseEntryList() {
    const b = state.browse;
    els.browseList.textContent = '';
    if (!b.items.length) {
      const empty = document.createElement('div');
      empty.className = 'empty';
      empty.textContent = '这个分组没有条目';
      els.browseList.appendChild(empty);
      renderBrowseFooter();
      return;
    }
    for (const item of b.items) {
      const row = document.createElement('div');
      row.className = 'result browse-entry';
      row.dataset.file = item.file;
      row.dataset.block = String(item.block);
      if (state.current && state.current.file === item.file && state.current.block === item.block) {
        row.classList.add('active');
      }

      const top = document.createElement('div');
      top.className = 'result-top';
      const file = document.createElement('span');
      file.className = 'result-file';
      file.textContent = item.file;
      const ctx = document.createElement('span');
      ctx.className = 'result-ctx';
      ctx.textContent = item.ctx || '事件消息';
      top.append(file, ctx);

      row.append(
        top,
        browseLine('原文', item.source, '（空）'),
        browseLine('译文', item.translation, '（未翻译）'),
      );
      row.addEventListener('click', () => loadEntry(item.file, item.block));
      els.browseList.appendChild(row);
    }
    renderBrowseFooter();
  }

  function renderBrowseFooter() {
    const b = state.browse;
    els.browseFooter.textContent = '';
    if (!b.total) return;
    const shown = b.items.length;
    if (shown >= b.total) {
      if (b.total > b.limit) {
        const done = document.createElement('div');
        done.className = 'muted small';
        done.textContent = `已显示全部 ${b.total.toLocaleString()} 条`;
        els.browseFooter.appendChild(done);
      }
      return;
    }
    const more = document.createElement('button');
    more.type = 'button';
    more.className = 'browse-more';
    more.textContent = `加载更多（已显示 ${shown} / ${b.total.toLocaleString()} 条）`;
    more.addEventListener('click', () => loadBrowseEntries(true));
    els.browseFooter.appendChild(more);
  }

  async function loadBrowseGroups() {
    const b = state.browse;
    const seq = ++b.seq;
    b.loading = true;
    b.group = null;
    b.groupLabel = '';
    b.items = [];
    b.total = 0;
    b.groups = [];
    els.browsePath.textContent = '加载中…';
    els.browseList.textContent = '';
    els.browseFooter.textContent = '';
    try {
      const data = await jsonFetch(`/api/browse?dim=${encodeURIComponent(b.dim)}`);
      if (seq !== b.seq) return;
      b.label = data.label;
      b.categories = data.categories;
      b.groups = data.groups;
      renderBrowseTabs();
      renderBrowseGroupPath(data);
      els.browseFilter.classList.toggle('hidden', data.groups.length <= 8);
      renderBrowseGroupList();
    } catch (e) {
      if (seq === b.seq) {
        toast(e.message, true);
        els.browsePath.textContent = '浏览加载失败';
      }
    } finally {
      if (seq === b.seq) b.loading = false;
    }
  }

  async function loadBrowseEntries(append) {
    const b = state.browse;
    if (!b.group) return;
    const seq = ++b.seq;
    b.loading = true;
    const offset = append ? b.items.length : 0;
    if (!append) {
      els.browsePath.textContent = '加载中…';
      els.browseList.textContent = '';
      els.browseFooter.textContent = '';
    }
    try {
      const data = await jsonFetch(
        `/api/browse?dim=${encodeURIComponent(b.dim)}` +
        `&group=${encodeURIComponent(b.group)}` +
        `&offset=${offset}&limit=${b.limit}`
      );
      if (seq !== b.seq) return;
      b.label = data.label;
      b.groupLabel = data.group_label;
      b.total = data.total;
      b.categories = data.categories;
      b.items = append ? b.items.concat(data.items) : data.items;
      renderBrowseTabs();
      renderBrowseEntryPath();
      els.browseFilter.classList.add('hidden');
      renderBrowseEntryList();
    } catch (e) {
      if (seq === b.seq) {
        toast(e.message, true);
        els.browsePath.textContent = '分组加载失败';
      }
    } finally {
      if (seq === b.seq) b.loading = false;
    }
  }

  function loadBrowse() {
    if (state.browse.group) return loadBrowseEntries(false);
    return loadBrowseGroups();
  }

  function severityLabel(severity) {
    return { error: '错误', warning: '警告', info: '提示' }[severity] || severity;
  }

  function updateIssueBadge(summary) {
    const err = summary ? (summary.by_severity.error || 0) : 0;
    const warn = summary ? (summary.by_severity.warning || 0) : 0;
    const info = summary ? (summary.by_severity.info || 0) : 0;
    const count = err || warn || info;
    if (!count) {
      els.issueBadge.classList.add('hidden');
      els.issueBadge.textContent = '';
      els.issueBadge.title = '';
      return;
    }
    els.issueBadge.className = 'mode-badge' + (err ? '' : (warn ? ' warn' : ' info'));
    els.issueBadge.textContent = String(count);
    els.issueBadge.title = `错误 ${err} · 警告 ${warn} · 提示 ${info}`;
  }

  function renderIssueSummary(summary) {
    if (!summary) {
      els.issueSummary.textContent = '尚未扫描';
      return;
    }
    const sev = summary.by_severity;
    if (!summary.total) {
      els.issueSummary.textContent = `扫描 ${summary.scanned.toLocaleString()} 条，未发现问题`;
      return;
    }
    els.issueSummary.textContent =
      `扫描 ${summary.scanned.toLocaleString()} 条 · ${summary.entries.toLocaleString()} 条有提示` +
      ` · 错误 ${sev.error} / 警告 ${sev.warning} / 提示 ${sev.info}`;
  }

  function renderIssueFilters() {
    const s = state.issues;
    const summary = s.summary;
    els.issueSeverity.textContent = '';
    if (!summary) return;
    const choices = [
      ['', '全部', summary.total],
      ['error', '错误', summary.by_severity.error || 0],
      ['warning', '警告', summary.by_severity.warning || 0],
      ['info', '提示', summary.by_severity.info || 0],
    ];
    for (const [value, label, count] of choices) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'issue-chip' +
        (value ? ' ' + value : '') +
        (s.severity === value ? ' active' : '');
      const name = document.createElement('span');
      name.textContent = label;
      const num = document.createElement('span');
      num.className = 'chip-count';
      num.textContent = Number(count || 0).toLocaleString();
      btn.append(name, num);
      btn.addEventListener('click', () => {
        if (s.severity === value) return;
        s.severity = value;
        s.code = '';
        loadIssues(false);
      });
      els.issueSeverity.appendChild(btn);
    }

    const codes = (summary.by_code || []).filter(
      (c) => !s.severity || c.severity === s.severity
    );
    if (s.code && !codes.some((c) => c.code === s.code)) s.code = '';
    els.issueCode.textContent = '';
    const all = document.createElement('option');
    all.value = '';
    all.textContent = '全部问题类型';
    els.issueCode.appendChild(all);
    for (const item of codes) {
      const option = document.createElement('option');
      option.value = item.code;
      option.textContent = `${item.label}（${item.count.toLocaleString()}）`;
      els.issueCode.appendChild(option);
    }
    els.issueCode.value = s.code;
  }

  function renderIssueList() {
    const s = state.issues;
    els.issueList.textContent = '';
    if (!s.items.length) {
      const empty = document.createElement('div');
      empty.className = 'empty';
      empty.textContent = s.loaded ? '当前筛选下没有条目' : '正在扫描全库…';
      els.issueList.appendChild(empty);
      renderIssueFooter();
      return;
    }
    for (const item of s.items) {
      const row = document.createElement('div');
      row.className = 'result issue-result';
      row.dataset.file = item.file;
      row.dataset.block = String(item.block);
      row.dataset.issueId = item.id || '';
      if (state.current && state.current.file === item.file && state.current.block === item.block) {
        row.classList.add('active');
      }

      const top = document.createElement('div');
      top.className = 'result-top';
      const file = document.createElement('span');
      file.className = 'result-file';
      file.textContent = item.file;
      const ctx = document.createElement('span');
      ctx.className = 'result-ctx';
      ctx.textContent = item.ctx || '事件消息';
      top.append(file, ctx);

      const headline = document.createElement('div');
      headline.className = 'issue-headline';
      const sev = document.createElement('span');
      sev.className = 'issue-sev ' + item.severity;
      sev.textContent = severityLabel(item.severity);
      const msg = document.createElement('span');
      msg.className = 'issue-message';
      msg.textContent = `${item.label}：${item.message}`;
      headline.append(sev, msg);

      row.append(
        top,
        headline,
        browseLine('原文', item.source, '（空）'),
        browseLine('译文', item.translation, '（未翻译）'),
      );
      if (item.id) {
        const actions = document.createElement('div');
        actions.className = 'issue-actions';
        const ignore = document.createElement('button');
        ignore.type = 'button';
        ignore.className = 'issue-add';
        ignore.textContent = '加入白名单';
        ignore.title = '确认此问题不是错误，以后不再报告';
        ignore.addEventListener('click', (e) => {
          e.stopPropagation();
          addWhitelist(item);
        });
        actions.appendChild(ignore);
        row.appendChild(actions);
      }
      row.addEventListener('click', () => loadEntry(item.file, item.block));
      els.issueList.appendChild(row);
    }
    renderIssueFooter();
  }

  function renderIssueFooter() {
    const s = state.issues;
    els.issueFooter.textContent = '';
    if (!s.total) return;
    const shown = s.items.length;
    if (shown >= s.total) {
      if (s.total > s.limit) {
        const done = document.createElement('div');
        done.className = 'muted small';
        done.textContent = `已显示全部 ${s.total.toLocaleString()} 条`;
        els.issueFooter.appendChild(done);
      }
      return;
    }
    const more = document.createElement('button');
    more.type = 'button';
    more.className = 'browse-more';
    more.textContent = `加载更多（已显示 ${shown} / ${s.total.toLocaleString()} 条）`;
    more.addEventListener('click', () => loadIssues(true));
    els.issueFooter.appendChild(more);
  }

  async function loadIssues(append, force = false) {
    const s = state.issues;
    if (els.search.value.trim()) return;
    const seq = ++s.seq;
    s.loading = true;
    els.issueRefresh.disabled = true;
    const offset = append ? s.items.length : 0;
    if (!append) {
      s.items = [];
      s.total = 0;
      els.issueList.textContent = '';
      els.issueFooter.textContent = '';
      els.issueSummary.textContent = '正在扫描全库…';
    }
    try {
      const data = await jsonFetch(
        `/api/issues?severity=${encodeURIComponent(s.severity)}` +
        `&code=${encodeURIComponent(s.code)}` +
        `&offset=${offset}&limit=${s.limit}` +
        (force ? '&refresh=1' : '')
      );
      if (seq !== s.seq) return;
      s.summary = data.summary;
      s.total = data.total;
      s.items = append ? s.items.concat(data.items) : data.items;
      s.loaded = true;
      renderIssueSummary(s.summary);
      renderIssueFilters();
      renderIssueList();
      updateIssueBadge(s.summary);
    } catch (e) {
      if (seq === s.seq) {
        els.issueSummary.textContent = '扫描失败';
        toast(e.message, true);
      }
    } finally {
      if (seq === s.seq) {
        s.loading = false;
        els.issueRefresh.disabled = false;
      }
    }
  }

  function renderWhitelist() {
    const w = state.whitelist;
    els.whitelistList.textContent = '';
    els.whitelistSummary.textContent =
      `已确认 ${w.entries.length.toLocaleString()} 条`;
    if (!w.entries.length) {
      const empty = document.createElement('div');
      empty.className = 'empty';
      empty.textContent = '还没有已确认的问题';
      els.whitelistList.appendChild(empty);
      return;
    }
    for (const entry of w.entries) {
      const row = document.createElement('div');
      row.className = 'result whitelist-row';
      row.dataset.file = entry.file;
      row.dataset.block = String(entry.block);
      if (state.current && state.current.file === entry.file &&
          state.current.block === entry.block) {
        row.classList.add('active');
      }

      const top = document.createElement('div');
      top.className = 'result-top';
      const file = document.createElement('span');
      file.className = 'result-file';
      file.textContent = `${entry.file} · #${entry.block}`;
      const code = document.createElement('span');
      code.className = 'result-ctx';
      code.textContent = entry.label || entry.code || '已确认';
      top.append(file, code);

      const message = document.createElement('div');
      message.className = 'issue-message';
      message.textContent = entry.message || '';
      const actions = document.createElement('div');
      actions.className = 'issue-actions';
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'whitelist-remove';
      remove.textContent = '移出白名单';
      remove.addEventListener('click', (e) => {
        e.stopPropagation();
        removeWhitelist(entry);
      });
      actions.appendChild(remove);
      row.append(top, message);
      if (entry.note) {
        const note = document.createElement('div');
        note.className = 'whitelist-note';
        note.textContent = entry.note;
        row.appendChild(note);
      }
      row.appendChild(actions);
      row.addEventListener('click', () => loadEntry(entry.file, entry.block));
      els.whitelistList.appendChild(row);
    }
  }

  async function loadWhitelist() {
    const w = state.whitelist;
    const seq = ++w.seq;
    w.loading = true;
    els.whitelistSummary.textContent = '加载中…';
    try {
      const data = await jsonFetch('/api/whitelist');
      if (seq !== w.seq) return;
      w.entries = data.entries || [];
      w.loaded = true;
      renderWhitelist();
    } catch (e) {
      if (seq === w.seq) {
        els.whitelistSummary.textContent = '白名单加载失败';
        toast(e.message, true);
      }
    } finally {
      if (seq === w.seq) w.loading = false;
    }
  }

  async function refreshIssueSummary() {
    const s = state.issues;
    try {
      const data = await jsonFetch(
        `/api/issues?severity=${encodeURIComponent(s.severity)}` +
        `&code=${encodeURIComponent(s.code)}&offset=0&limit=0`
      );
      s.summary = data.summary;
      s.total = data.total;
      renderIssueSummary(s.summary);
      renderIssueFilters();
      updateIssueBadge(s.summary);
      if (!s.items.length) renderIssueList();
      else renderIssueFooter();
    } catch (e) {
      toast(e.message, true);
    }
  }

  async function addWhitelist(item) {
    try {
      const data = await jsonFetch('/api/whitelist', {
        method: 'POST',
        body: JSON.stringify({ id: item.id }),
      });
      state.whitelist.entries = data.entries || [];
      state.whitelist.loaded = true;
      if (state.mode === 'whitelist') renderWhitelist();

      const s = state.issues;
      const index = s.items.findIndex((x) => x.id === item.id);
      if (index >= 0) s.items.splice(index, 1);
      const row = [...els.issueList.querySelectorAll('.result')]
        .find((x) => x.dataset.issueId === item.id);
      if (row) row.remove();
      s.total = Math.max(0, s.total - 1);
      await refreshIssueSummary();
      toast('已加入白名单');
    } catch (e) {
      toast(e.message, true);
    }
  }

  async function removeWhitelist(entry) {
    try {
      const data = await jsonFetch('/api/whitelist/remove', {
        method: 'POST',
        body: JSON.stringify({ id: entry.id }),
      });
      state.whitelist.entries = data.entries || [];
      state.whitelist.loaded = true;
      renderWhitelist();
      state.issues.loaded = false;
      toast('已移出白名单');
    } catch (e) {
      toast(e.message, true);
    }
  }

  function setMode(mode) {
    if (mode !== 'browse' && mode !== 'issues' && mode !== 'whitelist') return;
    if (state.mode === mode) return;
    state.mode = mode;
    els.modeBrowse.classList.toggle('active', mode === 'browse');
    els.modeIssues.classList.toggle('active', mode === 'issues');
    els.modeWhitelist.classList.toggle('active', mode === 'whitelist');
    if (els.search.value.trim()) return;
    setSearchMode(false);
    if (mode === 'issues') {
      loadIssues(false);
    } else if (mode === 'whitelist') {
      loadWhitelist();
    } else if (!state.browse.categories.length) {
      loadBrowse();
    }
  }

  function setSearchMode(searching) {
    const search = !!searching;
    els.results.classList.toggle('hidden', !search);
    els.leftModes.classList.toggle('hidden', search);
    if (search) {
      els.browsePanel.classList.add('hidden');
      els.issuesPanel.classList.add('hidden');
      els.whitelistPanel.classList.add('hidden');
    } else {
      els.browsePanel.classList.toggle('hidden', state.mode !== 'browse');
      els.issuesPanel.classList.toggle('hidden', state.mode !== 'issues');
      els.whitelistPanel.classList.toggle('hidden', state.mode !== 'whitelist');
      els.searchCount.textContent = '';
      els.searchMeta.textContent = '';
    }
  }

  async function runSearch() {
    const q = els.search.value.trim();
    if (!q) {
      state.searchSeq += 1;
      setSearchMode(false);
      return;
    }
    setSearchMode(true);
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
      div.className = 'issue ' + (issue.severity || 'warning');
      const t = document.createElement('div');
      t.className = 'issue-title';
      t.textContent = issue.severity === 'error'
        ? '错误'
        : (issue.severity === 'info' ? '提示' : '警告');
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

  function renderPreviewPages(container, countEl, pages, emptyText, altPrefix) {
    container.textContent = '';
    if (!pages || !pages.length) {
      container.className = 'preview empty';
      container.textContent = emptyText;
      countEl.textContent = '';
      return;
    }
    container.className = 'preview';
    pages.forEach((src, i) => {
      const wrap = document.createElement('div');
      wrap.className = 'preview-page';
      const label = document.createElement('div');
      label.className = 'preview-label';
      label.textContent = `第 ${i + 1} 页`;
      const img = document.createElement('img');
      img.src = src;
      img.alt = `${altPrefix}第 ${i + 1} 页`;
      wrap.append(label, img);
      container.appendChild(wrap);
    });
    countEl.textContent = `${pages.length} 页`;
  }

  function renderSourcePreview(pages) {
    renderPreviewPages(els.sourcePreview, els.sourcePageCount, pages, '暂无原版预览', '日文原版预览');
  }

  function renderPreview(pages) {
    renderPreviewPages(els.preview, els.pageCount, pages, '暂无预览', '中文译文预览');
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
    els.saveDeploy.disabled = false;
    els.lineHint.textContent = `${(data.metrics || []).length} 行`;
    renderIssues(data.issues);
    renderMetrics(data.metrics);
    renderSourcePreview(data.source_preview);
    renderPreview(data.preview);
    setDirty(false);
    history.replaceState(null, '', `#${encodeURIComponent(data.file)}/${data.block}`);

    for (const el of document.querySelectorAll('.result')) {
      el.classList.toggle('active',
        el.dataset.file === data.file && Number(el.dataset.block) === data.block);
    }
  }

  async function loadEntry(file, block) {
    if (state.dirty && !confirm('当前条目有未保存修改，确定切换吗？')) return;
    els.translation.disabled = true;
    els.save.disabled = true;
    els.saveDeploy.disabled = true;
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
          ctx: state.current.ctx || '',
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

  function updateCurrentRow(data) {
    const display = (data.display_msgstr || data.msgstr || '').slice(0, 160);
    const shown = display || '（未翻译）';
    for (const row of document.querySelectorAll('.result')) {
      if (row.dataset.file !== data.file || Number(row.dataset.block) !== data.block) continue;
      const lines = row.querySelectorAll('.browse-text');
      if (lines.length >= 2) {
        const text = lines[1].querySelector('span:last-child');
        if (text) {
          text.textContent = shown;
          text.classList.toggle('empty-text', !display);
        }
      }
      const snippet = row.querySelector('.result-snippet');
      if (snippet) snippet.textContent = shown;
    }
  }

  function refreshList() {
    if (els.search.value.trim()) {
      runSearch();
    } else {
      loadBrowse();
    }
  }

  async function ensureGameDir() {
    try {
      const cfg = await jsonFetch('/api/image/config');
      if (cfg.status && cfg.status.game_exists && cfg.config.game_dir) return true;
      const picked = await jsonFetch('/api/image/pick', {
        method: 'POST',
        body: JSON.stringify({ kind: 'dir', title: '选择 RyonaRPG 游戏目录' }),
      });
      if (!picked.path) return false;
      await jsonFetch('/api/image/config', {
        method: 'POST',
        body: JSON.stringify({ game_dir: picked.path }),
      });
      return true;
    } catch (e) {
      toast(e.message, true);
      return false;
    }
  }

  async function deployToGame() {
    if (state.deploying) return;
    if (!(await ensureGameDir())) return;
    state.deploying = true;
    els.saveDeploy.disabled = true;
    try {
      const data = await jsonFetch('/api/deploy', {
        method: 'POST',
        body: '{}',
      });
      const copied = Number(data.copied || 0);
      const suffix = copied ? `（${copied} 个文件）` : '（没有变化）';
      toast('已部署到游戏' + suffix + '，重启游戏生效');
      if (data.warnings && data.warnings.length) {
        toast(data.warnings[0], true);
      }
    } catch (e) {
      toast('部署失败：' + e.message, true);
    } finally {
      state.deploying = false;
      els.saveDeploy.disabled = !state.current;
    }
  }

  async function save(deployAfter = false) {
    if (!state.current) return;
    clearTimeout(state.checkTimer);
    const caretStart = els.translation.selectionStart;
    const caretEnd = els.translation.selectionEnd;
    const editorScroll = els.translation.scrollTop;
    const shouldDeploy = deployAfter || els.autoDeploy.checked;
    els.save.disabled = true;
    els.saveDeploy.disabled = true;
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
      const length = els.translation.value.length;
      if (caretStart !== null && caretStart !== undefined) {
        els.translation.setSelectionRange(
          Math.min(caretStart, length), Math.min(caretEnd, length));
        els.translation.scrollTop = editorScroll;
      }
      updateCurrentRow(data);
      toast('已保存，并已更新索引');
      if (shouldDeploy) await deployToGame();
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
      els.saveDeploy.disabled = false;
    }
  }

  async function reindex() {
    if (!confirm('重建全库搜索索引？这不会修改译文。')) return;
    els.reindex.disabled = true;
    try {
      const data = await jsonFetch('/api/reindex', { method: 'POST', body: '{}' });
      toast(`索引已重建：${data.entries.toLocaleString()} 条`);
      await loadStatus();
      refreshList();
      if (state.issues.loaded) loadIssues(false, true);
    } catch (e) {
      toast(e.message, true);
    } finally {
      els.reindex.disabled = false;
    }
  }

  els.search.addEventListener('input', () => {
    const q = els.search.value.trim();
    clearTimeout(state.searchTimer);
    setSearchMode(!!q);
    if (!q) {
      state.searchSeq += 1;
      els.searchMeta.textContent = '';
      if (state.mode === 'issues') {
        loadIssues(false);
      } else if (state.mode === 'whitelist') {
        loadWhitelist();
      } else if (!state.browse.categories.length) {
        loadBrowse();
      }
      return;
    }
    scheduleSearch();
  });
  els.mode.addEventListener('change', runSearch);
  els.modeBrowse.addEventListener('click', () => setMode('browse'));
  els.modeIssues.addEventListener('click', () => setMode('issues'));
  els.modeWhitelist.addEventListener('click', () => setMode('whitelist'));
  els.issueRefresh.addEventListener('click', () => loadIssues(false, true));
  els.whitelistRefresh.addEventListener('click', loadWhitelist);
  els.issueCode.addEventListener('change', () => {
    state.issues.code = els.issueCode.value;
    loadIssues(false);
  });
  els.browseFilter.addEventListener('input', () => {
    state.browse.filter = els.browseFilter.value;
    renderBrowseGroupList();
  });
  els.translation.addEventListener('input', () => {
    setDirty(true);
    scheduleCheck();
  });
  els.autoDeploy.checked = localStorage.getItem('ryona_auto_deploy') === '1';
  els.autoDeploy.addEventListener('change', () => {
    localStorage.setItem('ryona_auto_deploy', els.autoDeploy.checked ? '1' : '0');
  });
  els.save.addEventListener('click', () => save(false));
  els.saveDeploy.addEventListener('click', () => save(true));
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
    setSearchMode(false);
    await loadStatus();
    await loadBrowse();
    loadIssues(false);
    const m = location.hash.match(/^#([^/]+)\/(\d+)$/);
    if (m) loadEntry(decodeURIComponent(m[1]), Number(m[2]));
  })();
})();
