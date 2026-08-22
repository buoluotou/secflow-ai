#!/usr/bin/env bash
# =====================================================================
# SecFlow AI — interactive setup wizard (Linux / macOS / WSL2)
#
#   ./scripts/setup.sh
#
# 自动完成：
#   1. 检测 Docker / Compose
#   2. 探测可用的容器镜像源（Docker Hub 不通时自动尝试镜像站）
#   3. 交互式生成 .env（AI 接入 / Wazuh / MISP 可选配置）
#   4. 拉取 postgres / redis 镜像并启动全栈
#   5. 健康检查 + 访问信息
#
# 无交互（全部默认）模式：  ./scripts/setup.sh --auto
# 跳过镜像源探测：         ./scripts/setup.sh --skip-registry-check
# =====================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

AUTO=0
[ "${1:-}" = "--auto" ] && AUTO=1
[ "${1:-}" = "--skip-registry-check" ] && SKIP_REG=1

say()  { printf '\033[1;36m[SecFlow]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[SecFlow!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[SecFlow X]\033[0m %s\n' "$*" >&2; exit 1; }

ask() { # ask <prompt> <default>
  local prompt="$1" default="${2:-}"
  if [ "$AUTO" = "1" ]; then printf '%s\n' "$default"; return; fi
  local ans
  read -r -p "$(printf '\033[1;36m[SecFlow]\033[0m %s [%s]: ' "$prompt" "$default")" ans || true
  printf '%s\n' "${ans:-$default}"
}

# ---------------------------------------------------------------------
say "SecFlow AI 部署向导 v1.0"
echo

# 1. Docker 检测
command -v docker >/dev/null || die "未检测到 Docker。Linux: apt install docker.io docker-compose-plugin; Windows: Docker Desktop + WSL2"
docker compose version >/dev/null 2>&1 || die "Docker Compose 插件缺失 (docker compose version 失败)"
say "Docker $(docker --version | awk '{print $3}') / Compose $(docker compose version --short) ✓"

# 2. 镜像源探测（解决 Docker Hub 不通的部署难题）
REGISTRY=""
if [ "${SKIP_REG:-0}" != "1" ] && [ "$AUTO" = "1" ]; then
  for r in "" "docker.1ms.run/" "dockerproxy.net/" "docker.m.daocloud.io/"; do
    img="${r}library/postgres:16-alpine"
    if timeout 25 docker pull -q "$img" >/dev/null 2>&1; then
      REGISTRY="$r"; break
    fi
  done
elif [ "${SKIP_REG:-0}" != "1" ]; then
  say "正在探测可用镜像源（约 1 分钟，Docker Hub 不通时自动选镜像站）..."
  for r in "" "docker.1ms.run/" "dockerproxy.net/" "docker.m.daocloud.io/"; do
    img="${r}library/postgres:16-alpine"
    if timeout 25 docker pull -q "$img" >/dev/null 2>&1; then
      REGISTRY="$r"; say "使用镜像源: ${r:-Docker Hub}"; break
    fi
    warn "镜像源 ${r:-Docker Hub} 不可达，尝试下一个..."
  done
fi

if [ -z "$REGISTRY" ]; then
  warn "所有常用镜像源均不可达——请配置 /etc/docker/daemon.json 的 registry-mirrors 后重试"
  warn "或手动 docker pull postgres:16-alpine / redis:7-alpine 后运行 --skip-registry-check"
  [ "$AUTO" = "1" ] || die "无法拉取基础镜像"
fi

# 3. 交互生成 .env
if [ ! -f .env ]; then
  cp .env.example .env
  say "已创建 .env（首次配置）"
else
  say "使用已有 .env（如需重新配置请删除后重跑）"
fi

# 生成随机密钥（保留已有值）
gen_or_keep() { # gen_or_keep <key> <length>
  local key="$1" len="$2"
  if grep -q "^${key}=CHANGE_ME" .env || ! grep -q "^${key}=.\+" .env; then
    sed -i "s|^${key}=.*|${key}=$(openssl rand -hex "$len")|" .env
  fi
}
gen_or_keep SECRET_KEY 24
gen_or_keep POSTGRES_PASSWORD 16

