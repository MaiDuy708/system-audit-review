#!/usr/bin/env python3
"""audit_gate.py — verify an AUDIT-REPORT.md against the audit contract.

The report is treated as UNTRUSTED input (threat model T8): it is agent-authored and
the agent may have been influenced by target content. Parsing is structural (heading /
field based), never trusting substring coincidence, and the gate ships inverse-tests
(a spoofed report must FAIL).

Enforces references/audit-contract.md §7. Dependency-free.

Usage:
  audit_gate.py <report.md> --tier {small,medium,large} [--probes DIR] [--target DIR]
  audit_gate.py --selftest
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

VERSION = "0.2.0"

REQUIRED_SECTIONS = {
    "small": ["1. Scope", "7. Findings", "8. Claim-evidence ledger", "15. Evidence snapshot"],
    "medium": ["0. TL;DR", "1. Scope", "3. Asset census", "4. Coverage manifest",
               "6. NEEDS HUMAN/ADVISOR", "7. Findings", "8. Claim-evidence ledger",
               "15. Evidence snapshot"],
    "large": ["0. TL;DR", "1. Scope", "2. Classification", "3. Asset census",
              "4. Coverage manifest", "5. Checks run", "6. NEEDS HUMAN/ADVISOR",
              "7. Findings", "8. Claim-evidence ledger", "9. Failure matrix",
              "10. Contracts and receipt states", "11. Strengths and rejected hypotheses",
              "12. Remediation roadmap", "13. Verifier results",
              "14. Open blockers and unreviewed material", "15. Evidence snapshot"],
}

FINDING_FIELDS = ["Severity", "Explanation", "Reasoning", "Evidence", "Verification",
                  "Failure scenario", "Remediation", "Residual confidence"]

EVIDENCE_LABELS = {"verified-live", "verified-source", "verified-external",
                   "inference", "no-proven-edge", "not-a-finding"}

HEDGE = ["có vẻ", "có thể", "hình như", "dường như", "seems", "might be", "possibly",
         "probably", "appears to", "may be"]

# Heuristic secret shapes (documented limit: not a full secret scanner).
SECRET_PATTERNS = [
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[posu]_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{6,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
]

# Mutate/network binaries that must never appear in "Checks run" (read-only audit).
FORBIDDEN_CMD = re.compile(
    r"\b(curl|wget|nc|ncat|ssh|scp|rm|mv|cp\s+-|chmod|chown|dd|mkfs|"
    r"git\s+push|git\s+commit|git\s+fetch|git\s+pull|npm\s+install|pip\s+install|"
    r"apt|brew\s+install|kill|systemctl|launchctl)\b")


class Report:
    """Structural parse of the report: sections and findings, fences stripped."""

    def __init__(self, text: str):
        self.raw = text
        self.fences = self._extract_fences(text)          # list[(info, body)]
        self.defenced = self._strip_fences(text)
        self.sections = self._sections(self.defenced)     # heading -> body text
        self.findings = self._findings()

    @staticmethod
    def _extract_fences(text: str) -> list[tuple[str, str]]:
        out, info, buf, inside = [], "", [], False
        for line in text.splitlines():
            if line.lstrip().startswith("```"):
                if not inside:
                    inside, info, buf = True, line.strip()[3:].strip(), []
                else:
                    out.append((info, "\n".join(buf)))
                    inside = False
            elif inside:
                buf.append(line)
        return out

    @staticmethod
    def _strip_fences(text: str) -> str:
        out, inside = [], False
        for line in text.splitlines():
            if line.lstrip().startswith("```"):
                inside = not inside
                continue
            if not inside:
                out.append(line)
        return "\n".join(out)

    @staticmethod
    def _sections(text: str) -> dict:
        sections, current, buf = {}, None, []
        for line in text.splitlines():
            m = re.match(r"^##\s+(.*)$", line)
            if m and not line.startswith("###"):
                if current is not None:
                    sections[current] = "\n".join(buf)
                current, buf = m.group(1).strip(), []
            else:
                buf.append(line)
        if current is not None:
            sections[current] = "\n".join(buf)
        return sections

    def _findings(self) -> list[dict]:
        body = self.sections.get("7. Findings", "")
        findings, current, buf = [], None, []
        for line in body.splitlines():
            m = re.match(r"^###\s+(F\d+)\s*:\s*(.*)$", line)
            if m:
                if current:
                    current["_body"] = "\n".join(buf)
                    findings.append(current)
                current, buf = {"id": m.group(1), "title": m.group(2).strip()}, []
            elif current is not None:
                buf.append(line)
        if current:
            current["_body"] = "\n".join(buf)
            findings.append(current)
        for f in findings:
            for field in FINDING_FIELDS:
                fm = re.search(rf"^\s*-?\s*\*\*{re.escape(field)}:\*\*\s*(.*)$",
                               f["_body"], re.MULTILINE)
                f[field] = fm.group(1).strip() if fm else None
        return findings


def _fenced_secret_or_hedge_ignored(report: Report) -> str:
    """Concatenate only untrusted-quote fence bodies (ignored for hedge/secret)."""
    return "\n".join(b for info, b in report.fences if info.startswith("untrusted-quote"))


def check(report: Report, tier: str, probes_dir: str | None, target: str | None) -> list[str]:
    fails: list[str] = []

    # Gate 1 — sections present
    present = set(report.sections.keys())
    for sec in REQUIRED_SECTIONS[tier]:
        if sec not in present:
            fails.append(f"[sections] missing required section: '## {sec}'")

    # Gate 2 — finding fields
    if not report.findings and "7. Findings" in present:
        # allowed only if the report explicitly declares zero findings
        if "no findings" not in report.sections.get("7. Findings", "").lower():
            fails.append("[findings] section 7 has no findings and no explicit 'No findings' statement")
    for f in report.findings:
        for field in FINDING_FIELDS:
            if not f.get(field):
                fails.append(f"[findings] {f['id']} missing field: {field}")

    # Gate 3 — loud-flag: every inference finding must be listed in section 6
    loud = report.sections.get("6. NEEDS HUMAN/ADVISOR", "")
    for f in report.findings:
        ver = (f.get("Verification") or "").lower()
        if "inference" in ver and f["id"] not in loud:
            fails.append(f"[loud-flag] inference finding {f['id']} absent from section 6 "
                         "(NEEDS HUMAN/ADVISOR)")

    # Gate 4 — anti-vagueness inside findings (outside fences)
    for f in report.findings:
        for field in ("Explanation", "Reasoning", "Failure scenario"):
            val = f.get(field) or ""
            low = val.lower()
            for h in HEDGE:
                if h in low and not any(lbl in low for lbl in EVIDENCE_LABELS):
                    fails.append(f"[vagueness] {f['id']}.{field}: hedge '{h}' without an "
                                 "evidence-label")
                    break

    # Gate 5 — secret guard (outside fences)
    quoted = _fenced_secret_or_hedge_ignored(report)
    for pat in SECRET_PATTERNS:
        for m in pat.finditer(report.defenced):
            if m.group(0) not in quoted:
                fails.append(f"[secret] secret-shaped literal in report body "
                             f"(pattern {pat.pattern[:24]}...)")
                break

    # Gate 6 — reference existence + probe linkage
    manifest = set()
    if probes_dir and os.path.isdir(probes_dir):
        for p in Path(probes_dir).glob("*.json"):
            try:
                manifest.add(json.loads(p.read_text(encoding="utf-8")).get("probe"))
            except (OSError, json.JSONDecodeError):
                continue
    for f in report.findings:
        ev = f.get("Evidence") or ""
        pm = re.search(r"probe:\s*([A-Za-z0-9_\-]+)", ev)
        if pm:
            # Only enforce when a --probes dir was provided. Provided-but-empty must
            # fail (findings cite probes that did not run), so gate on probes_dir,
            # not on the manifest being non-empty.
            if probes_dir is not None and pm.group(1) not in manifest:
                fails.append(f"[reference] {f['id']} cites probe '{pm.group(1)}' not in "
                             "the probe manifest")
        path_m = re.search(r"([\w./\-]+):(\d+|\?)", ev)
        if target and path_m and not path_m.group(1).startswith(("http", "sha256")):
            cand = os.path.join(target, path_m.group(1))
            if "/" in path_m.group(1) or "." in path_m.group(1):
                if not os.path.exists(cand) and not os.path.exists(path_m.group(1)):
                    fails.append(f"[reference] {f['id']} path '{path_m.group(1)}' does not exist")

    # Gate 7 — command scope in 'Checks run'
    checks = report.sections.get("5. Checks run", "")
    for info, body in report.fences:
        # commands are usually fenced; scan fenced command blocks that are not quotes
        if info.startswith("untrusted-quote"):
            continue
        if body in checks or (checks and any(l in checks for l in body.splitlines()[:1])):
            for m in FORBIDDEN_CMD.finditer(body):
                fails.append(f"[command-scope] forbidden command in Checks run: '{m.group(0)}'")
    for m in FORBIDDEN_CMD.finditer(checks):
        fails.append(f"[command-scope] forbidden command in Checks run: '{m.group(0)}'")

    return fails


def verify_file(report_path: str, tier: str, probes_dir: str | None,
                target: str | None) -> tuple[bool, list[str]]:
    text = Path(report_path).read_text(encoding="utf-8", errors="ignore")
    report = Report(text)
    fails = check(report, tier, probes_dir, target)
    return (not fails), fails


def selftest() -> int:
    here = Path(__file__).resolve().parent.parent
    fixtures = here / "tests" / "fixtures"
    expect = {
        "good_report.md": True,
        "missing_section.md": False,
        "inference_not_flagged.md": False,
        "secret_leak.md": False,
        "vague_finding.md": False,
        "missing_field.md": False,
    }
    ok = True
    for name, should_pass in expect.items():
        fp = fixtures / name
        if not fp.exists():
            print(f"SELFTEST ERROR: fixture missing: {name}")
            ok = False
            continue
        passed, fails = verify_file(str(fp), "large", None, None)
        status = "OK" if passed == should_pass else "MISMATCH"
        if passed != should_pass:
            ok = False
        print(f"[{status}] {name}: expected {'PASS' if should_pass else 'FAIL'}, "
              f"got {'PASS' if passed else 'FAIL'}"
              + ("" if passed else f" ({len(fails)} issues)"))
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2

    def opt(name: str, default=None):
        if name in argv:
            i = argv.index(name)
            if i + 1 < len(argv):
                return argv[i + 1]
        return default

    tier = opt("--tier", "large")
    if tier not in REQUIRED_SECTIONS:
        print(f"ERROR: --tier must be one of {list(REQUIRED_SECTIONS)}", file=sys.stderr)
        return 2
    passed, fails = verify_file(args[0], tier, opt("--probes"), opt("--target"))
    if passed:
        print(f"AUDIT GATE: PASS ({tier})")
        return 0
    print(f"AUDIT GATE: FAIL ({tier}) — {len(fails)} issue(s):")
    for f in fails:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
