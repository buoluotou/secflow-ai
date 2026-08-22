# API 参考

基地址：`http://localhost:8000/api` · 交互文档：`/docs`（Swagger UI）

认证：除 `auth/*` 与 `health/*` 外均需 `Authorization: Bearer <JWT>`。

## 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/login` | 登录，返回 JWT |
| POST | `/auth/bootstrap-admin` | 首次部署创建管理员（仅当无管理员时） |
| GET | `/auth/me` | 当前用户 |

## 健康检查（规格 §48）

| 方法 | 路径 |
|------|------|
| GET | `/health` |
| GET | `/health/db` · `/health/redis` · `/health/wazuh` · `/health/misp` · `/health/llm` |

## 业务 API（规格 §51）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/projects` | 项目列表 / 新建 |
| GET/PATCH/DELETE | `/projects/{id}` | 项目详情 / 更新 / 删除 |
| GET/POST | `/assets` | 资产列表（支持 project_id、q 过滤）/ 新建 |
| GET/PATCH/DELETE | `/assets/{id}` | 资产详情 / 更新 / 删除 |
| GET/POST | `/events` | 安全事件列表 / 手动录入（触发关联） |
| GET | `/events/{id}` | 事件详情 |
| GET/POST | `/findings` | 漏洞列表 / 手动录入 |
| GET/PATCH | `/findings/{id}` | 漏洞详情 / 更新状态 |
| GET/POST | `/iocs` | IOC 列表 / 新建 |
| POST | `/iocs/search` | IOC 搜索（本地缺失时自动查询 MISP） |
| GET/POST | `/incidents` | 事件列表 / 手动创建 |
| GET/PATCH | `/incidents/{id}` | 事件详情 / 更新 |
| POST | `/incidents/{id}/analyze` | 执行 AI 研判管线（agents 可选） |
| POST | `/incidents/{id}/approve` · `/reject` | 人工审核 |
| POST | `/scans` | 发起扫描（202 异步入队） |
| GET | `/scans` · `/scans/{id}` | 扫描任务列表 / 详情 |
| GET | `/analysis` · `/analysis/{id}` | AI 研判记录 |
| GET | `/analysis/incident/{id}/risk` | 事件风险评估 |
| GET/POST | `/reports` | 报告列表 / 生成 |
| GET | `/reports/{id}/markdown` · `/reports/{id}/pdf` | 报告内容 / PDF |
| GET | `/audit/logs` | 审计日志 |
| POST | `/webhooks/wazuh` | Wazuh Webhook 接收（实时告警） |

## 统一响应

错误：`{"detail": "..."}`（HTTP 4xx/5xx）；审计字段含 `X-Request-ID`。

## 异步任务（规格 §52）

以下操作不阻塞 HTTP，通过 Redis → Celery 执行：

```
POST /api/scans            →  run_nuclei_scan
定时 (beat)                →  sync_wazuh_events / enrich_misp_iocs
POST /incidents/{id}/analyze →  analyze_incident（当前 V1 同步执行，便于演示；
                                LLM 超时由 LLM_TIMEOUT 控制）
POST /reports              →  generate_report
```
