---
name: mcp-server-builder
description: "Build Model Context Protocol servers exposing tools and resources to LLMs with proper error handling, transport config, and deployment patterns"
category: coding
difficulty: advanced
model_boost: "Weak models create MCP servers with missing error handling, unclear tool descriptions, and forget transport configuration. This skill ensures LLM-friendly tool design and production-ready deployment."
---

# MCP Server Builder

## Purpose
This skill teaches you to build Model Context Protocol (MCP) servers that extend LLM capabilities by exposing custom tools, resources, and prompts. Well-designed MCP servers are the bridge between AI assistants and your systems—they enable Claude to interact with databases, APIs, files, and custom logic safely and reliably. You'll learn to design agent-friendly tools (clear names, detailed descriptions, proper error handling), configure transports (stdio vs HTTP), and deploy for both local and remote access.

## When to Use
- You want Claude to interact with a proprietary API or database
- You're building an AI automation that needs external system access
- You want consistent, reusable integrations across multiple LLM applications
- You need versioning and monitoring of LLM tool interactions
- **Do NOT use when**: The task is a simple HTTP API call (just use native Claude instructions); you're building a user-facing application without LLM involvement

## Instructions

### Step 1: Choose Your SDK and Project Setup
Python (FastMCP) is easiest for rapid iteration. TypeScript SDK is better for Node.js ecosystems. Choose based on your team's strengths.

**Python/FastMCP approach:**
```bash
mkdir my-mcp-server
cd my-mcp-server
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install mcp fastmcp
```

**TypeScript approach:**
```bash
npm init -y
npm install @modelcontextprotocol/sdk typescript tsx ts-node
npx tsc --init
```

### Step 2: Define Your Tools (What Will the LLM Call?)
List 3-5 tools your LLM needs. For each, document:
- **Name** (snake_case, verb-based): `query_postgres_database`, not `db`
- **Description** (2-3 sentences): What it does, when to use it, any limitations
- **Input schema** (JSON Schema): Required fields, types, constraints
- **Example** (actual call + response)

Example:
```
Tool: query_postgres_database
Description: Execute a SELECT query against the production analytics database. Returns up to 1000 rows. Use for reporting, not mutations. Do NOT use UNION or subqueries (unsupported).
Input: {
  "query": {
    "type": "string",
    "description": "SQL SELECT statement. Use parameterized queries."
  },
  "timeout_seconds": {
    "type": "integer",
    "description": "Max execution time. Default 30."
  }
}
Example Input: {"query": "SELECT id, email FROM users WHERE created_at > NOW() - INTERVAL '7 days'", "timeout_seconds": 60}
Example Output: [{"id": 123, "email": "user@example.com"}, ...]
```

### Step 3: Implement Tools in FastMCP (Python)
Create `server.py`:

```python
from fastmcp import FastMCP
import psycopg2
from datetime import datetime
import json

mcp = FastMCP("analytics-server")

# Tool 1: Query database
@mcp.tool()
def query_postgres_database(query: str, timeout_seconds: int = 30) -> str:
    """
    Execute SELECT queries against production analytics DB.
    Returns up to 1000 rows. Use for reporting only.
    """
    try:
        conn = psycopg2.connect(
            host="analytics-db.company.com",
            database="analytics",
            user="llm_reader",
            password="<PASSWORD>",  # Use env vars in production
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute(f"SET statement_timeout TO {timeout_seconds * 1000}")

        # Validate query (anti-injection)
        if any(kw in query.upper() for kw in ["INSERT", "UPDATE", "DELETE", "DROP"]):
            return json.dumps({"error": "Only SELECT queries allowed"})

        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        # Convert to list of dicts
        results = [dict(zip(columns, row)) for row in rows[:1000]]

        cursor.close()
        conn.close()

        return json.dumps({
            "success": True,
            "row_count": len(results),
            "rows": results,
            "executed_at": datetime.utcnow().isoformat()
        })

    except psycopg2.errors.QueryCanceled:
        return json.dumps({"error": "Query timeout exceeded"})
    except Exception as e:
        return json.dumps({"error": f"Database error: {str(e)}"})

# Tool 2: Get table schema
@mcp.tool()
def describe_table(table_name: str) -> str:
    """
    Return column names, types, and null constraints for a table.
    Use this to understand available tables before querying.
    """
    try:
        conn = psycopg2.connect(
            host="analytics-db.company.com",
            database="analytics",
            user="llm_reader",
            password="<PASSWORD>",
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))

        columns = cursor.fetchall()
        if not columns:
            return json.dumps({"error": f"Table '{table_name}' not found"})

        schema = [
            {"name": col[0], "type": col[1], "nullable": col[2] == "YES"}
            for col in columns
        ]

        cursor.close()
        conn.close()
        return json.dumps({"table": table_name, "columns": schema})

    except Exception as e:
        return json.dumps({"error": str(e)})

# Resource: List available tables (for context)
@mcp.resource("tables://analytics")
def list_tables() -> str:
    """Return all tables in the analytics database."""
    try:
        conn = psycopg2.connect(
            host="analytics-db.company.com",
            database="analytics",
            user="llm_reader",
            password="<PASSWORD>",
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return "\n".join(tables)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### Step 4: Set Up Environment and Secrets
Create `.env` (never commit to git):
```
POSTGRES_HOST=analytics-db.company.com
POSTGRES_USER=llm_reader
POSTGRES_PASSWORD=secure_password_here
MCP_LOG_LEVEL=INFO
```

Load in your code:
```python
import os
from dotenv import load_dotenv

