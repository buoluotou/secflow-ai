#!/usr/bin/env bash
# SecFlow AI — Linux stop
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

docker compose down
echo "[SecFlow] 已停止（数据卷保留）"
