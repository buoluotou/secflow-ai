#!/usr/bin/env bash
# SecFlow AI — Linux update (spec §58)
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

echo "[SecFlow] 拉取最新代码并重建镜像..."
git pull --ff-only || { echo "本地有未提交修改，请先处理"; exit 1; }
docker compose pull || true
docker compose up -d --build
echo "[SecFlow] 更新完成"
