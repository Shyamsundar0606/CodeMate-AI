"""Opt-in controlled API benchmark; guarded test DB only, never live inference."""

import json
import os
import platform
import statistics
import time
import tracemalloc
from pathlib import Path

import pytest
from test_ai import ai as ai
from test_automation import SOURCE, suggestion
from test_automation import automation as automation
from test_sandbox import preview


def test_controlled_demo_benchmark(automation):
    phase = os.environ.get("CODEMATE_BENCHMARK_PHASE")
    if phase not in {"baseline", "hardened", "milestone12"}:
        pytest.skip("Explicit CODEMATE_BENCHMARK_PHASE=baseline, hardened or milestone12 required")
    client, model = automation
    source, _, item = preview(automation)
    routes = {
        "health": "/health",
        "authenticated_account": "/api/v1/auth/me",
        "github_repository_listing": "/api/v1/github/repositories?installation_id=10",
        "automation_history": "/api/v1/automation/sessions",
        "execution_preview": "/api/v1/sandbox/executions/" + item["id"],
    }
    result = {
        "phase": phase,
        "python": platform.python_version(),
        "platform": platform.system(),
        "environment": "test",
        "transport": "in-process TestClient",
        "upstream": "controlled GitHub and model fixtures; no real network inference",
        "source_bytes": len(SOURCE.encode()),
        "operations": {},
    }
    tracemalloc.start()
    for name, route in routes.items():
        assert client.get(route).status_code == 200
        values = []
        for _ in range(20):
            started = time.perf_counter()
            response = client.get(route)
            values.append((time.perf_counter() - started) * 1000)
            assert response.status_code == 200
        result["operations"][name] = {
            "samples": len(values),
            "median_ms": round(statistics.median(values), 3),
            "p95_ms": round(sorted(values)[18], 3),
        }
    value = suggestion()
    value["changes"] = []
    model.return_value = {"done": True, "message": {"content": json.dumps(value)}}
    started = time.perf_counter()
    response = client.post(
        f"/api/v1/auth/automation/sessions/{source['id']}/proposals",
        json={"request": "Explain addition", "mode": "explain"},
    )
    assert response.status_code == 200
    result["operations"]["controlled_ai_explanation"] = {
        "samples": 1,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "p95_ms": None,
    }
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result["python_tracemalloc_peak_bytes"] = peak
    name = (
        "milestone-12-benchmark.json"
        if phase == "milestone12"
        else f"milestone-11-benchmark-{phase}.json"
    )
    output = Path(__file__).resolve().parents[2] / "docs" / name
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
