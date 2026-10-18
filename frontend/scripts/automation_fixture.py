"""Disposable browser fixture. Reuses the existing guarded test helper; no personal credentials."""

import base64
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1] / "backend"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))


def main():
    import e2e_backend

    # Only fixture upstream responses change; production code has no fixture switch.
    import github_mock
    from ai_mock import MockOllama

    original = github_mock.MockGitHub.handle
    source = "def add(a, b):\n    return a - b\n"
    sha = hashlib.sha1(f"blob {len(source)}\0".encode() + source.encode()).hexdigest()

    def handle(self, request):
        import httpx

        path = request.url.path
        if path.endswith("/commits/main"):
            value = {"sha": "a" * 40}
        elif "/git/commits/" in path:
            value = {"tree": {"sha": "b" * 40}}
        elif "/git/trees/" in path:
            value = {
                "truncated": False,
                "tree": [
                    {
                        "path": "main.py",
                        "type": "blob",
                        "mode": "100644",
                        "sha": sha,
                        "size": len(source),
                    }
                ],
            }
        elif "/git/blobs/" in path:
            value = {
                "sha": sha,
                "encoding": "base64",
                "content": base64.b64encode(source.encode()).decode(),
            }
        else:
            return original(self, request)
        return httpx.Response(200, json=value)

    original_model = MockOllama.handle

    def model(self, request):
        import httpx

        if request.url.path == "/api/chat":
            body = json.loads(request.content)
            if body.get("format", {}).get("title") == "GeneratedSuggestion":
                from app.automation.policy import digest

                value = {
                    "explanation": "The inspected function subtracts operands.",
                    "expected_improvement": "Addition may resolve the reported mismatch.",
                    "risks": ["Unverified behavior change."],
                    "limitations": ["No tests ran."],
                    "confidence": "MEDIUM",
                    "evidence": [{"evidence_id": "E0001"}],
                    "changes": [
                        {
                            "path": "main.py",
                            "before_sha256": digest(source),
                            "replacement": source.replace("a - b", "a + b"),
                        }
                    ],
                    "validations": ["python_tests"],
                }
                if json.loads(body["messages"][1]["content"])["mode"] == "explain":
                    value["changes"] = []
                return httpx.Response(
                    200, json={"done": True, "message": {"content": json.dumps(value)}}
                )
        return original_model(self, request)

    github_mock.MockGitHub.handle = handle
    MockOllama.handle = model
    e2e_backend.main()


if __name__ == "__main__":
    main()
