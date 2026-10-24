import logging


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
