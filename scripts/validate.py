#!/usr/bin/env python3
"""Validate portable skill metadata and publish artefacts without dependencies."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
FORBIDDEN_NAMES = {".DS_Store"}
# Directories excluded from the secret/forbidden scan: .git internals (compressed,
# not our content) and tests/fixtures (intentional adversarial material the verifier
# self-test depends on — a real secret literal there is by design).
SCAN_SKIP_PARTS = {".git", "fixtures"}
REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "assets/evidence-flightpath.svg",
    "scripts/install.sh",
    "scripts/package.sh",
    "references/audit-protocol.md",
    "references/audit-contract.md",
    "scripts/audit_gate.py",
    "scripts/probes/census.py",
    "scripts/probes/git_state.py",
    "scripts/probes/scan_orchestrate.py",
)
SECRET_PATTERNS = (
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def frontmatter_value(text: str, key: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        fail("SKILL.md has no YAML frontmatter")
    value = re.search(rf"^{key}:\s*(.+)$", match.group(1), re.MULTILINE)
    if not value:
        fail(f"SKILL.md frontmatter is missing {key}")
    return value.group(1).strip().strip('"')


def main() -> None:
    for relative_path in REQUIRED_FILES:
        if not (ROOT / relative_path).is_file():
            fail(f"required publish artefact missing: {relative_path}")

    skill_text = SKILL.read_text(encoding="utf-8")
    name = frontmatter_value(skill_text, "name")
    description = frontmatter_value(skill_text, "description")
    if name != ROOT.name:
        fail(f"skill name {name!r} must match directory {ROOT.name!r}")
    if not description.startswith("Use when "):
        fail("skill description must start with 'Use when '")

    plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    marketplace = json.loads(
        (ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
    )
    entry = marketplace["plugins"][0]
    if {name, plugin["name"], entry["name"]} != {name}:
        fail("skill, plugin, and marketplace names must match")
    if plugin["version"] != entry["version"]:
        fail("plugin and marketplace versions must match")

    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    for source_name, source_text in (("SKILL.md", skill_text), ("README.md", readme_text)):
        for link in re.findall(r"\[[^]]+\]\(([^)]+)\)", source_text):
            target = link.split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (ROOT / target).exists():
                fail(f"broken {source_name} reference: {link}")

    for path in ROOT.rglob("*"):
        if any(part in SCAN_SKIP_PARTS for part in path.parts):
            continue
        if path.is_file() and path.name in FORBIDDEN_NAMES:
            fail(f"forbidden publish artefact: {path.relative_to(ROOT)}")
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                fail(f"secret-like material found in {path.relative_to(ROOT)}")

    selftest = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_gate.py"), "--selftest"],
        capture_output=True, text=True)
    if selftest.returncode != 0:
        fail(f"audit_gate self-test failed:\n{selftest.stdout}{selftest.stderr}")

    print(f"OK: {name} {plugin['version']} (gate self-test passed)")


if __name__ == "__main__":
    main()
