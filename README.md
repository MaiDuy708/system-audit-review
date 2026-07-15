# System Audit Review

> **MAIDUY** | Evidence before conclusions.

`system-audit-review` is a portable, read-only skill for evidence-led audits of systems, repositories, services, configurations, data pipelines, security boundaries, and operational workflows.

Maintained by [MaiDuy708](https://github.com/MaiDuy708).

## Publisher Mark

**MAIDUY** is the publisher mark for authoritative releases of this repository. It identifies the maintained distribution without claiming registered trademark status. Forks and derivative distributions should use a distinct name and state their relationship to this repository.

## Install

```bash
# Codex
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo MaiDuy708/system-audit-review --path .

# OpenClaw
openclaw skills install git:MaiDuy708/system-audit-review

# Gemini CLI
gemini skills install https://github.com/MaiDuy708/system-audit-review

# Claude Code
claude plugin marketplace add MaiDuy708/system-audit-review
claude plugin install system-audit-review@maiduy-system-audit-review
```

Inspect skills before installing them. They can influence agent behavior and access local tools and files.
