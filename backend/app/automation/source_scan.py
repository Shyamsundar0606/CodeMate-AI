"""Python value-aware inspection. Never evaluate code or return matched content."""

import ast
import io
import re
import tokenize

from app.integrations.github.logs import redact_logs

SENSITIVE = re.compile(
    r"(?:password|passwd|secret|token|api_?key|secret_key|private_key|database_url)$", re.I
)
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]")


def name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return name(node.value) + "." + node.attr
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        return str(node.slice.value)
    return ""


def embedded_value(node):
    """Literal defaults count as values; references and annotations alone do not."""
    if node is None:
        return False
    if isinstance(node, ast.Constant):
        return node.value not in (None, "", b"", Ellipsis)
    if isinstance(node, ast.Subscript):
        return embedded_value(node.value)
    if isinstance(node, ast.Lambda):
        return embedded_value(node.body)
    if isinstance(node, ast.Call):
        called = name(node.func)
        if called in {"secrets.token_urlsafe", "secrets.token_hex", "secrets.token_bytes"}:
            return any(
                not isinstance(a, ast.Constant) or not isinstance(a.value, int) for a in node.args
            ) or bool(node.keywords)
        if called in {"Field", "pydantic.Field"}:
            return any(
                embedded_value(k.value)
                for k in node.keywords
                if k.arg in {"default", "default_factory"}
            ) or any(embedded_value(a) for a in node.args)
        if called in {"os.getenv", "os.environ.get", "getenv", "environ.get"}:
            # Only the environment-variable name is syntax, never a supplied fallback.
            return any(embedded_value(a) for a in node.args[1:]) or any(
                embedded_value(k.value) for k in node.keywords if k.arg in {"default", "fallback"}
            )
    return any(embedded_value(child) for child in ast.iter_child_nodes(node))


def python_reason(value, secrets):
    normalized = value.replace("\r\n", "\n")
    if CONTROL.search(normalized) or "\r" in normalized or "\x1b" in normalized:
        return "unsafe control characters"
    # Exact configured values, recognizable tokens/keys/JWTs, PEMs and Authorization
    # headers are always scanned, independent of source syntax or field names.
    clean, _, changed = redact_logs(
        normalized.encode("utf-8"), False, secrets, assignment_values=False
    )
    if changed or clean != normalized:
        return "credential pattern or unsafe text"
    try:
        tree = ast.parse(value)
    except (SyntaxError, ValueError, RecursionError):
        return "unsupported or invalid Python syntax"
    for node in ast.walk(tree):
        pairs = []
        if isinstance(node, ast.AnnAssign):
            pairs = [(name(node.target), node.value)]
        elif isinstance(node, ast.Assign):
            pairs = [(name(target), node.value) for target in node.targets]
        elif isinstance(node, (ast.NamedExpr, ast.AugAssign)):
            pairs = [(name(node.target), node.value)]
        elif isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            pairs = [
                (name(left), right) for left, right in zip(operands, operands[1:], strict=False)
            ]
            pairs += [
                (name(right), left) for left, right in zip(operands, operands[1:], strict=False)
            ]
        elif isinstance(node, ast.keyword):
            pairs = [(node.arg or "", node.value)]
        elif isinstance(node, ast.Dict):
            pairs = [
                (key.value, value)
                for key, value in zip(node.keys, node.values, strict=True)
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            ]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = node.args
            positional = args.posonlyargs + args.args
            pairs = [
                (arg.arg, default)
                for arg, default in zip(
                    positional[-len(args.defaults) :], args.defaults, strict=False
                )
            ]
            pairs += [
                (arg.arg, default)
                for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True)
            ]
        if any(SENSITIVE.search(key) and embedded_value(default) for key, default in pairs):
            return "embedded credential value"
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Strings can themselves contain env-style credentials or log fragments.
            try:
                raw_literal = node.value.encode("utf-8")
            except UnicodeError:
                return "unsupported Unicode in a string literal"
            literal, _, modified = redact_logs(raw_literal, False, secrets)
            if modified or literal != node.value:
                return "credential pattern in a string literal"
    # Comments can contain real assignments too; preserve the conservative log rule.
    try:
        for token in tokenize.generate_tokens(io.StringIO(value).readline):
            if token.type == tokenize.COMMENT:
                clean, _, changed = redact_logs(token.string.encode("utf-8"), False, secrets)
                if changed or clean != token.string:
                    return "credential pattern in a comment"
    except (tokenize.TokenError, IndentationError):
        return "unsupported or invalid Python syntax"
    return None
