#!/usr/bin/env bash
# Build a self-contained .skill archive from an immutable Git ref.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REF="${1:-HEAD}"
VERSION="$(git -C "${ROOT}" show "${REF}:.claude-plugin/plugin.json" | sed -n 's/.*"version": "\([^"]*\)".*/\1/p')"

if [[ -z "${VERSION}" ]]; then
  printf 'Could not read a package version from %s.\n' "${REF}" >&2
  exit 1
fi

OUT_DIR="${ROOT}/dist"
OUT_FILE="${OUT_DIR}/system-audit-review-${VERSION}.skill"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TEMP_DIR}"' EXIT

mkdir -p "${OUT_DIR}"
git -C "${ROOT}" archive --format=tar "${REF}" | tar -x -C "${TEMP_DIR}"
rm -f "${OUT_FILE}"
(
  cd "${TEMP_DIR}"
  zip -X -q -r "${OUT_FILE}" .
)

(
  cd "${OUT_DIR}"
  shasum -a 256 "$(basename "${OUT_FILE}")" > "$(basename "${OUT_FILE}").sha256"
)

printf '%s\n' "${OUT_FILE}"
