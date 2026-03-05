---
name: api-documentation-writer
description: "Create developer-friendly API documentation with authentication guides, endpoint reference, code samples, and interactive examples. Follows OpenAPI/Swagger standards for maximum usability."
category: professional
difficulty: advanced
model_boost: "Weak models produce incomplete documentation missing examples; this skill ensures comprehensive docs with request/response examples, error codes, and SDKs in multiple languages"
---

# API Documentation Writer

## Purpose
API documentation is your product's instruction manual for developers. Poor documentation frustrates developers, increases support burden, and reduces API adoption. Great documentation (with quick-start guides, clear endpoint reference, working code examples in multiple languages, and interactive "Try It" features) enables developers to integrate your API in hours instead of days. This skill walks you through creating documentation that developers actually use and love.

## When to Use
- Building a public API (for external developer consumption)
- Publishing a new API or major version
- Improving existing documentation that receives support tickets
- Creating documentation for internal APIs (same principles apply)
- Building SDKs or code samples for multiple languages
- **Do NOT use when**: API design is incomplete (finish design first), you lack complete endpoint specifications, or API isn't stable (mark docs clearly as "beta")

## Instructions

### Step 1: Create Getting Started / Quickstart (300-500 words)
First-time developers should be able to make their first successful API call in <10 minutes.

**Quickstart Structure**:

**What You'll Learn** (50 words):
"In this guide, you'll learn how to authenticate with the API, make your first request, and handle responses. By the end, you'll have created a project and retrieved project details."

**Prerequisites** (50-75 words):
- An account with our service
- An API key (generated in your account settings)
- cURL, Postman, or a programming language with HTTP support
- 10 minutes

**Step 1: Get Your API Key** (100-150 words):
"Your API key authenticates all requests. To get it:
1. Log into your account at [link]
2. Navigate to Settings → API Keys
3. Click 'Generate New Key'
4. Copy the key—we'll use it in the next step
5. Store it safely; don't share it publicly

Your API key looks like: `sk_live_abc123def456`"

**Step 2: Make Your First Request** (100-150 words):
"Replace YOUR_API_KEY below with your actual key:

**Using cURL**:
```bash
curl -X GET "https://api.example.com/v1/projects" \
  -H "Authorization: Bearer sk_live_abc123def456"
```

**Using Python** (with requests library):
```python
import requests

url = "https://api.example.com/v1/projects"
headers = {
    "Authorization": "Bearer sk_live_abc123def456"
}
response = requests.get(url, headers=headers)
print(response.json())
```

**Using JavaScript** (with Fetch API):
```javascript
const apiKey = "sk_live_abc123def456";
const response = await fetch("https://api.example.com/v1/projects", {
  headers: {
    "Authorization": `Bearer ${apiKey}`
  }
});
const data = await response.json();
console.log(data);
```

Copy-paste one of the above and run it. You should see a response with your projects."

**Step 3: Understand the Response** (100-150 words):
"The response should look like:
```json
{
  "data": [
    {
      "id": "proj_123abc",
      "name": "My First Project",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 1
  }
}
```

Each project has:
- **id**: Unique identifier (use this to reference the project)
- **name**: Project name
- **status**: 'active' or 'archived'
- **created_at**: When the project was created

**Next Steps**: Create a project, add data, retrieve details. See [Create a Project] endpoint below."

**Step 4: Handle Errors** (50-100 words):
"If something goes wrong, you'll get an error response:
```json
{
  "error": {
    "code": "unauthorized",
    "message": "Invalid API key"
  }
}
```

Common errors:
- `unauthorized`: Check your API key is correct
- `not_found`: The resource doesn't exist (wrong ID)
- `rate_limit_exceeded`: You've made too many requests; wait 60 seconds

See [Error Codes] for full list."

### Step 2: Write Authentication Guide (250-400 words)
Many support issues stem from authentication confusion. Be crystal clear.

**Authentication Methods** (if you support multiple):

**Method 1: Bearer Token Authentication** (Most Common)
"Include your API key in the `Authorization` header of every request:

```
Authorization: Bearer YOUR_API_KEY
```

**Example**:
```bash
curl -H "Authorization: Bearer sk_live_abc123def456" \
  https://api.example.com/v1/projects
```

**Key Points**:
- Keep your API key secret (don't commit to version control, don't share)
- Use different keys for development and production
- Rotate keys periodically
- If a key is compromised, generate a new one immediately (old key stops working)"

**Method 2: API Key in Query Parameter** (If Supported)
"Alternative to Bearer token (less secure; recommended for read-only operations):

