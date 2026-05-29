from __future__ import annotations

import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class LogFile:
    path: str
    mtime: float


def check_lxc_available() -> None:
    if shutil.which("lxc") is None:
        sys.exit("Error: lxc not found. Is lxc installed and are you in the lxd group?")


def check_container_exists(container: str) -> None:
    result = subprocess.run(
        ["lxc", "info", container],
        capture_output=True,
    )
    if result.returncode != 0:
        sys.exit(f"Error: container '{container}' not found.")


def list_log_files(
    container: str,
    log_dir: str,
    pattern: str,
    days: int,
    now: float | None = None,
) -> list[LogFile]:
    if now is None:
        now = time.time()
    cutoff = now - days * 86400

    result = subprocess.run(
        ["lxc", "exec", container, "--", "find", log_dir, "-name", pattern, "-printf", "%T@ %p\n"],
        text=True,
        stdout=subprocess.PIPE,
    )

    files: list[LogFile] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        mtime_str, path = line.split(" ", 1)
        mtime = float(mtime_str)
        if mtime >= cutoff:
            files.append(LogFile(path=path.strip(), mtime=mtime))

    return sorted(files, key=lambda f: f.mtime)


def stream_lines(container: str, path: str) -> Iterator[str]:
    cmd = (
        ["lxc", "exec", container, "--", "zcat", path]
        if path.endswith(".gz")
        else ["lxc", "exec", container, "--", "cat", path]
    )
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, errors="replace")
    try:
        for line in proc.stdout:
            yield line.rstrip("\n")
    finally:
        proc.wait()
