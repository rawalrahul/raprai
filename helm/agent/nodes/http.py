"""HTTP request node executor."""

import json


async def execute_http_node(node: dict, context: str) -> str:
    """Make an HTTP request and return status plus response body."""
    url = node.get("http_url", "").strip()
    if not url:
        return "Error: http node requires http_url"

    try:
        import aiohttp
    except ImportError:
        return "Error: aiohttp not installed - run: pip install aiohttp"

    method = node.get("http_method", "GET").upper()
    headers = node.get("http_headers") or {}
    body = node.get("http_body", "") or ""
    timeout_sec = node.get("timeout", 30)

    url = url.replace("{{context}}", context.strip())
    body = body.replace("{{context}}", context.strip())

    try:
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            kwargs = {"headers": headers}
            if body:
                kwargs["data"] = body
            async with session.request(method, url, **kwargs) as resp:
                text = await resp.text()
                try:
                    parsed = json.loads(text)
                    text = json.dumps(parsed, indent=2, ensure_ascii=False)
                except Exception:
                    pass
                return f"HTTP {resp.status}\n\n{text}"
    except Exception as exc:
        return f"Error: HTTP request failed - {exc}"
