/**
 * Model picker: a chip in the message box, next to the AI chip, showing the
 * chat's model and effort ("Opus 5.5 · high ▾"). Clicking it lists the AI's
 * models with a ✓ on the one in use, and the effort levels that model takes. Picking one switches this chat right away (the next message uses
 * it, also mid-conversation) and becomes the model new chats with that AI start
 * with. Other open chats keep their own model. Shown only for AIs that support
 * it (MODEL_PICKER_AIS). DOM APIs only (no innerHTML with data).
 */

const MODEL_PICKER_AIS = ['claude'];
const _modelLabels = {};          // ai -> {id: label}, from the last fetch

function _mEl(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function _modelLabel(ai, id) {
  if (!id) return 'Default';
  return (_modelLabels[ai] && _modelLabels[ai][id]) || id;
}

/** What the chip shows: the version when the menu knows it ("Opus 5.5"), else the name. */
function _rememberLabels(ai, options) {
  _modelLabels[ai] = {};
  options.forEach(o => { if (o.id) _modelLabels[ai][o.id] = (o.sub && !o.group) ? o.sub : o.label; });
}

function _focusedSession() {
  try { return (_sessions || []).find(s => s.id === _focusedId) || null; } catch (_) { return null; }
}

async function _modelsApi(url, opts) {
  const o = Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {});
  if (typeof _csrfToken === 'function') o.headers['x-csrf-token'] = _csrfToken();
  const r = await fetch(url, o);
  let d = {};
  try { d = await r.json(); } catch (_) {}
  if (!r.ok || d.ok === false) throw new Error(d.error || ('HTTP ' + r.status));
  return d;
}

function _modelChip() { return document.getElementById('model-picker'); }
function _modelMenu() { return document.getElementById('model-menu'); }

function _buildModelPicker() {
  if (_modelChip()) return;
  const aiMenu = document.getElementById('ai-menu');
  if (!aiMenu) return;
  const chip = _mEl('button', 'model-picker');
  chip.id = 'model-picker';
  chip.type = 'button';
  chip.hidden = true;
  chip.setAttribute('aria-haspopup', 'true');
  chip.setAttribute('aria-expanded', 'false');
  chip.appendChild(_mEl('span', 'model-picker-label', 'Default'));
  const chev = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  chev.setAttribute('viewBox', '0 0 24 24');
  chev.setAttribute('class', 'chevron');
  chev.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', 'M6 9l6 6 6-6');
  chev.appendChild(path);
  chip.appendChild(chev);
  chip.addEventListener('click', e => { e.stopPropagation(); _toggleModelMenu(); });
  aiMenu.after(chip);

  const menu = _mEl('div', 'ai-menu model-menu');
  menu.id = 'model-menu';
  menu.setAttribute('role', 'menu');
  menu.setAttribute('aria-label', 'Choose the model');
  menu.addEventListener('click', e => e.stopPropagation());
  chip.after(menu);

  document.addEventListener('click', () => _closeModelMenu());
  document.addEventListener('keydown', e => { if (e.key === 'Escape') _closeModelMenu(); });
}

function _closeModelMenu() {
  const menu = _modelMenu(), chip = _modelChip();
  if (menu) menu.classList.remove('open');
  if (chip) { chip.classList.remove('menu-open'); chip.setAttribute('aria-expanded', 'false'); }
}

function _toggleModelMenu() {
  const menu = _modelMenu(), chip = _modelChip();
  if (!menu || !chip) return;
  if (menu.classList.contains('open')) { _closeModelMenu(); return; }
  if (typeof closeAiMenu === 'function') closeAiMenu();
  const sess = _focusedSession();
  if (!sess || !MODEL_PICKER_AIS.includes(sess.ai)) return;
  menu.style.setProperty('left', chip.offsetLeft + 'px', 'important');
  menu.textContent = '';
  menu.appendChild(_mEl('div', 'ai-menu-section', 'Loading models…'));
  menu.classList.add('open');
  chip.classList.add('menu-open');
  chip.setAttribute('aria-expanded', 'true');
  _fillModelMenu(menu, sess);
}

