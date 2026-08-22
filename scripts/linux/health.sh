#!/usr/bin/env bash
# SecFlow AI — Linux health check
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

echo "[SecFlow] 组件状态:"
docker compose ps --format "table {{.Name}}\t{{.Status}}"

echo
echo "[SecFlow] API 健康检查:"
curl -sf http://localhost:${API_PORT:-8000}/api/health && echo
for ep in db redis wazuh misp llm; do
  printf "  /api/health/%s: " "$ep"
  curl -sf "http://localhost:${API_PORT:-8000}/api/health/${ep}" || echo "unavailable"
  echo
done

echo
echo "[SecFlow] 前端:"
curl -sI http://localhost:${FRONTEND_PORT:-80} | head -1
