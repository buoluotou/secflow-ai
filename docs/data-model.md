# 数据模型

SecFlow 定义**统一安全数据模型**（规格 §20–§27）——第三方数据必须先经 Adapter
标准化后才能进入系统。V1 共 15 张表：

## 表清单

| 表 | 说明 |
|----|------|
| `organizations` | 组织 |
| `users` | 用户（admin / analyst / viewer） |
| `projects` | 项目 |
| `assets` | 资产（核心字段见下） |
| `security_events` | 安全事件（Wazuh 标准化后） |
| `findings` | 漏洞发现（Nuclei 标准化后） |
| `iocs` | 威胁情报指标（MISP 标准化后） |
| `evidence` | 证据（内容寻址，SHA-256 去重） |
| `incidents` | 安全事件（关联产物） |
| `attack_techniques` | ATT&CK 技术 |
| `ai_analyses` | AI 研判记录（输入/输出/模型/状态） |
| `risk_assessments` | 风险评估（评分 + 因子） |
| `reports` | 报告 |
| `scan_jobs` | 扫描任务（异步） |
| `audit_logs` | 审计日志 |

## 核心关系

```
Organization
    ↓
Project
    ↓
Asset
    │
    ├── SecurityEvent ──→ Incident
    │
    └── Finding

IOC ──→ Evidence ──→ Incident ──→ AI Analysis ──→ Risk Assessment ──→ Report
```

## 关键表字段

### assets
`id, project_id, name, hostname, ip, domain, asset_type, environment, criticality(1-5), owner, tags, status`

### security_events
`id, source, event_type, timestamp, project_id, asset_id, user, src_ip, src_port, dst_ip, dst_port, severity, confidence, indicators, techniques(ATT&CK), raw_data, external_id`

### findings
`id, project_id, asset_id, source, template_id, title, description, severity, cvss, cwe, request, response, evidence, remediation, status, first_seen, last_seen`

### iocs
`id, type(ip|domain|url|hash|email), value, source, confidence, tags, first_seen, last_seen`

### evidence
`id, type, source, source_id, title, content, raw_data, timestamp, hash`
—— `hash` 为规范化载荷的 SHA-256，重复导入自动去重（Evidence Engine）。

### incidents
`id, project_id, title, description, status, severity, confidence, attack_stage, detected_at, closed_at, assigned_to, related_event_ids, related_finding_ids, related_ioc_ids, evidence_ids, correlation_reason, ai_decision, human_decision, reviewer, review_comment, reviewed_at`

状态机：`new → triaging → investigating → awaiting_review → approved | rejected → contained → resolved → closed`

### risk_assessments
`id, incident_id, finding_id, risk_score, risk_level, factors(JSON)`
—— factors 完整记录六个乘法因子，可审计、可回放。

## 统一数据流

```
Wazuh JSON ──Adapter──→ SecurityEvent
Nuclei JSONL ──Adapter──→ Finding
MISP JSON ──Adapter──→ IOC (ThreatIntel)
         ↓
    Context Engine 组装统一上下文
         ↓
    AI Agents（只读统一模型，不吃原始 JSON）
```

## 数据库演进

- 开发环境：`init_db()` 自动建表 + 种子数据
- 生产环境：Alembic 迁移（`backend/alembic/`，`alembic revision --autogenerate`）