async function _fillModelMenu(menu, sess) {
  const ai = sess.ai;
  let d;
  try {
    d = await _modelsApi('/api/models/' + encodeURIComponent(ai) + '?session=' + encodeURIComponent(sess.id));
  } catch (err) {
    menu.textContent = '';
    menu.appendChild(_mEl('div', 'ai-menu-section', 'Could not load models: ' + err.message));
    return;
  }
  _rememberLabels(ai, d.options);
  menu.textContent = '';
  menu.appendChild(_mEl('div', 'ai-menu-section', (AI_LABEL[ai] || ai) + ' model for this chat'));
  const known = d.options.some(o => (o.id || null) === (d.selected || null));
  const opts = known ? d.options : d.options.concat([{ id: d.selected, label: d.selected, group: 'Your choice' }]);
  let group = null;
  opts.forEach(o => {
    if ((o.group || null) !== group) {
      group = o.group || null;
      if (group) menu.appendChild(_mEl('div', 'ai-menu-section model-group', group));
    }
    const on = (o.id || null) === (d.selected || null);
    const b = _mEl('button', 'ai-menu-item model-item');
    b.type = 'button';
    b.setAttribute('role', 'menuitemradio');
    b.setAttribute('aria-checked', on ? 'true' : 'false');
    if (o.title) b.title = o.title;
    b.appendChild(_mEl('span', 'model-check', on ? '✓' : ''));
    b.appendChild(_mEl('span', 'model-name', o.label));
    if (o.sub && o.sub !== o.label) b.appendChild(_mEl('span', 'model-sub', o.sub));
    b.addEventListener('click', () => _chooseModel(sess, o.id));
    menu.appendChild(b);
  });
  const other = _mEl('button', 'ai-menu-item model-item');
  other.type = 'button';
  other.appendChild(_mEl('span', 'model-check', ''));
  other.appendChild(_mEl('span', 'model-name', 'Other model…'));
  other.title = 'Type any model or exact version, e.g. claude-opus-4-5';
  other.addEventListener('click', () => {
    const name = (prompt('Model name or exact version, as Anthropic writes it (e.g. claude-opus-4-5):', d.selected || '') || '').trim();
    if (name) _chooseModel(sess, name);
  });
  menu.appendChild(other);

  // Effort: the levels Claude Code reports for this chat's model.
  const cur = opts.find(o => (o.id || null) === (d.selected || null));
  const levels = (cur && cur.efforts) || [];
  menu.appendChild(_mEl('div', 'ai-menu-divider'));
  menu.appendChild(_mEl('div', 'ai-menu-section', 'Effort'));
  if (!levels.length) {
    menu.appendChild(_mEl('div', 'model-note', (AI_LABEL[ai] || ai) + " doesn't list effort levels for this model."));
  } else {
    const row = _mEl('div', 'effort-row');
    row.setAttribute('role', 'radiogroup');
    row.setAttribute('aria-label', 'Effort');
    [null].concat(levels).forEach(level => {
      const on = (level || null) === (d.effort || null);
      const b = _mEl('button', 'effort-item' + (on ? ' on' : ''), level || 'Default');
      b.type = 'button';
      b.setAttribute('role', 'radio');
      b.setAttribute('aria-checked', on ? 'true' : 'false');
      b.title = level ? 'Effort level ' + level : "Claude's own default effort (your Claude setting, if you set one)";
      b.addEventListener('click', () => _chooseEffort(sess, level));
      row.appendChild(b);
    });
    menu.appendChild(row);
  }
  if (d.last_used) {
    menu.appendChild(_mEl('div', 'ai-menu-divider'));
    menu.appendChild(_mEl('div', 'model-note', 'Last reply: ' + d.last_used));
  }
}

async function _chooseModel(sess, id) {
  _closeModelMenu();
  try {
    await _modelsApi('/api/sessions/' + encodeURIComponent(sess.id) + '/model', { method: 'PUT', body: JSON.stringify({ model: id }) });
  } catch (err) {
    if (typeof Toast !== 'undefined') Toast.error('Model: ' + err.message);
    return;
  }
  sess.model = id || null;
  sess.model_used = null;
  _updateModelChip();   // the server's state update follows, with effort reset if the new model doesn't take it
}

async function _chooseEffort(sess, level) {
  _closeModelMenu();
  try {
    await _modelsApi('/api/sessions/' + encodeURIComponent(sess.id) + '/effort', { method: 'PUT', body: JSON.stringify({ effort: level }) });
  } catch (err) {
    if (typeof Toast !== 'undefined') Toast.error('Effort: ' + err.message);
    return;
  }
  sess.effort = level || null;
  _updateModelChip();
}

function _updateModelChip() {
  _buildModelPicker();
  const chip = _modelChip();
  if (!chip) return;
  const sess = _focusedSession();
  const show = !!(sess && MODEL_PICKER_AIS.includes(sess.ai));
  chip.hidden = !show;
  if (!show) { _closeModelMenu(); return; }
  chip.querySelector('.model-picker-label').textContent =
    _modelLabel(sess.ai, sess.model) + (sess.effort ? ' · ' + sess.effort : '');
  const title = 'Model for this chat: ' + _modelLabel(sess.ai, sess.model) +
    '\nEffort: ' + (sess.effort || 'Default') +
    (sess.model_used ? '\nLast reply: ' + sess.model_used : '') + '\nClick to change';
  chip.title = title;
  chip.setAttribute('aria-label', title.replace(/\n/g, '. '));
}

// Keep the chip in sync with every state update from the server.
(function () {
  const origApply = window.applyState;
  if (typeof origApply === 'function') {
    window.applyState = function () {
      const r = origApply.apply(this, arguments);
      try { _updateModelChip(); } catch (_) {}
      return r;
    };
  }
  const origToggle = window.toggleAiMenu;
  if (typeof origToggle === 'function') {
    window.toggleAiMenu = function () { _closeModelMenu(); return origToggle.apply(this, arguments); };
  }
  _buildModelPicker();
  _updateModelChip();
  MODEL_PICKER_AIS.forEach(ai => _modelsApi('/api/models/' + ai).then(d => {
    _rememberLabels(ai, d.options);
    _updateModelChip();
  }).catch(() => {}));
})();
