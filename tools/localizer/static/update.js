(() => {
  const $ = (id) => document.getElementById(id);
  const els = {
    newGameDir: $('newGameDir'),
    oldGameDir: $('oldGameDir'),
    pickNewGame: $('pickNewGame'),
    pickOldGame: $('pickOldGame'),
    run: $('runUpdateCheck'),
    hint: $('updateHint'),
    topStatus: $('updateTopStatus'),
    empty: $('updateEmpty'),
    results: $('updateResults'),
    summary: $('updateSummary'),
    recommendations: $('updateRecommendations'),
    details: $('updateDetails'),
    toast: $('updateToast'),
  };

  function toast(message, isError = false) {
    els.toast.textContent = message;
    els.toast.classList.toggle('error', !!isError);
    els.toast.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => els.toast.classList.remove('show'), 3200);
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

  async function loadConfig() {
    try {
      const data = await jsonFetch('/api/image/config');
      if (!els.newGameDir.value) els.newGameDir.value = data.config.game_dir || '';
      const savedOld = localStorage.getItem('ryona_update_old_game');
      if (!els.oldGameDir.value && savedOld) els.oldGameDir.value = savedOld;
      updateHint();
    } catch (e) {
      toast(e.message, true);
    }
  }

  function updateHint() {
    const hasNew = !!els.newGameDir.value.trim();
    const hasOld = !!els.oldGameDir.value.trim();
    els.hint.textContent = hasNew
      ? (hasOld ? '将比较新旧目录的 LDB/LMT/地图/图片' : '未选旧目录：只核对 LDB 哈希')
      : '请选择新游戏目录';
  }

  async function pickDir(target, title) {
    try {
      const data = await jsonFetch('/api/image/pick', {
        method: 'POST',
        body: JSON.stringify({ kind: 'dir', title }),
      });
      if (!data.path) return;
      target.value = data.path;
      updateHint();
      if (target === els.newGameDir) {
        await jsonFetch('/api/image/config', {
          method: 'POST',
          body: JSON.stringify({ game_dir: data.path }),
        });
      }
    } catch (e) {
      toast(e.message, true);
    }
  }

  function shortSha(value) {
    return value ? value.slice(0, 12) + '…' : '—';
  }

  function card(label, value, sub, cls = '') {
    const div = document.createElement('div');
    div.className = 'update-card ' + cls;
    const l = document.createElement('div');
    l.className = 'label';
    l.textContent = label;
    const v = document.createElement('div');
    v.className = 'value';
    v.textContent = value;
    const s = document.createElement('div');
    s.className = 'sub';
    s.textContent = sub || '';
    div.append(l, v, s);
    return div;
  }

  function countDiff(diff) {
    return diff ? diff.added.length + diff.removed.length + diff.changed.length : 0;
  }

  function render(data) {
    els.empty.classList.add('hidden');
    els.results.classList.remove('hidden');
    els.summary.textContent = '';

    const ldbOk = data.ldb.matches_compat;
    els.summary.appendChild(card(
      'LDB / compat',
      ldbOk ? '一致' : '不一致',
      `SHA ${shortSha(data.ldb.sha256)}`,
      ldbOk ? 'good' : 'bad'));

    const mapsDiff = data.changes.maps;
    const mapChanges = mapsDiff ? countDiff(mapsDiff) : null;
    els.summary.appendChild(card(
      '地图',
      `${data.counts.maps.toLocaleString()} 个`,
      mapChanges === null ? '未比较旧目录' : `变化 ${mapChanges} 个`,
      mapChanges ? 'warn' : ''));

    let imageChanges = 0;
    for (const diff of Object.values(data.changes.images || {})) {
      imageChanges += countDiff(diff);
    }
    const imageTotal = Object.values(data.counts.images || {})
      .reduce((a, b) => a + b, 0);
    els.summary.appendChild(card(
      '图片',
      `${imageTotal.toLocaleString()} 张`,
      data.changes.images ? `变化 ${imageChanges} 张` : '未比较旧目录',
      imageChanges ? 'warn' : ''));

    els.summary.appendChild(card(
      '语言包',
      `${data.counts.po_files.toLocaleString()} 个 PO`,
      ldbOk ? '可继续 QA/合并' : '先更新 compat 与重导数据',
      ldbOk ? '' : 'warn'));

    els.recommendations.textContent = '';
    for (const text of data.recommendations || []) {
      const li = document.createElement('li');
      li.textContent = text;
      els.recommendations.appendChild(li);
    }

    els.details.textContent = '';
    if (!data.old_game_dir) {
      const p = document.createElement('p');
      p.textContent = '未提供旧游戏目录，无法列出具体变化文件和图片。';
      els.details.appendChild(p);
    } else {
      const changes = data.changes;
      const status = document.createElement('p');
      status.className = data.has_changes ? 'warn' : 'ok';
      status.textContent = data.has_changes
        ? '检测到结构变化，需要按左侧建议处理。'
        : '未检测到 LDB/LMT/地图/图片结构变化。';
      els.details.appendChild(status);

      if (changes.maps) {
        appendDiffDetails(els.details, '地图文件', changes.maps);
      }
      for (const [family, diff] of Object.entries(changes.images || {})) {
        if (countDiff(diff)) appendDiffDetails(els.details, `图片 ${family}`, diff);
      }
    }

    let top = '检查完成';
    if (!ldbOk) top = 'LDB 哈希不一致';
    else if (!data.old_game_dir) top = '哈希核对完成';
    else if (data.has_changes) top = '发现结构变化';
    else top = '未发现结构变化';
    els.topStatus.textContent = top;
  }

  function appendDiffDetails(parent, title, diff) {
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = `${title}：+${diff.added.length} / -${diff.removed.length} / ~${diff.changed.length}`;
    details.appendChild(summary);
    for (const [kind, values] of [
      ['新增', diff.added], ['删除', diff.removed], ['变更', diff.changed],
    ]) {
      if (!values.length) continue;
      const heading = document.createElement('div');
      heading.textContent = `${kind}（${values.length}）`;
      details.appendChild(heading);
      const ul = document.createElement('ul');
      for (const value of values) {
        const li = document.createElement('li');
        li.textContent = value;
        ul.appendChild(li);
      }
      details.appendChild(ul);
    }
    parent.appendChild(details);
  }

  async function runCheck() {
    const gameDir = els.newGameDir.value.trim();
    const oldGameDir = els.oldGameDir.value.trim();
    if (!gameDir) {
      toast('请先选择新游戏目录', true);
      return;
    }
    localStorage.setItem('ryona_update_old_game', oldGameDir);
    els.run.disabled = true;
    els.hint.textContent = '检查中：正在计算 LDB/地图/图片哈希，可能需要几秒…';
    els.topStatus.textContent = '检查中…';
    try {
      const data = await jsonFetch('/api/update/check', {
        method: 'POST',
        body: JSON.stringify({ game_dir: gameDir, old_game_dir: oldGameDir }),
      });
      render(data);
      toast('检查完成');
    } catch (e) {
      toast(e.message, true);
      els.topStatus.textContent = '检查失败';
    } finally {
      els.run.disabled = false;
      updateHint();
    }
  }

  els.pickNewGame.addEventListener('click', () => pickDir(els.newGameDir, '选择新游戏目录'));
  els.pickOldGame.addEventListener('click', () => pickDir(els.oldGameDir, '选择旧游戏目录'));
  els.newGameDir.addEventListener('input', updateHint);
  els.oldGameDir.addEventListener('input', updateHint);
  els.run.addEventListener('click', runCheck);

  loadConfig();
})();
