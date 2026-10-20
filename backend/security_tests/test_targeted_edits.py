"""Exact edit reconstruction preserves all source outside the validated anchor."""

import ast
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.ai.errors import AIError
from app.automation.edits import TargetedSuggestion, expand_edits
from app.automation.graph import build_graph
from app.automation.policy import digest
from app.services.automation_service import AutomationService

SOURCE = "# retained context\n" * 240 + "def example():\n    return 1\n"
ANCHOR = "def example():\n    return 1\n"
REPLACEMENT = 'def example():\n    """Return the example value."""\n    return 1\n'


def suggestion(original=ANCHOR, replacement=REPLACEMENT, **extra):
    return TargetedSuggestion.model_validate(
        {
            "explanation": "Adds a docstring to the inspected function.",
            "expected_improvement": "Documents its purpose.",
            "risks": ["Review the proposal."],
            "limitations": ["Not executed."],
            "confidence": "LOW",
            "evidence": [{"evidence_id": "E0041"}],
            "validations": [],
            "changes": [
                {
                    "path": "main.py",
                    "before_sha256": digest(SOURCE),
                    "original": original,
                    "replacement": replacement,
                    **extra,
                }
            ],
        }
    )


def test_exact_edit_preserves_prefix_and_only_adds_docstring():
    output = expand_edits({"main.py": SOURCE}, suggestion())
    after = output.changes[0].replacement
    assert after == SOURCE.replace(ANCHOR, REPLACEMENT, 1)
    before_tree, after_tree = ast.parse(SOURCE), ast.parse(after)
    assert ast.get_docstring(after_tree.body[0]) == "Return the example value."
    after_tree.body[0].body.pop(0)
    assert ast.dump(before_tree) == ast.dump(after_tree)


@pytest.mark.parametrize(
    "anchor", ["missing", "# retained context\n", " ", ANCHOR.replace("    ", "  ")]
)
def test_absent_ambiguous_whitespace_or_fuzzy_anchor_rejected(anchor):
    with pytest.raises(AIError):
        expand_edits({"main.py": SOURCE}, suggestion(original=anchor))


@pytest.mark.parametrize("extra", [{"path": "other.py"}, {"before_sha256": "0" * 64}])
def test_path_and_base_hash_remain_exact(extra):
    with pytest.raises(AIError):
        expand_edits({"main.py": SOURCE}, suggestion(**extra))


def test_duplicate_edits_rejected():
    value = suggestion()
    value.changes *= 2
    with pytest.raises(AIError):
        expand_edits({"main.py": SOURCE}, value)


def test_large_file_graph_uses_anchored_protocol_and_persists_full_replacement():
    model = Mock(settings=SimpleNamespace(ollama_model="fixture"))
    model.request.return_value = {
        "done": True,
        "message": {"content": suggestion().model_dump_json()},
    }
    output = build_graph(model, lambda *args, **kwargs: None).invoke(
        {
            "mode": "patch",
            "request": "Edit the function comment",
            "files": {"main.py": SOURCE},
            "evidence": {},
        }
    )
    body = model.request.call_args.args[1]
    assert body["format"]["title"] == "TargetedSuggestion"
    assert "original" in body["format"]["$defs"]["TargetedChange"]["required"]
    assert json.loads(body["messages"][1]["content"])["files"]["main.py"]["content"] == SOURCE
    assert output["suggestion"].changes[0].replacement.endswith(REPLACEMENT)
    assert "original" not in output["suggestion"].changes[0].model_dump()


def test_syntax_error_is_distinct_from_credential_failure():
    settings = SimpleNamespace(
        github_client_secret=None, jwt_secret_key=SimpleNamespace(get_secret_value=lambda: "x" * 48)
    )
    service = AutomationService(None, settings, None, None, None, None)
    with pytest.raises(AIError) as failure:
        service.clean_text("def broken(:\n", source_path="main.py")
    assert failure.value.detail["code"] == "AUTOMATION_PYTHON_SYNTAX_INVALID"
    assert "does not establish a credential problem" in failure.value.detail["message"]
