<div align="center">

# 🛡️ SecFlow AI

**AI-Powered Security Service Automation Platform · AI 驱动的网络安全服务智能化平台**

将 **Wazuh 告警 · Nuclei 漏洞 · MISP 威胁情报** 串成一条自动化安全服务闭环：
统一数据模型 → 事件关联 → 证据链 → **AI 研判** → 风险评分 → 人工审核 → 安全报告。

</div>

---

## Why SecFlow AI

安全工程师每天面对 Wazuh 告警、Nuclei 漏洞结果、MISP 威胁情报，需要人工查日志、
查资产、查 IOC、查历史行为、判断攻击、确定风险、写报告。

**SecFlow AI 把这些工作串起来，由 AI 辅助完成研判** —— 但 AI 从不直接决定风险，
风险由确定性 Risk Engine 计算；AI 的每个重大结论都必须绑定可审计的证据。

```
资产 → Wazuh/Nuclei → 安全事件/漏洞 → 标准化 → IOC/威胁情报
    → 事件关联 → 证据链 → AI研判 → 风险评分 → 人工审核 → 安全报告
```

## ✨ 核心特性

| 模块 | 说明 |
|------|------|
| 🧩 统一安全数据模型 | Wazuh→`SecurityEvent`、Nuclei→`Finding`、MISP→`IOC`，AI 不吃原始 JSON |
| 🔗 Correlation Engine | 按资产 / IP / 域名 / 用户 / IOC / 时间窗口自动关联，生成 Incident |
| 📎 Evidence Engine | 内容寻址（SHA-256）证据链，AI 结论**强制证据绑定**，杜绝"我觉得" |
| 🧠 AI Agents | Triage / Threat / Vulnerability / Report 四个 Agent，JSON Schema 校验输出 |
| 📊 Risk Engine | 六因子乘法评分（技术严重性×资产关键性×暴露×威胁情报×利用证据×置信度），可校准 |
| 👤 Human Review | 高风险动作必须人工 Approve / Reject / Modify（V1 无 AI 自动执行） |
| 📄 Report Engine | 事件/漏洞/巡检报告，Markdown + PDF，含全部 12 个章节 |
| 🖥️ 全栈 Web | React + TS + Ant Design + ECharts Dashboard，支持中英文 |
| 🐳 双平台部署 | Windows (Docker Desktop + WSL2) / Linux (Docker Engine)，同一套 `docker compose up -d` |
| 🤖 多 LLM 兼容 | OpenAI-compatible / Ollama / **内置 Mock**（无 Key 也能完整跑通全流程） |
| 📈 AI 评测集 | Precision / Recall / F1 / FPR / 证据覆盖率 / 幻觉率 自动化评估 |
| 🗂️ 审计日志 | 登录、资产、扫描、AI 分析、审核、报告全量 JSON 审计 |

## 🚀 快速开始

### 前置条件

- Docker Engine 25+（Windows 用户：Docker Desktop + WSL2）
- 建议硬件：8 核 CPU / 16 GB RAM / 100 GB 磁盘（Wazuh 较重，规格 §5）

### 一键安装（推荐）—— 交互式向导

向导会自动：检测 Docker → **探测可用镜像源**（Docker Hub 不通时自动切换镜像站）→
引导配置 AI 接入（mock / OpenAI 兼容 / Ollama）→ 生成 `.env` → 构建启动 → 健康检查。

```bash
git clone https://github.com/buoluotou/secflow-ai.git secflow-ai && cd secflow-ai
./scripts/setup.sh          # 交互式；或 ./scripts/setup.sh --auto 全默认
```

### 手动安装（二选一）

**Linux**

```bash
git clone https://github.com/buoluotou/secflow-ai.git secflow-ai && cd secflow-ai
./scripts/linux/install.sh     # Docker + vm.max_map_count + 网络 + .env
./scripts/linux/start.sh       # docker compose up -d
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/buoluotou/secflow-ai.git secflow-ai; cd secflow-ai
.\scripts\windows\install.ps1
.\scripts\windows\start.ps1
```

### 登录与 AI 接入

打开 http://localhost —— 首次启动自动创建管理员：

```
用户名: admin
密码:   Admin@123456   ⚠️ 首次登录后请立即修改！
```

AI 研判默认 **mock 离线模式**（零配置可跑通全流程）。接入真实模型
（DeepSeek / OpenAI / Ollama）见 **[docs/ai-setup.md](docs/ai-setup.md)**
或登录后 **Settings → AI 接入向导**。

