#!/usr/bin/env bash
# 手动推送 GitHub（网络恢复时执行）：./scripts/push.sh <PAT>
set -euo pipefail
[ -n "${1:-}" ] || { echo "用法: ./scripts/push.sh <GitHub PAT>"; exit 1; }
cd "$(dirname "${BASH_SOURCE[0]}")/.."
git push "https://x-access-token:${1}@github.com/buoluotou/secflow-ai.git" main
echo "✓ 已推送。本地 remote 不含凭据。"
