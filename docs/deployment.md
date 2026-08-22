# 部署指南

## 快速部署（推荐）

```bash
./scripts/setup.sh          # 交互式向导：镜像源探测 + AI 接入引导 + 启动
./scripts/setup.sh --auto   # 全默认无交互
```

## 容器镜像源问题（常见部署失败原因）

Docker Hub（registry-1.docker.io）在某些网络环境不可达，导致 `docker compose
up -d --build` 在拉取 `postgres / redis / python / node / nginx` 基础镜像时失败。

三种解决方式：

1. **`./scripts/setup.sh`**：自动探测 `docker.1ms.run / dockerproxy.net /
   docker.m.daocloud.io` 等镜像站，选可用者写入 `.env` 的 `PY_IMAGE /
   NODE_IMAGE / NGINX_IMAGE`（compose 构建时生效）
2. 手动配置：在 `/etc/docker/daemon.json` 添加 `registry-mirrors`
3. 手动拉取后打标签：`docker pull <mirror>/library/postgres:16-alpine &&
   docker tag <mirror>/library/postgres:16-alpine postgres:16-alpine`

> pip / npm 同样支持镜像：`.env` 中 `PIP_INDEX_URL`（如清华源）、
> `NPM_REGISTRY`（如 npmmirror）会被 Dockerfile 构建时使用。

## 硬件基线（规格 §5）

| 组件 | 最低 | 推荐 |
|------|------|------|
| CPU | 8 核 | 8 核+ |
| RAM | 16 GB | 32 GB |
| 磁盘 | 100 GB | 200 GB+ |

Wazuh 官方单节点基线：4 CPU / 8 GB / 50 GB；再加 SecFlow、MISP、数据库与 AI 后按上表。

## Linux（Docker Engine）

```bash
git clone <repo-url> secflow-ai
cd secflow-ai
./scripts/linux/install.sh      # 系统依赖 + vm.max_map_count + secflow-net + .env
cp .env.example .env            # install.sh 会自动生成
# 编辑 .env（密码/集成项）
./scripts/linux/start.sh
```

访问 http://localhost

## Windows（Docker Desktop + WSL2）

```powershell
git clone <repo-url> secflow-ai
cd secflow-ai
.\scripts\windows\install.ps1
# 编辑 .env
.\scripts\windows\start.ps1
```

访问 http://localhost

## 部署 Wazuh（可选但推荐，规格 §11）

```bash
./deploy/wazuh/deploy.sh        # 克隆官方 wazuh-docker @ v4.14.7 → 证书 → up -d
# .env: WAZUH_URL / WAZUH_USERNAME / WAZUH_PASSWORD
```

## 部署 MISP（可选但推荐，规格 §13）

```bash
./deploy/misp/deploy.sh         # 生成 misp-docker/.env（先编辑）→ pull → up -d
# .env: MISP_URL / MISP_API_KEY（在 MISP 后台创建 Auth Key）
```

## 配置 Nuclei（规格 §15）

按任务调用，不常驻：

```dotenv
NUCLEI_MODE=docker              # 默认；worker 通过 docker.sock 运行容器
NUCLEI_IMAGE=projectdiscovery/nuclei:latest
# 或 NUCLEI_MODE=binary + NUCLEI_BIN=nuclei
```

## 配置 LLM（规格 §47）

三种模式：

```dotenv
# 1) 离线（默认，无需任何 Key）
LLM_PROVIDER=mock

# 2) OpenAI-compatible（云端）
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# 3) Ollama（本地）
LLM_PROVIDER=ollama
LLM_BASE_URL=http://host.docker.internal:11434
LLM_MODEL=qwen2.5:7b
```

## 健康检查

```bash
./scripts/linux/health.sh       # Linux
.\scripts\windows\health.ps1    # Windows
# 或浏览器访问 /api/health、/api/health/db 等
```

## 生产部署（规格 §12）

- 置于反向代理（Nginx/Traefik + TLS）之后
- 只暴露 Dashboard、Agent、必要 API
- PostgreSQL / Indexer / Redis 只进内部网络
- `docker compose -f docker-compose.prod.yml up -d`
- 数据库迁移使用 Alembic，禁用自动建表（`APP_ENV=production` 时仍会建表，建议生产关闭 init_db 或改用迁移）

## 升级

```bash
./scripts/linux/update.sh
# 或 git pull + docker compose up -d --build
```
