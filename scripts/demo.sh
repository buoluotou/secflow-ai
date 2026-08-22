#!/usr/bin/env bash
# =====================================================================
# SecFlow AI — Demo 01: Web 入侵事件自动研判 (spec §43)
#
# 一键跑通: 注入 Wazuh 告警 → 关联引擎 → Incident → AI 研判 → 风险评分
#           → 人工批准 → PDF 报告
#
# 用法: ./scripts/demo.sh [API_BASE]   (默认 http://localhost:8000/api)
# 前置: docker compose up -d 已启动; 种子数据已生成(demo 项目 + IOC)
# =====================================================================
set -euo pipefail

API="${1:-http://localhost:8000/api}"
USER="${SECFLOW_DEMO_USER:-admin}"
PASS="${SECFLOW_DEMO_PASS:-Admin@123456}"

echo "[SecFlow] >>> Demo 01 开始 (API: ${API})"

# 1. 等待 API 就绪
for i in $(seq 1 30); do
  curl -sf "${API}/health" >/dev/null 2>&1 && break
  echo "  等待 API 启动... ($i)"
  sleep 2
done
curl -sf "${API}/health" >/dev/null || { echo "API 不可达"; exit 1; }

# 2. 登录
TOKEN=$(curl -sf -X POST "${API}/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"${USER}\",\"password\":\"${PASS}\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
H="Authorization: Bearer ${TOKEN}"
echo "[1/7] 登录成功: ${USER}"

# 3. 准备项目与 IOC（种子数据已有，缺失则创建）
PID=$(curl -sf "${API}/projects" -H "$H" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d[0]['id'] if d else '')" || true)
if [ -z "$PID" ]; then
  PID=$(curl -sf -X POST "${API}/projects" -H "$H" -H 'Content-Type: application/json' \
    -d '{"name":"Demo 01","description":"Web 入侵事件自动研判"}' \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
fi
IOC_EXISTS=$(curl -sf "${API}/iocs?q=203.0.113.66" -H "$H" \
  | python3 -c "import sys,json;print(len(json.load(sys.stdin)))")
if [ "$IOC_EXISTS" = "0" ]; then
  curl -sf -X POST "${API}/iocs" -H "$H" -H 'Content-Type: application/json' \
    -d '{"type":"ip","value":"203.0.113.66","source":"demo","confidence":0.9,"tags":["apt","demo"]}' >/dev/null
fi
echo "[2/7] 项目与恶意 IOC 就绪 (project=${PID:0:8})"

# 4. 注入 Wazuh 告警（命中 IOC → 触发关联）
EVT=$(curl -sf -X POST "${API}/events" -H "$H" -H 'Content-Type: application/json' \
  -d "{\"source\":\"wazuh\",\"event_type\":\"Command execution detected\",\"severity\":\"high\",\"confidence\":0.9,\"src_ip\":\"203.0.113.66\",\"project_id\":\"${PID}\",\"techniques\":[\"T1059.001\"]}")
echo "[3/7] Wazuh 告警已注入: $(echo "$EVT" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'][:8])")"

# 5. 关联引擎 → Incident
sleep 1
IID=$(curl -sf "${API}/incidents" -H "$H" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d[0]['id'] if d else '')")
echo "[4/7] 关联生成 Incident: ${IID:0:8}"
curl -sf "${API}/incidents/${IID}" -H "$H" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('      标题:',d['title']);print('      证据链:',len(d['evidence_ids']),'条; 关联依据:',(d.get('correlation_reason') or '')[:80])"

# 6. AI 研判 + 风险评分
echo "[5/7] AI 研判中 (Triage/Threat/Vuln + Risk Engine)..."
curl -sf -X POST "${API}/incidents/${IID}/analyze" -H "$H" \
  | python3 -c "
import sys,json
r=json.load(sys.stdin)['results']
t=r.get('triage',{}); risk=r.get('risk',{})
print('      分类:',t.get('classification'),'| 严重性:',t.get('severity'),'| 置信度:',t.get('confidence'))
print('      威胁判定: 恶意' if (r.get('threat') or {}).get('malicious') else '      威胁判定: 未见恶意')
print('      风险评分:',risk.get('risk_score'),'→',risk.get('risk_level'))"

# 7. 人工审核 + 报告
curl -sf -X POST "${API}/incidents/${IID}/approve" -H "$H" -H 'Content-Type: application/json' \
  -d '{"decision":"approve","comment":"Demo 自动批准"}' >/dev/null
echo "[6/7] 人工审核: approved"
RID=$(curl -sf -X POST "${API}/reports" -H "$H" -H 'Content-Type: application/json' \
  -d "{\"incident_id\":\"${IID}\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -sf "${API}/reports/${RID}/pdf" -H "$H" -o /tmp/secflow_demo_report.pdf
echo "[7/7] PDF 报告: /tmp/secflow_demo_report.pdf ($(stat -c%s /tmp/secflow_demo_report.pdf) bytes)"

echo
echo "[SecFlow] >>> Demo 01 完成 ✅"
echo "  前端页面: http://localhost  (Incidents → 详情 → 查看 AI 研判/风险/报告)"
