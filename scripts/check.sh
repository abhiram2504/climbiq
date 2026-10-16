#!/usr/bin/env bash
set -euo pipefail

climbiq_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
climbiq_python="${CLIMBIQ_PYTHON:-}"

if [[ -z "$climbiq_python" && -x "$climbiq_root/backend/.venv/bin/python" ]]; then
  climbiq_python="$climbiq_root/backend/.venv/bin/python"
elif [[ -z "$climbiq_python" ]]; then
  climbiq_python="$(command -v python3)"
fi

(cd "$climbiq_root/backend" && "$climbiq_python" -m pytest && "$climbiq_python" -m ruff check .)
(cd "$climbiq_root/frontend" && npm run test && npm run typecheck && npm run build)
