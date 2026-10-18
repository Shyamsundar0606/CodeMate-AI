import re

WARNING = (
    "Known secret patterns have been redacted, but detection is not "
    "complete. Review before copying or sharing. Logs are not stored by CodeMate."
)


def redact_logs(
    raw: bytes, truncated: bool, secrets: list[str], *, assignment_values: bool = True
) -> tuple[str, bool, bool]:
    text = raw.decode("utf-8", errors="replace")
    if truncated:
        text = text.rsplit("\n", 1)[0] if "\n" in text else ""
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = re.sub(r"[^\S\n\t ]|[\x00-\x08\x0b-\x1f\x7f\u202a-\u202e\u2066-\u2069]", "", text)
    before = text
    for value in secrets:
        if value:
            text = text.replace(value, "[REDACTED]")
    patterns = [
        r"(?:gh[pousr]_[A-Za-z0-9_]{10,255}|github_pat_[A-Za-z0-9_]{10,255})",
        r"AKIA[A-Z0-9]{16}",
        r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text)
    if assignment_values:
        text = re.sub(
            r"(?i)((?:password|secret|token|api[_-]?key)\s*[=:]\s*)[^\s]+",
            r"\1[REDACTED]",
            text,
        )
    text = re.sub(r"(?i)(authorization:\s*(?:bearer|basic)\s+)[^\s]+", r"\1[REDACTED]", text)
    lines = text.splitlines()
    if len(lines) > 4000:
        text = "\n".join(lines[:4000])
        truncated = True
    return text, truncated, text != before
