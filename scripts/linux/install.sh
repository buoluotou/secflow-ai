#!/usr/bin/env bash
# =====================================================================
# SecFlow AI — Linux install (spec §6, §58)
#   ./scripts/linux/install.sh
#
# 宿主机准备: Docker Engine + Compose + 内核参数 + 网络 + Wazuh/MISP
# =====================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

echo "[SecFlow] >>> Linux 安装脚本"

# 1. 系统依赖 (spec §6)
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git curl jq

# 2. 启动 Docker
sudo systemctl enable --now docker

# 3. 当前用户加入 docker 组
sudo usermod -aG docker "$USER" || true

# 4. 内核参数 (spec §7)
if [ "$(sysctl -n vm.max_map_count 2>/dev/null || echo 0)" -lt 262144 ]; then
  sudo sysctl -w vm.max_map_count=262144
  echo "vm.max_map_count=262144" | sudo tee /etc/sysctl.d/99-wazuh.conf >/dev/null
  sudo sysctl --system >/dev/null
fi

# 5. 验证
docker --version
docker compose version

# 6. Docker 网络 (spec §10)
docker network inspect secflow-net >/dev/null 2>&1 || docker network create secflow-net

# 7. 环境文件
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[SecFlow] 已生成 .env —— 请修改 POSTGRES_PASSWORD / SECRET_KEY 等敏感项后再启动"
fi

echo
echo "[SecFlow] 安装完成。接下来:"
echo "  1) 编辑 .env（密码、WAZUH/MISP/LLM 配置）"
echo "  2) ./scripts/linux/start.sh"
echo "  3) 可选: ./deploy/wazuh/deploy.sh && ./deploy/misp/deploy.sh"
echo
echo "注意: 重新登录或执行 'newgrp docker' 使 docker 组生效"
