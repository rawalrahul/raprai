/**
 * Toast Notification System
 *
 * Provides non-blocking toast notifications with auto-dismiss and progress bar.
 * Supports success, error, warning, and info notification types with different styling.
 *
 * Usage:
 *   Toast.success('Saved successfully!');
 *   Toast.error('Something went wrong', 6000);
 *   Toast.info('Processing...', 4000);
 *   const id = Toast.show('Custom message', 'warning', 5000);
 */

const Toast = {
  /**
   * Container DOM element for all toasts
   * @type {HTMLElement|null}
   */
  container: null,

  /**
   * Next toast ID counter
   * @type {number}
   * @private
   */
  _nextId: 0,

  /**
   * Map of active toast IDs to their timeout IDs
   * @type {Object}
   * @private
   */
  _toastTimeouts: {},

  /**
   * Initialize toast system
   *
   * Creates the container element for toasts. Must be called once
   * during application startup.
   *
   * @returns {HTMLElement} Container element
   */
  init() {
    if (this.container) return this.container;

    this.container = document.createElement('div');
    this.container.id = 'toast-container';
    this.container.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 9999;
      max-width: 400px;
      pointer-events: none;
      display: flex;
      flex-direction: column-reverse;
      gap: 8px;
    `;

    document.body.appendChild(this.container);
    console.log('[Toast] Initialized');

    return this.container;
  },

  /**
   * Show toast notification
   *
   * Creates a toast element with icon, message, close button, and auto-dismissal.
   * Toast slides in from the right with optional progress bar.
   *
   * @param {string} message - Notification message
   * @param {string} type - Notification type: 'success', 'error', 'warning', 'info'
   * @param {number} duration - Auto-dismiss duration in milliseconds (0 = no auto-dismiss)
   * @returns {string} Toast ID for manual dismissal
   *
   * @example
   *   Toast.show('Operation complete', 'success', 4000);
   *   Toast.show('Failed to save', 'error', 6000);
   */
  show(message, type = 'info', duration = 4000) {
    if (!this.container) this.init();

    const toastId = String(this._nextId++);
    const toast = document.createElement('div');

    // Determine colors and icon based on type
    const { bgColor, textColor, borderColor, icon } = this._getTypeStyles(type);

    toast.className = 'toast';
    toast.id = 'toast-' + toastId;
    toast.style.cssText = `
      background: ${bgColor};
      color: ${textColor};
      border: 1px solid ${borderColor};
      border-radius: 6px;
      padding: 14px 16px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 12px;
      pointer-events: auto;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      font-size: 14px;
      font-weight: 500;
      animation: slideInRight 0.3s ease-out;
      position: relative;
      overflow: hidden;
    `;

    // Icon
    const iconEl = document.createElement('div');
    iconEl.innerHTML = icon;
    iconEl.style.cssText = `
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 20px;
      height: 20px;
    `;
    toast.appendChild(iconEl);

    // Message text
    const messageEl = document.createElement('div');
    messageEl.textContent = message;
    messageEl.style.cssText = `
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    `;
    toast.appendChild(messageEl);

    // Close button
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '✕';
    closeBtn.style.cssText = `
      background: none;
      border: none;
      color: inherit;
      cursor: pointer;
      padding: 0;
      width: 20px;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0.7;
      flex-shrink: 0;
      font-size: 16px;
      transition: opacity 0.2s;
    `;
    closeBtn.onmouseover = () => (closeBtn.style.opacity = '1');
    closeBtn.onmouseout = () => (closeBtn.style.opacity = '0.7');
    closeBtn.onclick = () => this._dismiss(toast, toastId);
    toast.appendChild(closeBtn);

    // Add progress bar if duration is set
    if (duration > 0) {
      const progressBar = document.createElement('div');
      progressBar.style.cssText = `
        position: absolute;
        bottom: 0;
        left: 0;
        height: 3px;
        background: ${textColor};
        opacity: 0.5;
        animation: shrinkWidth ${duration}ms linear forwards;
      `;
      toast.appendChild(progressBar);
    }

    this.container.appendChild(toast);

    // Auto-dismiss
    if (duration > 0) {
      const timeoutId = setTimeout(() => {
        this._dismiss(toast, toastId);
      }, duration);
      this._toastTimeouts[toastId] = timeoutId;
    }

    console.log('[Toast]', type, ':', message);
    return toastId;
  },

  /**
   * Show success toast
   *
   * @param {string} message - Success message
   * @param {number} duration - Auto-dismiss duration (default: 4000ms)
   * @returns {string} Toast ID
   */
  success(message, duration = 4000) {
    return this.show(message, 'success', duration);
  },

  /**
   * Show error toast
   *
   * @param {string} message - Error message
   * @param {number} duration - Auto-dismiss duration (default: 6000ms)
   * @returns {string} Toast ID
   */
  error(message, duration = 6000) {
    return this.show(message, 'error', duration);
  },

  /**
   * Show warning toast
   *
   * @param {string} message - Warning message
   * @param {number} duration - Auto-dismiss duration (default: 4000ms)
   * @returns {string} Toast ID
   */
  warning(message, duration = 4000) {
    return this.show(message, 'warning', duration);
  },

  /**
   * Show info toast
   *
   * @param {string} message - Info message
   * @param {number} duration - Auto-dismiss duration (default: 4000ms)
   * @returns {string} Toast ID
   */
  info(message, duration = 4000) {
    return this.show(message, 'info', duration);
  },

  /**
   * Dismiss and remove toast
   *
   * @param {HTMLElement} element - Toast element
   * @param {string} toastId - Toast ID
   * @private
   */
  _dismiss(element, toastId) {
    // Clear pending timeout
    if (this._toastTimeouts[toastId]) {
      clearTimeout(this._toastTimeouts[toastId]);
      delete this._toastTimeouts[toastId];
    }

    // Animate out
    element.style.animation = 'slideOutRight 0.3s ease-in forwards';

    // Remove after animation
    setTimeout(() => {
      try {
        element.remove();
      } catch (e) {
        // Already removed
      }
    }, 300);
  },

  /**
   * Get styles and icon for notification type
   *
   * @param {string} type - Notification type
   * @returns {Object} Style configuration
   * @private
   */
  _getTypeStyles(type) {
    const styles = {
      success: {
        bgColor: '#f0fdf4',
        textColor: '#166534',
        borderColor: '#86efac',
        icon: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="9" fill="currentColor"/><path d="M6 10l3 3 5-5" stroke="white" stroke-width="2" stroke-linecap="round"/></svg>',
      },
      error: {
        bgColor: '#fef2f2',
        textColor: '#991b1b',
        borderColor: '#fca5a5',
        icon: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="9" fill="currentColor"/><path d="M6 6l8 8M14 6l-8 8" stroke="white" stroke-width="2" stroke-linecap="round"/></svg>',
      },
      warning: {
        bgColor: '#fffbeb',
        textColor: '#92400e',
        borderColor: '#fcd34d',
        icon: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M10 2L2 16h16L10 2z" fill="currentColor"/><text x="10" y="15" text-anchor="middle" fill="white" font-weight="bold" font-size="12">!</text></svg>',
      },
      info: {
        bgColor: '#eff6ff',
        textColor: '#0c2d6b',
        borderColor: '#bfdbfe',
        icon: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="9" fill="currentColor"/><text x="10" y="15" text-anchor="middle" fill="white" font-weight="bold" font-size="14">i</text></svg>',
      },
    };

    return styles[type] || styles.info;
  },
};

// Add CSS animations
if (!document.getElementById('toast-animations')) {
  const style = document.createElement('style');
  style.id = 'toast-animations';
  style.textContent = `
    @keyframes slideInRight {
      from {
        transform: translateX(400px);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }

    @keyframes slideOutRight {
      from {
        transform: translateX(0);
        opacity: 1;
      }
      to {
        transform: translateX(400px);
        opacity: 0;
      }
    }

    @keyframes shrinkWidth {
      from {
        width: 100%;
      }
      to {
        width: 0;
      }
    }
  `;
  document.head.appendChild(style);
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    Toast.init();
  });
} else {
  Toast.init();
}
