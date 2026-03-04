# Linear / Jira Plugin — RAPR AI

This plugin supports both Linear and Jira. Use whichever the user has configured.

---

## OPTION A: Linear

### Authentication
```python
import os, requests

LINEAR_KEY = os.environ["LINEAR_API_KEY"]
HEADERS = {"Authorization": LINEAR_KEY, "Content-Type": "application/json"}
BASE = "https://api.linear.app/graphql"
```

### Query issues
```python
query = """
query {
  issues(first: 20, orderBy: updatedAt) {
    nodes {
      id identifier title state { name } priority assignee { name }
    }
  }
}
"""
resp = requests.post(BASE, headers=HEADERS, json={"query": query})
issues = resp.json()["data"]["issues"]["nodes"]
for i in issues:
    print(f"{i['identifier']}: {i['title']} [{i['state']['name']}]")
```

### Create an issue
```python
mutation = """
mutation($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success issue { id identifier title url }
  }
}
"""
variables = {
    "input": {
        "teamId": "TEAM_ID",
        "title": "Fix login bug",
        "description": "Login form returns 500 on submit",
        "priority": 2  # 0=none, 1=urgent, 2=high, 3=medium, 4=low
    }
}
resp = requests.post(BASE, headers=HEADERS, json={"query": mutation, "variables": variables})
```

### Update issue status
```python
mutation = """
mutation($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) { success }
}
"""
variables = {"id": "ISSUE_ID", "input": {"stateId": "STATE_ID"}}
requests.post(BASE, headers=HEADERS, json={"query": mutation, "variables": variables})
```

### List teams
```python
query = '{ teams { nodes { id name key } } }'
resp = requests.post(BASE, headers=HEADERS, json={"query": query})
```

---

## OPTION B: Jira

### Authentication
```python
import os, requests
from requests.auth import HTTPBasicAuth

JIRA_DOMAIN = os.environ["JIRA_DOMAIN"]  # e.g., "mycompany.atlassian.net"
JIRA_EMAIL = os.environ["JIRA_EMAIL"]
JIRA_TOKEN = os.environ["JIRA_API_TOKEN"]
AUTH = HTTPBasicAuth(JIRA_EMAIL, JIRA_TOKEN)
HEADERS = {"Content-Type": "application/json"}
BASE = f"https://{JIRA_DOMAIN}/rest/api/3"
```

### Search issues (JQL)
```python
resp = requests.get(f"{BASE}/search", auth=AUTH, headers=HEADERS, params={
    "jql": "project = PROJ AND status = 'In Progress' ORDER BY updated DESC",
    "maxResults": 20,
    "fields": "summary,status,assignee,priority"
})
issues = resp.json().get("issues", [])
for i in issues:
    print(f"{i['key']}: {i['fields']['summary']} [{i['fields']['status']['name']}]")
```

### Create an issue
```python
requests.post(f"{BASE}/issue", auth=AUTH, headers=HEADERS, json={
    "fields": {
        "project": {"key": "PROJ"},
        "summary": "Fix login bug",
        "description": {"type": "doc", "version": 1, "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Details here."}]}
        ]},
        "issuetype": {"name": "Bug"},
        "priority": {"name": "High"}
    }
})
```

### Update an issue
```python
requests.put(f"{BASE}/issue/PROJ-123", auth=AUTH, headers=HEADERS, json={
    "fields": {"summary": "Updated title"}
})
```

### Transition an issue (change status)
```python
# Get available transitions
resp = requests.get(f"{BASE}/issue/PROJ-123/transitions", auth=AUTH, headers=HEADERS)
transitions = resp.json()["transitions"]

# Apply transition
requests.post(f"{BASE}/issue/PROJ-123/transitions", auth=AUTH, headers=HEADERS, json={
    "transition": {"id": "31"}  # ID from above
})
```

## Tips
- **Linear**: Uses GraphQL exclusively. List teams first to get team IDs, then states.
- **Jira**: Uses REST. Jira Cloud uses Atlassian Document Format (ADF) for descriptions.
- Ask the user which tool they use if unclear from context.
- Linear rate limit: 1,500 req/hour. Jira: ~100 req/min.
