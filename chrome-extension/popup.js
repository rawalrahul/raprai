/**
 * RAPR AI Browser Tools — Popup
 *
 * Simple connection UI:  enter server URL + bearer token, click Connect.
 * Shows connection status and available tool count.
 */

const statusBar = document.getElementById("statusBar");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const connectForm = document.getElementById("connectForm");
const disconnectForm = document.getElementById("disconnectForm");
const connectBtn = document.getElementById("connectBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const serverUrlInput = document.getElementById("serverUrl");
const tokenInput = document.getElementById("token");
const errorMsg = document.getElementById("errorMsg");
const toolsInfo = document.getElementById("toolsInfo");


// ---------------------------------------------------------------------------
// Load saved config and check connection status
// ---------------------------------------------------------------------------

async function init() {
  const config = await chrome.storage.local.get(["rapr_url", "rapr_token"]);
  if (config.rapr_url) serverUrlInput.value = config.rapr_url;
  if (config.rapr_token) tokenInput.value = config.rapr_token;

  checkStatus();
}

function checkStatus() {
  chrome.runtime.sendMessage({ type: "get_connection_status" }, (resp) => {
    if (chrome.runtime.lastError || !resp) {
      showDisconnected();
      return;
    }
    if (resp.connected) {
      showConnected();
    } else {
      showDisconnected();
    }
  });
}

function showConnected() {
  statusBar.className = "status-bar connected";
  statusDot.className = "dot green";
  statusText.textContent = "Connected to RAPR AI";
  connectForm.style.display = "none";
  disconnectForm.style.display = "block";
  toolsInfo.style.display = "block";
  errorMsg.style.display = "none";
}

function showDisconnected() {
  statusBar.className = "status-bar disconnected";
  statusDot.className = "dot red";
  statusText.textContent = "Disconnected";
  connectForm.style.display = "block";
  disconnectForm.style.display = "none";
  toolsInfo.style.display = "none";
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.style.display = "block";
}


// ---------------------------------------------------------------------------
// Connect / Disconnect
// ---------------------------------------------------------------------------

connectBtn.addEventListener("click", async () => {
  const url = serverUrlInput.value.trim();
  let tok = tokenInput.value.trim();

  if (!url) { showError("Server URL is required"); return; }

  connectBtn.disabled = true;
  connectBtn.textContent = "Connecting...";
  errorMsg.style.display = "none";

  // Auto-fetch token from RAPR AI if not provided
  if (!tok) {
    try {
      const resp = await fetch(url + "/chrome/status");
      const data = await resp.json();
      if (data.token) {
        tok = data.token;
        tokenInput.value = tok;
      } else {
        connectBtn.disabled = false;
        connectBtn.textContent = "Connect";
        showError("Could not auto-fetch token. Paste it manually from RAPR AI logs.");
        return;
      }
    } catch (e) {
      connectBtn.disabled = false;
      connectBtn.textContent = "Connect";
      showError("Cannot reach RAPR AI at " + url + ". Is it running?");
      return;
    }
  }

  chrome.runtime.sendMessage(
    { type: "connect", url, token: tok },
    (resp) => {
      connectBtn.disabled = false;
      connectBtn.textContent = "Connect";

      // Give the connection a moment to establish
      setTimeout(checkStatus, 1500);
    }
  );
});

disconnectBtn.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "disconnect" }, () => {
    showDisconnected();
  });
});


// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

init();
