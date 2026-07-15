# Audit Protocol

## Contents

- Evidence and scope
- Forensic expansion gate
- Claim-evidence ledger
- Contract and receipt review
- Failure matrix
- Verification and quality gates

## Evidence And Scope

Use the primary evidence appropriate to the claim. Authoritative contracts define expected behavior; runtime probes establish observed behavior; producer-to-consumer traces establish internal flow. None substitutes for the others when a claim needs all three.

Default to read-only. Never use production as a test environment, mutate live configuration/state, send external messages, trade, restart a service, or call a destructive API merely to prove a finding. Use temporary fixtures, fakes, monkeypatches, sandboxes, testnets, or isolated database copies.

State the evidence ceiling: source-only, controlled fixture, sandbox/testnet, or production observation. Do not imply a higher level.

## Forensic Expansion Gate

Classify the target before collecting findings:

| Class | Observable predicate | Minimum audit shape |
|---|---|---|
| `small` | Narrow component, one side-effect domain, and less than 1,000 files and 1 GB. | Targeted trace plus claim ledger. |
| `medium` | Multiple components or one meaningful runtime/data boundary. | Targeted traces plus an asset summary and negative-space review. |
| `large` | More than 1,000 files or 1 GB; mixed source/runtime/data/media/vendor/credential assets; multiple material side-effect domains; or a user-requested whole-system/forensic review. | Complete the required forensic coverage checklist before drafting findings. |

For a `large` target, build a coverage manifest first. Classify each top-level area as one or more of: source/configuration, dependency/vendor, mutable runtime state, durable data, credentials/authentication, media/model/reference corpus, backup/archive, or unknown. Record file count and disk footprint where practical. A raw total is not a census.

### Required Forensic Coverage Checklist

Complete each applicable layer, or record it as blocked with the smallest safe resolving probe:

1. **File census:** top-level footprint, file counts, largest artifacts, file classes, executable files, and symlinks crossing the target boundary.
2. **Git and change control:** repository integrity, branch/remotes, tracked versus untracked material, dirty-state classification, ignored-secret rules, and history exposure for confirmed credentials.
3. **Runtime and configuration drift:** live process/service observation; source-of-truth configuration location; duplicate, stale, missing, or shadow copies; scheduler and launch references where relevant.
4. **Dependency and test surface:** lockfiles/manifests, local environments/vendor boundaries, test inventory, syntax/static checks that do not mutate state, and untested high-consequence areas.
5. **Credential and access surface:** tracked secrets, ignored secrets, permissions, browser/profile stores, TLS bypasses, and backup/archive inclusion. Never print secret values.
6. **Side-effect traces:** for each material write domain, trace trigger through validation, intent, submission, durable commit, readback, recovery, and alerting.
7. **Negative-space checks:** falsify plausible alternatives, including intentional exclusions, expected child processes, stale artifacts, and false-positive secret matches.

Do not substitute a generic scan result, a process exit, or a small list of sampled files for a completed layer. Mark a layer `unreviewed`, `blocked`, or `not-applicable` rather than silently omitting it.

### Pre-Draft Stop

Before writing findings for a `large` target, verify all three conditions:

1. The coverage manifest names every material asset class and says what was not reviewed.
2. The claim-evidence ledger has at least one direct reference for every proposed finding.
3. The report plan contains the required large-target sections.

If any condition fails, continue evidence collection or report the blocked layer. Do not publish an executive summary as the final audit report.

## Claim-Evidence Ledger

For every material claim, record:

| Field | Required content |
|---|---|
| Claim ID | Stable identifier linked to one finding. |
| Evidence label | `verified-live`, `verified-source`, `verified-external`, `inference`, `no-proven-edge`, or `not-a-finding`. |
| Expected behavior | Contract, policy, or specification. |
| Observed behavior | Probe result or source trace. |
| Reference | Command/probe, file line, log/event, timestamp, and source hash/version when useful. |
| Counterexample | Trigger and current guard outcome. |
| Confidence | What remains unverified and the smallest safe resolving probe. |

Do not promote a ledger row to a finding without a direct reference.

## Contract And Receipt Review

Trace each material side effect through trigger, validation, intent/receipt, payload, acknowledgement, durable commit, readback, exit/reporting, recovery, and alerting.

Use these terminal semantics when relevant:

| State | Meaning | Retry rule |
|---|---|---|
| `planned` | Validated but not submitted. | Retry is safe with the same identity. |
| `submitted` | Request left the process; outcome is not known. | Query the consumer before resend. |
| `accepted` | Consumer acknowledged request; target state remains unproven. | Poll/read back only. |
| `verified` | Readback or durable commit proves target state. | Terminal. |
| `partial` | A subset completed or evidence is incomplete. | Resume by item identity. |
| `unknown` | Timeout/death after submit. | Never blind-retry external, financial, or durable writes. |
| `recovery-incomplete` | Lookup/recovery budget exhausted. | Terminal non-green; alert and preserve evidence. |
| `rejected` | Policy, validation, or consumer reject has evidence. | New request only after relevant change. |

Require request identity, idempotency key when supported, input hash, contract version, terminal state, and evidence reference for material writes.

## Failure Matrix

For each pair of material findings, classify one of:

- `direct-edge`: caller, scheduler, queue, API, process, file, or database path was traced.
- `shared-state`: both paths touch the same durable authority.
- `shared-control`: a common control can mitigate both, but there is no causal flow.
- `overlap`: same root-cause class; do not double-count severity.
- `no-proven-edge`: no direct runtime or durable-state relationship was found.

Only direct-edge and shared-state rows may claim a concrete cross-process blast radius. Mark all other scenarios as inference.

## Verification And Quality Gates

Design fault tests with a test ID, fixture, injection point, invariant, expected terminal state, cleanup, and exit criterion. Positive-only tests are insufficient. Include timeout-after-submit, process death, malformed-but-accepted input, concurrent writers, stale readers, duplicate delivery, and authorization drift when applicable.

Before reporting 9/10 quality, pass or explicitly block with a named safe probe every gate below:

1. Scope and coverage manifest.
2. Claim-evidence ledger.
3. Evidence freshness and source snapshot.
4. Contract trace for each material side effect.
5. Failure-matrix edge verification.
6. Negative-space/rejected-hypothesis review.
7. Test or chaos design with explicit invariants.
8. Verifier pass from the ledger.
9. Allowed-change scope verification.

10/10 is possible only within a user-defined acceptance envelope and requires implemented fault-injection tests plus an independent verifier pass. Do not assign it from prompt quality alone.