### 验证

```bash
curl http://localhost:8000/api/health          # 服务状态
curl http://localhost:8000/api/health/db       # 数据库
curl http://localhost:8000/api/health/llm      # AI（默认 mock 离线模式）
```

## 🎬 Demo 01 — Web 入侵事件自动研判

完整的端到端演示（规格 §43）：靶场漏洞被 Nuclei 发现 → 授权攻击触发 Wazuh 告警 →
攻击 IP 命中 MISP IOC → 自动关联生成 Incident → 证据链 → AI 研判 → 风险评分 →
人工审核 → PDF 报告。

完整操作步骤见 **[docs/demo.md](docs/demo.md)**。

## 🏗️ 架构

```
┌─────────────────────┐   React + TypeScript + Ant Design + ECharts
│  SecFlow Frontend   │
└──────────┬──────────┘
           │ REST (JWT)
┌──────────▼──────────┐   FastAPI + SQLAlchemy + Celery
│    SecFlow API      │
└──────────┬──────────┘
  ┌────────┼─────────┬──────────┐
  ▼        ▼         ▼          ▼
PostgreSQL Redis  Object Store  Workers ──► Wazuh / Nuclei / MISP (独立 Compose)
  └──────────────┬─────────────────────────────┘
                 ▼
        Correlation → Evidence → Context → AI Agents → Risk → Human Review → Report
```

- 第三方组件（Wazuh / MISP / Nuclei）**不改源码、不内嵌仓库**，安装时由
  `deploy/` 脚本克隆官方指定版本（规格 §62）
- 网络三层隔离：`secflow-net`（对外）/ `secflow-internal`（DB/Redis）/ 第三方内部网络

详细文档：[架构](docs/architecture.md) · [数据模型](docs/data-model.md) · [API](docs/api.md) · [部署](docs/deployment.md) · [开发](docs/development.md) · [Demo](docs/demo.md) · [许可证](docs/licensing.md) · [路线图](docs/roadmap.md)

## 🧪 测试与评测

```bash
cd backend && pip install -e ".[dev]" && pytest     # 单元/集成/API 测试
python -m ai.evaluators.evaluate                     # AI 评测（离线 mock，输出指标 JSON）
cd frontend && npm install && npm run build          # 前端生产构建
```

## 📁 仓库结构

```
secflow-ai/
├── backend/          # FastAPI 应用（API/模型/服务/Celery/Alembic/测试）
├── frontend/         # React + TS 单页应用
├── ai/               # Agents / reasoning / LLM Provider / evaluators / prompts
├── integrations/     # wazuh / nuclei / misp 适配器（不改第三方源码）
├── risk/             # 风险引擎 + 校准参数（唯一调参点）
├── reports/          # 报告引擎（Markdown + PDF）
├── datasets/         # AI 评测集
├── deploy/           # Wazuh / MISP 独立部署脚本
├── scripts/          # Windows / Linux 发布脚本
├── docs/             # 全部文档
├── docker-compose.yml / docker-compose.dev.yml / docker-compose.prod.yml
├── .env.example      # 环境变量模板
├── NOTICE.md / LICENSE / docs/licensing.md
└── README.md
```

## 🔒 安全设计原则

1. **AI 不做最终风险决策** — Risk Engine 确定性计算（§39）
2. **高风险动作必须人工批准** — 封禁/隔离/禁用账号永不自动执行（§5）
3. **AI 结论必须绑定证据** — 引用不存在的证据 ID 即拒绝（§4）
4. **只做防御研判** — 定位是 Security Service Copilot，不是攻击平台（§8）

## 🗺️ 路线图

- **V2**：DefectDojo（漏洞生命周期）、Shuffle（SOAR）、通知/Webhook、Playbook、Attack Graph、Threat Hunting
- **V3**：Evidence-Grounded Agent、Context-Aware Risk、Risk Calibration、Agent Memory、论文/技术文章

详见 [docs/roadmap.md](docs/roadmap.md)。

## 📄 许可证

SecFlow AI 代码采用 [MIT License](LICENSE)。第三方组件（Wazuh GPL-2.0、Nuclei MIT、
MISP AGPL-3.0）各自保留许可证，详见 [NOTICE.md](NOTICE.md) 与 [docs/licensing.md](docs/licensing.md)。

---

<div align="center">
<sub>仅用于授权环境的安全运营与测试 · Built with FastAPI · React · Docker</sub>
</div>
