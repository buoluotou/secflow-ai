#!/usr/bin/env bash
# =====================================================================
# SecFlow AI — 一键部署 Wazuh + MISP（安服·开箱即用）
#
# 自动完成：内核参数 → 克隆官方指定版本仓库 → 生成证书/配置 → 启动 →
#           把连接信息写入 .env（系统自动接入）
#
#   ./scripts/deploy-wazuh-misp.sh          # 部署 Wazuh + MISP
#   ./scripts/deploy-wazuh-misp.sh wazuh    # 只部署 Wazuh
#   ./scripts/deploy-wazuh-misp.sh misp     # 只部署 MISP
#
# 要求：Docker 25+ / Compose 2.17+ / 建议 16GB+ 内存（Wazuh 官方基线 8GB）
# =====================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"
[ -f .env ] || { echo "缺少 .env —— 先运行 ./scripts/setup.sh"; exit 1; }

TARGET="${1:-all}"
say()  { printf '\033[1;36m[SecFlow]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[SecFlow!]\033[0m %s\n' "$*"; }

# ---------------------------------------------------------------------
# 内核参数（Wazuh 要求 vm.max_map_count=262144，规格 §7）
# ---------------------------------------------------------------------
ensure_kernel() {
  if [ "$(sysctl -n vm.max_map_count 2>/dev/null || echo 0)" -lt 262144 ]; then
    say "设置 vm.max_map_count=262144 ..."
    sudo sysctl -w vm.max_map_count=262144
    echo "vm.max_map_count=262144" | sudo tee /etc/sysctl.d/99-wazuh.conf >/dev/null
  fi
}

# ---------------------------------------------------------------------
# Wazuh（官方 wazuh-docker @ v4.14.7，single-node）
# ---------------------------------------------------------------------
deploy_wazuh() {
  say ">>> 部署 Wazuh (v4.14.7 single-node)..."
  ensure_kernel
  ./deploy/wazuh/deploy.sh

  # 读取默认凭据（官方模板默认 admin/SecretPassword；用户可改）
  WAZUH_PASS="${WAZUH_PASSWORD:-SecretPassword}"
  grep -q "^WAZUH_URL=" .env || cat >> .env <<ENV

# --- Wazuh（由 deploy-wazuh-misp.sh 自动写入）---
WAZUH_URL=https://localhost:55000
WAZUH_USERNAME=admin
WAZUH_PASSWORD=${WAZUH_PASS}
WAZUH_VERIFY_SSL=false
ENV
  say "Wazuh 已部署，连接信息已写入 .env。"
  warn "请修改 WAZUH_PASSWORD 为实际部署密码（deploy/wazuh/wazuh-docker/single-node/.env 中设置）"
  warn "并在 Wazuh 中为 SecFlow 创建专用 API 用户（Management → Security → Users）"
}

# ---------------------------------------------------------------------
# MISP（官方 misp-docker）
# ---------------------------------------------------------------------
deploy_misp() {
  say ">>> 部署 MISP (官方 misp-docker)..."
  ./deploy/misp/deploy.sh

  grep -q "^MISP_URL=" .env || cat >> .env <<'ENV'

# --- MISP（由 deploy-wazuh-misp.sh 自动写入；API Key 需在 MISP 后台创建）---
MISP_URL=https://localhost
MISP_API_KEY=REPLACE_WITH_MISP_AUTH_KEY
MISP_VERIFY_SSL=false
ENV
  say "MISP 已部署。请在 MISP 后台 Administration → Users → Auth Keys 创建 SecFlow 专用 Key，"
  say "并替换 .env 中的 MISP_API_KEY 后重启：docker compose up -d --build"
}

# ---------------------------------------------------------------------
case "$TARGET" in
  all)    deploy_wazuh; deploy_misp ;;
  wazuh)  deploy_wazuh ;;
  misp)   deploy_misp ;;
  *)      echo "用法: $0 [all|wazuh|misp]"; exit 1 ;;
esac

say "完成！重启 SecFlow 使配置生效：./scripts/linux/restart 或 docker compose up -d --build"
say "验证：curl http://localhost:8000/api/health/wazuh 与 /api/health/misp 应显示正常"
