"""Explicit opt-in real Ollama/API verification against only the guarded test DB.

Run with CODEMATE_REAL_OLLAMA_DOCSTRING_TEST=1 and pass this file explicitly.
This filename is intentionally outside ordinary pytest test_*.py discovery.
"""

import ast
import hashlib
import os
import subprocess
import time
import uuid
from unittest.mock import Mock

import pytest
import test_automation as fixtures
from test_ai import ai as ai
from test_automation import automation as automation

from app.integrations.ollama.client import OllamaClient
from app.services.github_repository_service import GitHubRepositoryService


@pytest.mark.skipif(
    os.environ.get("CODEMATE_REAL_OLLAMA_DOCSTRING_TEST") != "1",
    reason="Requires explicit opt-in and an existing local Ollama model.",
)
def test_real_docstring_api_persistence_review_and_preview(automation, monkeypatch):
    client, _ = automation
    source = subprocess.check_output(["git", "show", "HEAD:backend/app/main.py"], cwd="..").decode(
        "utf-8"
    )
    monkeypatch.setattr(fixtures, "SOURCE", source)
    monkeypatch.setattr(
        fixtures,
        "BLOB",
        hashlib.sha1(f"blob {len(source.encode())}\0".encode() + source.encode()).hexdigest(),
    )
    original_json = GitHubRepositoryService._json

    def pinned_source(self, path, params=None):
        value, headers = original_json(self, path, params)
        if "/git/trees/" in path:
            value["tree"][0]["path"] = "backend/app/main.py"
            value["tree"].extend(
                [
                    {"path": "backend", "type": "tree", "mode": "040000"},
                    {"path": "backend/app", "type": "tree", "mode": "040000"},
                ]
            )
        return value, headers

    monkeypatch.setattr(GitHubRepositoryService, "_json", pinned_source)
    real = OllamaClient(client.app.state.settings)
    calls = Mock(wraps=real.request)
    monkeypatch.setattr(real, "request", calls)
    monkeypatch.setattr(client.app.state, "ollama_client", real)
    started = time.monotonic()
    try:
        response = fixtures.create(client, paths=["backend/app/main.py"])
        assert response.status_code == 201
        row = response.json()
        body = {
            "request_id": str(uuid.uuid4()),
            "mode": "patch",
            "request": "Add a short docstring to create_app describing its purpose. "
            "Preserve every import and all existing behavior. Make no other changes.",
        }
        path = fixtures.BASE + "/" + row["id"] + "/proposals"
        response = client.post(path, json=body)
        assert response.status_code == 200, response.json().get("detail", {}).get("code")
        row = response.json()
        proposal = row["proposals"][0]
        assert proposal["files"] == ["backend/app/main.py"]
        changed = proposal["suggestion"]["changes"][0]["replacement"]
        tree = ast.parse(changed)
        function = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "create_app"
        )
        raw_docstring = ast.get_docstring(function, clean=False)
        assert raw_docstring
        whitespace_sensitive = ast.get_docstring(function) != raw_docstring
        function.body.pop(0)
        assert ast.dump(ast.parse(source)) == ast.dump(tree)
        assert client.get(fixtures.READ + "/" + row["id"]).json()["proposals"][0] == proposal
        assert client.post(path, json=body).json()["proposals"][0] == proposal
        assert calls.call_count == 1
        assert (
            client.post(
                fixtures.url(row), json={**fixtures.decision(row), "validations": []}
            ).status_code
            == 200
        )
        preview = client.post(
            "/api/v1/auth/sandbox/executions",
            json={
                "request_id": str(uuid.uuid4()),
                "session_id": row["id"],
                "proposal_id": proposal["id"],
                "profiles": ["python_syntax"],
            },
        )
        assert preview.status_code == 201
        result = preview.json()
        assert result["preview"]["diff"] == proposal["diff"]
        assert result["preview"]["patch_hash"] == proposal["patch_hash"]
        assert result["applied"] is False and result["execution_enabled"] is False
        assert client.get("/api/v1/sandbox/executions/" + result["id"]).json() == result
        print(
            {
                "real_local_ollama": True,
                "github": "controlled pinned-source fixture",
                "guarded_test_database": True,
                "authenticated_api": True,
                "reload_and_idempotency": True,
                "model_calls": calls.call_count,
                "review_and_preview": True,
                "docstring_only_ast": True,
                "whitespace_sensitive_docstring": whitespace_sensitive,
                "applied": False,
                "seconds": round(time.monotonic() - started, 2),
            }
        )
    finally:
        real.close()
