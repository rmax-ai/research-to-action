#!/usr/bin/env bash
set -euo pipefail

# High-precision patterns only: synthetic fixture values such as "token-demo-001"
# are intentionally not treated as secrets.
files=$(git ls-files)
if [[ -z "$files" ]]; then
  exit 0
fi
if printf '%s\n' "$files" | xargs -r grep -nE \
  -e '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----' \
  -e '(^|[^A-Za-z0-9])(AKIA|ASIA)[A-Z0-9]{16}([^A-Za-z0-9]|$)' \
  -e '(^|[^A-Za-z0-9])gh[pousr]_[A-Za-z0-9_]{30,}([^A-Za-z0-9]|$)' \
  -e '(^|[^A-Za-z0-9])sk-[A-Za-z0-9]{30,}([^A-Za-z0-9]|$)' \
  -e '(^|[^A-Za-z0-9])xox[baprs]-[0-9A-Za-z-]{20,}([^A-Za-z0-9]|$)' \
  -e '(^|[^A-Za-z0-9])AIza[0-9A-Za-z_-]{35}([^A-Za-z0-9]|$)'; then
  echo "Potential secret detected in tracked files." >&2
  exit 1
fi
echo "Secret scan passed."