load_dotenv()
password = os.getenv("POSTGRES_PASSWORD")
```

### Step 5: Test Tools Locally
Run the server:
```bash
python server.py
```

In another terminal, test with the MCP CLI:
```bash
# If FastMCP includes a test CLI, use it
# Otherwise, simulate a tool call by examining logs
```

### Step 6: Configure Transport (Stdio vs HTTP)
**Stdio** (default, secure, local only):
```python
mcp.run(transport="stdio")
```
Use when Claude runs on same machine as the server.

**HTTP** (for remote access, requires authentication):
```python
from fastmcp import FastMCP
from fastapi import FastAPI, Header, HTTPException

mcp = FastMCP("analytics-server")
app = FastAPI()

@app.post("/mcp")
async def mcp_handler(request: dict, x_api_key: str = Header(...)):
    """MCP requests must include x_api_key header."""
    if x_api_key != os.getenv("MCP_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Route to MCP server
    return await mcp.handle_request(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 7: Implement Error Handling
Every tool must handle failures gracefully. Return structured JSON errors:

```python
{
  "success": false,
  "error": "Query timeout exceeded",
  "error_code": "TIMEOUT",
  "retry_after_seconds": 30
}
```

LLM errors to prevent:
- Unvalidated user input → **Fix:** Sanitize all inputs, reject dangerous queries (INSERT, DROP, etc.)
- Missing error context → **Fix:** Return what failed and why (not just "error")
- No timeout protection → **Fix:** Add `timeout_seconds` param and enforce it
- Silent failures → **Fix:** Always return success/failure status

### Step 8: Write Tool Descriptions for LLMs
LLM-friendly descriptions include:
- What it does (function)
- When to use it (trigger)
- Limitations (what it won't do)
- Common mistakes (anti-patterns)

**Bad:**
```
Description: "Get database info"
```

**Good:**
```
Description: "Execute SELECT queries against the production analytics database. Returns up to 1000 rows. Use for reporting and analysis. WARNING: Queries timeout after 60 seconds. Do NOT attempt INSERT/UPDATE/DELETE (will be rejected). Do NOT use UNION or subqueries."
```

### Step 9: Add a Resource for Context
Resources give the LLM background information without needing tool calls:

```python
@mcp.resource("schema://analytics")
def schema_reference() -> str:
    """Available tables and their purposes."""
    return """
    TABLES IN ANALYTICS DATABASE:
    - users: User account data (id, email, created_at, plan_type)
    - events: Event logs (id, user_id, event_type, timestamp)
    - revenue: Payment records (id, user_id, amount, date)
    """
```

### Step 10: Version and Document Your Server
Add a version endpoint:

```python
@mcp.tool()
def get_server_info() -> str:
    """Return server version and available tools."""
    return json.dumps({
        "name": "analytics-server",
        "version": "1.0.0",
        "tools": ["query_postgres_database", "describe_table"],
        "resources": ["tables://analytics"],
        "last_updated": "2025-03-05",
        "maintainer": "your-team@company.com"
    })
```

Create a README:
```markdown
# Analytics MCP Server

Provides LLM access to production analytics database.

## Tools
- `query_postgres_database`: Execute SELECT queries
- `describe_table`: Get table schema

## Security
- Read-only access (SELECT queries only)
- Query timeout: 60 seconds
- Max results: 1000 rows
- Authentication: Required via x-api-key header

## Deployment
python server.py
```

### Step 11: Deploy (Docker + systemd)
**Docker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY server.py .
ENV MCP_LOG_LEVEL=INFO
CMD ["python", "server.py"]
```

Build and run:
```bash
docker build -t mcp-analytics:1.0 .
docker run -e POSTGRES_PASSWORD="***" -p 8000:8000 mcp-analytics:1.0
```

**systemd (for persistent local servers):**
```ini
[Unit]
Description=MCP Analytics Server
After=network.target

[Service]
Type=simple
User=mcp-user
WorkingDirectory=/opt/mcp-analytics
ExecStart=/opt/mcp-analytics/venv/bin/python server.py
Restart=on-failure
RestartSec=10
Environment="MCP_LOG_LEVEL=INFO"

[Install]
WantedBy=multi-user.target
```

### Step 12: Test Integration with Claude
Configure Claude to use your server. In Claude's settings (if using client), point to your server:
```json
{
  "mcp": {
    "servers": {
      "analytics": {
        "command": "python",
        "args": ["/path/to/server.py"]
      }
    }
  }
}
```

Ask Claude: "What were the top 5 events by user count in the last 7 days?" Claude should call your tools automatically.

## Output Template

A complete MCP server includes:
```
server.py
├── Tool definitions (name, description, schema, implementation)
├── Error handling (all edge cases caught)
├── Resource definitions (background context for LLM)
├── Transport config (stdio or HTTP with auth)
├── Logging and monitoring
└── README (usage, security, deployment)

environment setup
├── .env (secrets, never committed)
├── requirements.txt or package.json
├── Dockerfile (optional, for deployment)
└── systemd unit file (optional, for Linux deployment)

tests
├── Unit tests for each tool
├── Integration test (server running, Claude calls a tool)
└── Error scenario tests (timeout, invalid input, DB down)
```

## Quality Gates
- [ ] All tools have clear, LLM-friendly descriptions (>2 sentences, includes limitations)
- [ ] Every tool validates inputs and rejects dangerous queries/commands
- [ ] Error responses include error_code and retry_after_seconds (when applicable)
- [ ] At least one resource is defined to provide LLM context
- [ ] Server runs without errors for 5+ minutes with realistic load
- [ ] Documentation includes security constraints and deployment instructions
- [ ] Claude successfully calls at least one tool without manual intervention

## Examples

### Good Output (excerpt)
```python
@mcp.tool()
def query_postgres_database(query: str, timeout_seconds: int = 30) -> str:
    """Execute SELECT queries on production DB. Max 1000 rows, 60s timeout."""
    if "INSERT" in query.upper() or "DELETE" in query.upper():
        return json.dumps({"success": False, "error": "Mutations not allowed"})

    try:
        # Execute query
        return json.dumps({"success": True, "rows": results})
    except psycopg2.errors.QueryCanceled:
        return json.dumps({"success": False, "error": "Timeout", "retry_after_seconds": 30})
```
✓ Rejects mutations ✓ Handles timeout ✓ Returns structured errors

### Bad Output (what to avoid)
```python
def query_db(query):
    """Query the database."""
    cursor.execute(query)  # ✗ No input validation, SQL injection risk
    return cursor.fetchall()  # ✗ Unbounded results, no error handling
```

## Common Mistakes

1. **Mistake:** Tools with vague descriptions like "Get data" → **Fix:** Include what data, when to use it, and limitations. LLMs need detail to choose the right tool.

2. **Mistake:** No input validation → **Fix:** Validate all inputs. Reject mutations, enforce timeouts, escape dangerous SQL keywords.

3. **Mistake:** Returning raw exceptions → **Fix:** Return `{"success": false, "error": "Human-readable message", "error_code": "TIMEOUT"}`. Raw exceptions confuse LLMs.

4. **Mistake:** Forgetting to handle connection timeouts → **Fix:** Add `connect_timeout` and `statement_timeout` parameters. Network hiccups will break your server.

5. **Mistake:** No resource definitions → **Fix:** Add at least one resource (table list, schema, API docs) so Claude has context without tool calls.

## Anti-Patterns

- Never expose write access (INSERT/UPDATE/DELETE) without strict authentication and logging
- Never return unbounded result sets (always add LIMIT and pagination)
- Never skip transport security (HTTP requires API key authentication)
- Never hardcode secrets in code (use environment variables)
- Never assume tools won't be misused (validate every input)
