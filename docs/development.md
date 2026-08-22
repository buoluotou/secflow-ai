# 开发指南

## 本地快速开始（不需要 Docker 也可以跑通全流程）

### 后端

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 使用 SQLite 本地开发（覆盖默认 PostgreSQL 配置）
export DATABASE_URL=sqlite:///./dev.db   # 见下方说明
export SECRET_KEY=dev-secret
export LLM_PROVIDER=mock
```

> 说明：`app.core.config.Settings.database_url` 默认拼接 PostgreSQL 地址。
> 本地开发可设置 `POSTGRES_HOST=sqlite` 等，或直接修改 `DATABASE_URL`。
> 更简单的方式是使用 dev compose：`docker compose -f docker-compose.dev.yml up -d postgres redis`。

### 运行与测试

```bash
uvicorn app.main:app --reload --port 8000
pytest                                   # 单元/集成测试
python -m ai.evaluators.evaluate         # AI 评测集（离线 mock）
```

### 前端

```bash
cd frontend
npm install
npm run dev                              # http://localhost:5173 (代理 /api → 8000)
npm run build                            # 生产构建
```

## 代码风格与结构

- 后端：类型注解齐全；`ruff` 检查（`pip install ruff && ruff check app`）
- 数据流：Adapter 只做"标准化"，业务逻辑只读统一模型
- AI 输出：必须过 Pydantic JSON Schema 校验 + 证据绑定校验
- 日志：统一 JSON（见 `app/core/logging.py`）

## 数据库迁移（Alembic）

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

开发环境也可用 `init_db()` 自动建表（main.py lifespan 默认执行）。

## 新增集成（如 DefectDojo，V2）

1. 在 `integrations/<tool>/` 实现 `client / parser / mapper`
2. 标准化为统一模型（SecurityEvent / Finding / IOC）
3. 在 `app/services/correlation.py` 接入关联键
4. 添加健康检查端点
5. 编写 parser 单元测试

## 测试矩阵（规格 §53）

| 类型 | 覆盖 |
|------|------|
| Unit | parsers (wazuh/nuclei/misp)、evidence hash 去重、risk 计算 |
| Integration | correlation → incident、analysis 管线（mock LLM） |
| API | 认证、CRUD 冒烟 |
| AI Schema | Triage/Threat/Vuln 输出校验（datasets/evaluation） |
| E2E | Demo 01 流程（docs/demo.md） |

## 环境变量

见 `.env.example`（每个变量均有注释）。`.env` 绝不提交。
