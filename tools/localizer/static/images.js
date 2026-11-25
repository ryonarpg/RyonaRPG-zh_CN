(() => {
  const $ = (id) => document.getElementById(id);
  const state = {
    config: null,
    status: null,
    families: [],
    family: 'Menu',
    menuKinds: [],
    query: '',
    offset: 0,
    limit: 100,
    total: 0,
    items: [],
    selected: null,
    alpha: true,
    zoom: 1,
    listSeq: 0,
    compareSeq: 0,
    jobId: null,
    jobTimer: null,
    searchTimer: null,
  };

  const els = {
    status: $('imageStatus'),
    gameDir: $('gameDir'),
    edbPath: $('edbPath'),
    lcf2xmlPath: $('lcf2xmlPath'),
    fontPath: $('fontPath'),
    pickGame: $('pickGame'),
    pickEdb: $('pickEdb'),
    pickLcf: $('pickLcf'),
    pickFont: $('pickFont'),
    exportEdb: $('exportEdb'),
    saveConfig: $('saveConfig'),
    configStatus: $('configStatus'),
    familyTabs: $('familyTabs'),
    imageSearch: $('imageSearch'),
    imageList: $('imageList'),
    imageCount: $('imageCount'),
    prevPage: $('prevPage'),
    nextPage: $('nextPage'),
    pageLabel: $('pageLabel'),
    imageTitle: $('imageTitle'),
    imagePath: $('imagePath'),
    alphaToggle: $('alphaToggle'),
    sourceImg: $('sourceImg'),
    overrideImg: $('overrideImg'),
    sourceCanvas: $('sourceCanvas'),
    overrideCanvas: $('overrideCanvas'),
    sourceBadge: $('sourceBadge'),
    overrideBadge: $('overrideBadge'),
    sourceMeta: $('sourceMeta'),
    overrideMeta: $('overrideMeta'),
    diffBar: $('diffBar'),
    generatorHint: $('generatorHint'),
    genKind: $('genKind'),
    checkImages: $('checkImages'),
    buildImages: $('buildImages'),
    jobStatus: $('jobStatus'),
    jobLog: $('jobLog'),
    toast: $('toast'),
  };

  function toast(message, isError = false) {
    els.toast.textContent = message;
    els.toast.classList.toggle('error', !!isError);
    els.toast.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => els.toast.classList.remove('show'), 3000);
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

  function updateStatus() {
    const s = state.status || {};
    let text = '未配置游戏目录';
    if (s.game_exists && s.has_ldb && s.has_picture) {
      text = '游戏目录有效';
    } else if (s.game_exists) {
      text = '游戏目录缺少 RPG_RT.ldb 或 Picture';
    }
    if (s.edb_exists) text += ' · EDB 已配置';
    els.status.textContent = text;
    els.status.title = s.game_dir || '';

    const parts = [];
    if (!s.game_exists) {
      parts.push('尚未设置有效的游戏目录；只能查看已提交的中文覆盖图。');
    } else if (!s.has_picture) {
      parts.push('游戏目录中没有 Picture 文件夹。');
    }
    if (s.game_exists && !s.edb_exists) {
      parts.push('未配置 EDB：Menu 的 items/skills 生成会失败。');
    }
    if (!state.config || !state.config.lcf2xml) {
      parts.push('未设置 lcf2xml.exe，无法从 RPG_RT.ldb 自动导出 EDB。');
    }
    els.configStatus.textContent = parts.join(' ');
    els.configStatus.classList.toggle('warn-text', parts.length > 0);
  }

  function applyConfig(data) {
    state.config = data.config;
    state.status = data.status;
    state.families = data.families || [];
    state.menuKinds = data.menu_kinds || [];
    els.gameDir.value = state.config.game_dir || '';
    els.edbPath.value = state.config.edb_path || '';
    els.lcf2xmlPath.value = state.config.lcf2xml || '';
    els.fontPath.value = state.config.font || '';
    updateStatus();
    renderFamilies();
  }

  async function loadConfig() {
    const data = await jsonFetch('/api/image/config');
    applyConfig(data);
  }

  async function saveConfig() {
    els.saveConfig.disabled = true;
    try {
      const data = await jsonFetch('/api/image/config', {
        method: 'POST',
        body: JSON.stringify({
          game_dir: els.gameDir.value.trim(),
          edb_path: els.edbPath.value.trim(),
          lcf2xml: els.lcf2xmlPath.value.trim(),
          font: els.fontPath.value.trim(),
        }),
      });
      applyConfig(data);
      toast('配置已保存');
      await loadList();
      return true;
    } catch (e) {
      toast(e.message, true);
      return false;
    } finally {
      els.saveConfig.disabled = false;
    }
  }

  async function pickPath(kind, target, title) {
    try {
      const data = await jsonFetch('/api/image/pick', {
        method: 'POST',
        body: JSON.stringify({ kind, title }),
      });
      if (data.path) {
        target.value = data.path;
        await saveConfig();
      }
    } catch (e) {
      toast(e.message, true);
    }
  }

  function renderFamilies() {
    els.familyTabs.textContent = '';
    for (const family of state.families) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'image-tab' + (family.id === state.family ? ' active' : '');
      btn.textContent = family.label;
      btn.title = family.generator ? `生成脚本：${family.generator}` : '没有生成脚本';
      btn.addEventListener('click', () => setFamily(family.id));
      els.familyTabs.appendChild(btn);
    }
  }

  function familyInfo(id) {
    return state.families.find((f) => f.id === id) || null;
  }

  function setFamily(id) {
    if (id === state.family) return;
    state.family = id;
    state.offset = 0;
    state.selected = null;
    renderFamilies();
    clearSelection();
    updateGenerator();
    loadList();
  }

  function updateGenerator() {
    const info = familyInfo(state.family);
    const available = !!(info && info.generator);
    const isMenu = state.family === 'Menu';
    els.genKind.classList.toggle('hidden', !isMenu);
    els.checkImages.disabled = !available || !!state.jobId;
    els.buildImages.disabled = !available || !!state.jobId;
    if (!available) {
      els.generatorHint.textContent = '该图片组没有生成脚本，只能预览/对比。';
    } else if (isMenu) {
      els.generatorHint.textContent = `使用 tools/images/${info.generator}；检查会写入临时目录，生成会覆盖 language/zh_CN/${info.prefix || 'Picture'}`;
    } else {
      els.generatorHint.textContent = `使用 tools/images/${info.generator}；检查只校验，生成会写入 language/zh_CN/Picture/...`;
    }
  }

  async function loadList() {
    const seq = ++state.listSeq;
    els.imageList.textContent = '';
    const loading = document.createElement('div');
    loading.className = 'empty';
    loading.textContent = '加载中…';
    els.imageList.appendChild(loading);
    const params = new URLSearchParams({
      family: state.family,
      q: state.query,
      offset: String(state.offset),
      limit: String(state.limit),
    });
    try {
      const data = await jsonFetch('/api/image/list?' + params.toString());
      if (seq !== state.listSeq) return;
      state.items = data.items;
      state.total = data.total;
      renderList();
    } catch (e) {
      if (seq !== state.listSeq) return;
      els.imageList.textContent = '';
      const empty = document.createElement('div');
      empty.className = 'empty';
      empty.textContent = e.message;
      els.imageList.appendChild(empty);
      toast(e.message, true);
    }
  }

  function renderList() {
    els.imageList.textContent = '';
    els.imageCount.textContent = state.total.toLocaleString() + ' 张';
    const start = state.total ? state.offset + 1 : 0;
    const end = Math.min(state.offset + state.items.length, state.total);
    els.pageLabel.textContent = `${start}–${end} / ${state.total.toLocaleString()}`;
    els.prevPage.disabled = state.offset <= 0;
    els.nextPage.disabled = state.offset + state.limit >= state.total;

    if (!state.items.length) {
      const empty = document.createElement('div');
      empty.className = 'empty';
      empty.textContent = state.query ? '没有匹配的图片' : '该分组没有图片';
      els.imageList.appendChild(empty);
      return;
    }
    for (const item of state.items) {
      const row = document.createElement('div');
      row.className = 'image-row' + (state.selected && state.selected.path === item.path ? ' active' : '');
      row.dataset.path = item.path;

      const top = document.createElement('div');
      top.className = 'image-row-top';
      const name = document.createElement('span');
      name.className = 'image-row-name';
      name.textContent = item.name;
      name.title = item.path;
      top.appendChild(name);

      const badge = document.createElement('span');
      if (item.source && item.override) {
        badge.className = 'badge both';
        badge.textContent = '原版+覆盖';
      } else if (item.override) {
        badge.className = 'badge override';
        badge.textContent = '覆盖';
      } else {
        badge.className = 'badge source';
        badge.textContent = '仅原版';
      }
      top.appendChild(badge);

      const dir = document.createElement('div');
      dir.className = 'image-row-dir';
      dir.textContent = item.dir;
      dir.title = item.dir;
      row.append(top, dir);
      row.addEventListener('click', () => selectImage(item));
      els.imageList.appendChild(row);
    }
  }

  function fmtSize(value) {
    if (value === null || value === undefined) return '—';
    if (value < 1024) return value + ' B';
    if (value < 1024 * 1024) return (value / 1024).toFixed(1) + ' KB';
    return (value / 1024 / 1024).toFixed(2) + ' MB';
  }

  function clearSelection() {
    state.selected = null;
    els.imageTitle.textContent = '选择一张图片';
    els.imagePath.textContent = '';
    for (const pair of [
      [els.sourceImg, els.sourceCanvas, els.sourceBadge],
      [els.overrideImg, els.overrideCanvas, els.overrideBadge],
    ]) {
      pair[0].hidden = true;
      pair[0].removeAttribute('src');
      pair[2].className = 'badge muted-badge';
      pair[2].textContent = '未选择';
    }
    els.sourceMeta.textContent = '';
    els.overrideMeta.textContent = '';
    els.diffBar.classList.add('hidden');
  }

  function selectImage(item) {
    state.selected = item;
    for (const row of document.querySelectorAll('.image-row')) {
      row.classList.toggle('active', row.dataset.path === item.path);
    }
    els.imageTitle.textContent = item.name;
    els.imagePath.textContent = item.path;
    els.imagePath.title = item.path;
    els.sourceBadge.className = 'badge ' + (item.source ? 'source' : 'muted-badge');
    els.sourceBadge.textContent = item.source ? '存在' : '缺失';
    els.overrideBadge.className = 'badge ' + (item.override ? 'override' : 'muted-badge');
    els.overrideBadge.textContent = item.override ? '存在' : '缺失';
    els.sourceMeta.textContent = item.source
      ? `大小 ${fmtSize(item.source_size)}` : '游戏目录中未找到同名文件';
    els.overrideMeta.textContent = item.override
      ? `大小 ${fmtSize(item.override_size)}` : '仓库中没有中文覆盖图';
    updatePreview();
    loadCompare();
  }

  function previewUrl(side) {
    if (!state.selected) return '';
    const p = new URLSearchParams({
      path: state.selected.path,
      side,
      alpha: state.alpha ? '1' : '0',
      t: String(Date.now()),
    });
    return '/api/image/preview?' + p.toString();
  }

  function bindImage(img, side) {
    const item = state.selected;
    const exists = item && item[side];
    const empty = img.parentElement.querySelector('.image-empty');
    if (!exists) {
      img.hidden = true;
      img.removeAttribute('src');
      if (empty) empty.classList.remove('hidden');
      return;
    }
    if (empty) empty.classList.add('hidden');
    img.hidden = false;
    img.onload = () => {
      img.dataset.naturalWidth = String(img.naturalWidth);
      img.dataset.naturalHeight = String(img.naturalHeight);
      applyZoom(img);
    };
    img.onerror = () => {
      img.hidden = true;
      if (empty) {
        empty.classList.remove('hidden');
        empty.textContent = side === 'source'
          ? '无法读取原版图（检查游戏目录）'
          : '无法读取覆盖图';
      }
    };
    img.src = previewUrl(side);
  }

  function applyZoom(img) {
    if (!img || img.hidden) return;
    const width = Number(img.dataset.naturalWidth || img.naturalWidth || 0);
    img.style.width = width ? `${Math.round(width * state.zoom)}px` : '';
  }

  function updatePreview() {
    bindImage(els.sourceImg, 'source');
    bindImage(els.overrideImg, 'override');
  }

  function applyZoomAll() {
    for (const img of [els.sourceImg, els.overrideImg]) applyZoom(img);
  }

  async function loadCompare() {
    if (!state.selected || !state.selected.source || !state.selected.override) {
      els.diffBar.classList.add('hidden');
      return;
    }
    const seq = ++state.compareSeq;
    try {
      const data = await jsonFetch('/api/image/compare?path=' +
        encodeURIComponent(state.selected.path));
      if (seq !== state.compareSeq) return;
      els.diffBar.classList.remove('hidden');
      els.diffBar.textContent = '';
      if (!data.same_size) {
        els.diffBar.innerHTML = '';
        const b = document.createElement('strong');
        b.textContent = '尺寸不同：';
        const t = document.createElement('span');
        t.className = 'warn';
        t.textContent = `${data.source.size.join('×')} vs ${data.override.size.join('×')}`;
        els.diffBar.append(b, t);
        return;
      }
      const strong = document.createElement('strong');
      if (data.diff_pixels === 0) {
        strong.className = 'good';
        strong.textContent = '像素完全一致';
      } else {
        strong.className = 'warn';
        strong.textContent = `差异 ${data.diff_pixels.toLocaleString()} / ` +
          `${data.total_pixels.toLocaleString()} 像素 ` +
          `(${(data.ratio * 100).toFixed(2)}%)`;
      }
      els.diffBar.appendChild(strong);
      if (data.bbox) {
        const span = document.createElement('span');
        span.textContent = ` · 差异范围 ${data.bbox.join(', ')}`;
        els.diffBar.appendChild(span);
      }
    } catch (e) {
      if (seq !== state.compareSeq) return;
      els.diffBar.classList.remove('hidden');
      els.diffBar.textContent = '无法比较：' + e.message;
    }
  }

  async function exportEdb() {
    if (!els.gameDir.value.trim()) {
      toast('请先设置游戏目录', true);
      return;
    }
    if (!els.lcf2xmlPath.value.trim()) {
      toast('请先选择 lcf2xml.exe', true);
      return;
    }
    if (!(await saveConfig())) return;
    els.exportEdb.disabled = true;
    els.checkImages.disabled = true;
    els.buildImages.disabled = true;
    try {
      const data = await jsonFetch('/api/image/export-edb', {
        method: 'POST',
        body: '{}',
      });
      state.jobId = data.job_id;
      els.jobStatus.className = 'job-status running';
      els.jobStatus.textContent = '正在从 RPG_RT.ldb 导出 EDB…';
      els.jobLog.classList.add('show');
      els.jobLog.textContent = '';
      pollJob();
    } catch (e) {
      els.exportEdb.disabled = false;
      els.checkImages.disabled = false;
      els.buildImages.disabled = false;
      toast(e.message, true);
    }
  }

  async function startJob(mode) {
    const info = familyInfo(state.family);
    if (!info || !info.generator) return;
    if (mode === 'build' && !confirm('生成会直接覆盖 language/zh_CN 中对应图片，继续吗？')) return;
    const body = { family: state.family, mode };
    if (state.family === 'Menu') body.kind = els.genKind.value;
    try {
      const data = await jsonFetch('/api/image/generate', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      state.jobId = data.job_id;
      els.exportEdb.disabled = true;
      els.checkImages.disabled = true;
      els.buildImages.disabled = true;
      els.jobStatus.className = 'job-status running';
      els.jobStatus.textContent = '任务运行中…';
      els.jobLog.classList.add('show');
      els.jobLog.textContent = '';
      pollJob();
    } catch (e) {
      toast(e.message, true);
    }
  }

  async function jobDone(job) {
    state.jobId = null;
    els.checkImages.disabled = false;
    els.buildImages.disabled = false;
    els.exportEdb.disabled = false;
    if (job.family === 'EDB') {
      if (job.status === 'ok') {
        els.edbPath.value = job.result_path || els.edbPath.value;
        els.jobStatus.className = 'job-status ok';
        els.jobStatus.textContent = 'EDB 导出完成，已更新配置';
        await loadConfig();
        toast('EDB 已导出并保存');
      } else {
        els.jobStatus.className = 'job-status failed';
        els.jobStatus.textContent = `EDB 导出失败（退出码 ${job.returncode}）`;
        toast('EDB 导出失败，查看日志', true);
      }
      return;
    }
    if (job.status === 'ok') {
      els.jobStatus.className = 'job-status ok';
      els.jobStatus.textContent = `任务完成（退出码 ${job.returncode}）`;
      toast('图片任务完成');
      loadList();
      if (state.selected) loadCompare();
    } else {
      els.jobStatus.className = 'job-status failed';
      els.jobStatus.textContent = `任务失败（退出码 ${job.returncode}）`;
      toast('图片任务失败，查看日志', true);
    }
  }

  async function pollJob() {
    if (!state.jobId) return;
    clearTimeout(state.jobTimer);
    try {
      const job = await jsonFetch('/api/image/job/' + encodeURIComponent(state.jobId));
      els.jobLog.textContent = (job.log || []).join('\n');
      els.jobLog.scrollTop = els.jobLog.scrollHeight;
      if (job.status === 'running') {
        els.jobStatus.className = 'job-status running';
        els.jobStatus.textContent = `任务运行中…（${job.family} / ${job.mode}）`;
        state.jobTimer = setTimeout(pollJob, 900);
      } else {
        await jobDone(job);
      }
    } catch (e) {
      toast(e.message, true);
      state.jobId = null;
      els.checkImages.disabled = false;
      els.buildImages.disabled = false;
    }
  }

  els.pickGame.addEventListener('click', () => pickPath('dir', els.gameDir, '选择 RyonaRPG 游戏目录'));
  els.pickEdb.addEventListener('click', () => pickPath('file', els.edbPath, '选择 RPG_RT.edb'));
  els.pickLcf.addEventListener('click', () => pickPath('file', els.lcf2xmlPath, '选择 lcf2xml.exe'));
  els.pickFont.addEventListener('click', () => pickPath('file', els.fontPath, '选择字体文件'));
  els.exportEdb.addEventListener('click', exportEdb);
  els.saveConfig.addEventListener('click', saveConfig);
  els.prevPage.addEventListener('click', () => {
    state.offset = Math.max(0, state.offset - state.limit);
    loadList();
  });
  els.nextPage.addEventListener('click', () => {
    if (state.offset + state.limit >= state.total) return;
    state.offset += state.limit;
    loadList();
  });
  els.imageSearch.addEventListener('input', () => {
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(() => {
      state.query = els.imageSearch.value.trim();
      state.offset = 0;
      loadList();
    }, 220);
  });
  els.alphaToggle.addEventListener('change', () => {
    state.alpha = els.alphaToggle.checked;
    updatePreview();
    if (state.selected) loadCompare();
  });
  for (const btn of document.querySelectorAll('.zoom-btn')) {
    btn.addEventListener('click', () => {
      state.zoom = Number(btn.dataset.zoom);
      for (const b of document.querySelectorAll('.zoom-btn')) {
        b.classList.toggle('active', b === btn);
      }
      applyZoomAll();
    });
  }
  els.checkImages.addEventListener('click', () => startJob('check'));
  els.buildImages.addEventListener('click', () => startJob('build'));

  (async function init() {
    try {
      await loadConfig();
      updateGenerator();
      await loadList();
    } catch (e) {
      toast(e.message, true);
      els.status.textContent = '图片工具不可用';
    }
  })();
})();
