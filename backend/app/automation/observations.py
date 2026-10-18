"""Source-derived observations. Parsing never imports or executes repository code."""

import ast
import re


def identifier(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = identifier(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def observations_for(path, content, scoped):
    facts = []
    lines = content.splitlines(keepends=True)
    if path.endswith(".py"):
        tree = ast.parse(content)
        for node in ast.walk(tree):
            description, priority = "", 9
            first = getattr(node, "lineno", 0)
            last = getattr(node, "end_lineno", first)
            if isinstance(node, ast.ClassDef):
                bases = [identifier(base) for base in node.bases if identifier(base)]
                description = f"Defines class {node.name}"
                if bases:
                    description += " inheriting " + ", ".join(bases)
                priority = 0
                last = max(first, node.body[0].lineno - 1)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                description, priority = f"Defines function {node.name}", 1
                last = max(first, node.body[0].lineno - 1)
            elif isinstance(node, ast.Call) and identifier(node.func):
                description, priority = f"Calls {identifier(node.func)}", 3
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [identifier(target) for target in targets if identifier(target)]
                if names and isinstance(node.value, ast.Call) and identifier(node.value.func):
                    description = f"Assigns {', '.join(names)} using {identifier(node.value.func)}"
                    priority = 2
            elif isinstance(node, ast.ImportFrom) and node.module:
                description, priority = f"Imports from {node.module}", 4
            if description and len(description) <= 140:
                required = "".join(lines[first - 1 : last]).rstrip("\r\n")
                facts.append((priority, first, last, description + ".", required))
    result = {}
    for identity, entry in scoped.items():
        supported = [
            fact
            for fact in sorted(facts)
            if entry["line_start"] <= fact[1] <= fact[2] <= entry["line_end"]
            and fact[4] in entry["quote"]
        ]
        if supported:
            description = supported[0][3]
            for fact in supported[1:]:
                if fact[3] not in description and len(description) + len(fact[3]) < 140:
                    description += " " + fact[3]
            result[identity] = description
        else:
            # An exact extractive fallback describes no behavior beyond visible text.
            result[identity] = "Source excerpt begins: " + entry["quote"][:120]
    return result


def relevant_observations(path, request, observations):
    """Prefer facts naming the user's subject, without changing any evidence identity."""
    sentences = re.split(r"(?<=[.!?])\s+", request)
    query = " ".join(sentence for sentence in sentences if path in sentence) or request
    query = query.replace(path, " ")
    terms = set(re.findall(r"[a-z][a-z0-9_]{2,}", query.lower())) - {
        "explain",
        "how",
        "the",
        "this",
        "that",
        "then",
        "using",
        "from",
        "with",
        "and",
        "are",
        "what",
        "does",
        "file",
        "files",
        "source",
        "code",
        "cite",
        "evidence",
        "each",
        "separately",
        "missing",
        "say",
    }
    matches = {
        identity: observation
        for identity, observation in observations.items()
        if not observation.startswith("Source excerpt begins:")
        and terms.intersection(re.findall(r"[a-z][a-z0-9_]*", observation.lower()))
    }
    return matches or observations
