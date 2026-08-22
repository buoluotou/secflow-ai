#!/usr/bin/env bash
# =====================================================================
# SecFlow AI — system diagnostic (科学自查)
#
#   ./scripts/check.sh [API_BASE]
#
# 检查：服务/组件状态、AI 配置真实性（是否真的接了模型）、数据量、
# 进程与端口、常见故障。输出一目了然，帮助快速定位问题。
# =====================================================================
set -uo pipefail

API="${1:-http://localhost:${API_PORT:-8000}/api}"
say()  { printf '\033[1;36m[SecFlow]\033[0m %s\n' "$*"; }
pass() { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[1;33m!\033[0m %s\n' "$*"; }
fail() { printf '  \033[1;31m✗\033[0m %s\n' "$*"; }

echo
say "SecFlow AI 系统诊断"
echo

# 1. API 可达性
say "1. 服务状态"
if ! curl -sf -m 5 "${API}/health" >/dev/null 2>&1; then
  fail "API 不可达 (${API}) —— 请先启动服务 (./scripts/linux/start.sh)"
  exit 1
fi
pass "API 可达"

# 2. 核心组件
for ep in db redis; do
  if curl -sf -m 5 "${API}/health/${ep}" | grep -q '"ok":true'; then
    pass "${ep} 正常"
  else
    fail "${ep} 异常"
  fi
done

# 3. 可选组件
for ep in wazuh misp; do
  st=$(curl -sf -m 5 "${API}/health/${ep}" 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('status','?'))" 2>/dev/null || echo "?")
  case "$st" in
    ok)            pass "${ep} 正常" ;;
    not_configured) warn "${ep} 未配置（可选组件）" ;;
    *)             fail "${ep} 异常（${st}）" ;;
  esac
done

# 4. AI 配置真实性（关键：没有密钥就是没有接入真实 AI）
say "2. AI 接入状态（真实检查）"
llm=$(curl -sf -m 8 "${API}/health/llm" 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('status'),d.get('provider'),d.get('model') or '')" 2>/dev/null || echo "? ? ?")
st=$(echo "$llm" | awk '{print $1}')
case "$st" in
  mock) warn "未接入真实模型 —— 当前为 Mock 离线规则模式"
        warn "接入方法：登录界面 → 设置 → AI 接入 → 选择服务商 + 粘贴密钥 → 保存并启用"
        warn "         （或修改 .env 的 LLM_PROVIDER/LLM_API_KEY 后重启）" ;;
  ok)   pass "已接入真实模型: $(echo "$llm" | cut -d' ' -f2-)" ;;
  *)    fail "AI 连接异常（${llm}）—— 检查密钥/额度/网络" ;;
esac

# 5. 数据量
say "3. 数据量"
TOKEN=$(curl -sf -X POST "${API}/auth/login" -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123456"}' 2>/dev/null \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
if [ -n "$TOKEN" ]; then
  H="Authorization: Bearer ${TOKEN}"
  for res in incidents findings events iocs scans reports; do
    n=$(curl -sf "${API}/${res}" -H "$H" 2>/dev/null | python3 -c "import sys,json;print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
    printf '  %-12s %s\n' "${res}:" "$n"
  done
  pass "登录正常（admin）"
else
  warn "无法登录（默认密码可能已修改）——跳过数据统计"
fi

# 6. 进程/端口
say "4. 进程与端口"
for p in "8000:API" "80:前端"; do
  port="${p%%:*}"; name="${p##*:}"
  if ss -tln 2>/dev/null | grep -q ":${port} "; then pass "${name} 端口 ${port} 监听中"; else warn "${name} 端口 ${port} 未监听（dev 模式前端为 5173）"; fi
done

echo
say "诊断完成。仍有问题？查看 docs/deployment.md 或 docs/ai-setup.md"
