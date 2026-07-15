"""Shared, dependency-free helpers for read-only audit probes.

Security invariants enforced here (see references/audit-contract.md §8 and the
threat model T3/T6/T9):

- Boundary: every path a probe reads must resolve to a real path *inside* the target
  root. Symlinks are never followed; a symlink whose target escapes the boundary is
  reported as a finding, never read through.
- No target exec: probes read files as data. This module offers no process execution.
- Bounds: file count, per-file read size, and total walk time are capped to survive a
  hostile target (huge files, symlink loops, decompression-bomb bait).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

VERSION = "0.2.0"

# Bounds — deliberately conservative; a probe that hits one records bounded=True.
MAX_FILES = 200_000
MAX_READ_BYTES = 2_000_000  # per-file read cap for content inspection
MAX_WALK_SECONDS = 120


@dataclass
class Envelope:
    """The probe-output envelope from the contract."""

    probe: str
    target: str
    containment: str = "read-only-mount"
    coverage_pct: float = 100.0
    bounded: bool = False
    boundary_enforced: bool = True
    errors: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def add_finding(self, fid: str, kind: str, severity: str, path: str, detail: str) -> None:
        self.findings.append(
            {"id": fid, "kind": kind, "severity": severity, "path": path, "detail": detail}
        )

    def emit(self) -> None:
        out = {
            "probe": self.probe,
            "version": VERSION,
            "target": self.target,
            "boundary_enforced": self.boundary_enforced,
            "containment": self.containment,
            "coverage_pct": round(self.coverage_pct, 2),
            "bounded": self.bounded,
            "errors": self.errors,
            "findings": self.findings,
            "data": self.data,
        }
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")


def resolve_target(arg: str) -> Path:
    """Resolve the audited target root to a real absolute directory."""
    root = Path(arg).resolve()
    if not root.is_dir():
        raise SystemExit(f"ERROR: target is not a directory: {root}")
    return root


def within(root: Path, candidate: Path) -> bool:
    """True iff candidate's real path is inside root (no boundary escape)."""
    try:
        real = candidate.resolve()
    except (OSError, RuntimeError):
        return False
    return real == root or root in real.parents


def iter_entries(root: Path, env: Envelope) -> Iterator[tuple[Path, os.DirEntry]]:
    """Walk root WITHOUT following symlinks, bounded by count and time.

    Yields (dirpath, DirEntry). Symlinks that escape the boundary are reported as
    findings on the envelope and are not descended into or read through.
    """
    start = time.monotonic()
    count = 0
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except (OSError, PermissionError) as exc:
            env.errors.append(f"scandir failed: {current}: {exc}")
            continue
        for entry in entries:
            count += 1
            if count > MAX_FILES or (time.monotonic() - start) > MAX_WALK_SECONDS:
                env.bounded = True
                return
            p = Path(entry.path)
            if entry.is_symlink():
                if not within(root, p):
                    env.add_finding(
                        f"symlink-escape-{count}",
                        "boundary-escape",
                        "high",
                        os.path.relpath(p, root),
                        "symlink resolves outside the audited target; not followed",
                    )
                # Never follow symlinks, escaping or not.
                yield current, entry
                continue
            if entry.is_dir(follow_symlinks=False):
                stack.append(p)
            yield current, entry


def read_text_bounded(path: Path) -> str | None:
    """Read a file as text, capped at MAX_READ_BYTES. Returns None on failure.

    Never executes; opens as a plain file. Decodes with errors ignored so hostile
    binary content cannot crash the probe.
    """
    try:
        with open(path, "rb") as fh:
            raw = fh.read(MAX_READ_BYTES)
    except (OSError, PermissionError):
        return None
    return raw.decode("utf-8", errors="ignore")


def fingerprint(text: str) -> str:
    """Short, non-reversible fingerprint for evidence references (never the value)."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]
