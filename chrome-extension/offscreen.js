/**
 * RAPR AI Browser Tools — Offscreen Document
 *
 * Maintains a persistent WebSocket connection to the RAPR AI server
 * at /ws/chrome.  Receives tool-call requests from the server and
 * routes them to the service worker for execution.  Returns results
 * back over the WebSocket.
 */

let ws = null;
let connected = false;
let serverUrl = "";
let token = "";
let reconnectDelay = 1000;
let heartbeatInterval = null;
let connectedAt = null;

// ---------------------------------------------------------------------------
// Connection management
// ---------------------------------------------------------------------------

async function connect(url, bearerToken) {
  serverUrl = url;
  token = bearerToken;

  // Save config
  await chrome.storage.local.set({ rapr_url: url, rapr_token: bearerToken });

  // Close existing connection
  if (ws) {
    try { ws.close(); } catch (e) { /* ignore */ }
  }

  const wsUrl = url.replace(/^http/, "ws") + "/ws/chrome";
  console.log("[Offscreen] Connecting to", wsUrl);

  try {
    ws = new WebSocket(wsUrl);
  } catch (e) {
    console.error("[Offscreen] WebSocket creation failed:", e);
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    console.log("[Offscreen] WebSocket opened, sending auth...");
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
      console.warn("[Offscreen] Invalid JSON:", event.data);
      return;
    }

    // Handle auth response
    if (msg.type === "auth_response") {
      if (msg.ok) {
        connected = true;
        connectedAt = new Date().toISOString();
        reconnectDelay = 1000;  // reset backoff
        console.log("[Offscreen] Authenticated! Tools:", msg.tools);
        startHeartbeat();
      } else {
        console.error("[Offscreen] Auth failed");
        ws.close();
      }
      return;
    }

    // Handle tool call requests from RAPR AI
    if (msg.jsonrpc === "2.0" && msg.method === "tools/call") {
      const toolName = msg.params?.name;
      const toolArgs = msg.params?.arguments || {};
      const msgId = msg.id;

      console.log("[Offscreen] Tool call:", toolName, toolArgs);

      try {
        // Route to service worker for execution
        const response = await sendToServiceWorker({
          type: "exec_tool",
          tool: toolName,
          args: toolArgs,
          msgId: msgId,
        });

        if (response.ok) {
          // Send success result back to RAPR AI
          ws.send(JSON.stringify({
            jsonrpc: "2.0",
            id: msgId,
            result: {
              content: [
                { type: "text", text: JSON.stringify(response.result, null, 2) }
              ],
            },
          }));
        } else {
          // Send error back
          ws.send(JSON.stringify({
            jsonrpc: "2.0",
            id: msgId,
            error: {
              code: -32603,
              message: response.error || "Tool execution failed",
            },
          }));
        }
      } catch (err) {
        ws.send(JSON.stringify({
          jsonrpc: "2.0",
          id: msgId,
          error: {
            code: -32603,
            message: String(err),
          },
        }));
      }
      return;
    }
  };

  ws.onclose = (event) => {
    console.log("[Offscreen] WebSocket closed:", event.code, event.reason);
    connected = false;
    connectedAt = null;
    stopHeartbeat();
    if (token) {
      scheduleReconnect();
    }
  };

  ws.onerror = (error) => {
    console.error("[Offscreen] WebSocket error:", error);
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
  if (!token) return;  // Don't reconnect if deliberately disconnected
  console.log(`[Offscreen] Reconnecting in ${reconnectDelay / 1000}s...`);
  setTimeout(() => {
    if (token && !connected) {
      connect(serverUrl, token);
    }
  }, reconnectDelay);
  reconnectDelay = Math.min(reconnectDelay * 2, 30000);  // max 30s
}

// ---------------------------------------------------------------------------
// Heartbeat (keeps service worker and WebSocket alive)
// ---------------------------------------------------------------------------

function startHeartbeat() {
  stopHeartbeat();
  heartbeatInterval = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      // Send a JSON-RPC notification (no id = no response expected)
      ws.send(JSON.stringify({ jsonrpc: "2.0", method: "heartbeat" }));
    }
  }, 25000);  // every 25 seconds
}

function stopHeartbeat() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
    heartbeatInterval = null;
  }
}

// ---------------------------------------------------------------------------
// Message routing to service worker
// ---------------------------------------------------------------------------

function sendToServiceWorker(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(response || { ok: false, error: "No response" });
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Listen for messages from popup / service worker
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case "get_status":
      sendResponse({
        connected,
        serverUrl,
        connectedAt,
        tools: 12,
      });
      return false;

    case "connect":
      connect(message.url, message.token)
        .then(() => sendResponse({ ok: true }))
        .catch((err) => sendResponse({ ok: false, error: String(err) }));
      return true;

    case "disconnect":
      disconnect();
      sendResponse({ ok: true });
      return false;

    default:
      return false;
  }
});

// ---------------------------------------------------------------------------
// Auto-connect on startup if credentials are stored
// ---------------------------------------------------------------------------

(async () => {
  const config = await chrome.storage.local.get(["rapr_url", "rapr_token"]);
  if (config.rapr_url && config.rapr_token) {
    console.log("[Offscreen] Auto-connecting to", config.rapr_url);
    connect(config.rapr_url, config.rapr_token);
  }
})();
