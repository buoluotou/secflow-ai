# MISP 部署（SecFlow AI 集成）

> 原则（规格 §62）：不把 `misp-docker` 仓库提交进 SecFlow 仓库。
> 安装时由脚本克隆官方仓库并 `docker compose pull / up -d`。

## 前置条件

- Docker Engine 25+
- Docker Compose plugin 2.17+

## 部署

```bash
./deploy/misp/deploy.sh
```

第一次执行会生成 `misp-docker/.env`（来自官方 `template.env`），
编辑以下项后**重新执行脚本**：

| 配置项 | 说明 |
|--------|------|
| `MISP_ADMIN_EMAIL` | 管理员邮箱 |
| `MISP_ADMIN_PASSWD` | 管理员密码（立即修改默认值） |
| `MISP_BASEURL` | 对外访问地址 |
| `MISP_FQDN` | 主机名 |

随后脚本执行 `docker compose pull && docker compose up -d`。

## 生成 API Key（规格 §14）

MISP → Administration → Users → Auth Keys → 创建 `SecFlow` 专用 Key。

```dotenv
MISP_URL=https://localhost
MISP_API_KEY=********************************
MISP_VERIFY_SSL=false
```

**绝不硬编码**：Key 只存于 `.env`（已被 .gitignore 排除）。

## 检查

```bash
docker compose ps            # misp-core / misp-modules / db / redis
curl -k https://localhost/servers/getVersion
```
