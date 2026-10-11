#!/usr/bin/env bash
set -euo pipefail

(cd backend && python -m pytest && ruff check .)
(cd frontend && npm run test && npm run typecheck && npm run build)
