/**
 * Reactive State Manager
 *
 * Centralized state container for the entire application with reactive updates.
 * Any component can subscribe to state changes and receive automatic notifications.
 *
 * Usage:
 *   State.on('connected', (connected) => console.log('Connected:', connected));
 *   State.set('connected', true);
 *   State.update({ theme: 'light', sidebarOpen: false });
 *   const focused = State.getFocusedSession();
 */

const State = {
  // ==================== Session State ====================

  /**
   * Active sessions
   * @type {Array<Object>}
   */
  sessions: [],

  /**
   * Currently focused session ID
   * @type {string|null}
   */
  focusedId: null,

  /**
   * AI provider of focused session (claude, gemini, ollama, custom)
   * @type {string|null}
   */
  focusedAi: null,

  /**
   * Current working directory in focused session
   * @type {string}
   */
  focusedCwd: '',

  // ==================== Connection State ====================

  /**
   * WebSocket connection status
   * @type {boolean}
   */
  connected: false,

  // ==================== UI State ====================

  /**
   * Current theme (light, dark, auto)
   * @type {string}
   */
  theme: localStorage.getItem('raprTheme') || 'dark',

  /**
   * Sidebar visibility
   * @type {boolean}
   */
  sidebarOpen: true,

  /**
   * Right panel visibility (for previews, details, etc.)
   * @type {boolean}
   */
  rightPanelOpen: false,

  /**
   * Active modal dialog (null, 'settings', 'history', 'packages', 'memory', etc.)
   * @type {string|null}
   */
  activeModal: null,

  /**
   * Command palette open state
   * @type {boolean}
   */
  commandPaletteOpen: false,

  // ==================== Chat State ====================

  /**
   * Current chat messages
   * @type {Array<Object>}
   */
  messages: [],

  /**
   * Viewing historical conversation
   * @type {boolean}
   */
  viewingHistory: false,

  /**
   * ID of history session being viewed
   * @type {string|null}
   */
  viewedHistoryId: null,

  /**
   * Thinking status by session ID
   * Maps sessionId -> { active: boolean, ai: string, startTime: number }
   * @type {Object}
   */
  thinking: {},

  /**
   * Current input buffer (unsent message)
   * @type {string}
   */
  inputBuffer: '',

  // ==================== Data Caches ====================

  /**
   * Available integrations
   * @type {Array<Object>}
   */
  integrations: [],

  /**
   * History list (sessions)
   * @type {Array<Object>}
   */
  historyList: [],

  /**
   * Saved prompt templates
   * @type {Array<Object>}
   */
  templates: [],

  /**
   * Knowledge base memories
   * @type {Array<Object>}
   */
  memories: [],

  /**
   * Scheduled tasks
   * @type {Array<Object>}
   */
  scheduledTasks: [],

  /**
   * Available packages
   * @type {Array<Object>}
   */
  packages: [],

  /**
   * Pending approvals
   * @type {Array<Object>}
   */
  pendingApprovals: [],

  /**
   * User settings
   * @type {Object}
   */
  settings: {},

  /**
   * Current user info
   * @type {Object}
   */
  user: {},

  // ==================== Internal State ====================

  /**
   * Event listeners by key
   * Maps key -> [callback]
   * @type {Object}
   * @private
   */
  _listeners: {},

  /**
   * Register listener for state key changes
   *
   * Listener will be called with (newValue, key) whenever that key changes.
   * Use '*' as key to listen to all changes.
   *
   * @param {string} key - State key to watch (or '*' for all)
   * @param {Function} callback - Called with (newValue, key)
   *
   * @example
   *   State.on('connected', (connected) => {
   *     console.log('Connection status:', connected);
   *   });
   *
   * @example
   *   State.on('*', (value, key) => {
   *     console.log(key, 'changed to:', value);
   *   });
   */
  on(key, callback) {
    if (!this._listeners[key]) {
      this._listeners[key] = [];
    }
    this._listeners[key].push(callback);

    // Return unsubscribe function
    return () => this.off(key, callback);
  },

  /**
   * Unregister listener
   *
   * @param {string} key - State key
   * @param {Function} callback - Callback to remove
   */
  off(key, callback) {
    if (!this._listeners[key]) return;
    const index = this._listeners[key].indexOf(callback);
    if (index > -1) {
      this._listeners[key].splice(index, 1);
    }
  },

  /**
   * Set state value and notify listeners
   *
   * Only notifies if value actually changed (shallow equality).
   * Triggers callbacks for both the specific key and '*' wildcard.
   *
   * @param {string} key - State key
   * @param {*} value - New value
   *
   * @example
   *   State.set('connected', true);
   *   State.set('theme', 'light');
   *   State.set('messages', [...State.messages, newMessage]);
   */
  set(key, value) {
    // Avoid redundant updates
    if (this[key] === value) return;

    const oldValue = this[key];
    this[key] = value;

    // Persist theme preference
    if (key === 'theme') {
      localStorage.setItem('raprTheme', value);
    }

    // Notify listeners for specific key
    if (this._listeners[key]) {
      this._listeners[key].forEach((callback) => {
        try {
          callback(value, key);
        } catch (error) {
          console.error('[State] Listener error for', key, ':', error);
        }
      });
    }

    // Notify wildcard listeners
    if (this._listeners['*']) {
      this._listeners['*'].forEach((callback) => {
        try {
          callback(value, key);
        } catch (error) {
          console.error('[State] Listener error for *:', error);
        }
      });
    }

    console.log('[State]', key, '=', value);
  },

  /**
   * Batch update multiple state values
   *
   * More efficient than multiple set() calls when updating many keys.
   * Each key change triggers listeners independently.
   *
   * @param {Object} updates - Object with keys to update
   *
   * @example
   *   State.update({
   *     connected: true,
   *     theme: 'dark',
   *     sidebarOpen: false
   *   });
   */
  update(updates) {
    Object.entries(updates).forEach(([key, value]) => {
      this.set(key, value);
    });
  },

  /**
   * Get focused session object
   *
   * Returns the full session object for the currently focused session,
   * or null if no session is focused.
   *
   * @returns {Object|null} Focused session or null
   *
   * @example
   *   const session = State.getFocusedSession();
   *   if (session) {
   *     console.log('Focused on:', session.name);
   *   }
   */
  getFocusedSession() {
    if (!this.focusedId) return null;
    return this.sessions.find((s) => s.id === this.focusedId) || null;
  },

  /**
   * Clear all state (for logout/reset)
   *
   * Resets all state to initial values.
   */
  clear() {
    this.update({
      sessions: [],
      focusedId: null,
      focusedAi: null,
      focusedCwd: '',
      messages: [],
      inputBuffer: '',
      viewingHistory: false,
      viewedHistoryId: null,
      thinking: {},
      integrations: [],
      historyList: [],
      templates: [],
      memories: [],
      scheduledTasks: [],
      packages: [],
      pendingApprovals: [],
    });
  },

  /**
   * Get state snapshot for debugging
   *
   * @returns {Object} Current full state
   */
  snapshot() {
    return {
      // Session
      sessions: this.sessions,
      focusedId: this.focusedId,
      focusedAi: this.focusedAi,
      // Connection
      connected: this.connected,
      // UI
      theme: this.theme,
      sidebarOpen: this.sidebarOpen,
      rightPanelOpen: this.rightPanelOpen,
      activeModal: this.activeModal,
      commandPaletteOpen: this.commandPaletteOpen,
      // Chat
      messages: this.messages,
      viewingHistory: this.viewingHistory,
      inputBuffer: this.inputBuffer,
      // Caches
      integrations: this.integrations,
      historyList: this.historyList,
      templates: this.templates,
      memories: this.memories,
      scheduledTasks: this.scheduledTasks,
      packages: this.packages,
      pendingApprovals: this.pendingApprovals,
    };
  },
};

// Seal to prevent accidental property additions
Object.seal(State);
