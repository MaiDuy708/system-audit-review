#!/usr/bin/env python3
"""git_state probe — read .git as DATA, never exec git (threat model T7).

Running `git` inside an attacker-controlled repository is remote code execution via
.git/config (core.fsmonitor, core.pager, core.hooksPath, alias.*, diff.external) and
.gitattributes textconv/diff drivers. This probe therefore executes git ZERO times.
It reads .git/config, HEAD, packed-refs, and refs/* as plain files and REPORTS
dangerous configuration as findings.

For history-level facts that genuinely need git, this probe records a `blocked` layer
with the safe resolving command (run only inside the containment doctrine's disposable
environment), rather than exec-ing git here.

Usage: git_state.py <target-dir>
"""

from __future__ import annotations

import configparser
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import Envelope, read_text_bounded, resolve_target, within  # noqa: E402

# Config keys that can cause code execution when git runs. Detecting these in a
# target's .git/config is a finding regardless of value.
DANGEROUS_KEYS = {
    "core.fsmonitor",
    "core.pager",
    "core.editor",
    "core.hookspath",
    "core.sshcommand",
    "diff.external",
    "filter",  # filter.*.clean / .smudge
    "alias",   # alias.* can shell out
}


def scan_config(text: str, env: Envelope, rel: str) -> dict:
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    summary: dict = {"sections": [], "dangerous": []}
    try:
        parser.read_string(text)
    except configparser.Error as exc:
        env.errors.append(f"unparseable .git/config: {exc}")
        return summary
    for section in parser.sections():
        summary["sections"].append(section)
        sec_lower = section.lower().split()[0]  # e.g. 'filter "x"' -> 'filter'
        for key in parser[section]:
            full = f"{sec_lower}.{key.lower()}"
            hit = full in DANGEROUS_KEYS or sec_lower in {"alias", "filter"}
            if hit:
                summary["dangerous"].append(full)
                env.add_finding(
                    f"unsafe-git-config-{len(env.findings)+1}",
                    "unsafe-git-config",
                    "critical",
                    rel,
                    f"exec-capable git config key `{full}` present in target .git/config; "
                    "running git in this repo could execute attacker code",
                )
    return summary


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: git_state.py <target-dir>", file=sys.stderr)
        return 2
    root = resolve_target(argv[1])
    env = Envelope(probe="git_state", target=str(root))

    gitdir = root / ".git"
    if not gitdir.exists():
        env.data = {"status": "not-a-git-repository"}
        env.emit()
        return 0
    if not within(root, gitdir):
        env.add_finding("gitdir-escape-1", "boundary-escape", "high", ".git",
                        ".git resolves outside the target; not read")
        env.emit()
        return 0

    data: dict = {"is_git": True}

    head = read_text_bounded(gitdir / "HEAD")
    if head:
        data["head"] = head.strip()

    cfg = read_text_bounded(gitdir / "config")
    if cfg is not None:
        data["config"] = scan_config(cfg, env, ".git/config")

    packed = read_text_bounded(gitdir / "packed-refs")
    refs = []
    if packed:
        for line in packed.splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "^")):
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    refs.append(parts[1])
    refs_dir = gitdir / "refs"
    if refs_dir.is_dir():
        for dp, _, files in os.walk(refs_dir):
            for f in files:
                refs.append(os.path.relpath(os.path.join(dp, f), gitdir))
    data["refs"] = sorted(set(refs))[:200]

    # History-level facts need git; do not exec it here — record as blocked.
    data["history"] = {
        "status": "blocked",
        "reason": "history inspection requires executing git, which is unsafe in an "
                  "untrusted repository outside the containment doctrine",
        "resolving_command": "run inside a disposable, network-denied sandbox: "
                             "GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null "
                             "git -c core.fsmonitor= -c core.hooksPath=/dev/null log --oneline",
    }
    env.data = data
    env.emit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
