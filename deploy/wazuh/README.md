# Wazuh 部署（SecFlow AI 集成）

> 原则（规格 §62）：不把 `wazuh-docker` 仓库提交进 SecFlow 仓库。
> 安装时由脚本克隆官方**指定版本**。

## 前置条件

- Docker Engine + Compose plugin
- `vm.max_map_count = 262144`（脚本自动设置，规格 §7）

## 部署

```bash
./deploy/wazuh/deploy.sh
```

脚本执行：

1. 设置 `vm.max_map_count=262144`（永久写入 `/etc/sysctl.d/99-wazuh.conf`）
2. 克隆 https://github.com/wazuh/wazuh-docker 并 checkout `v4.14.7`
3. 生成 Indexer 证书（幂等）
4. `docker compose up -d` 启动 single-node 栈

## 接入 SecFlow

```dotenv
WAZUH_URL=https://localhost:55000
WAZUH_USERNAME=admin
WAZUH_PASSWORD=********
WAZUH_VERIFY_SSL=false
```

SecFlow 通过 Wazuh API（`/security/events`）拉取告警（Celery 定时同步），
也可通过 Webhook 实时接收（见 `integrations/wazuh/webhook.py`）。

## 安全建议（规格 §12）

- 只暴露 Dashboard / Agent / 必要 API
- PostgreSQL、Indexer 等内部组件不直接暴露公网
- 生产环境置于反向代理之后

## 检查

```bash
docker compose ps            # wazuh.manager / wazuh.indexer / wazuh.dashboard
curl -k https://localhost:55000   # Wazuh API
```

首次启动时 Indexer 和 Dashboard 可能出现暂时性连接失败，等待初始化完成即可。
