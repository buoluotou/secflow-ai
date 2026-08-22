#!/usr/bin/env bash
# =====================================================================
# SecFlow AI — MISP deployment (spec §13)
# Clones the OFFICIAL misp-docker repo (never vendored), prepares .env
# from template and starts the stack via docker compose.
#
# Usage: ./deploy/misp/deploy.sh
# Requires: Docker Engine 25+, Docker Compose plugin 2.17+
# =====================================================================
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${DEPLOY_DIR}/misp-docker"

echo "[SecFlow] >>> Deploying MISP (official misp-docker)"

# 0. Prerequisites
docker version --format '{{.Server.Version}}' >/dev/null || { echo "Docker Engine required"; exit 1; }
docker compose version >/dev/null || { echo "Docker Compose plugin v2.17+ required"; exit 1; }

# 1. Clone official repo
if [ ! -d "${TARGET_DIR}" ]; then
  git clone https://github.com/MISP/misp-docker.git "${TARGET_DIR}"
fi
cd "${TARGET_DIR}"

# 2. Prepare .env from official template (never overwrite existing)
if [ ! -f .env ]; then
  cp template.env .env
  echo "[SecFlow] 已生成 misp-docker/.env —— 请编辑并设置:"
  echo "  MISP_ADMIN_EMAIL / MISP_ADMIN_PASSWD / MISP_BASEURL / MISP_FQDN"
  echo "  然后重新执行本脚本"
  exit 0
fi

# 3. Pull & start
docker compose pull
docker compose up -d

echo
echo "[SecFlow] MISP stack started:"
echo "  docker compose ps          # misp-core / misp-modules / db / redis"
echo "  Web: https://localhost (立即修改默认密码)"
echo "  创建 API Key: Administration → Users → Auth Keys → 生成后填入 .env 的 MISP_API_KEY"
