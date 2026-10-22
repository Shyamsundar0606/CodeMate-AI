"""Fixed harmless fixtures. Only run inside the prototype Linux container."""

import ast
import errno
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path


def denied_write(path):
    try:
        with open(path, "x") as stream:
            stream.write("fixture")
    except OSError as exc:
        return exc.errno in {errno.EROFS, errno.EACCES, errno.EPERM}
    return False


def no_connection(host, port):
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return False
    except OSError:
        return True


def inaccessible(path):
    try:
        return not Path(path).exists()
    except PermissionError:
        return True


def baseline():
    status = Path("/proc/self/status").read_text()
    fields = dict(line.split(":", 1) for line in status.splitlines() if ":" in line)
    cgroup = Path("/sys/fs/cgroup")
    before = b"def add(a, b):\n    return a - b\n"
    after = b"def add(a, b):\n    return a + b\n"
    # No repository input, diff parsing, imports or execution. Disposable tmpfs only.
    original = Path("/workspace/original.py")
    patched = Path("/workspace/patched.py")
    original.write_bytes(before)
    patched.write_bytes(after)
    ast.parse(patched.read_bytes())
    checks = {
        "non_root": os.getuid() == 65532 and os.getgid() == 65532,
        "root_read_only": denied_write("/opt/codemate/write-probe"),
        "no_new_privileges": fields["NoNewPrivs"].strip() == "1",
        "no_effective_capabilities": int(fields["CapEff"].strip(), 16) == 0,
        "seccomp_filter": fields["Seccomp"].strip() == "2",
        "no_socket_or_host_paths": all(
            inaccessible(p)
            for p in (
                "/var/run/docker.sock",
                "/run/docker.sock",
                "/root/.ssh",
                "/host",
                "/mnt/c",
            )
        ),
        "no_app_environment": not any(
            k in os.environ for k in ("DATABASE_URL", "JWT_SECRET_KEY", "GITHUB_TOKEN", "GH_TOKEN")
        ),
        "external_ip_blocked": no_connection("1.1.1.1", 443),
        "host_database_blocked": no_connection("host.docker.internal", 5433),
        "host_ollama_blocked": no_connection("host.docker.internal", 11434),
        "memory_limit": (cgroup / "memory.max").read_text().strip() == "134217728",
        "pid_limit": (cgroup / "pids.max").read_text().strip() == "32",
        "cpu_limit": (cgroup / "cpu.max").read_text().strip() == "50000 100000",
        "tmpfs_limit": os.statvfs("/workspace").f_blocks * os.statvfs("/workspace").f_frsize
        <= 8 * 1024 * 1024,
        "original_unchanged": original.read_bytes() == before,
        "patched_hash": patched.read_bytes() == after,
    }
    print(json.dumps({"checks": checks, "after_sha256": hashlib.sha256(after).hexdigest()}))
    return 0 if all(checks.values()) else 1


def pids():
    children = []
    limited = False
    try:
        # Bounded even if the intended cgroup restriction is absent.
        for _ in range(40):
            try:
                child = os.fork()
            except OSError as exc:
                limited = exc.errno == errno.EAGAIN
                break
            if child == 0:
                time.sleep(5)
                os._exit(0)
            children.append(child)
    finally:
        for child in children:
            os.kill(child, 15)
            os.waitpid(child, 0)
    print(json.dumps({"pid_limit_enforced": limited, "children": len(children)}))
    return 0 if limited else 1


def main():
    # Refuse accidental host execution, including direct invocation on Windows.
    if sys.platform != "linux" or not Path("/.dockerenv").exists() or os.getuid() != 65532:
        raise SystemExit("This trusted probe requires its restricted prototype container.")
    case = sys.argv[1] if len(sys.argv) == 2 else "baseline"
    if case == "baseline":
        return baseline()
    if case == "pids":
        return pids()
    if case == "memory":
        value = bytearray(192 * 1024 * 1024)
        print(len(value))
        return 1  # Expected to be killed by the 128 MiB container limit.
    if case in {"timeout", "cancel"}:
        time.sleep(60)
        return 1
    raise SystemExit("Unknown fixed fixture.")


if __name__ == "__main__":
    raise SystemExit(main())
