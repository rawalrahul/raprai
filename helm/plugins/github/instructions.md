# GitHub Plugin — RAPR AI

You have access to the GitHub API via the `GITHUB_TOKEN` environment variable.

## Authentication
```python
import os, requests

GH_TOKEN = os.environ["GITHUB_TOKEN"]
HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}
BASE = "https://api.github.com"
```

## Common Operations

### List user repos
```python
resp = requests.get(f"{BASE}/user/repos", headers=HEADERS,
                    params={"sort": "updated", "per_page": 20})
repos = resp.json()
for r in repos:
    print(f"{r['full_name']} ({'private' if r['private'] else 'public'}) ★{r['stargazers_count']}")
```

### Get repo details
```python
resp = requests.get(f"{BASE}/repos/owner/repo-name", headers=HEADERS)
repo = resp.json()
```

### List issues
```python
resp = requests.get(f"{BASE}/repos/owner/repo/issues", headers=HEADERS,
                    params={"state": "open", "per_page": 20})
issues = resp.json()
```

### Create an issue
```python
requests.post(f"{BASE}/repos/owner/repo/issues", headers=HEADERS, json={
    "title": "Bug: login page broken",
    "body": "The login form throws a 500 error on submit.",
    "labels": ["bug", "high-priority"]
})
```

### List pull requests
```python
resp = requests.get(f"{BASE}/repos/owner/repo/pulls", headers=HEADERS,
                    params={"state": "open"})
prs = resp.json()
```

### Create a pull request
```python
requests.post(f"{BASE}/repos/owner/repo/pulls", headers=HEADERS, json={
    "title": "Add dark mode support",
    "body": "Implements dark mode toggle in settings.",
    "head": "feature/dark-mode",
    "base": "main"
})
```

### Get file contents
```python
resp = requests.get(f"{BASE}/repos/owner/repo/contents/path/to/file.py", headers=HEADERS)
import base64
content = base64.b64decode(resp.json()["content"]).decode()
```

### Search code
```python
resp = requests.get(f"{BASE}/search/code", headers=HEADERS,
                    params={"q": "className+repo:owner/repo"})
items = resp.json().get("items", [])
```

### List workflow runs (Actions)
```python
resp = requests.get(f"{BASE}/repos/owner/repo/actions/runs", headers=HEADERS,
                    params={"per_page": 5})
runs = resp.json().get("workflow_runs", [])
```

### Create a comment on an issue/PR
```python
requests.post(f"{BASE}/repos/owner/repo/issues/42/comments", headers=HEADERS, json={
    "body": "Looks good! Merging now."
})
```

## Tips
- Use a fine-grained personal access token with only the scopes you need.
- Rate limit: 5,000 req/hour for authenticated requests. Check `X-RateLimit-Remaining` header.
- Pagination: follow `Link` header or use `page` and `per_page` params.
- For large file contents, use the Git Blobs API instead of Contents API.
- PR and Issue numbers are interchangeable in the Issues API for comments.
