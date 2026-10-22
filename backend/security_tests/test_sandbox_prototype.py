"""Unit tests of the operator prototype contract, not proof of Docker isolation."""

import copy
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "sandbox_verify", ROOT / "infrastructure/sandbox/verify.py"
)
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
IMAGE = "sha256:" + "a" * 64
IDENTITY = "b" * 32
CONTAINER = "c" * 64


def configuration():
    return {
        "Image": IMAGE,
        "Config": {
            "User": "65532:65532",
            "WorkingDir": "/workspace",
            "Labels": {verify.LABEL: IDENTITY},
            "Entrypoint": ["python", "-I", "-S", "/opt/codemate/probe.py"],
            "Cmd": ["baseline"],
            "Volumes": None,
            "Env": ["PATH=/usr/local/bin:/usr/bin"],
        },
        "Mounts": [],
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Privileged": False,
            "PidMode": "",
            "IpcMode": "none",
            "CgroupnsMode": "private",
            "Memory": 134217728,
            "MemorySwap": 134217728,
            "PidsLimit": 32,
            "NanoCpus": 500000000,
            "CapDrop": ["ALL"],
            "CapAdd": None,
            "SecurityOpt": ["no-new-privileges=true"],
            "Binds": None,
            "Devices": [],
            "DeviceRequests": None,
            "PortBindings": {},
            "PublishAllPorts": False,
            "LogConfig": {"Type": "none"},
            "Tmpfs": {"/workspace": "rw,noexec,nosuid,nodev,size=8m,uid=65532,gid=65532,mode=0700"},
        },
    }


@pytest.mark.parametrize("image", ["python:latest", "--privileged", "sha256:a", IMAGE + " x"])
def test_mutable_or_injected_image_rejected(image):
    with pytest.raises(verify.ProbeFailure):
        verify.create_arguments(image, IDENTITY, "baseline")


@pytest.mark.parametrize("case", ["pytest", "sh", "../baseline", "baseline; echo unsafe"])
def test_no_command_input(case):
    with pytest.raises(verify.ProbeFailure):
        verify.create_arguments(IMAGE, IDENTITY, case)


@pytest.mark.parametrize(
    "field,value",
    [
        ("Privileged", True),
        ("NetworkMode", "host"),
        ("ReadonlyRootfs", False),
        ("PidMode", "host"),
        ("Memory", 0),
        ("PidsLimit", 0),
        ("NanoCpus", 0),
        ("Binds", ["/:/host"]),
        ("SecurityOpt", ["seccomp=unconfined"]),
        ("CapAdd", ["SYS_ADMIN"]),
        ("DeviceRequests", [{"Count": -1}]),
    ],
)
def test_actual_configuration_drift_rejected(field, value):
    item = configuration()
    item["HostConfig"][field] = value
    with pytest.raises(verify.ProbeFailure):
        verify.check_configuration(item, IMAGE, IDENTITY, "baseline")


def test_expected_configuration_and_no_application_mounts():
    verify.check_configuration(configuration(), IMAGE, IDENTITY, "baseline")
    item = copy.deepcopy(configuration())
    item["Mounts"] = [{"Type": "bind", "Destination": "/host"}]
    with pytest.raises(verify.ProbeFailure):
        verify.check_configuration(item, IMAGE, IDENTITY, "baseline")


def test_image_and_entrypoint_identity_are_checked():
    for key, value in [("User", "0"), ("Entrypoint", ["sh"]), ("Env", ["GITHUB_TOKEN=dummy"])]:
        item = configuration()
        item["Config"][key] = value
        with pytest.raises(verify.ProbeFailure):
            verify.check_configuration(item, IMAGE, IDENTITY, "baseline")


def test_failed_inspection_still_removes_only_created_container(monkeypatch):
    calls = []

    def command(args, **kwargs):
        calls.append(args)
        if args[0] == "create":
            return 0, CONTAINER, False
        if args[0] == "inspect":
            raise verify.ProbeFailure("Unavailable")
        return 0, "", False

    monkeypatch.setattr(verify, "command", command)
    with pytest.raises(verify.ProbeFailure):
        verify.verify_case(IMAGE, "baseline")
    assert ["rm", "--force", CONTAINER] in calls
    assert not any("prune" in c or "--volumes" in c for c in calls)


def test_output_capture_is_bounded_and_host_secrets_not_inherited(monkeypatch):
    process = Mock(stdout=io.BytesIO(b"x" * 100000), stderr=io.BytesIO(b""), returncode=0)
    popen = Mock(return_value=process)
    monkeypatch.setattr(verify.subprocess, "Popen", popen)
    monkeypatch.setenv("GITHUB_TOKEN", "dummy-private-value")
    with pytest.raises(verify.ProbeFailure, match="output exceeded"):
        verify.command(["version"])
    process.kill.assert_called()
    assert "GITHUB_TOKEN" not in popen.call_args.kwargs["env"]
    assert popen.call_args.kwargs["shell"] is False


def test_explicit_opt_in_required(monkeypatch):
    monkeypatch.setattr(
        verify.sys if hasattr(verify, "sys") else __import__("sys"),
        "argv",
        ["verify.py", "--image", IMAGE],
    )
    with pytest.raises(SystemExit) as result:
        verify.main()
    assert result.value.code == 2


def test_fixture_report_never_enables_application_execution(monkeypatch, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["verify.py", "--image", IMAGE, "--accept-local-docker-risk"])
    monkeypatch.setattr(verify, "verify_case", lambda image, case: {"case": case, "passed": True})
    assert verify.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["execution_enabled"] is False
    assert report["worker_separation_verified"] is False
    assert report["provenance_verified"] is False
