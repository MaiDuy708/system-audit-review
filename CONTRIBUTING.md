# Contributing

Contributions must improve audit truthfulness, coverage, safety, or portability. Do not add generic checklists, speculative controls, host-specific assumptions to the canonical workflow, or dependencies without a demonstrated need.

## Change Standard

Every behavior change must include:

1. The failure mode or observed gap it addresses.
2. The exact skill section changed and why a narrower change is insufficient.
3. A deterministic validation case or supported-agent installation check.
4. An update to the version when the plugin behavior changes.

Run the repository validator before opening a pull request:

```bash
python3 scripts/validate.py
```

Keep agent-facing instructions in English. Preserve the default read-only boundary unless the change is explicitly about a user-authorized mutation workflow.
