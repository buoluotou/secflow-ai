#!/usr/bin/env bash
# =====================================================================
# SecFlow AI — Wazuh deployment (spec §11)
# Clones the OFFICIAL wazuh-docker repo pinned to v4.14.7 (never vendored),
# generates indexer certificates and starts the single-node stack.
#
# Usage: ./deploy/wazuh/deploy.sh
# =====================================================================
set -euo pipefail

WAZUH_VERSION="${WAZUH_VERSION:-v4.14.7}"
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${DEPLOY_DIR}/wazuh-docker"

echo "[SecFlow] >>> Deploying Wazuh ${WAZUH_VERSION} (single-node)"

# 0. Kernel requirement (spec §7)
if [ "$(sysctl -n vm.max_map_count 2>/dev/null || echo 0)" -lt 262144 ]; then
  echo "[SecFlow] Setting vm.max_map_count=262144 ..."
  sudo sysctl -w vm.max_map_count=262144
  echo "vm.max_map_count=262144" | sudo tee /etc/sysctl.d/99-wazuh.conf >/dev/null
  sudo sysctl --system >/dev/null
fi

# 1. Clone pinned official repo (idempotent)
if [ ! -d "${TARGET_DIR}" ]; then
  git clone https://github.com/wazuh/wazuh-docker.git "${TARGET_DIR}"
fi
cd "${TARGET_DIR}"
git checkout "${WAZUH_VERSION}" 2>/dev/null || git fetch --tags && git checkout "${WAZUH_VERSION}"
cd single-node

# 2. Generate certificates (idempotent — skip if already generated)
if [ ! -f config/certs/root-ca.pem ]; then
  docker compose -f generate-indexer-certs.yml run --rm generator
fi

# 3. Start
docker compose up -d

echo
echo "[SecFlow] Wazuh stack started. First boot takes a few minutes:"
echo "  docker compose ps                  # wazuh.manager / wazuh.indexer / wazuh.dashboard"
echo "  Dashboard: https://<host>  (admin credentials from .env / WAZUH_USERNAME, WAZUH_PASSWORD)"
echo "  API: https://<host>:55000  (secflow 通过 WAZUH_URL 接入)"
echo
echo "[SecFlow] 下一步: 在 .env 中设置 WAZUH_URL / WAZUH_USERNAME / WAZUH_PASSWORD"
