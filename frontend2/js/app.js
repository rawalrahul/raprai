/**
 * RAPR AI v2 — Main Application Controller
 * Connects State, WebSocket, API, Toast, and CommandPalette systems to the DOM
 * This is the brain of the frontend application
 */

// ──────────────────────────────────────────────────────────────────────────────
// DOM References (cached once for performance)
// ──────────────────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

// ──────────────────────────────────────────────────────────────────────────────
// Helper Functions
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Escape HTML special characters to prevent XSS
 */
function escHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Format timestamp as relative time ("2m ago", "Yesterday", etc.)
 */
function formatTime(timestamp) {
  if (!timestamp) return '';

  const date = new Date(timestamp);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
  if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';

  // Check if it's yesterday
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';

  // Check if it's this year
  if (date.getFullYear() === now.getFullYear()) {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

/**
 * Format date string to user-friendly format
 */
function formatDate(dateStr) {
  if (!dateStr) return '';

  const date = new Date(dateStr);
  const today = new Date();

  if (date.toDateString() === today.toDateString()) return 'Today';

  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Remove markdown code block fences from text
 */
function stripCodeBlocks(text) {
  if (!text) return '';
  return text.replace(/```[\s\S]*?```/g, '').trim();
}

/**
 * Truncate text to maximum length with ellipsis
 */
function truncate(str, maxLen) {
  if (!str) return '';
  if (str.length <= maxLen) return str;
  return str.substring(0, maxLen - 3) + '...';
}

/**
 * Create AI color indicator span
 */
function createAiBadge(aiName, aiColor) {
  const badge = document.createElement('span');
  badge.className = 'ai-badge';
  badge.textContent = aiName.substring(0, 2).toUpperCase();
  badge.style.backgroundColor = aiColor || '#6366f1';
  badge.style.color = 'white';
  badge.style.fontSize = '0.7em';
  badge.style.padding = '0.15em 0.35em';
  badge.style.borderRadius = '2px';
  badge.style.marginLeft = '0.5em';
  return badge;
}

// ──────────────────────────────────────────────────────────────────────────────
// Theme Management
// ──────────────────────────────────────────────────────────────────────────────

function initTheme() {
  // Load theme from localStorage or default to 'dark'
  const savedTheme = localStorage.getItem('raprTheme');
  const theme = savedTheme || 'dark';
  State.set('theme', theme);
  document.documentElement.dataset.theme = theme;
  updateThemeButton();
}

function toggleTheme() {
  const newTheme = State.theme === 'dark' ? 'light' : 'dark';
  State.set('theme', newTheme);
  document.documentElement.dataset.theme = newTheme;
  localStorage.setItem('raprTheme', newTheme);
  updateThemeButton();
  Toast.info(`Switched to ${newTheme} mode`);
}

function updateThemeButton() {
  const btn = $('theme-btn');
  if (!btn) return;
  const useEl = btn.querySelector('use');
  if (useEl) {
    useEl.setAttribute('href', State.theme === 'dark' ? '#icon-sun' : '#icon-moon');
  }
  btn.title = State.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
}

// ──────────────────────────────────────────────────────────────────────────────
// Sidebar Management
// ──────────────────────────────────────────────────────────────────────────────

function toggleSidebar() {
  const sidebar = $('sidebar');
  const main = $('main');
  if (!sidebar) return;

  const isCollapsed = sidebar.classList.contains('collapsed');
  sidebar.classList.toggle('collapsed');
  if (main) main.classList.toggle('sidebar-collapsed');

  // Update collapse button icon direction
  const collapseBtn = $('sidebar-toggle');
  if (collapseBtn) {
    const useEl = collapseBtn.querySelector('use');
    if (useEl) {
      useEl.setAttribute('href', isCollapsed ? '#icon-chevron-left' : '#icon-chevron-right');
    }
    collapseBtn.title = isCollapsed ? 'Collapse' : 'Expand';
  }
}

/**
 * Render active sessions list in sidebar
 */
function renderSessions() {
  const container = $('sidebar-sessions');
  if (!container) return;

  container.innerHTML = '';

  if (!State.sessions || State.sessions.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'sidebar-empty';
    empty.textContent = 'No active sessions';
    container.appendChild(empty);
    return;
  }

  State.sessions.forEach(session => {
    const item = document.createElement('div');
    item.className = 'sidebar-item';
    if (session.id === State.focusedId) {
      item.classList.add('active');
    }

    // Status indicator
    const statusDot = document.createElement('div');
    statusDot.className = 'sidebar-item-status';
    statusDot.classList.add(
      session.status === 'busy' ? 'idle' :
      session.status === 'error' ? 'offline' :
      'online'
    );

    // AI icon
    const icon = document.createElement('div');
    icon.className = 'sidebar-item-icon';
    icon.textContent = (session.ai_name || 'AI').substring(0, 2).toUpperCase();
    icon.style.color = session.ai_color || 'var(--color-primary)';

    // Session name
    const name = document.createElement('span');
    name.className = 'truncate';
    name.style.flex = '1';
    name.textContent = truncate(session.name, 25);

    // Timer if busy
    let timerEl = null;
    if (session.busy_since) {
      timerEl = document.createElement('span');
      timerEl.className = 'sidebar-item-timer';
      timerEl.textContent = '...';
    }

    item.appendChild(icon);
    item.appendChild(name);
    if (timerEl) item.appendChild(timerEl);
    item.appendChild(statusDot);

    // Click to focus
    item.addEventListener('click', () => {
      WS.sendCommand(`focus_session:${session.id}`);
    });

    // Right-click context menu
    item.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      showSessionContextMenu(e, session);
    });

    container.appendChild(item);
  });
}

/**
 * Show context menu for session (right-click)
 */
function showSessionContextMenu(e, session) {
  // Remove existing context menu if any
  const existing = document.querySelector('.context-menu');
  if (existing) existing.remove();

  const menu = document.createElement('div');
  menu.className = 'context-menu';
  menu.style.position = 'fixed';
  menu.style.left = e.clientX + 'px';
  menu.style.top = e.clientY + 'px';
  menu.style.zIndex = '10000';
  menu.style.backgroundColor = 'var(--bg-secondary)';
  menu.style.border = '1px solid var(--border)';
  menu.style.borderRadius = '4px';
  menu.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';

  const options = [
    { label: 'Rename', action: () => renameSession(session.id) },
    { label: 'Archive', action: () => archiveSession(session.id) },
    { label: 'Delete', action: () => deleteSession(session.id) },
  ];

  options.forEach(opt => {
    const item = document.createElement('div');
    item.style.padding = '8px 16px';
    item.style.cursor = 'pointer';
    item.style.borderBottom = '1px solid var(--border)';
    item.textContent = opt.label;
    item.addEventListener('click', () => {
      opt.action();
      menu.remove();
    });
    item.addEventListener('mouseenter', () => {
      item.style.backgroundColor = 'var(--bg-tertiary)';
    });
    item.addEventListener('mouseleave', () => {
      item.style.backgroundColor = 'transparent';
    });
    menu.appendChild(item);
  });

  document.body.appendChild(menu);

  // Close menu on click outside
  setTimeout(() => {
    document.addEventListener('click', function closeMenu() {
      menu.remove();
      document.removeEventListener('click', closeMenu);
    }, 0);
  });
}

async function renameSession(sessionId) {
  const newName = prompt('New session name:');
  if (newName && newName.trim()) {
    try {
      await API.sessions.update(sessionId, { name: newName.trim() });
      Toast.success('Session renamed');
      WS.sendCommand('list_sessions');
    } catch (err) {
      Toast.error('Failed to rename: ' + err.message);
    }
  }
}

async function archiveSession(sessionId) {
  if (confirm('Archive this session?')) {
    try {
      await API.sessions.archive(sessionId);
      Toast.success('Session archived');
      WS.sendCommand('list_sessions');
    } catch (err) {
      Toast.error('Failed to archive: ' + err.message);
    }
  }
}

async function deleteSession(sessionId) {
  if (confirm('Delete this session? This cannot be undone.')) {
    try {
      await API.sessions.delete(sessionId);
      Toast.success('Session deleted');
      WS.sendCommand('list_sessions');
    } catch (err) {
      Toast.error('Failed to delete: ' + err.message);
    }
  }
}

/**
 * Render a sidebar section (History, Templates, Tasks, etc.)
 */
function renderSidebarSection(section, data) {
  const sectionEl = $(section);
  if (!sectionEl) return;

  const body = sectionEl.querySelector('.section-body');
  if (!body) return;

  body.innerHTML = '';

  if (!data || data.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'sidebar-empty';
    empty.textContent = 'No items';
    body.appendChild(empty);
    return;
  }

  data.forEach(item => {
    const el = document.createElement('div');
    el.className = 'sidebar-item';
    el.textContent = truncate(item.name || item.title || item.id, 30);
    el.addEventListener('click', () => {
      if (section === 'sb-history') {
        viewHistory(item.id);
      } else if (section === 'sb-templates') {
        useTemplate(item.id);
      } else if (section === 'sb-tasks') {
        editTask(item.id);
      }
    });
    body.appendChild(el);
  });
}

/**
 * Load sidebar history list
 */
async function loadSidebarHistory() {
  try {
    const data = await API.history.list();
    const historyData = (data.histories || data || []).map(h => ({
      id: h.date || h.id,
      name: formatDate(h.date || h.id) + (h.message_count ? ` (${h.message_count})` : '')
    }));
    renderSidebarSection('sb-history', historyData);
  } catch (err) {
    console.warn('loadSidebarHistory failed:', err);
  }
}

/**
 * Load sidebar templates
 */
async function loadSidebarTemplates() {
  try {
    const data = await API.templates.list();
    renderSidebarSection('sb-templates', data.templates || []);
  } catch (err) {
    console.warn('loadSidebarTemplates failed:', err);
  }
}

/**
 * Render scheduled tasks in sidebar
 */
function renderScheduledTasks(tasks) {
  const taskData = (tasks || []).map(t => ({
    id: t.id,
    name: t.description || t.id
  }));
  renderSidebarSection('sb-tasks', taskData);
}

/**
 * Filter sidebar session list by query
 */
function filterSidebar(query) {
  const items = $$('.sidebar-item');
  const q = query.toLowerCase();

  items.forEach(item => {
    const name = item.textContent.toLowerCase();
    item.style.display = name.includes(q) ? 'flex' : 'none';
  });
}

/**
 * Toggle sidebar section collapse/expand
 */
function toggleSection(sectionEl) {
  if (!sectionEl) return;
  const body = sectionEl.querySelector('.sidebar-section-list, .section-body');
  if (!body) return;

  const isCollapsed = body.classList.contains('collapsed');
  body.classList.toggle('collapsed');

  const header = sectionEl.querySelector('.sidebar-section-header, .section-header');
  if (header) {
    header.classList.toggle('collapsed', !isCollapsed);
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Header Management
// ──────────────────────────────────────────────────────────────────────────────

function updateHeader() {
  const session = State.getFocusedSession();
  const sessionNameEl = $('session-name');
  const aiBadgeEl = $('ai-badge');
  const cwdDisplay = $('cwd-display');
  const contextBar = $('context-bar');

  if (!session) {
    if (sessionNameEl) sessionNameEl.textContent = 'No session';
    if (aiBadgeEl) aiBadgeEl.innerHTML = '';
    if (cwdDisplay) cwdDisplay.textContent = '~/';
    if (contextBar) contextBar.style.display = 'none';
    return;
  }

  if (sessionNameEl) sessionNameEl.textContent = truncate(session.name, 40);

  if (aiBadgeEl) {
    const aiName = session.ai_name || 'AI';
    aiBadgeEl.textContent = aiName;
    // Update badge color class
    aiBadgeEl.className = 'badge badge-' + aiName.toLowerCase().replace(/[^a-z]/g, '');
  }

  if (cwdDisplay) {
    cwdDisplay.textContent = truncate(State.focusedCwd || '~/', 50);
  }

  updateContextBar(session);
  updateConnectionStatus();
}

/**
 * Update context window usage bar
 */
function updateContextBar(session) {
  const bar = $('context-bar');
  const label = $('context-label');

  if (!bar || !label || !session.context_used || !session.context_limit) {
    if (bar) bar.style.display = 'none';
    return;
  }

  const used = session.context_used;
  const limit = session.context_limit;
  const percent = Math.min(100, Math.floor((used / limit) * 100));

  bar.style.display = 'flex';
  const fill = bar.querySelector('.context-fill');
  if (fill) {
    fill.style.width = percent + '%';
    fill.style.backgroundColor =
      percent > 90 ? '#ef4444' :
      percent > 75 ? '#f97316' :
      '#10b981';
  }

  label.textContent = `${percent}%`;
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus() {
  // Update the AI dot in the header breadcrumb
  const dot = $('ai-dot');
  if (dot) {
    if (State.connected) {
      dot.style.backgroundColor = 'var(--color-claude)';
      dot.title = 'Connected';
    } else if (State.connecting) {
      dot.style.backgroundColor = '#eab308';
      dot.title = 'Connecting...';
    } else {
      dot.style.backgroundColor = '#ef4444';
      dot.title = 'Disconnected';
    }
  }

  // Update the connection indicator dot in header-right
  const indicator = $('connection-indicator');
  if (indicator) {
    indicator.className = 'header-status-dot';
    if (State.connected) {
      indicator.classList.add('online');
      indicator.title = 'Connected';
    } else if (State.connecting) {
      indicator.classList.add('connecting');
      indicator.title = 'Connecting...';
    } else {
      indicator.classList.add('offline');
      indicator.title = 'Disconnected';
    }
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Chat Messages
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Render a single message to the chat
 */
function renderMessage(msg) {
  if (!msg || !msg.role) return;

  const container = $('messages');
  if (!container) return;

  const session = State.sessions.find(s => s.id === msg.session_id);

  const el = document.createElement('div');
  el.className = 'chat-message ' + msg.role;

  if (msg.role === 'system') {
    el.innerHTML = `
      <div class="chat-avatar system">S</div>
      <div class="chat-bubble">
        <div class="chat-content">${escHtml(msg.content)}</div>
      </div>
    `;
  } else if (msg.role === 'user') {
    const source = msg.source === 'telegram' ? ' (Telegram)' : msg.source === 'voice' ? ' (Voice)' : '';
    el.innerHTML = `
      <div class="chat-avatar user">U</div>
      <div class="chat-bubble">
        <div class="chat-content">${escHtml(msg.content)}</div>
        <div class="chat-metadata">
          <span class="chat-timestamp">${formatTime(msg.timestamp)}${source}</span>
        </div>
      </div>
    `;
  } else if (msg.role === 'assistant') {
    const aiName = session?.ai_name || 'AI';
    const aiColor = session?.ai_color || 'var(--color-claude)';
    const initials = aiName.substring(0, 2).toUpperCase();
    el.innerHTML = `
      <div class="chat-avatar assistant" style="background:${aiColor}">${initials}</div>
      <div class="chat-bubble">
        <div class="chat-content">${escHtml(msg.content)}</div>
        <div class="chat-metadata">
          <span>${escHtml(aiName)}</span>
          <span class="chat-timestamp">${formatTime(msg.timestamp)}</span>
        </div>
      </div>
    `;
  }

  container.appendChild(el);
  updateEmptyState();
  scrollChat();
}

/**
 * Clear all messages from chat
 */
function clearMessages() {
  const container = $('messages');
  if (container) container.innerHTML = '';
  updateEmptyState();
}

/**
 * Scroll chat to bottom
 */
function scrollChat() {
  const chat = $('chat-scroll') || $('chat');
  if (chat) {
    setTimeout(() => {
      chat.scrollTop = chat.scrollHeight;
    }, 0);
  }
}

/**
 * Show/hide empty state based on message count
 */
function updateEmptyState() {
  const empty = $('empty-state');
  if (!empty) return;

  const hasMessages = $('messages') && $('messages').children.length > 0;
  empty.style.display = hasMessages ? 'none' : 'flex';
}

// ──────────────────────────────────────────────────────────────────────────────
// Thinking Indicator
// ──────────────────────────────────────────────────────────────────────────────

function updateThinking() {
  const t = State.thinking[State.focusedId];
  const el = $('thinking');

  if (!el) return;

  if (t && t.active) {
    el.hidden = false;
    const label = $('thinking-label');
    if (label) label.textContent = (t.ai || 'AI') + ' is thinking...';
  } else {
    el.hidden = true;
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Input and Message Sending
// ──────────────────────────────────────────────────────────────────────────────

function initInput() {
  const input = $('message-input');
  const sendBtn = $('send-btn');

  if (!input || !sendBtn) return;

  // Auto-grow textarea
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    const scrollHeight = input.scrollHeight;
    input.style.height = Math.min(scrollHeight, 200) + 'px';
    sendBtn.disabled = !input.value.trim();
  });

  // Enter to send, Shift+Enter for newline
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener('click', sendMessage);

  // Initial state
  sendBtn.disabled = true;
}

function sendMessage() {
  const input = $('message-input');
  if (!input) return;

  const text = input.value.trim();
  if (!text || !State.connected) {
    if (!State.connected) Toast.warning('Not connected');
    return;
  }

  // Return to live if viewing history
  if (State.viewingHistory) {
    returnToLive();
  }

  // Send via WebSocket
  WS.sendMessage(text, State.focusedId);

  // Clear input
  input.value = '';
  input.style.height = 'auto';
  const sendBtn = $('send-btn');
  if (sendBtn) sendBtn.disabled = true;
}

// ──────────────────────────────────────────────────────────────────────────────
// File Upload
// ──────────────────────────────────────────────────────────────────────────────

function initFileUpload() {
  const clipBtn = $('clip-btn');
  const fileInput = $('file-input');
  const inputArea = $('input-area');

  if (clipBtn && fileInput) {
    clipBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileUpload);
  }

  // Paste handler
  document.addEventListener('paste', handlePaste);

  // Drag and drop
  if (inputArea) {
    inputArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      inputArea.classList.add('drag-over');
    });
    inputArea.addEventListener('dragleave', () => {
      inputArea.classList.remove('drag-over');
    });
    inputArea.addEventListener('drop', handleDrop);
  }
}

async function handleFileUpload(e) {
  const files = e.target.files;
  if (!files || files.length === 0) return;

  for (const file of files) {
    try {
      const form = new FormData();
      form.append('file', file);

      const data = await API.files.upload(form);
      if (data.filename) {
        const input = $('message-input');
        if (input) {
          const prefix = input.value.trim() ? ' ' : '';
          input.value += prefix + `[📎 ${data.filename}]`;
          input.dispatchEvent(new Event('input'));
          Toast.success(`Uploaded: ${data.filename}`);
        }
      }
    } catch (err) {
      Toast.error('Upload failed: ' + (err.message || 'Unknown error'));
    }
  }

  const fileInput = $('file-input');
  if (fileInput) fileInput.value = '';
}

function handlePaste(e) {
  const items = e.clipboardData?.items || [];

  for (const item of items) {
    if (item.kind === 'file' && item.type.startsWith('image/')) {
      const file = item.getAsFile();
      if (file) {
        const syntheticEvent = { target: { files: [file] } };
        handleFileUpload(syntheticEvent);
      }
    }
  }
}

function handleDrop(e) {
  e.preventDefault();
  const inputArea = $('input-area');
  if (inputArea) inputArea.classList.remove('drag-over');

  const files = e.dataTransfer?.files || [];
  if (files.length > 0) {
    const syntheticEvent = { target: { files } };
    handleFileUpload(syntheticEvent);
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Voice Recording and Transcription
// ──────────────────────────────────────────────────────────────────────────────

let _mediaRec = null;
let _audioChunks = [];
let _isRecording = false;
let _voiceTargetSession = null;

function initVoice() {
  const micBtn = $('mic-btn');
  if (micBtn) {
    micBtn.addEventListener('click', toggleVoiceRec);
  }
}

async function toggleVoiceRec() {
  if (_isRecording) {
    stopVoiceRec();
  } else {
    startVoiceRec();
  }
}

async function startVoiceRec() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    _mediaRec = new MediaRecorder(stream);
    _audioChunks = [];
    _isRecording = true;
    _voiceTargetSession = State.focusedId;

    const micBtn = $('mic-btn');
    if (micBtn) {
      micBtn.classList.add('recording');
      micBtn.title = 'Click to stop recording';
    }

    Toast.info('Recording...');

    _mediaRec.addEventListener('dataavailable', (e) => {
      _audioChunks.push(e.data);
    });

    _mediaRec.start();
  } catch (err) {
    Toast.error('Microphone access denied: ' + err.message);
  }
}

async function stopVoiceRec() {
  if (!_mediaRec || !_isRecording) return;

  _isRecording = false;
  _mediaRec.stop();

  const micBtn = $('mic-btn');
  if (micBtn) {
    micBtn.classList.remove('recording');
    micBtn.title = 'Record voice message';
  }

  // Wait for mediarecorder to finish
  await new Promise(resolve => {
    _mediaRec.addEventListener('stop', resolve, { once: true });
  });

  // Create audio blob
  const audioBlob = new Blob(_audioChunks, { type: 'audio/webm' });
  _audioChunks = [];

  // Stop all tracks
  _mediaRec.stream.getTracks().forEach(t => t.stop());
  _mediaRec = null;

  // Upload and transcribe
  try {
    Toast.info('Transcribing...');

    const form = new FormData();
    form.append('audio', audioBlob, 'voice.webm');

    const data = await API.files.transcribe(form);
    if (data.text) {
      // Insert transcribed text into input
      const input = $('message-input');
      if (input) {
        input.value = data.text;
        input.dispatchEvent(new Event('input'));

        // Auto-send if configured
        if (RAPR_CONFIG.voiceAutoSend) {
          setTimeout(sendMessage, 100);
        }
      }
      Toast.success('Transcribed');
    }
  } catch (err) {
    Toast.error('Transcription failed: ' + (err.message || 'Unknown error'));
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// History Viewing
// ──────────────────────────────────────────────────────────────────────────────

async function viewHistory(date) {
  try {
    const data = await API.history.get(date);
    const messages = data.messages || data || [];

    State.set('viewingHistory', true);
    State.set('viewedHistoryId', date);

    clearMessages();
    messages.forEach(msg => renderMessage(msg));

    showHistoryBanner(date);
    scrollChat();
    Toast.info(`Viewing history: ${formatDate(date)}`);
  } catch (err) {
    Toast.error('Failed to load history: ' + err.message);
  }
}

function returnToLive() {
  State.set('viewingHistory', false);
  State.set('viewedHistoryId', null);
  hideHistoryBanner();
  clearMessages();

  // Re-render current session messages
  State.messages.forEach(msg => {
    if (!msg.session_id || msg.session_id === State.focusedId) {
      renderMessage(msg);
    }
  });

  scrollChat();
}

function showHistoryBanner(date) {
  const banner = $('history-banner');
  const text = $('history-banner-text');

  if (banner && text) {
    text.textContent = `Viewing history: ${formatDate(date)}`;
    banner.classList.add('visible');
  }
}

function hideHistoryBanner() {
  const banner = $('history-banner');
  if (banner) {
    banner.classList.remove('visible');
  }
}

async function resumeSession(date) {
  try {
    const data = await API.history.resume(date);
    // Clear and reload with resumed context
    clearMessages();
    (data.messages || []).forEach(msg => renderMessage(msg));
    State.set('viewingHistory', false);
    hideHistoryBanner();
    scrollChat();
    Toast.success('Session resumed');
  } catch (err) {
    Toast.error('Failed to resume: ' + err.message);
  }
}

async function useTemplate(templateId) {
  try {
    const data = await API.templates.get(templateId);
    const input = $('message-input');
    if (input && data.content) {
      input.value = data.content;
      input.dispatchEvent(new Event('input'));
      input.focus();
      Toast.info('Template loaded');
    }
  } catch (err) {
    Toast.error('Failed to load template: ' + err.message);
  }
}

async function editTask(taskId) {
  openModal('memory-modal');
  // Modal should load the task details
  try {
    const data = await API.tasks.get(taskId);
    const form = $('memory-modal');
    if (form && data) {
      form.dataset.taskId = taskId;
      // Populate form with task data
      const input = form.querySelector('textarea');
      if (input) input.value = data.content || '';
    }
  } catch (err) {
    Toast.error('Failed to load task: ' + err.message);
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Working Directory (CWD)
// ──────────────────────────────────────────────────────────────────────────────

function initCwd() {
  const display = $('cwd-display');
  const input = $('cwd-input');
  const browseBtn = document.querySelector('[data-action="browse-dir"]');

  if (display) {
    display.addEventListener('click', enterCwdEdit);
  }

  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const path = input.value.trim();
        if (path) applyCwd(path);
      } else if (e.key === 'Escape') {
        exitCwdEdit();
      }
    });
    input.addEventListener('blur', exitCwdEdit);
  }

  if (browseBtn) {
    browseBtn.addEventListener('click', openBrowse);
  }
}

function enterCwdEdit() {
  const display = $('cwd-display');
  const input = $('cwd-input');

  if (display && input) {
    display.style.display = 'none';
    input.value = State.focusedCwd || '';
    input.style.display = 'block';
    input.focus();
    input.select();
  }
}

function exitCwdEdit() {
  const display = $('cwd-display');
  const input = $('cwd-input');

  if (display && input) {
    input.style.display = 'none';
    display.style.display = 'block';
  }
}

function applyCwd(path) {
  if (!path) return;

  State.set('focusedCwd', path);
  updateHeader();
  exitCwdEdit();

  // Send to backend
  WS.sendCommand(`set_cwd:${path}`);
  Toast.info(`Working directory: ${path}`);
}

function updateCwdDisplay(path) {
  const display = $('cwd-display');
  if (display) {
    display.textContent = truncate(path || '~/', 50);
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Directory Browse Modal
// ──────────────────────────────────────────────────────────────────────────────

async function openBrowse() {
  // Try native picker first
  if (window.showDirectoryPicker) {
    try {
      const dir = await window.showDirectoryPicker();
      applyCwd(dir.name);
      return;
    } catch (err) {
      // User cancelled or not supported
    }
  }

  // Fallback to modal
  openModal('browse-modal');
  await loadBrowseDir(State.focusedCwd || '/');
}

async function loadBrowseDir(path) {
  try {
    const data = await API.browse.list(path);
    const container = $('browse-modal')?.querySelector('.browse-list');

    if (!container) return;
    container.innerHTML = '';

    const dirs = data.dirs || [];

    dirs.forEach(dir => {
      const item = document.createElement('div');
      item.className = 'browse-item';
      item.textContent = '📁 ' + dir.name;
      item.addEventListener('click', () => {
        const fullPath = path.endsWith('/') ? path + dir.name : path + '/' + dir.name;
        loadBrowseDir(fullPath);
      });
      container.appendChild(item);
    });

    if (dirs.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'sidebar-empty';
      empty.textContent = 'No subdirectories';
      container.appendChild(empty);
    }

    // Show parent dir button
    if (path !== '/') {
      const parentBtn = document.createElement('div');
      parentBtn.className = 'browse-item browse-parent';
      parentBtn.textContent = '📁 ..';
      parentBtn.addEventListener('click', () => {
        const parent = path.substring(0, path.lastIndexOf('/')) || '/';
        loadBrowseDir(parent);
      });
      container.insertBefore(parentBtn, container.firstChild);
    }

  } catch (err) {
    Toast.error('Failed to list directory: ' + err.message);
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Approval System
// ──────────────────────────────────────────────────────────────────────────────

function showApproval(approval) {
  const banner = $('approval-banner');
  const text = $('approval-text');
  const approveBtn = $('approval-approve');
  const denyBtn = $('approval-deny');

  if (!banner || !text) return;

  text.textContent = approval.description || 'Approval required';
  banner.classList.add('visible');

  if (approveBtn) {
    approveBtn.onclick = async () => {
      try {
        await API.approval.resolve(approval.id, true);
        hideApproval();
        Toast.success('Approved');
      } catch (err) {
        Toast.error('Failed to approve: ' + err.message);
      }
    };
  }

  if (denyBtn) {
    denyBtn.onclick = async () => {
      try {
        await API.approval.resolve(approval.id, false);
        hideApproval();
        Toast.warning('Denied');
      } catch (err) {
        Toast.error('Failed to deny: ' + err.message);
      }
    };
  }
}

function hideApproval() {
  const banner = $('approval-banner');
  if (banner) {
    banner.classList.remove('visible');
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Pipeline Visualization
// ──────────────────────────────────────────────────────────────────────────────

function handlePipelineUpdate(pipeline) {
  if (!pipeline) return;

  const panel = $('right-panel');
  if (!panel) return;

  let pipelineEl = panel.querySelector(`[data-pipeline-id="${pipeline.id}"]`);
  if (!pipelineEl) {
    pipelineEl = document.createElement('div');
    pipelineEl.className = 'pipeline-card';
    pipelineEl.setAttribute('data-pipeline-id', pipeline.id);
    panel.appendChild(pipelineEl);
  }

  // Render pipeline progress
  let html = `<div class="pipeline-header">${escHtml(pipeline.name || pipeline.id)}</div>`;
  html += '<div class="pipeline-steps">';

  (pipeline.steps || []).forEach(step => {
    const status = step.status || 'pending';
    const icon =
      status === 'completed' ? '✓' :
      status === 'running' ? '⊙' :
      status === 'error' ? '✗' :
      '○';

    html += `
      <div class="pipeline-step step-${status}">
        <span class="step-icon">${icon}</span>
        <span class="step-name">${escHtml(step.name)}</span>
      </div>
    `;
  });

  html += '</div>';
  pipelineEl.innerHTML = html;
}

function handlePipelineStream(pipelineId, stepId, chunk) {
  const pipelineEl = $('right-panel')?.querySelector(`[data-pipeline-id="${pipelineId}"]`);
  if (!pipelineEl) return;

  let outputEl = pipelineEl.querySelector(`[data-step-output="${stepId}"]`);
  if (!outputEl) {
    outputEl = document.createElement('div');
    outputEl.className = 'step-output';
    outputEl.setAttribute('data-step-output', stepId);
    pipelineEl.appendChild(outputEl);
  }

  outputEl.textContent += escHtml(chunk);
}

// ──────────────────────────────────────────────────────────────────────────────
// Modal Management
// ──────────────────────────────────────────────────────────────────────────────

function openModal(id) {
  closeAllModals();
  const modal = $(id);
  if (!modal) return;

  modal.classList.add('visible');
  modal.classList.add('open');
  State.set('activeModal', id);

  // Call modal-specific init if needed
  if (id === 'settings-modal') initSettingsModal();
  else if (id === 'history-modal') initHistoryModal();
  else if (id === 'packages-modal') initPackagesModal();
  else if (id === 'memory-modal') initMemoryModal();
}

function closeModal() {
  const modal = State.activeModal ? $(State.activeModal) : null;
  if (modal) {
    modal.classList.remove('visible');
    modal.classList.remove('open');
    State.set('activeModal', null);
  }
}

function closeAllModals() {
  $$('.modal-overlay').forEach(m => {
    m.classList.remove('visible');
    m.classList.remove('open');
  });
  State.set('activeModal', null);
}

async function initSettingsModal() {
  // Load and populate settings
  try {
    const settings = await API.settings.get();
    const form = $('settings-modal');
    if (!form) return;

    Object.keys(settings).forEach(key => {
      const input = form.querySelector(`[name="${key}"]`);
      if (input) {
        if (input.type === 'checkbox') {
          input.checked = settings[key];
        } else {
          input.value = settings[key];
        }
      }
    });
  } catch (err) {
    console.warn('Failed to load settings:', err);
  }
}

async function saveSettings() {
  try {
    const form = $('settings-modal');
    if (!form) return;

    const formData = new FormData(form);
    const settings = Object.fromEntries(formData);

    await API.settings.save(settings);
    Toast.success('Settings saved');
    closeModal();
  } catch (err) {
    Toast.error('Failed to save settings: ' + err.message);
  }
}

async function initHistoryModal() {
  try {
    const data = await API.history.list();
    const list = $('history-modal')?.querySelector('.history-list');
    if (!list) return;

    list.innerHTML = '';
    (data.histories || []).forEach(h => {
      const item = document.createElement('div');
      item.className = 'history-item';
      item.innerHTML = `
        <div class="history-date">${formatDate(h.date || h.id)}</div>
        <div class="history-messages">${h.message_count || 0} messages</div>
      `;
      item.addEventListener('click', () => {
        viewHistory(h.date || h.id);
        closeModal();
      });
      list.appendChild(item);
    });
  } catch (err) {
    Toast.error('Failed to load history: ' + err.message);
  }
}

async function initPackagesModal() {
  try {
    const data = await API.packages.list();
    const list = $('packages-modal')?.querySelector('.packages-list');
    if (!list) return;

    list.innerHTML = '';
    (data.packages || []).forEach(pkg => {
      const card = document.createElement('div');
      card.className = 'package-card';
      card.innerHTML = `
        <div class="package-name">${escHtml(pkg.name)}</div>
        <div class="package-desc">${escHtml(pkg.description || '')}</div>
        <div class="package-version">v${escHtml(pkg.version || '1.0')}</div>
      `;
      list.appendChild(card);
    });
  } catch (err) {
    Toast.error('Failed to load packages: ' + err.message);
  }
}

async function initMemoryModal() {
  try {
    const data = await API.memory.list();
    const list = $('memory-modal')?.querySelector('.memory-list');
    if (!list) return;

    list.innerHTML = '';
    (data.memories || []).forEach(mem => {
      const item = document.createElement('div');
      item.className = 'memory-item';
      item.innerHTML = `
        <div class="memory-title">${escHtml(mem.title || 'Untitled')}</div>
        <div class="memory-content">${escHtml(truncate(mem.content || '', 100))}</div>
      `;
      item.addEventListener('click', () => {
        const textarea = $('memory-modal')?.querySelector('textarea');
        if (textarea) {
          textarea.value = mem.content || '';
        }
      });
      list.appendChild(item);
    });
  } catch (err) {
    Toast.error('Failed to load memories: ' + err.message);
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Integrations
// ──────────────────────────────────────────────────────────────────────────────

async function loadIntegrations() {
  try {
    const data = await API.integrations.list();
    const integrations = data.integrations || [];

    State.set('integrations', integrations);

    // Inject CSS variables for AI colors
    integrations.forEach(i => {
      document.documentElement.style.setProperty(
        '--color-' + (i.key || i.id),
        i.color || '#6366f1'
      );
    });

    // Add session creation commands to CommandPalette
    integrations.forEach(i => {
      CommandPalette.registerCommand({
        id: 'new-' + (i.key || i.id),
        label: 'New ' + (i.name || 'AI') + ' Session',
        category: 'Sessions',
        action: () => WS.sendCommand(`new_session:${i.key || i.id}`)
      });
    });
  } catch (err) {
    console.warn('loadIntegrations failed:', err);
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// WebSocket Event Handlers
// ──────────────────────────────────────────────────────────────────────────────

function initWebSocket() {
  WS.on('connected', () => {
    console.log('[RAPR AI] Connected to backend');
    const wasReconnect = State._hasConnectedOnce;
    State.set('connected', true);
    State.set('connecting', false);
    State._hasConnectedOnce = true;
    updateConnectionStatus();
    hideConnectionBanner();
    if (wasReconnect) Toast.success('Reconnected to RAPR AI');

    // Load initial data
    loadIntegrations();
    loadSidebarHistory();
    loadSidebarTemplates();
    WS.sendCommand('schedule_list');
  });

  WS.on('disconnected', (event) => {
    console.log('[RAPR AI] Disconnected from backend', event);
    const wasConnected = State.connected;
    State.set('connected', false);
    State.set('connecting', false);
    updateConnectionStatus();

    // Only show banner if we previously had a successful connection
    // (don't flash "Connection lost" on first page load)
    if (wasConnected || State._hasConnectedOnce) {
      if (event.code === 4401) {
        showConnectionBanner('Session expired — please re-login', 'error', '/login');
      } else {
        showConnectionBanner('Connection lost — retrying...', 'warning');
      }
    }
  });

  WS.on('message', (msg) => {
    if (msg && msg.content) {
      State.messages.push(msg);

      // Render if current session or no session filter
      if (!State.viewingHistory && (!msg.session_id || msg.session_id === State.focusedId)) {
        renderMessage(msg);
      }

      // Desktop notification if tab not focused
      if (msg.role === 'assistant' && document.hidden) {
        sendDesktopNotification(msg);
      }
    }
  });

  WS.on('state', (s) => {
    const oldFocusedId = State.focusedId;

    State.update({
      sessions: s.sessions || [],
      focusedId: s.focused_id || null,
      focusedAi: s.focused_ai || null,
      focusedCwd: s.focused_cwd || '',
    });

    renderSessions();
    updateHeader();

    // Re-render messages if focus changed
    if (oldFocusedId !== State.focusedId && !State.viewingHistory) {
      clearMessages();
      State.messages.forEach(msg => {
        if (!msg.session_id || msg.session_id === State.focusedId) {
          renderMessage(msg);
        }
      });
      scrollChat();
    }

    updateThinking();
  });

  WS.on('thinking', (d) => {
    if (d.session_id) {
      if (d.active) {
        State.thinking[d.session_id] = { active: true, ai: d.ai };
      } else {
        delete State.thinking[d.session_id];
      }
    }
    updateThinking();
  });

  WS.on('cwd', (d) => {
    State.set('focusedCwd', d.path || '');
    updateCwdDisplay(d.path || '');
  });

  WS.on('schedule_list', (d) => {
    State.set('scheduledTasks', d.tasks || []);
    renderScheduledTasks(d.tasks || []);
  });

  WS.on('pipeline_update', (d) => {
    if (d.pipeline) handlePipelineUpdate(d.pipeline);
  });

  WS.on('pipeline_step_stream', (d) => {
    if (d.pipeline_id && d.step_id) {
      handlePipelineStream(d.pipeline_id, d.step_id, d.chunk || '');
    }
  });

  WS.on('approval_request', (d) => {
    if (d.approval) showApproval(d.approval);
  });

  WS.on('approval_resolved', () => {
    hideApproval();
  });

  WS.on('error', (err) => {
    console.error('[RAPR AI] WebSocket error:', err);
    Toast.error('Error: ' + (err.message || 'Unknown'));
  });

  // Connect to backend
  WS.connect();
}

// ──────────────────────────────────────────────────────────────────────────────
// Desktop Notifications
// ──────────────────────────────────────────────────────────────────────────────

function sendDesktopNotification(msg) {
  if (!('Notification' in window)) return;

  if (Notification.permission === 'granted') {
    const session = State.sessions.find(s => s.id === msg.session_id);
    const title = session?.name || 'RAPR AI';
    const content = stripCodeBlocks(msg.content);

    new Notification(title, {
      body: truncate(content, 100),
      icon: '/static/icon.png',
      tag: msg.session_id || 'rapr'
    });
  } else if (Notification.permission !== 'denied') {
    Notification.requestPermission();
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Connection Banner
// ──────────────────────────────────────────────────────────────────────────────

function showConnectionBanner(msg, type, actionUrl) {
  const banner = $('conn-banner');
  const bannerMsg = $('conn-banner-msg');
  const bannerAction = $('conn-banner-action');

  if (!banner) return;

  if (bannerMsg) bannerMsg.textContent = msg;
  banner.className = 'input-connection-banner visible ' + (type || '');

  if (actionUrl && bannerAction) {
    bannerAction.textContent = 'Reload';
    bannerAction.onclick = () => window.location.href = actionUrl;
    bannerAction.style.display = 'block';
  } else if (bannerAction) {
    bannerAction.style.display = 'none';
  }
}

function hideConnectionBanner() {
  const banner = $('conn-banner');
  if (banner) {
    banner.classList.remove('visible');
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Keyboard Shortcuts
// ──────────────────────────────────────────────────────────────────────────────

function initKeyboard() {
  document.addEventListener('keydown', (e) => {
    // Cmd/Ctrl + B: Toggle sidebar
    if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
      e.preventDefault();
      toggleSidebar();
    }

    // Cmd/Ctrl + Shift + T: Toggle theme
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'T') {
      e.preventDefault();
      toggleTheme();
    }

    // Escape: Close modals/command palette
    if (e.key === 'Escape') {
      closeAllModals();
      CommandPalette.close?.();
    }

    // Cmd/Ctrl + ,: Open settings
    if ((e.metaKey || e.ctrlKey) && e.key === ',') {
      e.preventDefault();
      openModal('settings-modal');
    }
  });
}

// ──────────────────────────────────────────────────────────────────────────────
// Right Panel Toggle
// ──────────────────────────────────────────────────────────────────────────────

function initRightPanel() {
  const toggle = $('right-panel-toggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      const panel = $('right-panel');
      if (panel) {
        panel.classList.toggle('open');
      }
    });
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Initialization — Entry Point
// ──────────────────────────────────────────────────────────────────────────────

async function init() {
  console.log('[RAPR AI] Initializing v2 frontend...');

  // Apply theme
  initTheme();

  // Initialize notification systems
  if (Toast && Toast.init) Toast.init();
  if (CommandPalette && CommandPalette.init) CommandPalette.init();

  // Set up DOM interactions
  initInput();
  initFileUpload();
  initVoice();
  initCwd();
  initKeyboard();
  initRightPanel();

  // Sidebar and header controls
  const sidebarToggle = $('sidebar-toggle');
  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', toggleSidebar);
  }

  const themeBtn = $('theme-btn');
  if (themeBtn) {
    themeBtn.addEventListener('click', toggleTheme);
  }

  // Sidebar section collapse handlers
  $$('.section-header').forEach(el => {
    el.addEventListener('click', () => {
      const section = el.closest('.sidebar-section');
      if (section) toggleSection(section);
    });
  });

  // Sidebar search/filter
  const sidebarSearch = $('sidebar-search');
  if (sidebarSearch) {
    sidebarSearch.addEventListener('input', (e) => {
      filterSidebar(e.target.value);
    });
  }

  // New Session button
  const newSessionBtn = $('new-session-btn');
  if (newSessionBtn) {
    newSessionBtn.addEventListener('click', () => {
      WS.sendCommand('new_session:claude');
    });
  }

  // Settings button
  const settingsBtn = $('settings-btn');
  if (settingsBtn) {
    settingsBtn.addEventListener('click', () => {
      openModal('settings-modal');
    });
  }

  // Command palette trigger (⌘K icon in header)
  const cmdTrigger = $('command-palette-trigger');
  if (cmdTrigger) {
    cmdTrigger.addEventListener('click', () => {
      if (CommandPalette && CommandPalette.toggle) CommandPalette.toggle();
    });
  }

  // Directory select button in browse modal
  const dirSelectBtn = $('directory-select-btn');
  if (dirSelectBtn) {
    dirSelectBtn.addEventListener('click', () => {
      const pathDisplay = $('directory-path');
      if (pathDisplay && pathDisplay.textContent) {
        WS.sendCommand('change_cwd', { path: pathDisplay.textContent });
        closeModal();
      }
    });
  }

  // History banner close button
  const histBannerClose = $('history-banner-close');
  if (histBannerClose) {
    histBannerClose.addEventListener('click', () => {
      hideHistoryBanner();
      State.set('viewingHistory', false);
      // Re-render current session messages
      clearMessages();
      State.messages.forEach(msg => {
        if (!msg.session_id || msg.session_id === State.focusedId) {
          renderMessage(msg);
        }
      });
      scrollChat();
    });
  }

  // Modal backdrop click-to-close handlers
  $$('.modal-backdrop').forEach(el => {
    el.addEventListener('click', (e) => {
      if (e.target === el) closeModal();
    });
  });

  // Modal close buttons (X buttons inside modals)
  $$('.modal-close').forEach(btn => {
    btn.addEventListener('click', () => closeModal());
  });

  // Initialize WebSocket event handlers, then connect
  initWebSocket();

  // Actually establish the WebSocket connection
  State.set('connected', false);
  State.set('connecting', true);
  WS.connect();

  console.log('[RAPR AI] v2 frontend initialized successfully');
}

// Boot when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