```
https://api.example.com/v1/projects?api_key=sk_live_abc123def456
```

**When to use**: Only for GET requests in client-side code where headers can't be set (e.g., image URLs). Never use for sensitive operations."

**Method 3: OAuth 2.0** (If Applicable)
"For third-party integrations:
[Detailed OAuth flow steps, code examples]"

**API Key Management**:
- **Generate**: Visit Settings → API Keys → Generate New Key
- **List**: All active keys are listed with creation date and last used date
- **Revoke**: Click 'Revoke' to deactivate a key immediately
- **Rotate**: Best practice is to generate a new key, update your application, then revoke the old key
- **Rate Limits**: Each key has its own rate limit (100 requests/minute by default; upgrade for higher limits)

**Environment Variable Recommendation**:
"Store your API key in an environment variable instead of hardcoding:

**Python**:
```python
import os
api_key = os.getenv('API_KEY')
```

**JavaScript/Node.js**:
```javascript
const apiKey = process.env.API_KEY;
```

**Bash**:
```bash
export API_KEY="sk_live_abc123def456"
curl -H "Authorization: Bearer $API_KEY" ...
```"

### Step 3: Document Each Endpoint (400-600 words per endpoint)
Follow OpenAPI/Swagger structure. Include method, URL, parameters, request, response, and errors.

**Endpoint Documentation Template**:

```
### Create a Project
```
POST /v1/projects
```

**Description**: Creates a new project.

**Parameters** (Request Body):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | string | Yes | Project name (1-255 characters) |
| description | string | No | Project description |
| status | string | No | 'active' (default) or 'archived' |
| tags | array | No | Array of tag strings (up to 10 tags) |

**Request Example**:

```bash
curl -X POST "https://api.example.com/v1/projects" \
  -H "Authorization: Bearer sk_live_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q1 Marketing Campaign",
    "description": "Social media and email campaign for Q1 2024",
    "tags": ["marketing", "q1-2024"]
  }'
```

**Response** (201 Created):

```json
{
  "data": {
    "id": "proj_456def",
    "name": "Q1 Marketing Campaign",
    "description": "Social media and email campaign for Q1 2024",
    "status": "active",
    "tags": ["marketing", "q1-2024"],
    "created_at": "2024-01-15T14:30:00Z",
    "updated_at": "2024-01-15T14:30:00Z"
  }
}
```

**Errors**:

| Status | Error Code | Message | Fix |
|--------|------------|---------|-----|
| 400 | bad_request | Name is required | Include 'name' field in request |
| 400 | validation_error | Name must be 1-255 characters | Shorten project name |
| 401 | unauthorized | Invalid API key | Check API key is correct |
| 429 | rate_limit_exceeded | Too many requests | Wait 60 seconds before retrying |
| 500 | server_error | Internal server error | Retry after 5 seconds; contact support if persists |

**Response Headers**:

| Header | Description |
|--------|-------------|
| X-Request-ID | Unique request identifier (useful for support tickets) |
| X-RateLimit-Limit | Maximum requests allowed per minute |
| X-RateLimit-Remaining | Requests remaining in current minute |
| X-RateLimit-Reset | Unix timestamp when rate limit resets |

**Code Samples** (Multiple Languages):

**Python**:
```python
import requests

api_key = "sk_live_abc123def456"
url = "https://api.example.com/v1/projects"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
data = {
    "name": "Q1 Marketing Campaign",
    "description": "Social media and email campaign",
    "tags": ["marketing", "q1"]
}

response = requests.post(url, headers=headers, json=data)
if response.status_code == 201:
    project = response.json()["data"]
    print(f"Created project: {project['id']}")
else:
    print(f"Error: {response.status_code}")
```

**JavaScript/Node.js**:
```javascript
const apiKey = "sk_live_abc123def456";
const response = await fetch("https://api.example.com/v1/projects", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${apiKey}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    name: "Q1 Marketing Campaign",
    description: "Social media and email campaign",
    tags: ["marketing", "q1"]
  })
});

if (response.status === 201) {
  const { data } = await response.json();
  console.log("Created project:", data.id);
} else {
  console.error("Error:", response.status);
}
```

**Go**:
```go
package main

import (
  "bytes"
  "encoding/json"
  "fmt"
  "io/ioutil"
  "net/http"
)

