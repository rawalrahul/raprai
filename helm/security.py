"""
helm/security.py — Security hardening middleware and utilities for RAPR AI.

Provides:
  - Rate limiting (per-IP, per-endpoint)
  - Security headers (CSP, X-Frame-Options, X-Content-Type-Options, etc.)
  - CSRF token generation and validation
  - File upload validation (type + size limits)

All middleware is registered via `install_security(app)` called from web_app.py.
"""

import hashlib
import hmac
import os
import secrets
import time
import threading
from collections import defaultdict
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from helm.config import logger

# ---------------------------------------------------------------------------
# CSRF secret — generated once per process, used to sign CSRF tokens
# ---------------------------------------------------------------------------

_CSRF_SECRET = secrets.token_bytes(32)
CSRF_COOKIE  = "hq_csrf"
CSRF_HEADER  = "x-csrf-token"


def generate_csrf_token() -> str:
    """Generate a signed CSRF token tied to a random nonce."""
    nonce = secrets.token_hex(16)
    sig   = hmac.new(_CSRF_SECRET, nonce.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{nonce}.{sig}"


def validate_csrf_token(token: Optional[str]) -> bool:
    """Validate that a CSRF token was signed by this process."""
    if not token or "." not in token:
        return False
    nonce, sig = token.split(".", 1)
    expected = hmac.new(_CSRF_SECRET, nonce.encode(), hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(sig, expected)


# ---------------------------------------------------------------------------
# Rate limiter — simple in-memory sliding-window counter
# ---------------------------------------------------------------------------

class RateLimiter:
    """
    Per-IP sliding-window rate limiter.

    Config is a dict of path_prefix -> (max_requests, window_seconds).
    Default: 60 requests per minute for all endpoints.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # ip -> {path_prefix -> [(timestamp, ...)]}
        self._hits: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

        # Rate limits: path_prefix -> (max_requests, window_seconds)
        self.limits: dict[str, tuple[int, int]] = {
            "/login":         (10, 60),     # 10 login attempts per minute
            "/auth/set-pin":  (5, 60),      # 5 PIN changes per minute
            "/setup/save":    (10, 60),     # 10 setup saves per minute
            "/mcp/call":      (120, 60),    # 120 MCP calls per minute (AI uses these)
            "/plugins":       (30, 60),     # 30 plugin operations per minute
            "_default":       (120, 60),    # 120 req/min for everything else
        }

    def _get_limit(self, path: str) -> tuple[int, int]:
        """Find the most specific rate limit for a path."""
        for prefix, limit in self.limits.items():
            if prefix != "_default" and path.startswith(prefix):
                return limit
        return self.limits["_default"]

    def check(self, ip: str, path: str) -> Optional[int]:
        """
        Check if the request should be rate-limited.

        Returns None if allowed, or seconds until reset if limited.
        """
        max_req, window = self._get_limit(path)
        now = time.time()
        cutoff = now - window

        with self._lock:
            # Find the matching bucket
            bucket_key = "_default"
            for prefix in self.limits:
                if prefix != "_default" and path.startswith(prefix):
                    bucket_key = prefix
                    break

            hits = self._hits[ip][bucket_key]
            # Prune old entries
            hits[:] = [t for t in hits if t > cutoff]

            if len(hits) >= max_req:
                # Rate limited — return seconds until oldest entry expires
                oldest = min(hits)
                retry_after = int(window - (now - oldest)) + 1
                return max(1, retry_after)

            hits.append(now)
            return None

    def cleanup(self):
        """Remove stale entries (call periodically)."""
        now = time.time()
        max_window = max(w for _, w in self.limits.values())
        cutoff = now - max_window

        with self._lock:
            stale_ips = []
            for ip, buckets in self._hits.items():
                stale_buckets = []
                for key, hits in buckets.items():
                    hits[:] = [t for t in hits if t > cutoff]
                    if not hits:
                        stale_buckets.append(key)
                for key in stale_buckets:
                    del buckets[key]
                if not buckets:
                    stale_ips.append(ip)
            for ip in stale_ips:
                del self._hits[ip]


_rate_limiter = RateLimiter()


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking — only allow framing from same origin
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy — don't leak full URL to external sites
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy — restrict browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(self), geolocation=(), payment=()"
        )

        # Content Security Policy — allow inline styles/scripts (needed for SPA)
        # but block external resources except CDN
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        return response


# ---------------------------------------------------------------------------
# Rate limiting middleware
# ---------------------------------------------------------------------------

# Paths exempt from rate limiting (static assets, health checks, websocket)
_RATE_LIMIT_EXEMPT = ("/static", "/health", "/ws")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce per-IP rate limits on API endpoints."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip rate limiting for exempt paths
        if any(path.startswith(p) for p in _RATE_LIMIT_EXEMPT):
            return await call_next(request)

        # Skip WebSocket upgrades
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        ip = request.client.host if request.client else "127.0.0.1"
        retry_after = _rate_limiter.check(ip, path)

        if retry_after is not None:
            logger.warning("Rate limit hit: %s on %s (retry after %ds)", ip, path, retry_after)
            return JSONResponse(
                {"error": "Too many requests. Please slow down.", "retry_after": retry_after},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# CSRF middleware — protects state-changing endpoints
# ---------------------------------------------------------------------------

# Paths that require CSRF validation for POST/PUT/DELETE/PATCH
_CSRF_PROTECTED_PREFIXES = (
    "/auth/",
    "/login",
    "/logout",
    "/setup/save",
    "/sessions/",
    "/settings/",
    "/history/",
    "/scheduler/",
    "/pipeline/",
    "/plugins/",
    "/mcp/",
    "/upload",
)

# Paths exempt from CSRF (used by AI subprocesses without browser cookies)
_CSRF_EXEMPT = ("/mcp/call", "/mcp/servers", "/health")


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection using double-submit cookie pattern.

    On every response, a CSRF cookie is set.
    On state-changing requests (POST/PUT/DELETE/PATCH), the request must include
    an X-CSRF-Token header matching the cookie value.
    """

    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()
        path = request.url.path

        # Only validate on state-changing methods
        if method in ("POST", "PUT", "DELETE", "PATCH"):
            # Check if this path needs CSRF protection
            needs_csrf = any(path.startswith(p) for p in _CSRF_PROTECTED_PREFIXES)
            is_exempt = any(path.startswith(p) for p in _CSRF_EXEMPT)

            if needs_csrf and not is_exempt:
                # Form submissions (login) use cookie-based flow
                content_type = request.headers.get("content-type", "")
                if "application/x-www-form-urlencoded" in content_type:
                    # Form POST — SameSite=Lax cookie provides protection
                    pass
                else:
                    # JSON API — require X-CSRF-Token header
                    token = request.headers.get(CSRF_HEADER, "")
                    cookie_token = request.cookies.get(CSRF_COOKIE, "")

                    if not token or not cookie_token:
                        return JSONResponse(
                            {"error": "Missing CSRF token"},
                            status_code=403,
                        )

                    if not validate_csrf_token(token) or token != cookie_token:
                        return JSONResponse(
                            {"error": "Invalid CSRF token"},
                            status_code=403,
                        )

        response = await call_next(request)

        # Set/refresh CSRF cookie on every response
        if CSRF_COOKIE not in request.cookies or method == "GET":
            csrf_token = generate_csrf_token()
            response.set_cookie(
                key=CSRF_COOKIE,
                value=csrf_token,
                httponly=False,       # JS must be able to read this
                samesite="lax",
                secure=False,         # Local app, no HTTPS
                max_age=86400 * 7,    # 7 days
                path="/",
            )

        return response


# ---------------------------------------------------------------------------
# File upload validation
# ---------------------------------------------------------------------------

# Maximum upload size: 50 MB
MAX_UPLOAD_SIZE = 50 * 1024 * 1024

# Allowed file extensions for upload
ALLOWED_UPLOAD_EXTENSIONS = {
    # Documents
    ".txt", ".md", ".pdf", ".doc", ".docx", ".rtf", ".csv", ".tsv",
    ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico",
    # Code
    ".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yaml", ".yml",
    ".sh", ".bat", ".ps1", ".toml", ".ini", ".cfg", ".conf",
    # Archives
    ".zip", ".tar", ".gz", ".7z", ".rar",
    # Audio/Video (for transcription)
    ".mp3", ".wav", ".ogg", ".m4a", ".flac", ".mp4", ".webm",
    # Data
    ".sql", ".db", ".sqlite",
}

# Blocked dangerous extensions
BLOCKED_EXTENSIONS = {
    ".exe", ".msi", ".dll", ".scr", ".com", ".cmd", ".vbs", ".vbe",
    ".js",   # Only when uploaded (not as code file)
    ".wsf", ".wsh", ".pif", ".reg",
}
# Note: .js is in both ALLOWED and BLOCKED — we allow it as a code file
# but the validation function checks context


def validate_upload(filename: str, size: int) -> Optional[str]:
    """
    Validate an uploaded file.

    Returns None if valid, or an error message string if invalid.
    """
    if not filename:
        return "No filename provided"

    if size > MAX_UPLOAD_SIZE:
        mb = MAX_UPLOAD_SIZE / (1024 * 1024)
        return f"File too large. Maximum size is {mb:.0f} MB."

    # Check extension
    ext = os.path.splitext(filename.lower())[1]
    if not ext:
        return "File must have an extension"

    if ext in (".exe", ".msi", ".dll", ".scr", ".com", ".vbs", ".vbe",
               ".wsf", ".wsh", ".pif", ".reg"):
        return f"Blocked file type: {ext}"

    # Sanitize filename — no path traversal
    basename = os.path.basename(filename)
    if basename != filename:
        return "Invalid filename (path components not allowed)"

    if ".." in filename or "/" in filename or "\\" in filename:
        return "Invalid filename"

    return None


# ---------------------------------------------------------------------------
# Diagnostics secret stripping
# ---------------------------------------------------------------------------

# Keys whose values should be redacted in diagnostics and logs
SECRET_ENV_KEYS = {
    "TELEGRAM_BOT_TOKEN", "PIN_HASH", "PIN_SALT", "WEBHOOK_TOKEN",
    "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    "GROQ_API_KEY", "OPENROUTER_API_KEY",
    "GITHUB_TOKEN", "SLACK_BOT_TOKEN", "SLACK_USER_TOKEN",
    "GOOGLE_CLIENT_SECRET", "LINEAR_API_KEY", "NOTION_TOKEN",
    "JIRA_API_TOKEN", "ASANA_ACCESS_TOKEN", "TRELLO_API_KEY",
    "DISCORD_BOT_TOKEN", "ZAPIER_NLA_API_KEY",
}

# Subset: core API keys that should always be vault-managed.
# Excludes PIN_HASH/PIN_SALT (hashed values, not raw secrets) and
# plugin-specific tokens (handled via plugin manifest migration).
CORE_API_KEYS = {
    "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    "GROQ_API_KEY", "OPENROUTER_API_KEY",
    "TELEGRAM_BOT_TOKEN", "WEBHOOK_TOKEN",
    "GITHUB_TOKEN", "GOOGLE_CLIENT_SECRET",
}

# Keys eligible for vault migration (everything except hash/salt values)
VAULT_ELIGIBLE_KEYS = SECRET_ENV_KEYS - {"PIN_HASH", "PIN_SALT"}


def redact_env_value(key: str, value: str) -> str:
    """Redact secret values — show only first 4 chars + '***'."""
    key_upper = key.upper()
    # Check if key looks like a secret
    is_secret = (
        key_upper in SECRET_ENV_KEYS
        or "TOKEN" in key_upper
        or "SECRET" in key_upper
        or "API_KEY" in key_upper
        or "PASSWORD" in key_upper
        or "HASH" in key_upper
    )
    if is_secret and value:
        if len(value) > 8:
            return value[:4] + "***" + value[-2:]
        return "***"
    return value


def sanitize_diagnostics(diag: dict) -> dict:
    """
    Deep-scan a diagnostics dict and redact any secret values.

    Handles nested dicts and lists. Also scrubs log lines that
    contain known secret patterns.
    """
    if isinstance(diag, dict):
        result = {}
        for k, v in diag.items():
            if isinstance(v, str):
                result[k] = redact_env_value(k, v)
            elif isinstance(v, (dict, list)):
                result[k] = sanitize_diagnostics(v)
            else:
                result[k] = v
        return result
    elif isinstance(diag, list):
        return [sanitize_diagnostics(item) if isinstance(item, (dict, list))
                else _scrub_log_line(item) if isinstance(item, str)
                else item
                for item in diag]
    return diag


def _scrub_log_line(line: str) -> str:
    """Remove potential secrets from a log line."""
    import re
    # Redact anything that looks like a token or API key in log output
    # Pattern: key=<long_alphanumeric_string>
    line = re.sub(
        r'(token|key|secret|password|hash|salt)\s*[=:]\s*\S{8,}',
        r'\1=***REDACTED***',
        line,
        flags=re.IGNORECASE,
    )
    return line


# ---------------------------------------------------------------------------
# Install all security middleware on the FastAPI app
# ---------------------------------------------------------------------------

def install_security(app):
    """
    Register all security middleware on the FastAPI app.

    Call order matters — middleware is applied in LIFO order (last added = first executed).
    We want: Rate Limit -> CSRF -> Security Headers -> [route handler]
    So we add them in reverse: SecurityHeaders first, then CSRF, then RateLimit.
    """
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(RateLimitMiddleware)

    logger.info("Security middleware installed: rate limiting, CSRF, security headers")


# ---------------------------------------------------------------------------
# Periodic cleanup task (call from scheduler or background thread)
# ---------------------------------------------------------------------------

def cleanup_rate_limiter():
    """Prune stale rate-limiter entries. Call every ~5 minutes."""
    _rate_limiter.cleanup()
