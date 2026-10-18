"""File-local grounding, call budgets and atomic generation regressions."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.ai.errors import AIError
from app.automation.citations import catalog_for
from app.automation.explanations import explain_files


def response(identity="E0001", **extra):
    return {
        "done": True,
        "message": {
            "content": json.dumps(
                {
                    "evidence": [{"evidence_id": identity}],
                }
            )
        },
        **extra,
    }


def setup():
    state = {"request": "Explain both files", "files": {"a.py": "x = 1\n", "b.py": "y = 2\n"}}
    model = SimpleNamespace(settings=SimpleNamespace(ollama_model="fixture"), request=Mock())
    return state, model, catalog_for(state["files"], {})


def test_file_calls_are_scoped_bounded_and_never_remap_ids():
    state, model, catalog = setup()
    model.request.side_effect = [response(), response("E0002")]
    clean = Mock()
    result = explain_files(model, state, catalog, clean)
    assert [e.evidence_id for e in result.evidence] == ["E0001", "E0002"]
    assert model.request.call_count == 2
    for call, path, identity in zip(
        model.request.call_args_list, ["a.py", "b.py"], ["E0001", "E0002"], strict=True
    ):
        body = call.args[1]
        assert body["options"] == {"temperature": 0, "num_ctx": 8192, "num_predict": 192}
        assert 0 < call.kwargs["timeout"] <= 35
        assert body["format"]["$defs"]["CitationReference"]["properties"]["evidence_id"][
            "enum"
        ] == [identity]
        prompt = json.loads(body["messages"][1]["content"])
        assert prompt["current_file"] == path
        assert [e["evidence_id"] for e in prompt["evidence_catalog"]] == [identity]
    assert clean.call_count == 4


@pytest.mark.parametrize(
    "bad",
    [
        response("E0002"),
        response("INVENTED"),
        response(done=False),
        response(done_reason="length"),
        response(prompt_eval_count=8192),
        {"done": True, "message": {"content": "private invalid model output"}},
        {
            "done": True,
            "message": {
                "content": json.dumps(
                    {
                        "explanation": "An invented vulnerability",
                        "evidence": [{"evidence_id": "E0001"}],
                    }
                )
            },
        },
    ],
)
def test_bad_file_output_stops_without_retry_or_partial_result(bad):
    state, model, catalog = setup()
    model.request.return_value = bad
    with pytest.raises(AIError) as error:
        explain_files(model, state, catalog, Mock())
    assert "No suggestion was saved" in error.value.detail["message"]
    assert "private invalid model output" not in str(error.value.detail)
    assert model.request.call_count == 1


def test_timeout_is_actionable_and_has_no_retry():
    state, model, catalog = setup()
    model.request.side_effect = AIError("AI_TIMEOUT", "fixture", 504)
    with pytest.raises(AIError) as error:
        explain_files(model, state, catalog, Mock())
    assert error.value.detail["code"] == "AI_TIMEOUT"
    assert "a.py" in error.value.detail["message"]
    assert "No suggestion was saved" in error.value.detail["message"]
    assert model.request.call_count == 1


def test_total_deadline_prevents_later_call(monkeypatch):
    state, model, catalog = setup()
    model.request.return_value = response()
    monkeypatch.setattr("app.automation.explanations.time.monotonic", Mock(side_effect=[0, 0, 91]))
    with pytest.raises(AIError, match="time budget exhausted"):
        explain_files(model, state, catalog, Mock())
    assert model.request.call_count == 1


def test_remaining_total_budget_limits_next_file(monkeypatch):
    state, model, catalog = setup()
    model.request.side_effect = [response(), response("E0002")]
    monkeypatch.setattr(
        "app.automation.explanations.time.monotonic", Mock(side_effect=[0, 0, 70, 70, 80])
    )
    explain_files(model, state, catalog, Mock())
    assert model.request.call_args_list[1].kwargs["timeout"] == 20


def test_observations_are_source_derived_and_request_focused():
    from app.automation.observations import observations_for, relevant_observations

    source = (
        "class Settings(BaseSettings):\n    pass\n\ndef get_settings():\n    return Settings()\n"
    )
    catalog = catalog_for({"settings.py": source}, {})
    observations = observations_for("settings.py", source, catalog)
    assert "Defines class Settings inheriting BaseSettings." in " ".join(observations.values())
    assert "Calls Settings." in " ".join(observations.values())
    scoped = relevant_observations(
        "settings.py",
        "Explain how settings load from settings.py.",
        {
            "E0001": "Calls Settings.",
            "E0002": "Assigns logger using logging.getLogger.",
        },
    )
    assert scoped == {"E0001": "Calls Settings."}


def test_header_fact_requires_header_in_exact_citation():
    from app.automation.observations import observations_for

    source = "class Settings(BaseSettings):\n    x = 1\n"
    catalog = {"E0009": {"line_start": 2, "line_end": 2, "quote": "    x = 1"}}
    assert "Defines class" not in observations_for("settings.py", source, catalog)["E0009"]


def test_calls_cannot_exceed_file_limit():
    state, model, _ = setup()
    state["files"] = {f"file{i}.py": "x = 1\n" for i in range(5)}
    with pytest.raises(AIError):
        explain_files(model, state, catalog_for(state["files"], {}), Mock())
    model.request.assert_not_called()


def test_long_line_fragments_cannot_support_a_complete_header():
    from app.automation.observations import observations_for

    source = "def initialize(" + ", ".join(f"argument{i}" for i in range(50)) + "):\n    pass\n"
    catalog = catalog_for({"main.py": source}, {})
    observations = observations_for("main.py", source, catalog)
    assert all("Defines function initialize" not in fact for fact in observations.values())