func main() {
  apiKey := "sk_live_abc123def456"

  data := map[string]interface{}{
    "name": "Q1 Marketing Campaign",
    "description": "Social media and email campaign",
    "tags": []string{"marketing", "q1"},
  }

  jsonData, _ := json.Marshal(data)

  req, _ := http.NewRequest("POST", "https://api.example.com/v1/projects", bytes.NewBuffer(jsonData))
  req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", apiKey))
  req.Header.Set("Content-Type", "application/json")

  client := &http.Client{}
  resp, _ := client.Do(req)

  body, _ := ioutil.ReadAll(resp.Body)
  fmt.Println(string(body))
}
```
```

### Step 4: Document Rate Limits and Pagination (200-300 words)

**Rate Limiting**:
"API requests are rate-limited to prevent abuse. Default limits:
- **Free tier**: 100 requests per minute
- **Pro tier**: 1,000 requests per minute
- **Enterprise**: Custom limits

When you hit the limit, you'll receive a 429 (Too Many Requests) response:
```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Too many requests. Try again in 60 seconds."
  }
}
```

**Headers to Monitor**:
- `X-RateLimit-Limit`: Your rate limit (e.g., 100)
- `X-RateLimit-Remaining`: Requests left in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

**Best Practice**: Check `X-RateLimit-Remaining` and pause if approaching the limit. Implement exponential backoff for retries."

**Pagination**:
"Large result sets are paginated (default: 10 items per page). Control pagination with query parameters:

```
GET /v1/projects?page=2&limit=50
```

**Parameters**:
- `page`: Page number (1-indexed; default: 1)
- `limit`: Items per page (1-100; default: 10)

**Response Structure**:
```json
{
  "data": [ ... ],
  "pagination": {
    "page": 2,
    "limit": 50,
    "total": 150,
    "pages": 3
  }
}
```

Use `total` and `limit` to calculate remaining pages. Example: (Total: 150, Limit: 50) = 3 pages."

### Step 5: Document Webhooks (if applicable) (200-300 words)

"Webhooks allow you to subscribe to events and receive HTTP callbacks when they occur.

**Supported Events**:
- `project.created`: A new project was created
- `project.updated`: A project was modified
- `task.created`: A new task was created
- `task.completed`: A task was marked complete

**Setting Up a Webhook**:
1. Go to Settings → Webhooks
2. Click 'Add Webhook'
3. Enter your endpoint URL (must be HTTPS)
4. Select events to subscribe to
5. Click 'Save'

**Webhook Payload** (Example: project.created):
```json
{
  "event": "project.created",
  "data": {
    "id": "proj_123abc",
    "name": "New Project",
    "created_at": "2024-01-15T14:30:00Z"
  },
  "timestamp": "2024-01-15T14:30:00Z",
  "id": "evt_456def"
}
```

**Retry Logic**:
- Initial attempt: Immediately after event
- Retry 1: 30 seconds later
- Retry 2: 5 minutes later
- Retry 3: 30 minutes later
- After 3 failures: Webhook is disabled (re-enable in Settings)

**Signature Verification** (Security Best Practice):
All webhooks are signed with HMAC-SHA256. Verify the signature to ensure webhooks are authentic.

Header: `X-Webhook-Signature: sha256=abc123...`

```python
import hmac
import hashlib

def verify_webhook(payload, signature, webhook_secret):
    expected = hmac.new(
        webhook_secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature.replace("sha256=", ""), expected)
```"

### Step 6: Provide Migration Guides and Changelog (200-300 words)

"**API Versioning**:
Current version: v1. We support the current version and the previous major version (v0) for 12 months after releasing a new major version.

**Upcoming Changes**:
- **v2** (planned for Q2 2024): Simplified webhook payloads, new authentication method
- v0 (deprecating Q1 2025): Stop supporting v0 after Q1 2025; migrate to v1 or v2

**Migration Guides**:
- [Migrate from v0 to v1]: Changes, examples, timeline
- [Migrate from v1 to v2 (Coming Soon)]: Planned changes

**Changelog**:
- **v1.2.0** (Jan 2024): Added webhook signature verification, new 'tags' field on projects, deprecation notice for /projects/legacy endpoint
- **v1.1.0** (Dec 2023): Added custom fields feature, improved error messages
- **v1.0.0** (Oct 2023): Initial release"

### Step 7: Include SDK Documentation and Try It (100-200 words)

"**Official SDKs**:
We maintain SDKs for popular languages:
- [Python SDK](link) – pip install example-api
- [Node.js/JavaScript SDK](link) – npm install example-api
- [Go SDK](link) – go get github.com/example/api-go
- [Ruby SDK](link) – gem install example-api

