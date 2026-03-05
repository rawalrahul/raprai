---
name: app-connector
description: "Connect AI assistants to external apps using OAuth2, API keys, REST patterns, webhooks, and error handling for Gmail, Slack, GitHub, Notion, Jira, Google Sheets"
category: ai-automation
difficulty: intermediate
model_boost: "Weak models often confuse OAuth flows, hardcode secrets, ignore rate limits, and fail to implement retry logic"
---

# AI App Connector: API Integration Framework

## Purpose
Enable AI assistants to reliably integrate with external services through standardized API patterns. This skill covers authentication flows (OAuth2, API keys), REST operations, webhook handling, rate limiting, and production-ready error recovery. Use this to build automated workflows that safely connect Claude to Gmail, Slack, GitHub, Notion, Jira, Google Sheets, and similar platforms.

## When to Use / Do NOT use when
**USE WHEN:** Building assistant features that send emails, post messages, create tasks, update databases, or sync data across platforms.
**DO NOT:** Use hardcoded credentials, skip error handling, ignore rate limits, or store secrets in configuration files.

## Instructions

### Step 1: Choose Authentication Method
**OAuth2** (recommended for user-facing apps): Users grant permission, tokens auto-refresh
- Best for: Gmail, Slack, GitHub, Google Sheets
- Flow: Redirect → Authorize → Receive code → Exchange for token

**API Key** (for service-to-service): Static credential, simpler but less secure
- Best for: Notion, Jira, internal APIs
- Storage: Environment variables only, never in code

**Personal Access Token**: User-generated OAuth alternative
- Best for: GitHub, internal tools

### Step 2: Implement OAuth2 Flow for Gmail
```javascript
const oauth2Client = new google.auth.OAuth2(
  CLIENT_ID,
  CLIENT_SECRET,
  REDIRECT_URL  // e.g., http://localhost:3000/oauth/callback
);

// Step 1: Generate authorization URL
const authUrl = oauth2Client.generateAuthUrl({
  access_type: 'offline',
  scope: ['https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.readonly']
});
// Redirect user to authUrl

// Step 2: Handle callback with authorization code
async function handleCallback(code) {
  const {tokens} = await oauth2Client.getToken(code);
  oauth2Client.setCredentials(tokens);
  // Store tokens.refresh_token in secure database
  return tokens.access_token;
}

// Step 3: Auto-refresh expired tokens
oauth2Client.on('tokens', (tokens) => {
  if (tokens.refresh_token) {
    // Update refresh_token in secure storage
    saveRefreshToken(tokens.refresh_token);
  }
});
```

### Step 3: Build a Generic API Client with Error Handling
```javascript
class APIClient {
  constructor(baseURL, authHeader) {
    this.baseURL = baseURL;
    this.authHeader = authHeader;
    this.maxRetries = 3;
    this.retryDelay = 1000; // ms
  }

  async request(method, endpoint, data = null, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...this.authHeader,
      ...options.headers
    };

    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        const response = await fetch(url, {
          method,
          headers,
          body: data ? JSON.stringify(data) : null,
          timeout: 30000
        });

        // Handle rate limiting
        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After') || 60;
          if (attempt < this.maxRetries) {
            await this.sleep(parseInt(retryAfter) * 1000);
            continue;
          }
        }

        // Handle auth errors
        if (response.status === 401) {
          throw new Error('Authentication failed: Invalid or expired token');
        }

        if (!response.ok) {
          throw new Error(`API Error ${response.status}: ${await response.text()}`);
        }

        return await response.json();
      } catch (error) {
        if (attempt === this.maxRetries) throw error;

        // Exponential backoff: 1s, 2s, 4s
        await this.sleep(this.retryDelay * Math.pow(2, attempt - 1));
      }
    }
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  get(endpoint) { return this.request('GET', endpoint); }
  post(endpoint, data) { return this.request('POST', endpoint, data); }
  put(endpoint, data) { return this.request('PUT', endpoint, data); }
  delete(endpoint) { return this.request('DELETE', endpoint); }
}
```

### Step 4: Slack Integration Example
```javascript
const slack = new APIClient(
  'https://slack.com/api',
  { 'Authorization': `Bearer ${process.env.SLACK_BOT_TOKEN}` }
);

// Send message
async function sendSlackMessage(channel, text) {
  return slack.post('/chat.postMessage', {
    channel,
    text,
    blocks: [  // Rich formatting
      {
        type: 'section',
        text: { type: 'mrkdwn', text }
      }
    ]
  });
}

// Get conversation history with pagination
async function getConversationHistory(channel, limit = 100) {
  let allMessages = [];
  let cursor = null;

  while (true) {
    const response = await slack.get(
      `/conversations.history?channel=${channel}&limit=${limit}` +
      (cursor ? `&cursor=${cursor}` : '')
    );

    allMessages = [...allMessages, ...response.messages];

    if (!response.response_metadata?.next_cursor) break;
    cursor = response.response_metadata.next_cursor;
  }

  return allMessages;
}
```

