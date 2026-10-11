import hashlib
import json
import re
import threading
import time
from urllib.parse import urlsplit

import httpx

from app.core.config import Settings
from app.integrations.github.exceptions import GitHubError, malformed
from app.integrations.github.rate_limit import RateLimitGuard

API = "https://api.github.com"
OAUTH = "https://github.com/login/oauth/access_token"
VERSION = "2026-03-10"
JSON_LIMIT = 2 * 1024 * 1024
LOG_LIMIT = 256 * 1024


class StatelessHTTPClient(httpx.Client):
    def build_request(self, *args, **kwargs) -> httpx.Request:
        request = super().build_request(*args, **kwargs)
        request.headers.pop("cookie", None)
        return request


class GitHubClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self.http = StatelessHTTPClient(
            transport=transport,
            timeout=httpx.Timeout(5, connect=3, pool=3),
            follow_redirects=False,
            trust_env=False,
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=8),
        )
        self.rate = RateLimitGuard()
        self.slots = threading.BoundedSemaphore(8)

    def close(self) -> None:
        self.http.close()

    def _request(
        self,
        method: str,
        url: str,
        *,
        token: str | None = None,
        params: dict | None = None,
        body: dict | None = None,
        basic: bool = False,
        log_download: bool = False,
    ) -> tuple[int, httpx.Headers, bytes, bool]:
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError as exc:
            raise GitHubError("GITHUB_UNSAFE_REDIRECT", "Invalid GitHub destination.", 502) from exc
        if log_download:
            valid = (
                parsed.scheme == "https"
                and parsed.hostname is not None
                and (
                    parsed.hostname == "pipelines.actions.githubusercontent.com"
                    or re.fullmatch(
                        r"productionresultssa[0-9]+\.blob\.core\.windows\.net", parsed.hostname
                    )
                )
                and port in {None, 443}
                and not parsed.username
                and not parsed.password
                and not parsed.fragment
            )
            if not valid:
                raise GitHubError(
                    "GITHUB_UNSAFE_REDIRECT",
                    (
                        "GitHub supplied an unsupported log "
                        "destination. Open the log on GitHub instead."
                    ),
                    502,
                )
        elif not ((parsed.scheme, parsed.netloc) == ("https", "api.github.com") or url == OAUTH):
            raise GitHubError(
                "GITHUB_UNSAFE_DESTINATION", "GitHub request destination rejected.", 502
            )
        headers = {
            "Accept": "text/plain" if log_download else "application/vnd.github+json",
            "User-Agent": "CodeMate-AI",
            "Accept-Encoding": "identity",
        }
        if not log_download:
            headers["X-GitHub-Api-Version"] = VERSION
            if token:
                headers["Authorization"] = f"Bearer {token}"
        # Signed log URLs have a fresh request with neither Authorization nor cookie credentials.
        auth = (
            httpx.BasicAuth(
                self.settings.github_client_id,
                self.settings.github_client_secret.get_secret_value(),
            )
            if basic
            else None
        )
        limit = LOG_LIMIT if log_download else JSON_LIMIT
        if not self.slots.acquire(timeout=2):
            raise GitHubError("GITHUB_BUSY", "GitHub requests are busy. Try again shortly.", 503)
        try:
            started = time.monotonic()
            with self.http.stream(
                method, url, headers=headers, auth=auth, params=params, json=body
            ) as response:
                if response.headers.get("content-encoding", "identity").lower() not in {
                    "identity",
                    "",
                }:
                    raise GitHubError(
                        "GITHUB_UNSUPPORTED_ENCODING",
                        "GitHub returned an unsupported compressed response.",
                        502,
                    )
                raw = bytearray()
                truncated = False
                for chunk in response.iter_bytes(chunk_size=8192):
                    if time.monotonic() - started > 12:
                        raise GitHubError(
                            "GITHUB_TIMEOUT", "GitHub request timed out. Try again.", 504
                        )
                    if len(raw) + len(chunk) > limit:
                        if not log_download:
                            raise GitHubError(
                                "GITHUB_RESPONSE_TOO_LARGE",
                                "GitHub response exceeded the safe limit. Use a smaller page.",
                                502,
                            )
                        raw.extend(chunk[: limit - len(raw)])
                        truncated = True
                        break
                    raw.extend(chunk)
                return response.status_code, response.headers, bytes(raw), truncated
        except httpx.TimeoutException as exc:
            raise GitHubError(
                "GITHUB_TIMEOUT", "GitHub request timed out. Try again.", 504
            ) from exc
        except httpx.HTTPError as exc:
            raise GitHubError(
                "GITHUB_UNAVAILABLE", "Cannot reach GitHub. Try again later.", 502
            ) from exc
        finally:
            self.slots.release()

    def _check(self, status: int, headers: httpx.Headers, raw: bytes, key: str) -> None:
        if status in {200, 204, 302}:
            return
        message = ""
        try:
            message = str(json.loads(raw).get("message", "")).lower()
        except (ValueError, AttributeError):
            pass
        if status == 429 or (
            status == 403
            and (
                headers.get("x-ratelimit-remaining") == "0"
                or "rate limit" in message
                or "retry-after" in headers
            )
        ):

            def number(value: str | None) -> int | None:
                try:
                    return int(value) if value else None
                except ValueError:
                    return None

            reset = number(headers.get("x-ratelimit-reset"))
            wait = number(headers.get("retry-after"))
            seconds = min(
                86400,
                max(1, wait if wait is not None else (reset - int(time.time()) if reset else 60)),
            )
            self.rate.record(key, seconds, reset)
            raise GitHubError(
                "GITHUB_RATE_LIMITED",
                "GitHub primary or secondary rate limit reached. Wait before refreshing.",
                429,
                retry_after=seconds,
                reset_at=reset,
            )
        if status == 401:
            raise GitHubError(
                "GITHUB_REAUTHORIZATION_REQUIRED",
                "GitHub authorization expired or was revoked. Reconnect your account.",
            )
        if status == 403:
            raise GitHubError(
                "GITHUB_PERMISSION_REQUIRED",
                (
                    "GitHub denied access. Check the App's read "
                    "permissions, repository selection and organization approval."
                ),
            )
        if status in {404, 410}:
            raise GitHubError(
                "GITHUB_RESOURCE_UNAVAILABLE",
                "This resource is missing, not authorized, or no longer available.",
                404,
            )
        if status >= 500:
            raise GitHubError(
                "GITHUB_UNAVAILABLE", "GitHub is temporarily unavailable. Try again later.", 502
            )
        raise GitHubError("GITHUB_REQUEST_REJECTED", "GitHub could not complete this request.", 502)

    def json(
        self, path: str, token: str, params: dict | None = None
    ) -> tuple[object, httpx.Headers]:
        # Callers supply validated fixed endpoint paths, never complete upstream URLs.
        if not path.startswith("/") or ".." in path.split("/") or "?" in path or "#" in path:
            raise malformed()
        key = hashlib.sha256(token.encode()).hexdigest()
        self.rate.check(key)
        for attempt in range(2):
            status, headers, raw, _ = self._request("GET", API + path, token=token, params=params)
            if status >= 500 and attempt == 0 and "retry-after" not in headers:
                continue  # One retry for an idempotent read only.
            self._check(status, headers, raw, key)
            try:
                return json.loads(raw), headers
            except ValueError as exc:
                raise malformed() from exc
        raise malformed()

    def exchange(self, values: dict) -> dict:
        if not self.settings.github_configured:
            raise GitHubError("GITHUB_NOT_CONFIGURED", "GitHub integration is not configured.", 503)
        payload = {
            "client_id": self.settings.github_client_id,
            "client_secret": self.settings.github_client_secret.get_secret_value(),
            **values,
        }
        status, headers, raw, _ = self._request("POST", OAUTH, body=payload)
        self._check(status, headers, raw, "oauth:" + self.settings.github_client_id)
        try:
            value = json.loads(raw)
            if not isinstance(value, dict) or value.get("error"):
                raise ValueError("Token exchange rejected")
            if (
                not isinstance(value.get("token_type"), str)
                or value["token_type"].lower() != "bearer"
                or not re.fullmatch(r"ghu_[A-Za-z0-9_]{20,255}", value.get("access_token", ""))
            ):
                raise ValueError("Invalid user access token")
            refresh = value.get("refresh_token")
            if refresh is not None and not re.fullmatch(r"ghr_[A-Za-z0-9_]{20,255}", refresh):
                raise ValueError("Invalid refresh token")
            for field in ("expires_in", "refresh_token_expires_in"):
                if value.get(field) is not None and (
                    not isinstance(value[field], int)
                    or isinstance(value[field], bool)
                    or not 1 <= value[field] <= 20000000
                ):
                    raise ValueError("Invalid token expiry")
            return value
        except (ValueError, TypeError) as exc:
            raise GitHubError(
                "GITHUB_AUTHORIZATION_FAILED",
                "GitHub authorization could not be completed. Start again.",
            ) from exc

    def revoke(self, token: str) -> bool:
        status, headers, raw, _ = self._request(
            "DELETE",
            API + f"/applications/{self.settings.github_client_id}/grant",
            body={"access_token": token},
            basic=True,
        )
        if status == 204:
            return True
        self._check(status, headers, raw, "oauth:" + self.settings.github_client_id)
        return False

    def logs(self, path: str, token: str) -> tuple[bytes, bool]:
        key = hashlib.sha256(token.encode()).hexdigest()
        self.rate.check(key)
        status, headers, raw, _ = self._request("GET", API + path, token=token)
        self._check(status, headers, raw, key)
        if status != 302 or not headers.get("location"):
            raise GitHubError(
                "GITHUB_LOGS_UNAVAILABLE", "Job logs are unavailable, expired or deleted.", 404
            )
        status, headers, raw, truncated = self._request(
            "GET", headers["location"], log_download=True
        )
        # Further redirects are rejected, never automatically followed.
        if status != 200:
            raise GitHubError(
                "GITHUB_LOGS_UNAVAILABLE", "Job logs are unavailable, expired or deleted.", 404
            )
        return raw, truncated

    @staticmethod
    def has_next(headers: httpx.Headers, path: str) -> bool:
        for entry in headers.get("link", "").split(","):
            match = re.match(r'\s*<([^>]+)>;\s*rel="next"', entry)
            if match:
                parsed = urlsplit(match[1])
                if (
                    parsed.scheme != "https"
                    or parsed.netloc != "api.github.com"
                    or parsed.path != path
                    or parsed.username
                    or parsed.fragment
                ):
                    raise GitHubError(
                        "GITHUB_UNSAFE_PAGINATION", "GitHub pagination link was rejected.", 502
                    )
                return True  # The next URL is never fetched; we construct the next bounded page.
        return False
