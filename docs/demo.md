# Demo 01 — Web 入侵事件自动研判

> **仅限自建靶场 / 授权环境运行。**

## 实验环境

```
Kali (或任意 Docker 主机)
│
├── SecFlow AI  (docker compose up -d)
├── Wazuh       (./deploy/wazuh/deploy.sh)
├── MISP        (./deploy/misp/deploy.sh)
├── Nuclei      (按任务临时启动)
└── Demo Web    (自建漏洞靶场，如 DVWA / 任意测试应用)
```

## 演示故事（规格 §43）

```
Demo Web
  ↓ 1. 存在测试漏洞
Nuclei 发现漏洞 (POST /api/scans → Finding)
  ↓ 2. 模拟授权攻击行为
Wazuh 产生告警 (→ SecurityEvent)
  ↓ 3. 提取攻击 IP
↓ 4. MISP 发现恶意 IOC (POST /api/iocs 或 MISP 同步)
  ↓ 5. Correlation Engine 自动关联
Incident 生成（含证据链 evidence_ids）
  ↓ 6. Evidence Engine 固定证据
  ↓ 7. AI Triage / Threat / Vuln 研判
  ↓ 8. Risk Engine 计算风险评分
  ↓ 9. 人工审核 (approve / reject)
  ↓ 10. Report Engine 生成 PDF 报告
```

## 操作步骤

### 1. 启动平台

```bash
docker network create secflow-net
docker compose up -d --build
# 首次启动自动创建管理员 admin / Admin@123456（请立即修改！）
```

### 2. 准备 Demo Web

```bash
docker run -d --name demo-web --network secflow-net -p 8081:80 vulnerables/web-dvwa
# 或任意自建靶场
```

### 3. 添加资产与 IOC

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123456"}' | jq -r .access_token)
H="Authorization: Bearer $TOKEN"

# 添加资产（或用前端页面）
curl -s -X POST localhost:8000/api/assets -H "$H" -H 'Content-Type: application/json' \
  -d '{"project_id":"<project-id>","name":"demo-web","ip":"172.20.0.10","asset_type":"webapp","environment":"dmz","criticality":4}'

# 注册恶意 IOC（攻击源 IP）
curl -s -X POST localhost:8000/api/iocs -H "$H" -H 'Content-Type: application/json' \
  -d '{"type":"ip","value":"203.0.113.66","source":"demo","confidence":0.9,"tags":["apt","demo"]}'
```

### 4. 触发扫描

```bash
curl -s -X POST localhost:8000/api/scans -H "$H" -H 'Content-Type: application/json' \
  -d '{"project_id":"<project-id>","scan_type":"nuclei","targets":["http://demo-web"],"options":{"severity":"high"}}'
```

Nuclei 结果 → `Finding` → Correlation Engine 自动检查同资产事件与 IOC 命中。

### 5. 模拟攻击 + Wazuh 告警

从 `203.0.113.66`（或任意测试 IP）对 Demo Web 执行授权测试；在 Wazuh 触发告警
后，SecFlow 通过定时同步或 Webhook 接收：

```bash
# Webhook 方式（Wazuh 集成 → 自定义 Webhook）:
curl -s -X POST localhost:8000/api/webhooks/wazuh -H "$H" -H 'Content-Type: application/json' \
  -d '{"data":{"id":12345,"rule":{"description":"Command execution detected","level":12,"mitre":{"technique":[{"id":"T1059.001"}]}},"srcip":"203.0.113.66","dstip":"172.20.0.10","timestamp":"2026-08-22T09:15:00Z"}}'
```

### 6. 查看关联事件

```bash
curl -s localhost:8000/api/incidents -H "$H" | jq
```

事件包含 `correlation_reason`、`evidence_ids`、`related_*` 关联引用。

### 7. AI 研判 + 风险评分

```bash
curl -s -X POST localhost:8000/api/incidents/<incident-id>/analyze -H "$H" | jq
```

输出：分类 / 严重性 / 置信度 / ATT&CK / 证据绑定 / 处置建议 + 风险评分与等级。

### 8. 人工审核

```bash
curl -s -X POST localhost:8000/api/incidents/<incident-id>/approve -H "$H" \
  -H 'Content-Type: application/json' -d '{"decision":"approve","comment":"确认，按建议处置"}'
```

### 9. 生成报告

```bash
curl -s -X POST localhost:8000/api/reports -H "$H" \
  -H 'Content-Type: application/json' -d '{"incident_id":"<incident-id>","report_type":"incident"}'
curl -s localhost:8000/api/reports/<report-id>/pdf -H "$H" -o report.pdf
```

## 研究指标（规格 §55）

记录并对比：

| 指标 | 人工 | AI 辅助 |
|------|------|---------|
| 平均研判时间 (Mean Triage Time) | ~20 分钟/事件 | ~5 分钟/事件 |
| 平均报告时间 (Mean Report Time) | ~30 分钟 | ~8 分钟 |
| MTTR | — | 显著下降 |

这些指标即项目核心业务价值，可用于技术文章与求职展示。
