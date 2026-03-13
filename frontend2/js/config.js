/**
 * RAPR AI Frontend Configuration Module
 *
 * Provides centralized configuration for API endpoints and WebSocket connections.
 * This module handles URL construction for both development and production environments.
 *
 * Usage:
 *   const apiPath = RAPR_CONFIG.apiUrl('/integrations');
 *   const wsPath = RAPR_CONFIG.wsUrl();
 *   const staticPath = RAPR_CONFIG.staticUrl('icons/claude.svg');
 */

const RAPR_CONFIG = {
  /**
   * Backend API base URL (no trailing slash)
   *
   * Configuration options:
   * - '' (empty): Uses same origin (production default, or when using dev proxy)
   * - 'http://localhost:8585': Direct connection to backend on specific port
   * - 'https://api.example.com': Remote backend server
   */
  API_BASE: '',

  /**
   * WebSocket URL for real-time communication (no trailing slash)
   *
   * If empty, will be auto-derived from API_BASE and window.location.
   * Set explicitly if WebSocket server runs on different host/port.
   */
  WS_URL: '',

  /**
   * Constructs full API endpoint URL
   *
   * @param {string} path - API path (should start with '/')
   * @returns {string} Full API URL including API_BASE
   *
   * Example:
   *   RAPR_CONFIG.apiUrl('/integrations') // => 'http://localhost:8585/integrations'
   */
  apiUrl(path) {
    if (!path) return this.API_BASE;
    return this.API_BASE + path;
  },

  /**
   * Constructs WebSocket URL for real-time connection
   *
   * Automatically handles protocol selection (ws/wss) based on API_BASE
   * or current page origin.
   *
   * @returns {string} WebSocket URL (e.g., 'ws://localhost:8585/ws')
   */
  wsUrl() {
    if (this.WS_URL) return this.WS_URL;

    // Determine base from API_BASE or current origin
    const base = this.API_BASE || window.location.origin;

    // Select appropriate protocol
    const wsProto = base.startsWith('https') ? 'wss' : 'ws';

    // Extract host from base URL
    const host = base.replace(/^https?:\/\//, '');

    // Construct WebSocket URL
    return wsProto + '://' + host + '/ws';
  },

  /**
   * Constructs static asset URL
   *
   * Used for images, icons, and other static resources served by backend.
   *
   * @param {string} path - Asset path relative to /static/
   * @returns {string} Full static asset URL
   *
   * Example:
   *   RAPR_CONFIG.staticUrl('icons/claude.svg') // => '/static/icons/claude.svg'
   */
  staticUrl(path) {
    if (!path) return this.API_BASE + '/static/';
    return this.API_BASE + '/static/' + path;
  },

  /**
   * Get environment information for debugging
   *
   * @returns {Object} Current configuration state
   */
  getInfo() {
    return {
      apiBase: this.API_BASE,
      wsUrl: this.wsUrl(),
      apiUrl: this.apiUrl('/'),
      staticUrl: this.staticUrl(''),
      isDevelopment: !this.API_BASE && window.location.hostname === 'localhost',
      currentOrigin: window.location.origin,
    };
  },
};

// Freeze to prevent accidental modifications (still allows method calls)
Object.freeze(RAPR_CONFIG);
