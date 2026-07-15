#!/usr/bin/env python3
"""census probe — exhaustive, read-only file census of the audited target.

Pure measurement (no specialist tool, no target exec). Reports footprint, file
counts, file-class histogram, largest artifacts, executable files, and symlinks that
cross the target boundary. Boundary/bounds are enforced by _common.

Usage: census.py <target-dir>
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import Envelope, iter_entries, resolve_target  # noqa: E402

CODE_EXT = {".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".c", ".cpp", ".sh", ".mjs"}
CONFIG_EXT = {".json", ".yaml", ".yml", ".toml", ".ini", ".env", ".cfg"}


def classify(name: str) -> str:
    ext = Path(name).suffix.lower()
    if ext in CODE_EXT:
        return "source"
    if ext in CONFIG_EXT:
        return "config"
    if ext in {".md", ".rst", ".txt"}:
        return "docs"
    if ext in {".png", ".jpg", ".jpeg", ".svg", ".gif", ".pdf"}:
        return "media"
    if ext in {".lock", ".sum"} or name in {"package-lock.json", "poetry.lock", "Cargo.lock"}:
        return "lockfile"
    return "other"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: census.py <target-dir>", file=sys.stderr)
        return 2
    root = resolve_target(argv[1])
    env = Envelope(probe="census", target=str(root))

    classes: Counter = Counter()
    total_files = 0
    total_bytes = 0
    executables = 0
    largest: list[tuple[int, str]] = []

    for _, entry in iter_entries(root, env):
        if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
            continue
        try:
            st = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        total_files += 1
        total_bytes += st.st_size
        classes[classify(entry.name)] += 1
        if st.st_mode & 0o111:
            executables += 1
        rel = os.path.relpath(entry.path, root)
        largest.append((st.st_size, rel))

    largest.sort(reverse=True)
    env.data = {
        "total_files": total_files,
        "total_bytes": total_bytes,
        "file_classes": dict(classes),
        "executable_files": executables,
        "largest_artifacts": [{"bytes": b, "path": p} for b, p in largest[:10]],
        "symlink_escapes": sum(1 for f in env.findings if f["kind"] == "boundary-escape"),
    }
    env.emit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
