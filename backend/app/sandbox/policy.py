"""Preparation-only security gate. Deliberately no launcher or enable setting."""

import hashlib
import json

PROFILE = {
    "id": "python_syntax",
    "argv": ["python", "-I", "-S", "/opt/codemate/validate_syntax.py"],
    "working_directory": "/workspace",
    "environment": {},
    "description": "Parse approved Python files with a trusted AST validator (not executed).",
}
ISOLATION = {
    "version": "m8-preparation-v1",
    "image_digest": None,
    "network": "none",
    "read_only_root": True,
    "user": "65532:65532",
    "capabilities": [],
    "no_new_privileges": True,
    "host_mounts": [],
    "pids": 64,
    "memory_mib": 256,
    "cpus": 1,
    "timeout_seconds": 30,
    "output_bytes": 65536,
    "tmpfs_mib": 32,
    "seccomp": "unverified",
}
REASONS = [
    "No verified isolated execution service is configured.",
    "Image provenance, runtime separation and negative isolation tests are unverified.",
    "Patch application and validation have not run. Review approval is not execution approval.",
    "Fixture-only Docker probes cannot approve image provenance, "
    "worker separation or execution readiness.",
]


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def capabilities():
    return {
        "execution_enabled": False,
        "verification": "unverified",
        "reasons": REASONS,
        "isolation": ISOLATION,
        "profiles": [PROFILE],
    }
