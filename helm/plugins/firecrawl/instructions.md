# Firecrawl Plugin — RAPR AI

You have access to the Firecrawl API via the `FIRECRAWL_API_KEY` environment variable.

## Authentication
```python
import os, requests

FC_KEY = os.environ["FIRECRAWL_API_KEY"]
HEADERS = {
    "Authorization": f"Bearer {FC_KEY}",
    "Content-Type": "application/json"
}
BASE = "https://api.firecrawl.dev/v1"
```

## Common Operations

### Scrape a single page
```python
resp = requests.post(f"{BASE}/scrape", headers=HEADERS, json={
    "url": "https://example.com/page",
    "formats": ["markdown", "html"]  # or just ["markdown"]
})
data = resp.json().get("data", {})
markdown_content = data.get("markdown", "")
metadata = data.get("metadata", {})  # title, description, language, etc.
print(f"Title: {metadata.get('title')}")
print(markdown_content[:500])
```

### Scrape with content extraction (LLM Extract)
```python
resp = requests.post(f"{BASE}/scrape", headers=HEADERS, json={
    "url": "https://example.com/products",
    "formats": ["extract"],
    "extract": {
        "schema": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string"},
                "price": {"type": "number"},
                "features": {"type": "array", "items": {"type": "string"}}
            }
        }
    }
})
extracted = resp.json()["data"]["extract"]
```

### Crawl an entire site
```python
# Start crawl job
resp = requests.post(f"{BASE}/crawl", headers=HEADERS, json={
    "url": "https://example.com",
    "limit": 50,              # max pages to crawl
    "maxDepth": 3,            # how deep to follow links
    "formats": ["markdown"]
})
job_id = resp.json()["id"]

# Poll for results
import time
while True:
    status = requests.get(f"{BASE}/crawl/{job_id}", headers=HEADERS).json()
    if status["status"] == "completed":
        pages = status["data"]
        break
    time.sleep(5)

for page in pages:
    print(f"URL: {page['metadata']['url']}")
    print(page["markdown"][:200])
    print("---")
```

### Map a site (discover URLs)
```python
resp = requests.post(f"{BASE}/map", headers=HEADERS, json={
    "url": "https://example.com"
})
urls = resp.json().get("links", [])
print(f"Found {len(urls)} URLs")
```

### Scrape with screenshots
```python
resp = requests.post(f"{BASE}/scrape", headers=HEADERS, json={
    "url": "https://example.com",
    "formats": ["markdown", "screenshot"]
})
screenshot_url = resp.json()["data"].get("screenshot")
```

## Tips
- Use `scrape` for single pages, `crawl` for multi-page sites, `map` to discover URLs first.
- The `extract` format uses AI to pull structured data — define a JSON schema for what you want.
- Crawl jobs are async — always poll until `status == "completed"`.
- `limit` in crawl controls cost. Start small (10-20) and increase if needed.
- Firecrawl handles JavaScript-rendered pages, login walls (with cookies), and anti-bot measures.
- Rate limits depend on plan: Free = 500 credits/month, Hobby = 3,000.
- Each scrape = 1 credit, each crawled page = 1 credit.
