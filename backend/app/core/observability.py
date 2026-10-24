"""Process-local, bounded-label telemetry. No request content or identity labels."""

import asyncio
import json
import logging
import re
import time
import uuid
from collections import defaultdict
from contextvars import ContextVar
from datetime import UTC, datetime
from threading import Lock

from starlette.datastructures import Headers
from starlette.responses import JSONResponse

correlation = ContextVar("codemate_correlation", default=None)
BUCKETS = (5, 25, 100, 500, 2000, 10000)


def valid_id(value):
    try:
        parsed = uuid.UUID(value or "")
        return str(parsed) if parsed.version == 4 and str(parsed) == value else None
    except (ValueError, TypeError, AttributeError):
        return None


class SafeJSONFormatter(logging.Formatter):
    def __init__(self, environment, service="codemate-api"):
        super().__init__()
        self.environment = environment
        self.service = service

    def format(self, record):
        result = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "service": self.service,
            "environment": self.environment,
            "event": "application_event",
        }
        try:
            value = json.loads(record.getMessage())
        except (ValueError, TypeError):
            value = {}
            matched = re.fullmatch(
                r"automation_generation_failed code=([A-Z_]{1,80}) status=([0-9]{3})",
                record.getMessage(),
            )
            if matched:
                value = {
                    "event": "automation_generation_failed",
                    "code": matched[1],
                    "status": int(matched[2]),
                }
        # Never serialize exception messages, traceback, arbitrary extras or free-form text.
        for key in ("event", "category", "method", "stage", "code"):
            item = value.get(key) if isinstance(value, dict) else None
            if isinstance(item, str) and re.fullmatch(r"[A-Za-z0-9_/-]{1,80}", item):
                result[key] = item
        for key in ("status", "duration_ms", "attempt"):
            item = value.get(key) if isinstance(value, dict) else None
            if isinstance(item, (int, float)) and 0 <= item < 1e12:
                result[key] = item
        if isinstance(value, dict):
            route = value.get("route")
            if isinstance(route, str) and len(route) <= 160:
                result["route"] = route
            for key in ("request_id", "correlation_id", "investigation_id"):
                if valid_id(value.get(key)):
                    result[key] = value[key]
        result.update(correlation.get() or {})
        return json.dumps(result, allow_nan=False)


def configure_logging(environment, service="codemate-api"):
    parent = logging.getLogger("codemate")
    parent.setLevel(logging.INFO)
    handler = next((h for h in parent.handlers if getattr(h, "codemate_json", False)), None)
    if handler is None:
        handler = logging.StreamHandler()
        handler.codemate_json = True
        parent.addHandler(handler)
    handler.setFormatter(SafeJSONFormatter(environment, service))


class Metrics:
    def __init__(self):
        self.lock = Lock()
        self.rows = {}
        self.events = defaultdict(int)

    def observe(self, route, method, status, elapsed):
        method = (
            method
            if method in {"GET", "POST", "HEAD", "OPTIONS", "PUT", "DELETE", "PATCH"}
            else "OTHER"
        )
        key = (route, method, min(5, max(1, status // 100)))
        with self.lock:
            row = self.rows.setdefault(key, {"count": 0, "duration_ms_sum": 0, "buckets": [0] * 7})
            row["count"] += 1
            row["duration_ms_sum"] += elapsed
            for index, bound in enumerate((*BUCKETS, float("inf"))):
                row["buckets"][index] += int(elapsed <= bound)
            if status in {401, 403}:
                self.events["authorization_denied"] += 1
            if route == "/health/ready" and status == 503:
                self.events["readiness_unavailable"] += 1
            if route.endswith("/confirm") and "/sandbox/" in route and status == 503:
                self.events["sandbox_admission_denied"] += 1

    def snapshot(self):
        with self.lock:
            return {
                "scope": "process",
                "resets_on_restart": True,
                "duration_ms_bucket_upper_bounds": [*BUCKETS, "infinity"],
                "http": [
                    {
                        "route": r,
                        "method": m,
                        "status_class": s,
                        "count": v["count"],
                        "duration_ms_sum": round(v["duration_ms_sum"], 3),
                        "buckets": list(v["buckets"]),
                    }
                    for (r, m, s), v in sorted(self.rows.items())
                ],
                "events": dict(self.events),
            }


class HTTPProtectionMiddleware:
    def __init__(self, app, settings, metrics):
        self.app, self.settings, self.metrics = app, settings, metrics

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        identity = str(uuid.uuid4())
        headers = Headers(scope=scope)
        context = {
            "environment": self.settings.app_env,
            "request_id": identity,
            "correlation_id": valid_id(headers.get("x-correlation-id")) or identity,
        }
        scope.setdefault("state", {}).update(context)
        token = correlation.set(context)
        started, status, sent = time.perf_counter(), 500, False

        async def protected_send(message):
            nonlocal status, sent
            if message["type"] == "http.response.start":
                sent, status = True, message["status"]
                safe = {
                    b"x-request-id": identity.encode(),
                    b"x-correlation-id": context["correlation_id"].encode(),
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"no-referrer",
                    b"permissions-policy": b"camera=(), geolocation=(), microphone=(self)",
                }
                if self.settings.app_env == "production":
                    safe[b"strict-transport-security"] = b"max-age=31536000"
                    safe[b"content-security-policy"] = (
                        b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
                    )
                if scope["path"].startswith("/api/") or scope["path"].startswith("/health"):
                    safe[b"cache-control"] = b"no-store"
                message["headers"] = [
                    (k, v) for k, v in message.get("headers", []) if k.lower() not in safe
                ]
                message["headers"].extend(safe.items())
            await send(message)

        async def reject(code, detail):
            await JSONResponse({"detail": detail, "request_id": identity}, status_code=code)(
                scope, receive, protected_send
            )

        try:
            limit = self.settings.http_max_body_bytes
            if scope["path"] == "/api/v1/auth/voice/transcribe":
                limit = self.settings.voice_max_upload_bytes
            lengths = headers.getlist("content-length")
            if lengths and (
                len(lengths) != 1
                or not lengths[0].isascii()
                or not lengths[0].isdigit()
                or len(lengths[0]) > 12
            ):
                return await reject(400, "Invalid request length")
            if lengths and int(lengths[0]) > limit:
                return await reject(413, "Request body exceeds the allowed size")
            body = bytearray()
            while True:
                remaining = self.settings.http_body_timeout_seconds - (
                    time.perf_counter() - started
                )
                if remaining <= 0:
                    return await reject(408, "Request body upload timed out")
                try:
                    message = await asyncio.wait_for(receive(), timeout=max(0.001, remaining))
                except TimeoutError:
                    return await reject(408, "Request body upload timed out")
                if message["type"] == "http.disconnect":
                    status = 499
                    return
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > limit:
                    return await reject(413, "Request body exceeds the allowed size")
                body.extend(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, bounded_receive, protected_send)
        except Exception:
            logging.getLogger("codemate.errors").error(
                json.dumps({"event": "unexpected_failure", "category": "internal"})
            )
            if not sent:
                await reject(500, "Internal server error")
            else:
                await send({"type": "http.response.body", "body": b"", "more_body": False})
        finally:
            route = getattr(scope.get("route"), "path", "unmatched")
            elapsed = (time.perf_counter() - started) * 1000
            self.metrics.observe(route, scope["method"], status, elapsed)
            logging.getLogger("codemate.requests").info(
                json.dumps(
                    {
                        "event": "http_request",
                        **context,
                        "route": route,
                        "method": scope["method"],
                        "status": status,
                        "duration_ms": round(elapsed, 3),
                    }
                )
            )
            correlation.reset(token)
