---
name: system-audit-review
description: Use when auditing or reviewing a system, repository, service, configuration, data pipeline, security boundary, automation, or operational workflow, especially a large, mixed, risky, or forensic target.
---

# System Audit Review

Use this skill to produce decision-grade reviews rather than generic code commentary. Read [references/audit-protocol.md](references/audit-protocol.md) before starting the audit.

## Operating Boundaries

Default to read-only. Do not modify the target, runtime state, configuration, service state, external systems, or credentials unless the user explicitly authorizes those mutations. Writing the requested report is allowed.

Before collecting findings, classify the target from observable facts using the `Forensic Expansion Gate` in the protocol. Treat the audit as `large` when it exceeds 1 GB or 1,000 files, mixes source with runtime/data/credentials/backups, has multiple material side-effect domains, or is requested as a whole-system or forensic review.

For a `large` target, do not draft findings or a final report until the required forensic coverage checklist is complete or each blocked layer is recorded. An executive summary never substitutes for the coverage manifest and evidence ledger.

## Workflow

1. Lock scope, exclusions, allowed actions, evidence ceiling, language, and report destination. Use the safest default for missing material input and disclose it.
2. Inventory the target. Separate automated scan, deep traces, negative-space checks, exclusions, and unreviewed material. For `large`, complete the forensic checklist before drafting.
3. Gather evidence before conclusions. Trace each material side effect from trigger through validation, durable commit, readback, recovery, and alerting.
4. Maintain a claim-evidence ledger. A material claim without a direct reference is not a finding.
5. For multiple findings, create a sparse failure matrix. Do not infer a cascade from topical similarity.
6. Define receipt states for writes. Treat timeout-after-submit as `unknown`; never recommend blind retry for financial, external, or durable writes.
7. Propose only testable upgrades, then run an independent or deterministic verifier pass. Label self-verification and re-check references, counts, report sections, report gate, and allowed change scope.

## Required Output

Start with findings ordered by severity. For a `large` target, the report must include: target classification, asset census, coverage manifest, checks run, claim-evidence ledger, findings, failure matrix, contracts/receipt states, strengths/rejected hypotheses, roadmap/chaos tests, verifier results, open blockers, and evidence snapshot. Identify every unreviewed or blocked material layer.

For a `small` or `medium` target, include the sections that apply. Never present an executive summary as the complete forensic report for a `large` target.

Evidence labels are mandatory: `verified-live`, `verified-source`, `verified-external`, `inference`, `no-proven-edge`, and `not-a-finding`.

Never call a proposed test, a log line, a successful process exit, a function call, or an HTTP acknowledgement proof of business success without the contract-required readback. Every final audit report must end with `Advisor review: done` or `Advisor review: SKIPPED - <reason>`.
