#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

uv run pytest -q
uv run ruff check .
npm install
npm run typecheck
npm run test:ts
./scripts/scan_secrets.sh
