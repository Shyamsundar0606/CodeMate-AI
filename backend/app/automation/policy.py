"""Fail-closed proposal policy. No host checkout, patch application or subprocesses."""

import difflib
import hashlib
import re
from pathlib import PurePosixPath

from app.ai.errors import AIError

VALIDATIONS = {
    "python_syntax": ["python", "-m", "compileall", "-q", "."],
    "python_tests": ["python", "-m", "pytest", "-W", "error"],
    "typescript": ["npm", "run", "typecheck"],
    "eslint": ["npm", "run", "lint", "--", "--max-warnings=0"],
}
EXECUTION_MESSAGE = (
    "Patch application and validation are disabled: no verified isolated runner is configured. "
    "Approval records review only; no files are changed and no commands run."
)


def reject(message="Proposal rejected by security policy.", status=422):
    return AIError("AUTOMATION_POLICY", message, status)


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_path(value):
    # Intentionally restrict to unambiguous ASCII repository paths on Windows and Linux.
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_./()-]{1,180}", value):
        raise reject("Only bounded relative ASCII source paths are supported.")
    parts = value.split("/")
    if any(p in {"", ".", ".."} or p.endswith((".", " ")) for p in parts):
        raise reject("Ambiguous or traversing repository path rejected.")
    for part in parts:
        stem = part.split(".")[0].upper()
        if stem in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(10)),
            *(f"LPT{i}" for i in range(10)),
        }:
            raise reject("Windows reserved path rejected.")
        low = part.lower()
        if low.startswith(".env") or low in {
            ".git",
            ".ssh",
            ".aws",
            ".codex",
            ".agents",
            "node_modules",
            "__pycache__",
            ".venv",
        }:
            raise reject("Sensitive or generated repository path rejected.")
        if any(word in low for word in ("secret", "credential", "private_key", "id_rsa")):
            raise reject("Credential-related path rejected.")
    if PurePosixPath(value).suffix.lower() not in {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".mjs",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".md",
        ".txt",
    }:
        raise reject("Unsupported source file type.")
    return value


def text_file(raw):
    if len(raw) > 12000 or b"\0" in raw:
        raise reject("Source file is binary or exceeds 12 KB.")
    try:
        value = raw.decode("utf-8")
    except UnicodeError as exc:
        raise reject("Source file must be UTF-8 text.") from exc
    if "\r" in value.replace("\r\n", ""):
        raise reject("Mixed or legacy carriage-return line endings are unsupported.")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise reject("Source contains unsupported control characters.")
    return value


def patch(files, changes):
    seen, result = set(), []
    for change in changes:
        path = safe_path(change.path)
        if path in seen or path not in files:
            raise reject("Only distinct, explicitly inspected existing files may change.")
        seen.add(path)
        before = files[path]
        if change.before_sha256 != digest(before):
            raise reject("Patch base content hash does not match the pinned source.")
        after = text_file(change.replacement.encode("utf-8"))
        # Preserve an existing CRLF convention rather than silently rewriting the file.
        if "\r\n" in before and "\n" in after and "\r\n" not in after:
            after = after.replace("\n", "\r\n")
        if before == after:
            raise reject("Empty changes rejected.")
        lines = list(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile="a/" + path,
                tofile="b/" + path,
            )
        )
        rendered = "".join(
            line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
            for line in lines
        )
        result.append(
            {
                "path": path,
                "before_sha256": digest(before),
                "after_sha256": digest(after),
                "replacement": after,
                "diff": rendered,
            }
        )
    if len(str(result).encode()) > 64000:
        raise reject("Patch exceeds its storage budget.")
    return result
