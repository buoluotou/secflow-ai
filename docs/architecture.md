# 架构总览

SecFlow AI 是 **AI 驱动的网络安全服务智能化平台**：把 Wazuh 告警、Nuclei 漏洞结果、
MISP 威胁情报串起来，由 AI 辅助完成安全事件的自动研判、风险评分与报告生成。

## 完整闭环

```
资产
  ↓
Wazuh / Nuclei
  ↓
安全事件 / 漏洞
  ↓
标准化 (Adapter → 统一数据模型)
  ↓
IOC / 威胁情报 (MISP)
  ↓
事件关联 (Correlation Engine)
  ↓
证据链 (Evidence Engine)
  ↓
AI研判 (Triage / Threat / Vuln Agents)
  ↓
风险评分 (Risk Engine — 确定性计算，LLM 不参与)
  ↓
人工审核 (Human Review)
  ↓
安全报告 (Report Engine)
```

## 分层架构

```
┌─────────────────────┐
│  SecFlow Frontend   │  React + TypeScript + Vite + Ant Design + ECharts
└──────────┬──────────┘
           │ REST (JWT)
┌──────────▼──────────┐
│    SecFlow API      │  FastAPI (backend/)
└──────────┬──────────┘
  ┌────────┼─────────┬──────────┐
  ▼        ▼         ▼          ▼
PostgreSQL Redis  Object Store  Celery Workers
  │        │         │          │
  │        └─────────┼──────────┤
  │                  ▼          ▼
  │           Wazuh Adapter   Nuclei / MISP Adapters
  └──────────────────┬───────────────────────────
                     ▼
             Unified Security Data
                     ▼
             Correlation Engine
                     ▼
              Evidence Engine
                     ▼
               Context Engine
                     ▼
               AI Security Engine
              (Triage/Threat/Vuln/Report Agents)
                     ▼
                Risk Engine
                     ▼
               Human Review
                     ▼
                Report Engine
```

## 代码组织

| 目录 | 职责 |
|------|------|
| `backend/` | FastAPI 应用：API 路由、模型、服务层、Celery workers |
| `frontend/` | React + TS 单页应用 |
| `ai/` | LLM Provider 抽象、4 个 Agent、推理层（证据绑定/决策）、评测器 |
| `integrations/` | 第三方工具适配器（Wazuh / Nuclei / MISP），不改第三方源码 |
| `risk/` | 风险引擎 + 校准参数（唯一调参点） |
| `reports/` | 报告引擎（Markdown + PDF） |
| `datasets/evaluation/` | AI 评测集 |
| `deploy/` | Wazuh / MISP 独立部署脚本（安装时克隆官方指定版本） |
| `scripts/` | Windows / Linux 发布脚本 |
| `docs/` | 本文档 |

## 八条核心原则（规格 §4）

1. **第三方工具不改源码** — 只通过 API / 容器交互
2. **SecFlow 定义统一数据模型** — Wazuh→SecurityEvent、Nuclei→Finding、MISP→ThreatIntel(IOC)
3. **AI 不负责最终风险计算** — Risk Engine 计算，AI 只分析/解释/归纳
4. **AI 重大结论必须绑定证据** — 证据 ID 校验（Evidence Engine + reasoning 层强校验）
5. **高风险动作必须人工批准** — V1 不允许 AI 自动执行危险操作
6. **Windows/Linux 同一套容器部署逻辑** — 都是 `docker compose up -d`
7. **第一版不做 Kubernetes** — Docker Compose 足够
8. **第一版不做"AI 黑客"** — 定位是 Security Service Copilot

## 网络分层（规格 §45）

```
Internet
   ↓
Reverse Proxy (生产环境)
   ↓
SecFlow (secflow-net)
   ↓
secflow-internal ─── postgres / redis / worker
   ↓
Wazuh (wazuh-internal) / MISP (misp-internal)   ← 各自独立 Compose
```

## 技术栈

- **后端**：Python 3.12+ / FastAPI / Pydantic v2 / SQLAlchemy 2 / Alembic / Celery / Redis / PostgreSQL / httpx / pytest
- **前端**：React 18 / TypeScript / Vite / Ant Design 5 / ECharts / React Router / Zustand
- **AI**：OpenAI-compatible / Ollama / 内置 Mock Provider（离线可用）
- **部署**：Docker Compose（base/dev/prod 三套），Windows = Docker Desktop + WSL2