### Step 5: GitHub API Integration
```javascript
const github = new APIClient(
  'https://api.github.com',
  { 'Authorization': `token ${process.env.GITHUB_TOKEN}`,
    'User-Agent': 'AI-Assistant' }
);

// Create issue
async function createGitHubIssue(owner, repo, title, body, labels = []) {
  return github.post(`/repos/${owner}/${repo}/issues`, {
    title,
    body,
    labels
  });
}

// List pull requests with filtering
async function listPullRequests(owner, repo, state = 'open') {
  return github.get(
    `/repos/${owner}/${repo}/pulls?state=${state}&per_page=100&sort=updated`
  );
}

// Get user repositories
async function getUserRepos(username) {
  return github.get(`/users/${username}/repos?per_page=100&sort=updated`);
}
```

### Step 6: Notion Database Integration
```javascript
const notion = new APIClient(
  'https://api.notion.com/v1',
  { 'Authorization': `Bearer ${process.env.NOTION_TOKEN}`,
    'Notion-Version': '2022-06-28' }
);

// Add item to Notion database
async function addNotionPage(databaseId, properties) {
  return notion.post('/pages', {
    parent: { database_id: databaseId },
    properties  // Must match database schema
  });
}

// Query database with filtering
async function queryNotionDatabase(databaseId, filterCriteria) {
  return notion.post(`/databases/${databaseId}/query`, {
    filter: filterCriteria,
    sorts: [{ property: 'Created', direction: 'descending' }]
  });
}

// Example properties format
const taskProperties = {
  'Title': { title: [{ text: { content: 'Task name' } }] },
  'Status': { select: { name: 'In Progress' } },
  'Due Date': { date: { start: '2026-03-15' } },
  'Priority': { select: { name: 'High' } },
  'Assigned': { people: [{ id: 'user-id' }] }
};
```

### Step 7: Webhook Receiver Implementation
```javascript
// Express.js webhook receiver
const express = require('express');
const app = express();

app.post('/webhooks/slack', express.json(), async (req, res) => {
  const { token, challenge, type, event } = req.body;

  // Verify webhook authenticity
  if (token !== process.env.SLACK_VERIFICATION_TOKEN) {
    return res.status(401).send('Unauthorized');
  }

  // Respond to challenge immediately
  if (type === 'url_verification') {
    return res.json({ challenge });
  }

  // Handle actual event asynchronously
  if (type === 'event_callback') {
    res.status(200).send('OK');  // Respond immediately

    try {
      await handleSlackEvent(event);
    } catch (error) {
      console.error('Webhook processing error:', error);
      // Log for manual retry
    }
  }
});

async function handleSlackEvent(event) {
  if (event.type === 'message' && !event.bot_id) {
    console.log(`New message in ${event.channel}: ${event.text}`);
    // Process message
  }
}
```

### Step 8: Rate Limiting and Backoff
```javascript
class RateLimiter {
  constructor(maxRequests = 100, timeWindowMs = 60000) {
    this.maxRequests = maxRequests;
    this.timeWindowMs = timeWindowMs;
    this.requests = [];
  }

  async waitIfNeeded() {
    const now = Date.now();
    // Remove old requests outside window
    this.requests = this.requests.filter(t => t > now - this.timeWindowMs);

    if (this.requests.length >= this.maxRequests) {
      const oldestRequest = this.requests[0];
      const waitTime = oldestRequest + this.timeWindowMs - now;
      console.log(`Rate limit hit, waiting ${waitTime}ms`);
      await new Promise(r => setTimeout(r, waitTime));
    }

    this.requests.push(now);
  }
}

// Usage
const limiter = new RateLimiter(15, 60000);  // 15 req/min for Slack
// Before each API call:
await limiter.waitIfNeeded();
```

### Step 9: Secret Management
```javascript
// CORRECT: Environment variables
const GMAIL_CLIENT_ID = process.env.GMAIL_CLIENT_ID;
const SLACK_TOKEN = process.env.SLACK_TOKEN;

// Store in .env file (never commit)
// SLACK_TOKEN=xoxb-xxx-yyy-zzz
// GMAIL_CLIENT_ID=abc123.apps.googleusercontent.com

// For secure storage in production, use:
// - AWS Secrets Manager
// - HashiCorp Vault
// - Google Cloud Secret Manager
// - Azure Key Vault

// Rotating tokens
async function rotateToken(service, oldToken) {
  const newToken = await requestNewToken(service);
  await saveToSecureStore(service, newToken);
  return newToken;
}
```

