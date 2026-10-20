import ast
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.ai.errors import AIError
from app.automation.docstrings import DocstringSuggestion, expand_docstring, requested, targets_for
from app.automation.graph import build_graph

SOURCE = "import json\n\ndef example():\n    return json.dumps(1)\n"


def suggestion(text='Describe "quotes", \\slashes and\nnewlines.'):
    return DocstringSuggestion.model_validate(
        {
            "explanation": "Documents the selected function.",
            "expected_improvement": "Clarifies purpose.",
            "risks": ["Review required."],
            "limitations": ["No tests ran."],
            "confidence": "LOW",
            "evidence": [{"evidence_id": "E0001"}],
            "validations": [],
            "changes": [{"function_id": "D0001", "docstring": text}],
        }
    )


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_docstring_is_safely_quoted_and_all_executable_syntax_preserved(newline):
    source = SOURCE.replace("\n", newline)
    output = expand_docstring({"main.py": source}, suggestion(), targets_for({"main.py": source}))
    changed = output.changes[0].replacement
    tree = ast.parse(changed)
    assert ast.get_docstring(tree.body[1], clean=False) == suggestion().changes[0].docstring
    tree.body[1].body.pop(0)
    assert ast.dump(ast.parse(source)) == ast.dump(tree)
    assert (
        changed.replace("    " + repr(suggestion().changes[0].docstring) + newline, "", 1) == source
    )


@pytest.mark.parametrize(
    "source",
    [
        "def f(): return 1\n",
        'def f():\n    """Existing."""\n    return 1\n',
        "def f(\n): return 1\n",
    ],
)
def test_unsupported_targets_are_rejected(source):
    with pytest.raises(AIError):
        targets_for({"main.py": source})


def test_unknown_function_id_is_not_remapped():
    value = suggestion()
    value.changes[0].function_id = "D9999"
    with pytest.raises(AIError):
        expand_docstring({"main.py": SOURCE}, value, targets_for({"main.py": SOURCE}))


def test_documentation_graph_uses_text_only_model_protocol():
    model = Mock(settings=SimpleNamespace(ollama_model="fixture"))
    model.request.return_value = {
        "done": True,
        "message": {"content": suggestion().model_dump_json()},
    }
    output = build_graph(model, lambda *args, **kwargs: None).invoke(
        {
            "mode": "patch",
            "request": "Add a short docstring to example describing its purpose.",
            "files": {"main.py": SOURCE},
            "evidence": {},
        }
    )
    assert model.request.call_args.args[1]["format"]["title"] == "DocstringSuggestion"
    assert output["validated"][0]["replacement"].startswith("import json\n")
    assert "function_id" not in output["suggestion"].changes[0].model_dump()
    assert not requested({"mode": "explain", "request": "Add a docstring"})
    assert not requested({"mode": "patch", "request": "Do not add a docstring"})


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize(
    "text",
    [
        "  Leading spaces.",
        "\tLeading tab.",
        "\nSummary.\n",
        "Summary.\n    Indented details.\n",
        "Summary.\n\n    Details.\n    ",
        'Describe "quotes" and \\slashes.',
        "  Résumé documentation.\n",
        "A" * 299 + " ",
    ],
)
def test_docstring_preserves_exact_text_without_cleaning(newline, text):
    source = SOURCE.replace("\n", newline)
    output = expand_docstring(
        {"main.py": source}, suggestion(text), targets_for({"main.py": source})
    )
    tree = ast.parse(output.changes[0].replacement)
    assert ast.get_docstring(tree.body[1], clean=False) == text
    tree.body[1].body.pop(0)
    assert ast.dump(ast.parse(source)) == ast.dump(tree)
    inserted_line = "    " + repr(text) + newline
    assert output.changes[0].replacement.replace(inserted_line, "", 1) == source
