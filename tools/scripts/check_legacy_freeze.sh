#!/usr/bin/env bash
set -euo pipefail

matches="$(
  rg -n \
    --glob '*.py' \
    --glob '*.sh' \
    --glob '!tools/scripts/check_legacy_freeze.sh' \
    'legacy[-_]family|legacy-family/' \
    apps packages tests tools || true
)"
if [[ -n "${matches}" ]]; then
  echo "legacy freeze violated"
  echo "${matches}"
  exit 1
fi
echo "legacy freeze ok"
