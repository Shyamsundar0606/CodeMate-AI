"""Mode contracts guide generation and fail closed without rewriting model output."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.ai.errors import AIError
from app.automation.graph import build_graph
from app.automation.policy import digest

SOURCE = "def add(a, b):\n    return a - b\n"
FIXED = SOURCE.replace("a - b", "a + b")


def result(changes):
    return {
        "explanation": "The inspected function subtracts operands.",
        "expected_improvement": "Review the intended arithmetic.",
        "risks": ["Behavior requires review."],
        "limitations": ["No validation ran."],
        "confidence": "LOW",
        "evidence": [{"evidence_id": "E0001"}],
        "changes": [{"path": "main.py", "before_sha256": digest(SOURCE), "replacement": FIXED}]
        if changes
        else [],
        "validations": [],
    }


def invoke(mode, changes):
    ollama = Mock(settings=SimpleNamespace(ollama_model="fixture"))
    ollama.request.return_value = {
        "done": True,
        "message": {"content": json.dumps(result(changes))},
    }
    state = {
        "request": "Explain addition" if mode == "explain" else "Fix addition",
        "mode": mode,
        "files": {"main.py": SOURCE},
        "evidence": {},
    }
    return build_graph(ollama, lambda *args, **kwargs: None), ollama, state


@pytest.mark.parametrize(
    "mode,changes,min_items,max_items",
    [
        ("explain", False, 0, 0),
        ("patch", True, 1, 1),
    ],
)
def test_generation_schema_matches_selected_mode(mode, changes, min_items, max_items):
    graph, model, state = invoke(mode, changes)
    response = graph.invoke(state)
    schema = model.request.call_args.args[1]["format"]["properties"]["changes"]
    assert schema["minItems"] == min_items
    assert schema["maxItems"] == max_items
    assert bool(response["validated"]) == changes


@pytest.mark.parametrize(
    "mode,changes,message",
    [
        ("patch", False, "select Explain source"),
        ("explain", True, "unexpectedly included edits"),
    ],
)
def test_noncompliant_model_output_is_rejected_with_actionable_guidance(mode, changes, message):
    graph, model, state = invoke(mode, changes)
    with pytest.raises(AIError) as failure:
        graph.invoke(state)
    assert message in failure.value.detail["message"]
    assert "No suggestion was saved" in failure.value.detail["message"]
    assert model.request.call_count == 1


@pytest.mark.parametrize("replacement", ["", " ", "\n\t\r\n"])
def test_empty_file_replacement_is_rejected_even_if_model_ignores_schema(replacement):
    graph, model, state = invoke("patch", True)
    value = result(True)
    value["changes"][0]["replacement"] = replacement
    model.request.return_value["message"]["content"] = json.dumps(value)
    with pytest.raises(AIError) as failure:
        graph.invoke(state)
    assert "Clearing an existing file is unsupported" in failure.value.detail["message"]
    schema = model.request.call_args.args[1]["format"]["$defs"]["Change"]
    assert schema["properties"]["replacement"]["minLength"] == 1
    assert schema["properties"]["replacement"]["pattern"] == r"\S"


def test_patch_generation_receives_exact_paths_hashes_and_complete_source():
    graph, model, state = invoke("patch", True)
    graph.invoke(state)
    body = model.request.call_args.args[1]
    change = body["format"]["$defs"]["Change"]["properties"]
    assert change["path"]["enum"] == ["main.py"]
    assert change["before_sha256"]["enum"] == [digest(SOURCE)]
    assert json.loads(body["messages"][1]["content"])["files"]["main.py"]["content"] == SOURCE


@pytest.mark.parametrize("path", ["other.py", "backend/main.py"])
def test_uninspected_path_is_rejected_even_when_model_ignores_enum(path):
    graph, model, state = invoke("patch", True)
    value = result(True)
    value["changes"][0]["path"] = path
    model.request.return_value["message"]["content"] = json.dumps(value)
    with pytest.raises(AIError):
        graph.invoke(state)


def test_duplicate_path_is_rejected_even_when_model_ignores_item_limit():
    graph, model, state = invoke("patch", True)
    value = result(True)
    value["changes"] *= 2
    model.request.return_value["message"]["content"] = json.dumps(value)
    with pytest.raises(AIError):
        graph.invoke(state)
