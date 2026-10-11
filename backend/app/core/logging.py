import json
import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger("codemate.requests")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Do not trust supplied IDs or log headers, bodies, URL query strings, or tokens.
        request.state.request_id = str(uuid.uuid4())
        started = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith(("/api/v1/github", "/api/v1/auth/github")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
        logger.info(
            json.dumps(
                {
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                }
            )
        )
        return response


class SensitiveURLFilter(logging.Filter):
    """Remove callback and signed-download query values from server/library access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        from urllib.parse import urlsplit, urlunsplit

        if isinstance(record.args, tuple):
            values = []
            for value in record.args:
                text = str(value)
                if "/api/v1/github/callback?" in text:
                    prefix = text.split("/api/v1/github/callback?", 1)[0]
                    suffix = " HTTP/" + text.rsplit(" HTTP/", 1)[1] if " HTTP/" in text else ""
                    value = prefix + "/api/v1/github/callback" + suffix
                elif isinstance(value, str) or type(value).__module__.startswith("httpx"):
                    try:
                        parsed = urlsplit(text)
                    except ValueError:
                        values.append(value)
                        continue
                    if parsed.scheme in {"http", "https"} and parsed.query:
                        value = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
                values.append(value)
            record.args = tuple(values)
        return True


def protect_external_access_logs() -> None:
    for name in ("uvicorn.access", "httpx", "httpx2"):
        target = logging.getLogger(name)
        if not any(isinstance(item, SensitiveURLFilter) for item in target.filters):
            target.addFilter(SensitiveURLFilter())
