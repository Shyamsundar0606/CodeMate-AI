"""Opt-in Docker fixture verification, never imported by the application.

This operator tool controls only containers it creates. It cannot accept source,
commands, mounts, network settings or application execution requests.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

DOCKER = ["docker", "--context", "desktop-linux"]
LABEL = "org.codemate.sandbox.verification"
LIMIT = 65536
CASES = ("baseline", "pids", "memory", "timeout", "cancel")


class ProbeFailure(RuntimeError):
    pass


def command(arguments, timeout=20, *, allow_failure=False):
    """Bound both pipes while reading, including output from fixed container probes."""
    environment = {
        k: v
        for k, v in os.environ.items()
        if k.upper()
        in {
            "PATH",
            "SYSTEMROOT",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "TEMP",
            "TMP",
        }
    }
    process = subprocess.Popen(
        [*DOCKER, *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        shell=False,
    )
    output = [bytearray(), bytearray()]
    overflow = threading.Event()

    def read(pipe, target):
        with pipe:
            while block := pipe.read(4096):
                remaining = LIMIT // 2 - len(target)
                target.extend(block[: max(0, remaining)])
                if len(block) > remaining:
                    overflow.set()
                    process.kill()
                    break

    readers = [
        threading.Thread(target=read, args=(pipe, target), daemon=True)
        for pipe, target in zip((process.stdout, process.stderr), output, strict=True)
    ]
    for reader in readers:
        reader.start()
    expired = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        expired = True
        process.kill()
        process.wait(timeout=5)
    finally:
        for reader in readers:
            reader.join(timeout=5)
    if overflow.is_set() or any(reader.is_alive() for reader in readers):
        raise ProbeFailure("Docker output exceeded the safe capture boundary.")
    if not allow_failure and (process.returncode or expired):
        # Do not echo daemon stderr, environment, credentials or arbitrary terminal text.
        raise ProbeFailure("Docker operation failed or timed out.")
    return process.returncode, bytes(output[0]).decode("utf-8", "replace"), expired


def create_arguments(image, identity, case):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ProbeFailure("Use the exact locally built immutable image ID.")
    if not re.fullmatch(r"[0-9a-f]{32}", identity) or case not in CASES:
        raise ProbeFailure("Invalid fixed fixture identity.")
    return [
        "create",
        "--pull=never",
        "--name",
        "codemate-m9-probe-" + identity,
        "--label",
        LABEL + "=" + identity,
        "--network=none",
        "--read-only",
        "--user=65532:65532",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges=true",
        "--pids-limit=32",
        "--memory=128m",
        "--memory-swap=128m",
        "--cpus=0.5",
        "--ipc=none",
        "--cgroupns=private",
        "--ulimit=nofile=64:64",
        "--tmpfs=/workspace:rw,noexec,nosuid,nodev,size=8m,uid=65532,gid=65532,mode=0700",
        "--log-driver=none",
        image,
        case,
    ]


def check_configuration(item, image, identity, case):
    host, config = item["HostConfig"], item["Config"]
    expected = {
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
    }
    checks = [host.get(k) == v for k, v in expected.items()]
    checks += [
        item["Image"] == image,
        config["User"] == "65532:65532",
        config.get("WorkingDir") == "/workspace",
        config["Labels"].get(LABEL) == identity,
        config["Entrypoint"] == ["python", "-I", "-S", "/opt/codemate/probe.py"],
        config["Cmd"] == [case],
        not config.get("Volumes"),
        host.get("CapDrop") == ["ALL"],
        not host.get("CapAdd"),
        host.get("SecurityOpt") == ["no-new-privileges=true"],
        not host.get("Binds"),
        not host.get("Devices"),
        not host.get("DeviceRequests"),
        not host.get("PortBindings"),
        not host.get("PublishAllPorts"),
        host.get("LogConfig", {}).get("Type") == "none",
        host.get("Tmpfs")
        == {"/workspace": "rw,noexec,nosuid,nodev,size=8m,uid=65532,gid=65532,mode=0700"},
        all(
            m["Type"] == "tmpfs" and m["Destination"] == "/workspace"
            for m in item.get("Mounts", [])
        ),
        all(
            e.split("=", 1)[0]
            in {
                "PATH",
                "LANG",
                "GPG_KEY",
                "PYTHON_VERSION",
                "PYTHON_SHA256",
                "PYTHONDONTWRITEBYTECODE",
            }
            for e in config.get("Env", [])
        ),
    ]
    if not all(checks):
        raise ProbeFailure("Actual container configuration differs from the fixed restriction set.")


def verify_case(image, case):
    identity = uuid.uuid4().hex
    container = None
    result = {"case": case, "passed": False, "cleanup": "not_created"}
    try:
        _, output, _ = command(create_arguments(image, identity, case))
        container = output.strip()
        if not re.fullmatch(r"[0-9a-f]{64}", container):
            raise ProbeFailure("Docker did not return an exact container identity.")
        _, output, _ = command(["inspect", container])
        check_configuration(json.loads(output)[0], image, identity, case)
        code, output, expired = command(
            ["start", "--attach", container],
            timeout=1 if case == "cancel" else 3 if case == "timeout" else 20,
            allow_failure=True,
        )
        result.update(
            client_exit_code=code,
            timed_out=expired and case == "timeout",
            cancellation_requested=case == "cancel",
            configuration_checked=True,
        )
        if case in {"timeout", "cancel"}:
            # Killing the client does not terminate its container; terminate the exact runtime.
            command(["kill", container])
            _, output, _ = command(["inspect", container])
            state = json.loads(output)[0]["State"]
            result["exit_code"] = state["ExitCode"]
            result["runtime_stopped"] = not state["Running"] and state["ExitCode"] == 137
            result["passed"] = expired and result["runtime_stopped"]
        elif case == "memory":
            _, output, _ = command(["inspect", container])
            state = json.loads(output)[0]["State"]
            result["exit_code"] = state["ExitCode"]
            result["oom_killed"] = state["OOMKilled"]
            result["passed"] = not expired and state["OOMKilled"] and state["ExitCode"] == 137
        else:
            result["exit_code"] = code
            evidence = json.loads(output)
            result["evidence"] = evidence
            result["passed"] = not expired and code == 0
    finally:
        if container and re.fullmatch(r"[0-9a-f]{64}", container):
            # No prune, path deletion, volume deletion or other project container operation.
            command(["rm", "--force", container])
            _, output, _ = command(
                [
                    "ps",
                    "--all",
                    "--quiet",
                    "--no-trunc",
                    "--filter",
                    "label=" + LABEL + "=" + identity,
                ]
            )
            result["cleanup"] = "removed" if not output.strip() else "failed"
            result["passed"] = result["passed"] and result["cleanup"] == "removed"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--accept-local-docker-risk", action="store_true")
    args = parser.parse_args()
    if not args.accept_local_docker_risk:
        parser.error(
            "Explicit operator opt-in is required. This does not verify hostile-code safety."
        )
    report = {
        "version": "m9-fixture-v1",
        "at": datetime.now(UTC).isoformat(),
        "image_id": args.image,
        "execution_enabled": False,
        "provenance_verified": False,
        "worker_separation_verified": False,
        "source_sha256": {
            name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ("Dockerfile", "probe.py", "verify.py")
        },
    }
    try:
        report["cases"] = []
        for case in CASES:
            report["cases"].append(verify_case(args.image, case))
        report["fixture_checks_passed"] = all(case["passed"] for case in report["cases"])
    except (ProbeFailure, OSError, ValueError, KeyError) as exc:
        report["fixture_checks_passed"] = False
        report["error"] = str(exc) if isinstance(exc, ProbeFailure) else "Probe failed safely."
    print(json.dumps(report, indent=2))
    return 0 if report["fixture_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
