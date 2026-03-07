/**
 * RAPR AI Browser Tools — Service Worker
 *
 * Single entry point for the extension:
 *   - Maintains WebSocket connection to RAPR AI (/ws/chrome)
 *   - Handles tool-call requests from the server
 *   - Executes Chrome API tools (tabs, screenshots)
 *   - Routes DOM tools to content scripts
 */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let ws = null;
let connected = false;
let serverUrl = "";
let token = "";
let reconnectDelay = 1000;
let heartbeatTimer = null;
let connectedAt = null;

// ---------------------------------------------------------------------------
// WebSocket connection management
// ---------------------------------------------------------------------------

async function connect(url, bearerToken) {
  serverUrl = url;
  token = bearerToken;

  // Save config
  await chrome.storage.local.set({ rapr_url: url, rapr_token: bearerToken });

  // Close existing connection
  if (ws) {
    try { ws.close(); } catch (e) { /* ignore */ }
    ws = null;
  }

  const wsUrl = url.replace(/^http/, "ws") + "/ws/chrome";
  console.log("[SW] Connecting to", wsUrl);

  try {
    ws = new WebSocket(wsUrl);
  } catch (e) {
    console.error("[SW] WebSocket creation failed:", e);
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    console.log("[SW] WebSocket opened, sending auth...");
    ws.send(JSON.stringify({
      type: "auth",
      token: token,
      extension_id: "rapr-chrome-ext",
      version: chrome.runtime.getManifest().version,
    }));
  };

  ws.onmessage = async (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch (e) {
      console.warn("[SW] Invalid JSON:", event.data);
      return;
    }

    // Handle auth response
    if (msg.type === "auth_response") {
      if (msg.ok) {
        connected = true;
        connectedAt = new Date().toISOString();
        reconnectDelay = 1000;
        console.log("[SW] Authenticated! Tools:", msg.tools);
        startHeartbeat();
      } else {
        console.error("[SW] Auth failed");
        ws.close();
      }
      return;
    }

    // Handle tool call requests from RAPR AI
    if (msg.jsonrpc === "2.0" && msg.method === "tools/call") {
      const toolName = msg.params?.name;
      const toolArgs = msg.params?.arguments || {};
      const msgId = msg.id;

      console.log("[SW] Tool call:", toolName, JSON.stringify(toolArgs));

      try {
        const result = await executeTool(toolName, toolArgs);
        ws.send(JSON.stringify({
          jsonrpc: "2.0",
          id: msgId,
          result: {
            content: [
              { type: "text", text: JSON.stringify(result, null, 2) }
            ],
          },
        }));
      } catch (err) {
        console.error("[SW] Tool error:", toolName, err);
        ws.send(JSON.stringify({
          jsonrpc: "2.0",
          id: msgId,
          error: {
            code: -32603,
            message: String(err.message || err),
          },
        }));
      }
      return;
    }
  };

  ws.onclose = (event) => {
    console.log("[SW] WebSocket closed:", event.code, event.reason);
    connected = false;
    connectedAt = null;
    stopHeartbeat();
    if (token) {
      scheduleReconnect();
    }
  };

  ws.onerror = (error) => {
    console.error("[SW] WebSocket error:", error);
  };
}

function disconnect() {
  token = "";
  connected = false;
  connectedAt = null;
  stopHeartbeat();
  if (ws) {
    try { ws.close(); } catch (e) { /* ignore */ }
    ws = null;
  }
  chrome.storage.local.remove(["rapr_token"]);
}

function scheduleReconnect() {
  if (!token) return;
  console.log(`[SW] Reconnecting in ${reconnectDelay / 1000}s...`);
  setTimeout(() => {
    if (token && !connected) {
      connect(serverUrl, token);
    }
  }, reconnectDelay);
  reconnectDelay = Math.min(reconnectDelay * 2, 30000);
}

// ---------------------------------------------------------------------------
// Heartbeat  (keeps service worker + WebSocket alive)
// ---------------------------------------------------------------------------