**Using the Python SDK**:
```python
from example_api import Client

client = Client(api_key="sk_live_abc123def456")
project = client.projects.create(name="My Project")
print(f"Created: {project.id}")
```

**Try It Interactive**:
We provide interactive 'Try It' buttons for every endpoint (powered by [Swagger UI / Postman / Your Platform]). Click the endpoint, enter parameters, and execute requests directly from the docs without leaving the page."

## Output Template

```
---
api_name: "[API Name]"
api_version: "[Version, e.g., v1]"
base_url: "[Base URL, e.g., https://api.example.com]"
auth_type: "[Bearer Token / API Key / OAuth 2.0]"
documentation_version: "[YYYY-MM-DD]"
---

# [API Name] Documentation

## Getting Started / Quickstart
[300-500 words with step-by-step first API call]

## Authentication
[250-400 words covering auth methods, key management, security]

---

## API Endpoints Reference

### [Resource Name] Endpoints

#### Create [Resource]
```
POST /v1/[resource]
```
[400-600 words: description, parameters table, request/response examples, error table, code samples in 3+ languages]

#### List [Resource]
```
GET /v1/[resource]
```
[Similar structure]

#### Get [Resource]
```
GET /v1/[resource]/{id}
```
[Similar structure]

#### Update [Resource]
```
PUT /v1/[resource]/{id}
```
[Similar structure]

#### Delete [Resource]
```
DELETE /v1/[resource]/{id}
```
[Similar structure]

---

## Rate Limits
[200-300 words on limits, monitoring, best practices]

## Pagination
[200-300 words with examples]

## Webhooks
[200-300 words if applicable]

## Error Codes Reference
[Comprehensive list of error codes with descriptions and fixes]

## Migration Guides
[Links to version migration documentation]

## Changelog
[Version history with changes documented]

## SDKs and Libraries
[Links to official SDKs with language-specific examples]

## Support & Troubleshooting
[Links to support channels, FAQ, common issues]
```

## Quality Gates
1. **Completeness**: Can developer integrate the API using only the documentation? Do all endpoints have examples?
2. **Code Examples Work**: Have code examples been tested? Do they actually run without modification (substituting API key)?
3. **Error Codes Comprehensive**: Are all possible error responses documented with solution guidance?
4. **Multiple Languages**: Are examples provided in 3+ languages (Python, JavaScript, Go minimum)?
5. **Try It Functionality**: Are interactive examples/endpoints available for testing?
6. **Accessibility**: Can a developer unfamiliar with the domain understand the documentation?
7. **Maintenance**: Is changelog updated with every API change? Is deprecation clearly documented?

## Common Mistakes

1. **Missing Code Examples** — Documentation has theory but no working examples. Developers waste time guessing. Solution: Every endpoint needs 3+ language examples (Python, JavaScript, Go).

2. **Incomplete Error Documentation** — Errors documented without explaining how to fix them. Developers contact support. Solution: Every error code should have "Why This Happened" and "How to Fix" sections.

3. **Request/Response Mismatch** — Example request doesn't match documented parameters, or response doesn't match schema. Developers get frustrated. Solution: Test all examples before publishing.

4. **Unclear Authentication** — Auth explained theoretically without showing where to put the API key in code. Solution: Show actual HTTP headers and code examples.

5. **No Rate Limit Guidance** — Rate limits documented but no guidance on how to handle them. Solution: Include retry logic and monitoring strategies.

6. **Deprecated Endpoints Not Marked** — Old endpoints still documented without "deprecated" label. New developers integrate with endpoints being removed. Solution: Mark deprecated endpoints clearly; provide migration guidance.

## Anti-Patterns

1. **The Theory-Only Documentation** — Explanation of what endpoint does without working example. Anti-pattern: "Endpoint creates a project with name and description" without code. Better: Show actual request/response with working code.

2. **The Single-Language Bias** — Examples only in one language. Developers using other languages are stuck. Anti-pattern: Python examples only. Better: Provide examples in Python, JavaScript, Go, Ruby (at minimum).

3. **The Incomplete Reference** — Some endpoints documented, others missing. Anti-pattern: "Create", "List", "Get" documented but "Update" and "Delete" are not. Better: Document all endpoints comprehensively.

4. **The Assumption of Knowledge** — Documentation assumes developer understands your domain jargon. Anti-pattern: "Use CAC field for cost optimization" without explaining CAC. Better: Define terms; assume no prior knowledge.

5. **The Stale Changelog** — Changelog hasn't been updated in months despite API changes. Developers don't know what's new. Better: Update changelog with every release; timestamp entries.