### Step 10: Error Recovery and Logging
```javascript
class IntegrationLogger {
  log(service, action, status, details) {
    const timestamp = new Date().toISOString();
    const entry = {
      timestamp,
      service,
      action,
      status,  // 'success', 'retry', 'failed'
      details,
      duration_ms: details.duration_ms
    };

    // Write to structured log
    console.log(JSON.stringify(entry));

    // Alert on failures
    if (status === 'failed') {
      alertOpsTeam(entry);
    }
  }
}

// Usage
const logger = new IntegrationLogger();

try {
  const start = Date.now();
  await sendSlackMessage('general', 'Test message');
  logger.log('slack', 'send_message', 'success', {
    duration_ms: Date.now() - start
  });
} catch (error) {
  logger.log('slack', 'send_message', 'failed', {
    error: error.message,
    duration_ms: Date.now() - start
  });
}
```

## Output Template

```
API Integration Summary
======================
Service: [Gmail/Slack/GitHub/etc]
Endpoint: [Base URL]
Auth Method: [OAuth2/API Key/PAT]
Rate Limits: [X requests per Y seconds]
Retry Strategy: [Max retries, backoff]
Logging Level: [Debug/Info/Error]

Endpoints Configured:
- GET /endpoint → [Purpose]
- POST /endpoint → [Purpose]

Error Handling:
- 401 → [Action]
- 429 → [Action]
- 5xx → [Action]

Webhook Status: [Active/Inactive]
Last Test: [Timestamp]
```

## Quality Gates

1. **Authentication works**: Can successfully call at least 2 API endpoints
2. **Tokens refresh automatically**: No 401 errors after initial auth
3. **Rate limits respected**: Requests never exceed service limits
4. **Retries work**: API recovers from transient failures within maxRetries
5. **No hardcoded secrets**: Zero secrets in code or config files
6. **Webhooks respond promptly**: Challenge response < 3 seconds
7. **Error messages are actionable**: Developer can debug from logs

## Examples

### Good: Slack Message with Error Handling
```javascript
async function sendAlert(message) {
  const slack = new APIClient(
    'https://slack.com/api',
    { 'Authorization': `Bearer ${process.env.SLACK_BOT_TOKEN}` }
  );

  try {
    const result = await slack.post('/chat.postMessage', {
      channel: '#alerts',
      text: message,
      blocks: [{
        type: 'section',
        text: { type: 'mrkdwn', text: `⚠️ *Alert*: ${message}` }
      }]
    });

    return { success: true, ts: result.ts };
  } catch (error) {
    console.error('Failed to send Slack alert:', error.message);
    return { success: false, error: error.message };
  }
}
```

### Bad: Direct Slack Call Without Error Handling
```javascript
// DO NOT DO THIS
fetch('https://slack.com/api/chat.postMessage', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${TOKEN}` },
  body: JSON.stringify({ channel: '#alerts', text: message })
}).then(r => r.json()).then(console.log);
// Missing: retry logic, error handling, rate limiting
```

## Common Mistakes

1. **Storing secrets in code**: Hardcoding API keys in source or config. Use environment variables and secure vaults.

2. **Not handling rate limits**: Ignoring 429 responses causes cascading failures. Implement Retry-After and exponential backoff.

3. **Ignoring token expiration**: OAuth tokens expire. Use refresh tokens and re-authenticate automatically.

4. **Synchronous error responses in webhooks**: Taking > 3s to respond causes timeouts. Respond immediately, process asynchronously.

5. **No pagination for large datasets**: Requesting 10,000 items in one call fails. Always paginate with cursors or offsets.

## Anti-Patterns

1. **Polling instead of webhooks**: Checking status every 10 seconds wastes API calls. Use webhooks when available.

2. **Single-threaded API calls**: Making requests sequentially when they could be parallel. Use Promise.all() for multiple independent calls.

3. **No circuit breaker**: If an API is down, continuously retrying wastes resources. Implement circuit breaker: fail fast after N failures, retry after delay.

4. **Storing entire responses**: Caching full API responses without TTL causes stale data. Cache with expiration times based on data freshness.

5. **Global error handling**: Generic catch-all handlers mask specific issues. Handle 401, 429, 5xx separately with different logic.