function startHeartbeat() {
  stopHeartbeat();
  heartbeatTimer = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ jsonrpc: "2.0", method: "heartbeat" }));
    }
  }, 25000);
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

// ---------------------------------------------------------------------------
// Message handler  (popup → service worker)
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const { type } = message;

  switch (type) {
    case "get_connection_status":
      sendResponse({
        connected,
        serverUrl,
        connectedAt,
        tools: 12,
      });
      return false;

    case "connect":
      connect(message.url, message.token)
        .then(() => {
          // Wait a moment for auth handshake to complete
          setTimeout(() => {
            sendResponse({ ok: true, connected });
          }, 2000);
        })
        .catch((err) => {
          sendResponse({ ok: false, error: String(err) });
        });
      return true;  // async response

    case "disconnect":
      disconnect();
      sendResponse({ ok: true });
      return false;

    // Tool execution (if called from other extension contexts)
    case "exec_tool":
      executeTool(message.tool, message.args)
        .then((result) => sendResponse({ ok: true, result }))
        .catch((err) => sendResponse({ ok: false, error: String(err) }));
      return true;

    default:
      return false;
  }
});


// ---------------------------------------------------------------------------
// Tool executors
// ---------------------------------------------------------------------------

async function executeTool(toolName, args) {
  switch (toolName) {

    case "list_tabs": {
      const tabs = await chrome.tabs.query({});
      return tabs
        .filter((t) => t.url && !t.url.startsWith("chrome://") && !t.url.startsWith("chrome-extension://"))
        .map((t) => ({
          tab_id: t.id,
          url: t.url,
          title: t.title || "",
          active: t.active,
          window_id: t.windowId,
        }));
    }

    case "navigate": {
      const url = args.url;
      if (args.tab_id) {
        await chrome.tabs.update(args.tab_id, { url });
        return { ok: true, tab_id: args.tab_id };
      }
      const tab = await chrome.tabs.create({ url });
      return { ok: true, tab_id: tab.id };
    }

    case "close_tab": {
      await chrome.tabs.remove(args.tab_id);
      return { ok: true };
    }

    case "new_tab": {
      const tab = await chrome.tabs.create({ url: args.url || "about:blank" });
      return { ok: true, tab_id: tab.id };
    }

    case "screenshot": {
      const dataUrl = await chrome.tabs.captureVisibleTab(undefined, {
        format: "png",
      });
      return { image_data: dataUrl };
    }

    // DOM-based tools — forward to content script
    case "read_page":
    case "click":
    case "type_text":
    case "find_element":
    case "get_page_text":
    case "extract_table":
    case "fill_form": {
      const tabId = args.tab_id || (await getActiveTabId());
      if (!tabId) throw new Error("No active tab found");

      // Ensure content script is injected
      try {
        await chrome.scripting.executeScript({
          target: { tabId },
          files: ["content-script.js"],
        });
      } catch (e) {
        // Already injected or protected page — continue anyway
        console.log("[SW] Content script inject note:", e.message);
      }

      return new Promise((resolve, reject) => {
        chrome.tabs.sendMessage(
          tabId,
          { action: toolName, ...args },
          (response) => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else if (response && response.error) {
              reject(new Error(response.error));
            } else {
              resolve(response || { ok: true });
            }
          }
        );
      });
    }

    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}

async function getActiveTabId() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs.length > 0 ? tabs[0].id : null;
}


// ---------------------------------------------------------------------------
// Auto-connect on startup if credentials are stored
// ---------------------------------------------------------------------------

chrome.runtime.onInstalled.addListener(async () => {
  console.log("[SW] Extension installed/updated");
  await autoConnect();
});

chrome.runtime.onStartup.addListener(async () => {
  console.log("[SW] Browser started");
  await autoConnect();
});

async function autoConnect() {
  const config = await chrome.storage.local.get(["rapr_url", "rapr_token"]);
  if (config.rapr_url && config.rapr_token) {
    console.log("[SW] Auto-connecting to", config.rapr_url);
    connect(config.rapr_url, config.rapr_token);
  }
}
