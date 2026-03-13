/**
 * WebSocket Manager Module
 *
 * Manages real-time WebSocket connection to backend with automatic reconnection,
 * exponential backoff, and event-based message routing.
 *
 * Usage:
 *   WS.on('message', (data) => console.log('New message:', data));
 *   WS.on('connected', () => console.log('Connected'));
 *   WS.connect();
 *   WS.sendMessage('Hello', sessionId);
 *   WS.sendCommand('list_sessions');
 */

class WebSocketManager {
  /**
   * Initialize WebSocket manager
   */
  constructor() {
    /**
     * WebSocket instance
     * @type {WebSocket|null}
     */
    this.ws = null;

    /**
     * Event handlers by type
     * @type {Object<string, Function[]>}
     */
    this.handlers = {};

    /**
     * Current reconnection delay in ms
     * @type {number}
     */
    this.reconnectDelay = 2500;

    /**
     * Maximum reconnection delay
     * @type {number}
     */
    this.maxReconnectDelay = 30000;

    /**
     * Reconnection timeout ID
     * @type {number|null}
     */
    this.reconnectTimeoutId = null;

    /**
     * Connection status
     * @type {boolean}
     */
    this.connected = false;

    /**
     * Prevent reconnection flag (used during manual disconnect)
     * @type {boolean}
     */
    this.shouldReconnect = true;
  }

  /**
   * Establish WebSocket connection with automatic reconnection
   *
   * If already connecting, does nothing. On successful connection, resets
   * reconnection delay. On failure, schedules reconnection with exponential backoff.
   *
   * @returns {Promise<void>}
   */
  connect() {
    // Prevent multiple simultaneous connection attempts
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      try {
        const wsUrl = RAPR_CONFIG.wsUrl();
        console.log('[WS] Connecting to:', wsUrl);

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          this._onOpen();
          resolve();
        };

        this.ws.onclose = (event) => {
          this._onClose(event);
          if (this.shouldReconnect) {
            this._scheduleReconnect();
          }
          resolve();
        };

        this.ws.onerror = (error) => {
          console.error('[WS] Error:', error);
          resolve();
        };

        this.ws.onmessage = (event) => {
          this._onMessage(event);
        };
      } catch (error) {
        console.error('[WS] Connection failed:', error);
        if (this.shouldReconnect) {
          this._scheduleReconnect();
        }
        resolve();
      }
    });
  }

  /**
   * Disconnect from WebSocket
   *
   * Clears any pending reconnection and closes the connection.
   * To reconnect later, call connect() again.
   */
  disconnect() {
    this.shouldReconnect = false;

    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }

    if (this.ws) {
      try {
        this.ws.close(1000, 'Client disconnect');
      } catch (error) {
        console.error('[WS] Error closing connection:', error);
      }
      this.ws = null;
    }

    this.connected = false;
    this._emit('disconnected', {});
  }

  /**
   * Send message to AI
   *
   * @param {string} content - Message content
   * @param {string} sessionId - Session ID to send message to
   */
  sendMessage(content, sessionId) {
    this.send('message', {
      content,
      session_id: sessionId,
    });
  }

  /**
   * Send command to backend
   *
   * @param {string} command - Command name (e.g., 'new_session:claude', 'list_sessions')
   * @param {Object} data - Optional command data
   */
  sendCommand(command, data) {
    this.send('command', {
      command,
      ...data,
    });
  }

  /**
   * Send raw message over WebSocket
   *
   * If not connected, buffers are not sent. Consider waiting for 'connected' event.
   *
   * @param {string} type - Message type
   * @param {Object} data - Message data
   */
  send(type, data) {
    if (!this.connected) {
      console.warn('[WS] Not connected, message not sent:', type);
      return;
    }

    try {
      const message = { type, ...data };
      this.ws.send(JSON.stringify(message));
      console.log('[WS] Sent:', type);
    } catch (error) {
      console.error('[WS] Send failed:', error);
    }
  }

  /**
   * Register event handler
   *
   * Multiple handlers can be registered for the same type.
   * Handlers are called in registration order.
   *
   * @param {string} type - Event type (e.g., 'message', 'connected', 'thinking')
   * @param {Function} callback - Handler function, called with (data, type)
   */
  on(type, callback) {
    if (!this.handlers[type]) {
      this.handlers[type] = [];
    }
    this.handlers[type].push(callback);
  }

  /**
   * Unregister event handler
   *
   * @param {string} type - Event type
   * @param {Function} callback - Handler function to remove
   */
  off(type, callback) {
    if (!this.handlers[type]) return;
    const index = this.handlers[type].indexOf(callback);
    if (index > -1) {
      this.handlers[type].splice(index, 1);
    }
  }

  /**
   * Internal: Emit event to all registered handlers
   *
   * @param {string} type - Event type
   * @param {Object} data - Event data
   * @private
   */
  _emit(type, data) {
    const handlers = this.handlers[type] || [];
    handlers.forEach((callback) => {
      try {
        callback(data, type);
      } catch (error) {
        console.error('[WS] Handler error for', type, ':', error);
      }
    });
  }

  /**
   * Internal: Handle WebSocket open
   *
   * Resets reconnection delay and emits 'connected' event.
   *
   * @private
   */
  _onOpen() {
    console.log('[WS] Connected');
    this.connected = true;
    this.reconnectDelay = 2500; // Reset backoff
    this._emit('connected', {});
  }

  /**
   * Internal: Handle WebSocket close
   *
   * Handles special case of 4401 (authentication expired).
   * Other codes trigger automatic reconnection.
   *
   * @param {CloseEvent} event - Close event
   * @private
   */
  _onClose(event) {
    console.log('[WS] Closed:', event.code, event.reason);
    this.connected = false;

    // Authentication expired - need manual re-login
    if (event.code === 4401) {
      console.warn('[WS] Authentication expired');
      this.shouldReconnect = false;
      this._emit('auth-expired', {});
    }

    this._emit('disconnected', { code: event.code, reason: event.reason });
  }

  /**
   * Internal: Handle incoming message
   *
   * Parses JSON message and routes to handlers by type.
   * Unknown message types are logged but not emitted.
   *
   * @param {MessageEvent} event - Message event
   * @private
   */
  _onMessage(event) {
    try {
      const data = JSON.parse(event.data);
      const type = data.type || 'unknown';

      console.log('[WS] Received:', type);

      // Emit to type-specific handlers
      this._emit(type, data);

      // Also emit to generic 'message' handler
      if (type !== 'message') {
        this._emit('message', data);
      }
    } catch (error) {
      console.error('[WS] Parse error:', error, 'Raw:', event.data);
    }
  }

  /**
   * Internal: Schedule reconnection with exponential backoff
   *
   * Delay starts at 2.5 seconds and increases up to 30 seconds.
   *
   * @private
   */
  _scheduleReconnect() {
    if (this.reconnectTimeoutId) return;

    console.log('[WS] Reconnecting in', this.reconnectDelay, 'ms');

    this.reconnectTimeoutId = setTimeout(() => {
      this.reconnectTimeoutId = null;

      // Increase backoff for next attempt
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);

      this.connect();
    }, this.reconnectDelay);
  }
}

/**
 * Global WebSocket manager instance
 * @type {WebSocketManager}
 */
const WS = new WebSocketManager();