# 镜像源写入 .env（compose build 使用）
if [ -n "$REGISTRY" ]; then
  sed -i "s|^PY_IMAGE=.*|PY_IMAGE=${REGISTRY}library/python:3.12-slim|" .env
  sed -i "s|^NODE_IMAGE=.*|NODE_IMAGE=${REGISTRY}library/node:20-alpine|" .env
  sed -i "s|^NGINX_IMAGE=.*|NGINX_IMAGE=${REGISTRY}library/nginx:1.27-alpine|" .env
fi

# AI 接入引导（关键配置）
LLM_P="${LLM_PROVIDER:-}"
if [ -z "$LLM_P" ] || grep -q "^LLM_PROVIDER=mock$" .env; then
  echo
  say "AI 接入方式（必选，影响 AI 研判能力）："
  echo "   1) mock      —— 离线规则研判，零配置（推荐先跑通，之后可切换）"
  echo "   2) openai    —— 任意 OpenAI 兼容 API（DeepSeek/OpenAI/通义等）"
  echo "   3) ollama    —— 本地 Ollama（免费、隐私）"
  choice=$(ask "选择 [1/2/3]" "1")
  case "$choice" in
    2|openai)
      sed -i "s|^LLM_PROVIDER=.*|LLM_PROVIDER=openai|" .env
      sed -i "s|^LLM_BASE_URL=.*|LLM_BASE_URL=$(ask 'OpenAI 兼容 Base URL' 'https://api.deepseek.com/v1')|" .env
      sed -i "s|^LLM_API_KEY=.*|LLM_API_KEY=$(ask 'API Key' '')|" .env
      sed -i "s|^LLM_MODEL=.*|LLM_MODEL=$(ask '模型名' 'deepseek-chat')|" .env
      ;;
    3|ollama)
      sed -i "s|^LLM_PROVIDER=.*|LLM_PROVIDER=ollama|" .env
      sed -i "s|^LLM_BASE_URL=.*|LLM_BASE_URL=$(ask 'Ollama 地址' 'http://host.docker.internal:11434')|" .env
      sed -i "s|^LLM_MODEL=.*|LLM_MODEL=$(ask '模型名' 'qwen2.5:7b')|" .env
      ;;
    *) sed -i "s|^LLM_PROVIDER=.*|LLM_PROVIDER=mock|" .env ;;
  esac
fi

# 可选组件：Wazuh / MISP（默认跳过，不影响核心功能）
if [ "$AUTO" != "1" ] && grep -q "^WAZUH_URL=$" .env; then
  if [ "$(ask '配置 Wazuh 集成？（可选，y/n）' 'n')" = "y" ]; then
    sed -i "s|^WAZUH_URL=.*|WAZUH_URL=$(ask 'Wazuh API 地址' 'https://localhost:55000')|" .env
    sed -i "s|^WAZUH_USERNAME=.*|WAZUH_USERNAME=$(ask '用户名' 'admin')|" .env
    sed -i "s|^WAZUH_PASSWORD=.*|WAZUH_PASSWORD=$(ask '密码' '')|" .env
  fi
fi
if [ "$AUTO" != "1" ] && grep -q "^MISP_URL=$" .env; then
  if [ "$(ask '配置 MISP 集成？（可选，y/n）' 'n')" = "y" ]; then
    sed -i "s|^MISP_URL=.*|MISP_URL=$(ask 'MISP 地址' 'https://localhost')|" .env
    sed -i "s|^MISP_API_KEY=.*|MISP_API_KEY=$(ask 'API Key' '')|" .env
  fi
fi

# 4. 网络 + 启动
docker network inspect secflow-net >/dev/null 2>&1 || docker network create secflow-net
say "构建并启动（首次构建需数分钟，取决于网络）..."
docker compose up -d --build

# 5. 健康检查
say "等待服务就绪..."
for i in $(seq 1 30); do
  curl -sf "http://localhost:${API_PORT:-8000}/api/health" >/dev/null 2>&1 && break
  sleep 3
done

FRONTEND_PORT=$(grep -oP '^FRONTEND_PORT=\K.*' .env 2>/dev/null || echo 80)
echo
say "部署完成！"
echo "  🖥  前端:   http://localhost:${FRONTEND_PORT:-80}"
echo "  🔌 API:    http://localhost:${API_PORT:-8000}/docs"
echo "  🔑 账号:   admin / Admin@123456  （首次登录后请立即修改！）"
echo
say "后续操作: ./scripts/linux/health.sh 查看状态 | ./scripts/linux/stop.sh 停止"
