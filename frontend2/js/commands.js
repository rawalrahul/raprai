/**
 * Command Palette System
 *
 * Global keyboard-driven command launcher with fuzzy search filtering.
 * Provides fast access to core features and commands via Cmd/Ctrl+K shortcut.
 *
 * Usage:
 *   CommandPalette.open();
 *   CommandPalette.toggle();
 *   CommandPalette.registerCommand({
 *     id: 'custom-action',
 *     label: 'Do Something Custom',
 *     category: 'Custom',
 *     action: () => console.log('Executed')
 *   });
 */

const CommandPalette = {
  /**
   * Command palette open state
   * @type {boolean}
   */
  isOpen: false,

  /**
   * Current search query
   * @type {string}
   */
  query: '',

  /**
   * Currently selected result index
   * @type {number}
   */
  selectedIndex: 0,

  /**
   * Filtered search results
   * @type {Array<Object>}
   */
  results: [],

  /**
   * DOM elements
   * @type {Object}
   * @private
   */
  _elements: {
    backdrop: null,
    palette: null,
    input: null,
    resultsList: null,
  },

  /**
   * All available commands
   * @type {Array<Object>}
   */
  commands: [
    // Session commands
    {
      id: 'new-claude',
      label: 'New Claude Session',
      category: 'Sessions',
      shortcut: 'Ctrl+Shift+C',
      action: () => WS.sendCommand('new_session:claude'),
    },
    {
      id: 'new-gemini',
      label: 'New Gemini Session',
      category: 'Sessions',
      shortcut: 'Ctrl+Shift+G',
      action: () => WS.sendCommand('new_session:gemini'),
    },
    {
      id: 'new-ollama',
      label: 'New Ollama Session',
      category: 'Sessions',
      shortcut: 'Ctrl+Shift+O',
      action: () => WS.sendCommand('new_session:ollama'),
    },
    {
      id: 'new-custom',
      label: 'New Custom Integration',
      category: 'Sessions',
      action: () => WS.sendCommand('new_session:custom'),
    },

    // Appearance commands
    {
      id: 'toggle-theme',
      label: 'Toggle Theme',
      category: 'Appearance',
      shortcut: 'Ctrl+Shift+T',
      action: () => {
        const newTheme = State.theme === 'dark' ? 'light' : 'dark';
        State.set('theme', newTheme);
        document.documentElement.setAttribute('data-theme', newTheme);
      },
    },
    {
      id: 'toggle-sidebar',
      label: 'Toggle Sidebar',
      category: 'Appearance',
      shortcut: 'Ctrl+B',
      action: () => State.set('sidebarOpen', !State.sidebarOpen),
    },
    {
      id: 'toggle-right-panel',
      label: 'Toggle Right Panel',
      category: 'Appearance',
      shortcut: 'Ctrl+Shift+P',
      action: () => State.set('rightPanelOpen', !State.rightPanelOpen),
    },

    // Navigation commands
    {
      id: 'settings',
      label: 'Open Settings',
      category: 'Navigation',
      shortcut: 'Ctrl+,',
      action: () => State.set('activeModal', 'settings'),
    },
    {
      id: 'history',
      label: 'Browse History',
      category: 'Navigation',
      shortcut: 'Ctrl+H',
      action: () => State.set('activeModal', 'history'),
    },
    {
      id: 'memory',
      label: 'View Memories',
      category: 'Navigation',
      shortcut: 'Ctrl+M',
      action: () => State.set('activeModal', 'memory'),
    },
    {
      id: 'packages',
      label: 'Browse Marketplace',
      category: 'Navigation',
      shortcut: 'Ctrl+J',
      action: () => State.set('activeModal', 'packages'),
    },
    {
      id: 'templates',
      label: 'View Templates',
      category: 'Navigation',
      action: () => State.set('activeModal', 'templates'),
    },
    {
      id: 'integrations',
      label: 'Manage Integrations',
      category: 'Navigation',
      action: () => State.set('activeModal', 'integrations'),
    },

    // Action commands
    {
      id: 'backup-now',
      label: 'Backup Now',
      category: 'Actions',
      action: async () => {
        try {
          const result = await API.backups.now();
          Toast.success('Backup started: ' + result.job_id);
        } catch (error) {
          Toast.error('Backup failed: ' + error.message);
        }
      },
    },
    {
      id: 'export-session',
      label: 'Export Current Session',
      category: 'Actions',
      action: async () => {
        const session = State.getFocusedSession();
        if (!session) {
          Toast.warning('No session focused');
          return;
        }
        // Trigger export (implementation in main app)
        window.dispatchEvent(new CustomEvent('export-session', { detail: session }));
      },
    },
    {
      id: 'clear-history',
      label: 'Clear All History',
      category: 'Actions',
      action: () => {
        if (confirm('Permanently delete all chat history? This cannot be undone.')) {
          window.dispatchEvent(new CustomEvent('clear-history'));
        }
      },
    },

    // Task commands
    {
      id: 'schedule-list',
      label: 'View Scheduled Tasks',
      category: 'Tasks',
      action: () => WS.sendCommand('schedule_list'),
    },
    {
      id: 'schedule-new',
      label: 'Create Scheduled Task',
      category: 'Tasks',
      action: () => State.set('activeModal', 'schedule-task'),
    },

    // Development commands
    {
      id: 'dev-reload',
      label: 'Reload Application',
      category: 'Development',
      shortcut: 'F5',
      action: () => location.reload(),
    },
    {
      id: 'dev-state-log',
      label: 'Log Current State',
      category: 'Development',
      action: () => {
        console.log('[Development] Current State:', State.snapshot());
      },
    },
    {
      id: 'dev-api-info',
      label: 'Show API Configuration',
      category: 'Development',
      action: () => {
        console.log('[Development] API Config:', RAPR_CONFIG.getInfo());
      },
    },
  ],

  /**
   * Initialize command palette
   *
   * Creates DOM elements and attaches keyboard listeners.
   * Should be called during application startup.
   */
  init() {
    // Create backdrop
    this._elements.backdrop = document.createElement('div');
    this._elements.backdrop.id = 'command-palette-backdrop';
    this._elements.backdrop.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      z-index: 10000;
      display: none;
    `;
    this._elements.backdrop.onclick = () => this.close();
    document.body.appendChild(this._elements.backdrop);

    // Create palette container
    this._elements.palette = document.createElement('div');
    this._elements.palette.id = 'command-palette';
    this._elements.palette.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 90%;
      max-width: 600px;
      max-height: 70vh;
      background: white;
      border-radius: 8px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      z-index: 10001;
      display: none;
      flex-direction: column;
      overflow: hidden;
    `;

    // Create search input
    this._elements.input = document.createElement('input');
    this._elements.input.type = 'text';
    this._elements.input.placeholder = 'Search commands...';
    this._elements.input.style.cssText = `
      padding: 16px;
      border: none;
      border-bottom: 1px solid #e5e7eb;
      font-size: 16px;
      outline: none;
    `;
    this._elements.input.oninput = (e) => this._search(e.target.value);
    this._elements.input.onkeydown = (e) => this._handleInputKeydown(e);
    this._elements.palette.appendChild(this._elements.input);

    // Create results list
    this._elements.resultsList = document.createElement('div');
    this._elements.resultsList.id = 'command-palette-results';
    this._elements.resultsList.style.cssText = `
      flex: 1;
      overflow-y: auto;
      padding: 8px 0;
    `;
    this._elements.palette.appendChild(this._elements.resultsList);

    document.body.appendChild(this._elements.palette);

    // Register keyboard shortcuts
    this._registerKeyboardShortcuts();

    console.log('[CommandPalette] Initialized with', this.commands.length, 'commands');
  },

  /**
   * Open command palette
   */
  open() {
    if (this.isOpen) return;

    this.isOpen = true;
    this.query = '';
    this.selectedIndex = 0;

    this._elements.backdrop.style.display = 'block';
    this._elements.palette.style.display = 'flex';

    // Reset and show all commands
    this.results = [...this.commands];
    this._render();

    // Focus input
    this._elements.input.value = '';
    this._elements.input.focus();

    State.set('commandPaletteOpen', true);
  },

  /**
   * Close command palette
   */
  close() {
    if (!this.isOpen) return;

    this.isOpen = false;
    this._elements.backdrop.style.display = 'none';
    this._elements.palette.style.display = 'none';

    State.set('commandPaletteOpen', false);
  },

  /**
   * Toggle command palette open/closed
   */
  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  },

  /**
   * Register custom command
   *
   * @param {Object} command - Command object with id, label, category, shortcut?, action
   */
  registerCommand(command) {
    if (!command.id || !command.label || !command.action) {
      console.error('[CommandPalette] Invalid command:', command);
      return;
    }

    this.commands.push(command);
    console.log('[CommandPalette] Registered:', command.label);
  },

  /**
   * Internal: Search commands by query
   *
   * Uses fuzzy matching to filter commands by label and category.
   *
   * @param {string} query - Search query
   * @private
   */
  _search(query) {
    this.query = query.toLowerCase();
    this.selectedIndex = 0;

    if (!this.query) {
      this.results = [...this.commands];
    } else {
      this.results = this.commands.filter((cmd) => {
        const label = cmd.label.toLowerCase();
        const category = (cmd.category || '').toLowerCase();
        return this._fuzzyMatch(label) || this._fuzzyMatch(category);
      });
    }

    this._render();
  },

  /**
   * Internal: Fuzzy match a string against query
   *
   * @param {string} str - String to match
   * @returns {boolean} Match found
   * @private
   */
  _fuzzyMatch(str) {
    let queryIdx = 0;
    for (let i = 0; i < str.length && queryIdx < this.query.length; i++) {
      if (str[i] === this.query[queryIdx]) {
        queryIdx++;
      }
    }
    return queryIdx === this.query.length;
  },

  /**
   * Internal: Handle input keyboard events
   *
   * @param {KeyboardEvent} e - Keyboard event
   * @private
   */
  _handleInputKeydown(e) {
    switch (e.key) {
      case 'Escape':
        e.preventDefault();
        this.close();
        break;
      case 'ArrowUp':
        e.preventDefault();
        this._moveSelection(-1);
        break;
      case 'ArrowDown':
        e.preventDefault();
        this._moveSelection(1);
        break;
      case 'Enter':
        e.preventDefault();
        this._execute(this.results[this.selectedIndex]);
        break;
    }
  },

  /**
   * Internal: Move selection up/down
   *
   * @param {number} direction - -1 for up, 1 for down
   * @private
   */
  _moveSelection(direction) {
    this.selectedIndex = Math.max(0, Math.min(this.results.length - 1, this.selectedIndex + direction));
    this._render();

    // Auto-scroll selected item into view
    const items = this._elements.resultsList.querySelectorAll('[data-index]');
    const selectedItem = items[this.selectedIndex];
    if (selectedItem) {
      selectedItem.scrollIntoView({ block: 'nearest' });
    }
  },

  /**
   * Internal: Execute command
   *
   * @param {Object} command - Command to execute
   * @private
   */
  _execute(command) {
    if (!command) return;

    try {
      command.action();
      Toast.success('Executed: ' + command.label);
      console.log('[CommandPalette] Executed:', command.id);
    } catch (error) {
      Toast.error('Command failed: ' + error.message);
      console.error('[CommandPalette] Execution error:', error);
    }

    this.close();
  },

  /**
   * Internal: Render command palette UI
   *
   * @private
   */
  _render() {
    this._elements.resultsList.innerHTML = '';

    if (this.results.length === 0) {
      const noResults = document.createElement('div');
      noResults.textContent = 'No commands found';
      noResults.style.cssText = `
        padding: 32px;
        text-align: center;
        color: #9ca3af;
      `;
      this._elements.resultsList.appendChild(noResults);
      return;
    }

    this.results.forEach((cmd, index) => {
      const item = document.createElement('div');
      item.dataset.index = index;
      item.style.cssText = `
        padding: 12px 16px;
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 3px solid transparent;
        transition: background 0.15s;
        ${index === this.selectedIndex ? 'background: #f3f4f6; border-left-color: #3b82f6;' : 'background: white;'}
      `;

      item.onmouseover = () => {
        this.selectedIndex = index;
        this._render();
      };
      item.onclick = () => this._execute(cmd);

      // Left: Label + Category
      const left = document.createElement('div');
      left.innerHTML = `
        <div style="font-weight: 500; color: #111;">${cmd.label}</div>
        <div style="font-size: 12px; color: #9ca3af;">${cmd.category || 'General'}</div>
      `;
      item.appendChild(left);

      // Right: Shortcut
      if (cmd.shortcut) {
        const shortcut = document.createElement('div');
        shortcut.textContent = cmd.shortcut;
        shortcut.style.cssText = `
          font-size: 12px;
          color: #d1d5db;
          margin-left: 12px;
          white-space: nowrap;
        `;
        item.appendChild(shortcut);
      }

      this._elements.resultsList.appendChild(item);
    });
  },

  /**
   * Internal: Register global keyboard shortcuts
   *
   * @private
   */
  _registerKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Cmd+K or Ctrl+K = toggle palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        this.toggle();
      }

      // Only handle other shortcuts if palette is open
      if (!this.isOpen) return;

      // Escape = close palette (handled in input handler)
      // Arrow keys = navigate (handled in input handler)
      // Enter = execute (handled in input handler)
    });

    // Also listen for individual command shortcuts when palette is closed
    this.commands.forEach((cmd) => {
      if (cmd.shortcut) {
        // Parse shortcut like "Ctrl+Shift+C"
        const parts = cmd.shortcut.split('+');
        const key = parts[parts.length - 1].toLowerCase();
        const ctrl = parts.includes('Ctrl');
        const shift = parts.includes('Shift');
        const alt = parts.includes('Alt');

        // Only register if there's a shortcut and palette is not open
        if (!this.isOpen && ctrl && shift) {
          document.addEventListener('keydown', (e) => {
            if (
              e.ctrlKey === ctrl &&
              e.shiftKey === shift &&
              e.altKey === alt &&
              e.key.toLowerCase() === key
            ) {
              e.preventDefault();
              cmd.action();
            }
          });
        }
      }
    });
  },
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    CommandPalette.init();
  });
} else {
  CommandPalette.init();
}
