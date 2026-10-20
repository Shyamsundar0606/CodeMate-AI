"""Large-file anchored generation persists the ordinary review/preview contract."""

import hashlib
import json

import pytest
import test_automation as fixtures
from test_ai import ai as ai
from test_automation import automation as automation


def test_large_file_edits_persist_review_and_prepare_without_execution(automation, monkeypatch):
    client, model = automation
    source = "# retained context\n" * 240 + "def add(a, b):\n    return a - b\n"
    original = "def add(a, b):\n    return a - b\n"
    replacement = 'def add(a, b):\n    """Subtract the second operand."""\n    return a - b\n'
    monkeypatch.setattr(fixtures, "SOURCE", source)
    monkeypatch.setattr(
        fixtures,
        "BLOB",
        hashlib.sha1(f"blob {len(source)}\0".encode() + source.encode()).hexdigest(),
    )
    value = fixtures.suggestion()
    value["changes"] = [
        {
            "path": "main.py",
            "before_sha256": fixtures.digest(source),
            "original": original,
            "replacement": replacement,
        }
    ]
    value["evidence"] = [{"evidence_id": "E0041"}]
    model.return_value = {"done": True, "message": {"content": json.dumps(value)}}
    row = fixtures.prepare(automation)
    proposal = row["proposals"][0]
    assert model.call_args.args[1]["format"]["title"] == "TargetedSuggestion"
    assert proposal["suggestion"]["changes"][0]["replacement"] == source.replace(
        original, replacement
    )
    assert "original" not in proposal["suggestion"]["changes"][0]
    assert "-# retained context" not in proposal["diff"]
    assert client.post(fixtures.url(row), json=fixtures.decision(row)).status_code == 200
    import uuid

    response = client.post(
        "/api/v1/auth/sandbox/executions",
        json={
            "request_id": str(uuid.uuid4()),
            "session_id": row["id"],
            "proposal_id": proposal["id"],
            "profiles": ["python_syntax"],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["preview"]["diff"] == proposal["diff"]
    assert response.json()["applied"] is False
    assert response.json()["execution_enabled"] is False


@pytest.mark.parametrize(
    "docstring",
    [
        "Subtract the second operand.",
        "\n    Subtract the second operand.\n",
    ],
    ids=["plain", "whitespace"],
)
def test_docstring_operation_persists_normal_review_and_preview_contract(automation, docstring):
    import uuid

    client, model = automation
    value = fixtures.suggestion()
    value["changes"] = [{"function_id": "D0001", "docstring": docstring}]
    model.return_value = {"done": True, "message": {"content": json.dumps(value)}}
    source = fixtures.create(client)
    assert source.status_code == 201
    row = source.json()
    response = client.post(
        fixtures.BASE + "/" + row["id"] + "/proposals",
        json={
            "request": "Add a short docstring to add describing its purpose.",
            "mode": "patch",
        },
    )
    assert response.status_code == 200, response.text
    row = response.json()
    proposal = row["proposals"][0]
    assert model.call_args.args[1]["format"]["title"] == "DocstringSuggestion"
    assert proposal["suggestion"]["changes"][0]["replacement"] == (
        "def add(a, b):\n    " + repr(docstring) + "\n    return a - b\n"
    )
    assert client.post(fixtures.url(row), json=fixtures.decision(row)).status_code == 200
    preview = client.post(
        "/api/v1/auth/sandbox/executions",
        json={
            "request_id": str(uuid.uuid4()),
            "session_id": row["id"],
            "proposal_id": proposal["id"],
            "profiles": ["python_syntax"],
        },
    )
    assert preview.status_code == 201, preview.text
    assert preview.json()["preview"]["diff"] == proposal["diff"]
    assert preview.json()["applied"] is False
