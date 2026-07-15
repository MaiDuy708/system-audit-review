#!/usr/bin/env python3
"""Validate portable skill metadata and publish artefacts without dependencies."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
FORBIDDEN_NAMES = {".DS_Store"}
REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "assets/evidence-flightpath.svg",
    "scripts/install.sh",
    "scripts/package.sh",
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

    for link in re.findall(r"\[[^]]+\]\(([^)]+)\)", skill_text):
        if not link.startswith(("http://", "https://")) and not (ROOT / link).is_file():
            fail(f"broken SKILL.md reference: {link}")

    for path in ROOT.rglob("*"):
        if path.is_file() and path.name in FORBIDDEN_NAMES:
            fail(f"forbidden publish artefact: {path.relative_to(ROOT)}")
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                fail(f"secret-like material found in {path.relative_to(ROOT)}")

    print(f"OK: {name} {plugin['version']}")


if __name__ == "__main__":
    main()
