#!/usr/bin/env bash
# Install this skill for exactly one requested agent.
set -euo pipefail

REPOSITORY="${SYSTEM_AUDIT_REVIEW_REPOSITORY:-MaiDuy708/system-audit-review}"
REF="${SYSTEM_AUDIT_REVIEW_REF:-v0.1.2}"
SKILL="system-audit-review"
MARKETPLACE="maiduy-system-audit-review"

usage() {
  cat <<'EOF'
Usage: install.sh <claude|codex|openclaw|gemini>

Environment:
  SYSTEM_AUDIT_REVIEW_REF=main|tag|branch     Source ref for Claude, Codex, and OpenClaw.
  SYSTEM_AUDIT_REVIEW_REPOSITORY=owner/repo   Override the GitHub source for a fork.
EOF
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'Required command not found: %s\n' "$1" >&2
    exit 1
  }
}

install_claude() {
  need claude
  if ! claude plugin marketplace list --json | grep -Fq "\"name\": \"${MARKETPLACE}\""; then
    claude plugin marketplace add "${REPOSITORY}@${REF}"
  fi
  claude plugin install "${SKILL}@${MARKETPLACE}"
}

install_codex() {
  need python3
  local codex_home="${CODEX_HOME:-${HOME}/.codex}"
  local installer="${codex_home}/skills/.system/skill-installer/scripts/install-skill-from-github.py"
  if [[ ! -f "${installer}" ]]; then
    printf 'Codex skill installer not found: %s\n' "${installer}" >&2
    exit 1
  fi
  python3 "${installer}" --repo "${REPOSITORY}" --path . --ref "${REF}" --name "${SKILL}"
}

install_openclaw() {
  need openclaw
  openclaw skills install "git:${REPOSITORY}@${REF}" --global --as "${SKILL}" --force
}

install_gemini() {
  need gemini
  need curl
  local archive
  archive="$(mktemp "${TMPDIR:-/tmp}/system-audit-review.XXXXXX.skill")"
  trap 'rm -f "${archive}"' RETURN
  curl -fsSL "https://github.com/${REPOSITORY}/releases/download/${REF}/${SKILL}-${REF#v}.skill" -o "${archive}"
  gemini skills install "${archive}" --scope user --consent
}

case "${1:-}" in
  claude) install_claude ;;
  codex) install_codex ;;
  openclaw) install_openclaw ;;
  gemini) install_gemini ;;
  -h|--help|help) usage ;;
  *) usage; exit 2 ;;
esac
