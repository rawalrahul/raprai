/**
 * RAPR AI API Client Module
 *
 * Centralized REST API client that wraps all HTTP communication with the backend.
 * Provides organized methods for all API endpoints with automatic error handling,
 * CSRF token injection, and JSON serialization.
 *
 * Usage:
 *   const status = await API.auth.status();
 *   const models = await API.integrations.models();
 *   await API.memory.create('New memory', 'general');
 */

const API = {
  /**
   * Internal: Retrieve CSRF token from cookies
   *
   * Looks for 'hq_csrf' cookie which is set by the backend
   * on initial page load for CSRF protection.
   *
   * @returns {string|null} CSRF token or null if not found
   * @private
   */
  _csrfToken() {
    const name = 'hq_csrf=';
    const decodedCookie = decodeURIComponent(document.cookie);
    const cookies = decodedCookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.indexOf(name) === 0) {
        return cookie.substring(name.length);
      }
    }
    return null;
  },

  /**
   * Internal: Execute GET request
   *
   * @param {string} path - API endpoint path
   * @returns {Promise<*>} Parsed JSON response
   * @throws {Error} On network or HTTP error
   * @private
   */
  async _get(path) {
    try {
      const response = await fetch(RAPR_CONFIG.apiUrl(path), {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const error = new Error(`API Error: ${response.statusText}`);
        error.status = response.status;
        throw error;
      }

      return await response.json();
    } catch (error) {
      console.error(`GET ${path} failed:`, error);
      throw error;
    }
  },

  /**
   * Internal: Execute POST request with CSRF protection
   *
   * Automatically injects CSRF token in headers. Body is JSON-encoded.
   *
   * @param {string} path - API endpoint path
   * @param {Object} body - Request body (will be JSON-stringified)
   * @returns {Promise<*>} Parsed JSON response
   * @throws {Error} On network or HTTP error
   * @private
   */
  async _post(path, body) {
    try {
      const response = await fetch(RAPR_CONFIG.apiUrl(path), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-CSRF-Token': this._csrfToken() || '',
        },
        credentials: 'include',
        body: JSON.stringify(body || {}),
      });

      if (!response.ok) {
        const error = new Error(`API Error: ${response.statusText}`);
        error.status = response.status;
        throw error;
      }

      return await response.json();
    } catch (error) {
      console.error(`POST ${path} failed:`, error);
      throw error;
    }
  },

  /**
   * Internal: Execute DELETE request with CSRF protection
   *
   * @param {string} path - API endpoint path
   * @returns {Promise<*>} Parsed JSON response (if any)
   * @throws {Error} On network or HTTP error
   * @private
   */
  async _delete(path) {
    try {
      const response = await fetch(RAPR_CONFIG.apiUrl(path), {
        method: 'DELETE',
        headers: {
          'Accept': 'application/json',
          'X-CSRF-Token': this._csrfToken() || '',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const error = new Error(`API Error: ${response.statusText}`);
        error.status = response.status;
        throw error;
      }

      const text = await response.text();
      return text ? JSON.parse(text) : {};
    } catch (error) {
      console.error(`DELETE ${path} failed:`, error);
      throw error;
    }
  },

  /**
   * Internal: Execute multipart form upload with CSRF protection
   *
   * Used for file uploads (packages, backups, voice transcription).
   *
   * @param {string} path - API endpoint path
   * @param {FormData} formData - Form data with files
   * @returns {Promise<*>} Parsed JSON response
   * @throws {Error} On network or HTTP error
   * @private
   */
  async _upload(path, formData) {
    try {
      const response = await fetch(RAPR_CONFIG.apiUrl(path), {
        method: 'POST',
        headers: {
          'X-CSRF-Token': this._csrfToken() || '',
        },
        credentials: 'include',
        body: formData,
      });

      if (!response.ok) {
        const error = new Error(`Upload Error: ${response.statusText}`);
        error.status = response.status;
        throw error;
      }

      return await response.json();
    } catch (error) {
      console.error(`Upload to ${path} failed:`, error);
      throw error;
    }
  },

  /**
   * Authentication API
   */
  auth: {
    /**
     * Get current authentication status
     *
     * @returns {Promise<Object>} Auth status object
     */
    status() {
      return API._get('/auth/status');
    },

    /**
     * Set or change PIN code
     *
     * @param {string} pin - New PIN code
     * @param {string} oldPin - Current PIN (required if updating existing PIN)
     * @returns {Promise<Object>} Updated status
     */
    setPin(pin, oldPin) {
      return API._post('/auth/set-pin', { pin, old_pin: oldPin });
    },
  },

  /**
   * Integrations API - LLM provider configuration and status
   */
  integrations: {
    /**
     * List all available integrations
     *
     * @returns {Promise<Array>} Array of integration objects
     */
    list() {
      return API._get('/integrations');
    },

    /**
     * Get Claude integration status
     *
     * @returns {Promise<Object>} Claude integration details
     */
    claudeStatus() {
      return API._get('/integrations/claude/status');
    },

    /**
     * Get Gemini integration status
     *
     * @returns {Promise<Object>} Gemini integration details
     */
    geminiStatus() {
      return API._get('/integrations/gemini/status');
    },

    /**
     * Get Ollama integration status
     *
     * @returns {Promise<Object>} Ollama integration details
     */
    ollamaStatus() {
      return API._get('/integrations/ollama/status');
    },

    /**
     * List custom LLM integrations
     *
     * @returns {Promise<Array>} Array of custom integration configs
     */
    customList() {
      return API._get('/integrations/custom');
    },

    /**
     * Add custom LLM integration
     *
     * @param {Object} data - Custom integration configuration
     * @returns {Promise<Object>} New custom integration
     */
    customAdd(data) {
      return API._post('/integrations/custom', data);
    },

    /**
     * Remove custom LLM integration
     *
     * @param {string} key - Integration key/ID
     * @returns {Promise<Object>} Deletion confirmation
     */
    customRemove(key) {
      return API._delete('/integrations/custom/' + encodeURIComponent(key));
    },

    /**
     * Get available models from all integrations
     *
     * @returns {Promise<Array>} Array of available model objects
     */
    models() {
      return API._get('/integrations/models');
    },
  },

  /**
   * Session History API - Browse and manage past conversations
   */
  history: {
    /**
     * List all sessions in history
     *
     * @returns {Promise<Array>} Array of session history entries
     */
    list() {
      return API._get('/history');
    },

    /**
     * Get conversation for specific date
     *
     * @param {string} date - Date identifier (YYYY-MM-DD format)
     * @returns {Promise<Object>} Conversation data
     */
    get(date) {
      return API._get('/history/' + encodeURIComponent(date));
    },

    /**
     * Delete conversation for specific date
     *
     * @param {string} date - Date identifier
     * @returns {Promise<Object>} Deletion confirmation
     */
    delete(date) {
      return API._delete('/history/' + encodeURIComponent(date));
    },

    /**
     * Rename a history session
     *
     * @param {string} date - Date identifier
     * @param {string} name - New name for session
     * @returns {Promise<Object>} Updated session
     */
    rename(date, name) {
      return API._post('/history/' + encodeURIComponent(date) + '/rename', { name });
    },

    /**
     * Resume a previous conversation
     *
     * @param {string} date - Date identifier
     * @returns {Promise<Object>} Resumed session data
     */
    resume(date) {
      return API._get('/history/' + encodeURIComponent(date) + '/resume');
    },

    /**
     * Search history conversations
     *
     * @param {string} q - Search query
     * @returns {Promise<Array>} Matching sessions
     */
    search(q) {
      return API._get('/history/search?q=' + encodeURIComponent(q));
    },
  },

  /**
   * Templates API - Prompt and conversation templates
   */
  templates: {
    /**
     * List all saved templates
     *
     * @returns {Promise<Array>} Array of template objects
     */
    list() {
      return API._get('/templates');
    },

    /**
     * Create new template
     *
     * @param {Object} data - Template data (name, content, category)
     * @returns {Promise<Object>} Created template
     */
    create(data) {
      return API._post('/templates', data);
    },

    /**
     * Delete a template
     *
     * @param {string} name - Template name
     * @returns {Promise<Object>} Deletion confirmation
     */
    delete(name) {
      return API._delete('/templates/' + encodeURIComponent(name));
    },
  },

  /**
   * Memory API - Knowledge and context management
   */
  memory: {
    /**
     * List memories with optional filtering
     *
     * @param {Object} opts - Query options (category, archived, pinned, limit, offset)
     * @returns {Promise<Object>} Paginated memory list
     */
    list(opts) {
      const params = new URLSearchParams(opts || {});
      return API._get('/memory?' + params.toString());
    },

    /**
     * Search memories by content
     *
     * @param {string} q - Search query
     * @returns {Promise<Array>} Matching memory entries
     */
    search(q) {
      return API._get('/memory/search?q=' + encodeURIComponent(q));
    },

    /**
     * Get memory statistics
     *
     * @returns {Promise<Object>} Stats including count by category
     */
    stats() {
      return API._get('/memory/stats');
    },

    /**
     * Create new memory entry
     *
     * @param {string} content - Memory content
     * @param {string} category - Memory category
     * @returns {Promise<Object>} Created memory
     */
    create(content, category) {
      return API._post('/memory', { content, category });
    },

    /**
     * Update existing memory
     *
     * @param {string} id - Memory ID
     * @param {Object} data - Update data
     * @returns {Promise<Object>} Updated memory
     */
    update(id, data) {
      return API._post('/memory/' + encodeURIComponent(id), data);
    },

    /**
     * Delete memory entry
     *
     * @param {string} id - Memory ID
     * @returns {Promise<Object>} Deletion confirmation
     */
    delete(id) {
      return API._delete('/memory/' + encodeURIComponent(id));
    },

    /**
     * Pin or unpin a memory
     *
     * @param {string} id - Memory ID
     * @param {boolean} pinned - Pin state
     * @returns {Promise<Object>} Updated memory
     */
    pin(id, pinned) {
      return API._post('/memory/' + encodeURIComponent(id) + '/pin', { pinned });
    },

    /**
     * Archive a memory
     *
     * @param {string} id - Memory ID
     * @returns {Promise<Object>} Updated memory
     */
    archive(id) {
      return API._post('/memory/' + encodeURIComponent(id) + '/archive', {});
    },
  },

  /**
   * Settings API - User preferences and configuration
   */
  settings: {
    /**
     * Get all settings
     *
     * @returns {Promise<Object>} Settings object
     */
    get() {
      return API._get('/settings');
    },

    /**
     * Update settings
     *
     * @param {Object} data - Settings to update
     * @returns {Promise<Object>} Updated settings
     */
    update(data) {
      return API._post('/settings', data);
    },

    /**
     * Get default AI models
     *
     * @returns {Promise<Object>} Default model selections
     */
    defaultModels() {
      return API._get('/settings/default-models');
    },

    /**
     * Set default AI models
     *
     * @param {Object} data - Model selections by type
     * @returns {Promise<Object>} Updated defaults
     */
    setDefaultModels(data) {
      return API._post('/settings/default-models', data);
    },

    /**
     * Get API keys
     *
     * @returns {Promise<Array>} Array of configured API keys (with tokens redacted)
     */
    apiKeys() {
      return API._get('/settings/api-keys');
    },

    /**
     * Add new API key
     *
     * @param {Object} data - API key data
     * @returns {Promise<Object>} Created API key entry
     */
    addApiKey(data) {
      return API._post('/settings/api-keys', data);
    },

    /**
     * Remove API key
     *
     * @param {string} key - API key identifier
     * @returns {Promise<Object>} Deletion confirmation
     */
    removeApiKey(key) {
      return API._delete('/settings/api-keys/' + encodeURIComponent(key));
    },
  },

  /**
   * Packages API - Marketplace and package management
   */
  packages: {
    /**
     * Browse package catalog
     *
     * @param {Object} opts - Filter options (search, category, limit, offset)
     * @returns {Promise<Object>} Paginated catalog
     */
    catalog(opts) {
      const params = new URLSearchParams(opts || {});
      return API._get('/packages/catalog?' + params.toString());
    },

    /**
     * List installed packages
     *
     * @returns {Promise<Array>} Array of installed packages
     */
    installed() {
      return API._get('/packages/installed');
    },

    /**
     * Install package by ID
     *
     * @param {string} id - Package ID
     * @param {boolean} force - Force installation if already installed
     * @returns {Promise<Object>} Installation status
     */
    install(id, force) {
      return API._post('/packages/install', { package_id: id, force: force || false });
    },

    /**
     * Uninstall package
     *
     * @param {string} id - Package ID
     * @returns {Promise<Object>} Uninstallation confirmation
     */
    uninstall(id) {
      return API._post('/packages/uninstall', { package_id: id });
    },

    /**
     * Upload and install package from file
     *
     * @param {FormData} formData - Form data with 'file' field
     * @returns {Promise<Object>} Installation result
     */
    upload(formData) {
      return API._upload('/packages/install/upload', formData);
    },

    /**
     * Check for package updates
     *
     * @returns {Promise<Array>} Available updates
     */
    updates() {
      return API._get('/packages/updates');
    },

    /**
     * Get package setup instructions
     *
     * @param {string} id - Package ID
     * @returns {Promise<Object>} Setup info
     */
    setup(id) {
      return API._get('/packages/setup/' + encodeURIComponent(id));
    },

    /**
     * Configure package environment variables
     *
     * @param {string} id - Package ID
     * @param {Object} envVars - Environment variables
     * @returns {Promise<Object>} Configuration result
     */
    configure(id, envVars) {
      return API._post('/packages/configure', { package_id: id, env_vars: envVars });
    },

    /**
     * Refresh package catalog from marketplace
     *
     * @returns {Promise<Object>} Refresh status
     */
    refreshCatalog() {
      return API._post('/packages/catalog/refresh', {});
    },
  },

  /**
   * Backups API - Data backup and restore
   */
  backups: {
    /**
     * Get backup configuration
     *
     * @returns {Promise<Object>} Backup provider config
     */
    config() {
      return API._get('/backups/config');
    },

    /**
     * Configure backup provider
     *
     * @param {string} provider - Provider name (e.g., 's3', 'gdrive')
     * @param {Object} data - Provider configuration
     * @returns {Promise<Object>} Updated config
     */
    configure(provider, data) {
      return API._post('/backups/config/' + encodeURIComponent(provider), data);
    },

    /**
     * Trigger backup now
     *
     * @param {Object} opts - Backup options (provider, include_db, etc.)
     * @returns {Promise<Object>} Backup job ID and status
     */
    now(opts) {
      return API._post('/backups/now', opts || {});
    },

    /**
     * Get backup job history
     *
     * @param {number} limit - Max jobs to return
     * @returns {Promise<Array>} Array of backup jobs
     */
    jobs(limit) {
      return API._get('/backups/jobs?limit=' + (limit || 20));
    },

    /**
     * Restore from backup job
     *
     * @param {string} jobId - Job ID to restore from
     * @returns {Promise<Object>} Restore status
     */
    restore(jobId) {
      return API._post('/backups/restore/' + encodeURIComponent(jobId), {});
    },

    /**
     * Disconnect backup provider
     *
     * @param {string} provider - Provider name
     * @returns {Promise<Object>} Disconnection confirmation
     */
    disconnect(provider) {
      return API._post('/backups/providers/' + encodeURIComponent(provider) + '/disconnect', {});
    },
  },

  /**
   * Pipelines API - Workflow execution and approval
   */
  pipelines: {
    /**
     * List all pipelines
     *
     * @returns {Promise<Array>} Array of pipeline objects
     */
    list() {
      return API._get('/api/pipelines');
    },

    /**
     * Get single pipeline
     *
     * @param {string} id - Pipeline ID
     * @returns {Promise<Object>} Pipeline details
     */
    get(id) {
      return API._get('/api/pipeline/' + encodeURIComponent(id));
    },

    /**
     * Plan pipeline execution
     *
     * @param {Object} data - Pipeline definition
     * @returns {Promise<Object>} Execution plan
     */
    plan(data) {
      return API._post('/api/pipeline/plan', data);
    },

    /**
     * Approve pipeline execution
     *
     * @param {string} id - Pipeline ID
     * @returns {Promise<Object>} Approval confirmation
     */
    approve(id) {
      return API._post('/api/pipeline/' + encodeURIComponent(id) + '/approve', {});
    },

    /**
     * Pause pipeline execution
     *
     * @param {string} id - Pipeline ID
     * @returns {Promise<Object>} Pause confirmation
     */
    pause(id) {
      return API._post('/api/pipeline/' + encodeURIComponent(id) + '/pause', {});
    },

    /**
     * Cancel pipeline execution
     *
     * @param {string} id - Pipeline ID
     * @returns {Promise<Object>} Cancellation confirmation
     */
    cancel(id) {
      return API._post('/api/pipeline/' + encodeURIComponent(id) + '/cancel', {});
    },
  },

  /**
   * Approval API - Request approvals
   */
  approval: {
    /**
     * Get pending approvals
     *
     * @returns {Promise<Array>} Array of pending approval requests
     */
    pending() {
      return API._get('/approval/pending');
    },

    /**
     * Resolve approval request
     *
     * @param {string} reqId - Approval request ID
     * @param {boolean} approved - Approval decision
     * @returns {Promise<Object>} Resolution confirmation
     */
    resolve(reqId, approved) {
      return API._post('/approval/' + encodeURIComponent(reqId), { approved, source: 'web' });
    },
  },

  /**
   * Usage API - Token and resource usage tracking
   */
  usage: {
    /**
     * Get current usage statistics
     *
     * @returns {Promise<Object>} Usage data
     */
    get() {
      return API._get('/api/usage');
    },

    /**
     * Get usage budget/limits
     *
     * @returns {Promise<Object>} Budget information
     */
    budget() {
      return API._get('/api/budget');
    },
  },

  /**
   * Files API - Generated files and uploads
   */
  files: {
    /**
     * List generated files
     *
     * @returns {Promise<Array>} Array of file entries
     */
    list() {
      return API._get('/generated-files');
    },

    /**
     * Upload file
     *
     * @param {FormData} formData - Form data with 'file' field
     * @returns {Promise<Object>} Upload result
     */
    upload(formData) {
      return API._upload('/upload', formData);
    },

    /**
     * Get system diagnostics
     *
     * @returns {Promise<Object>} Diagnostics data
     */
    diagnostics() {
      return API._get('/diagnostics');
    },
  },

  /**
   * Voice API - Audio transcription
   */
  voice: {
    /**
     * Transcribe audio file
     *
     * @param {FormData} formData - Form data with audio 'file' field
     * @returns {Promise<Object>} Transcription result
     */
    transcribe(formData) {
      return API._upload('/transcribe', formData);
    },
  },

  /**
   * Browse API - File system browsing
   */
  browse: {
    /**
     * List files in directory
     *
     * @param {string} path - Directory path
     * @returns {Promise<Array>} Directory contents
     */
    list(path) {
      return API._get('/browse?path=' + encodeURIComponent(path || ''));
    },

    /**
     * Open native file browser
     *
     * @returns {Promise<string>} Selected path
     */
    native() {
      return API._get('/browse/native');
    },
  },

  /**
   * MCP API - Model Context Protocol servers
   */
  mcp: {
    /**
     * List MCP servers
     *
     * @returns {Promise<Array>} Array of MCP server configs
     */
    servers() {
      return API._get('/mcp/servers');
    },

    /**
     * Toggle MCP server
     *
     * @param {string} id - Server ID
     * @param {boolean} enabled - Enable/disable state
     * @returns {Promise<Object>} Updated server
     */
    toggle(id, enabled) {
      return API._post('/mcp/servers/' + encodeURIComponent(id) + '/toggle', { enabled });
    },
  },

  /**
   * Skills API - User-created skills and extensions
   */
  skills: {
    /**
     * List all skills
     *
     * @returns {Promise<Array>} Array of skill objects
     */
    list() {
      return API._get('/skills');
    },

    /**
     * Rescan skill directory
     *
     * @returns {Promise<Object>} Scan results
     */
    rescan() {
      return API._get('/skills/rescan');
    },
  },

  /**
   * Setup API - Initial configuration wizard
   */
  setup: {
    /**
     * Get setup status
     *
     * @returns {Promise<Object>} Current setup progress
     */
    status() {
      return API._get('/setup/status');
    },

    /**
     * Save setup configuration
     *
     * @param {Object} data - Setup data
     * @returns {Promise<Object>} Save confirmation
     */
    save(data) {
      return API._post('/setup/save', data);
    },
  },

  /**
   * Health Check API - Server status
   */
  health() {
    return API._get('/health');
  },
};

// Freeze to prevent accidental modifications
Object.freeze(API);
