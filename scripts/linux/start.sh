#!/usr/bin/env bash
# SecFlow AI — Linux start
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

[ -f .env ] || { echo "缺少 .env —— 先执行 ./scripts/linux/install.sh"; exit 1; }

docker network inspect secflow-net >/dev/null 2>&1 || docker network create secflow-net
docker compose up -d --build

echo "[SecFlow] 已启动:"
echo "  Frontend : http://localhost"
echo "  API      : http://localhost:${API_PORT:-8000}/docs"
docker compose ps
