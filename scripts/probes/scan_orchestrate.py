#!/usr/bin/env python3
"""scan_orchestrate probe — run a mature specialist scanner, or record `blocked`.

Design decision (threat model T9, non-goal "don't reinvent scanners"): specialist
scanning (secrets/CVE/taint) is delegated to mature tools, never reimplemented in
dependency-free Python. This probe:

- Resolves the tool by ABSOLUTE path (never trusts a bare name from $PATH ordering
  when it can help it) and runs it with OUR flags, ignoring target-supplied config.
- Runs secrets detection via `gitleaks` in filesystem mode with `--redact`, so secret
  VALUES never enter our output (only path:line:rule). This also avoids git exec on
  the untrusted repo (`--no-git`).
- For tools that are absent, records the layer as `blocked` with the smallest safe
  resolving command — never a fake pass.

CVE (trivy) and taint (semgrep) orchestration are declared blocked-with-command in
v0.2; wiring their parsers is future work, and saying so is the honest state.

Usage: scan_orchestrate.py <target-dir> [--run]
  Without --run, every scanner is reported as blocked-with-command (safe default:
  running a scanner over untrusted content belongs in the containment doctrine).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import Envelope, resolve_target  # noqa: E402

TIMEOUT = 300


def _blocked(reason: str, command: str) -> dict:
    return {"status": "blocked", "reason": reason, "resolving_command": command}


def run_gitleaks(target: str, env: Envelope) -> dict:
    exe = shutil.which("gitleaks")
    cmd_hint = f"gitleaks detect --no-git --redact --source {target}"
    if not exe:
        return _blocked("gitleaks not installed", cmd_hint)
    with tempfile.NamedTemporaryFile("r", suffix=".json", delete=False) as rpt:
        report_path = rpt.name
    try:
        proc = subprocess.run(
            [exe, "detect", "--no-git", "--redact", "--source", target,
             "--report-format", "json", "--report-path", report_path, "--exit-code", "0"],
            capture_output=True, text=True, timeout=TIMEOUT, cwd=tempfile.gettempdir(),
        )
        with open(report_path, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read().strip()
        results = json.loads(content) if content else []
        for i, r in enumerate(results):
            path = r.get("File", "?")
            line = r.get("StartLine", "?")
            rule = r.get("RuleID", "secret")
            env.add_finding(
                f"secret-{i+1}", "secret-detected", "high",
                f"{path}:{line}",
                f"gitleaks rule `{rule}` (value redacted)",
            )
        return {"status": "ran", "tool": "gitleaks", "exit": proc.returncode,
                "count": len(results)}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return _blocked(f"gitleaks run failed: {exc}", cmd_hint)
    finally:
        try:
            os.unlink(report_path)
        except OSError:
            pass


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--run"]
    do_run = "--run" in argv
    if len(args) != 1:
        print("usage: scan_orchestrate.py <target-dir> [--run]", file=sys.stderr)
        return 2
    root = resolve_target(args[0])
    env = Envelope(probe="scan_orchestrate", target=str(root))

    secrets = run_gitleaks(str(root), env) if do_run else _blocked(
        "not run (safe default); run inside containment doctrine",
        f"gitleaks detect --no-git --redact --source {root}")
    env.data = {
        "secrets": secrets,
        "dependencies_cve": _blocked(
            "trivy orchestration not wired in v0.2",
            f"trivy fs --scanners vuln {root}"),
        "taint_sink": _blocked(
            "semgrep orchestration not wired in v0.2",
            f"semgrep --config auto --error {root}"),
    }
    # If nothing actually ran, this probe reviewed nothing itself.
    if secrets.get("status") != "ran":
        env.coverage_pct = 0.0
    env.emit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
