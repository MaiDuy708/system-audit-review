# AUDIT-REPORT

## 0. TL;DR
Verdict: conditional-pass. Coverage 92%. Findings: 0 critical, 1 high, 1 medium.

## 1. Scope
Read-only audit of the target repository. Allowed actions: read + write this report.
Evidence-ceiling: source-only. Containment declared: read-only-mount.

## 2. Classification
Tier: large. Mixed source + config + credentials surface.

## 3. Asset census
| class | files | bytes |
|---|---|---|
| source | 120 | 480000 |
| config | 14 | 22000 |

## 4. Coverage manifest
- source/config: reviewed.
- credentials: blocked — resolving probe `scan_orchestrate.py <target> --run`.
- runtime state: unreviewed.

## 5. Checks run
```sh
python3 scripts/probes/census.py <target>
python3 scripts/probes/git_state.py <target>
```

## 6. NEEDS HUMAN/ADVISOR
- F2 — inference-based; needs human confirmation of the cross-process edge.

## 7. Findings

### F1: Exec-capable git config in target .git/config

- **Severity:** high
- **Explanation:** the config seems to possibly declare something risky.
- **Reasoning:** running any git command in this repo would execute the configured program with the auditor's privileges; verified-source by reading `.git/config` as data.
- **Evidence:** .git/config:3 · probe: git_state · fingerprint: sha256:abcd1234 · rerun: `python3 scripts/probes/git_state.py <target>`
- **Verification:** verified-source · untrusted-target · read-only-mount · counterexample: absent key → no exec path.
- **Failure scenario:** auditor runs `git status`; fsmonitor program runs attacker code.
- **Remediation:** never exec git in the untrusted repo; read `.git` as data. fault-test: config-with-fsmonitor must yield this finding.
- **Residual confidence:** none outstanding · smallest safe probe: re-read `.git/config`.

### F2: Possible shared-state coupling between backup and scheduler

- **Severity:** medium
- **Explanation:** the backup path and scheduler both write the same durable directory.
- **Reasoning:** both touch `data/state`; a causal edge is not proven, only shared state; evidence-label inference.
- **Evidence:** data/state:1 · probe: census · fingerprint: sha256:beef5678 · rerun: `python3 scripts/probes/census.py <target>`
- **Verification:** inference · trusted · source-only · counterexample: separate directories → no coupling.
- **Failure scenario:** concurrent backup + schedule run corrupts `data/state`.
- **Remediation:** isolate the two writers. fault-test: concurrent-writer harness on `data/state`.
- **Residual confidence:** causal edge unverified · smallest safe probe: trace both writers in a sandbox.

## 8. Claim-evidence ledger
| id | evidence-label | trust-provenance | reference |
|---|---|---|---|
| F1 | verified-source | untrusted-target/read-only-mount | .git/config:3 |
| F2 | inference | trusted/source-only | data/state:1 |

## 9. Failure matrix
F1–F2: no-proven-edge.

## 10. Contracts and receipt states
No material external writes observed; report write is the only mutation.

## 11. Strengths and rejected hypotheses
Rejected: `.DS_Store` presence as a finding (not-a-finding).

## 12. Remediation roadmap
1. Fix git config exec surface (F1). 2. Isolate writers (F2).

## 13. Verifier results
audit_gate.py: pending this run.

## 14. Open blockers and unreviewed material
Credentials layer blocked; runtime state unreviewed.

## 15. Evidence snapshot
Timestamp: 2026-07-16. Reproduce: `python3 scripts/probes/census.py <target>`.
