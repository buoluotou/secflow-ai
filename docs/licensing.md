# 许可证说明

## SecFlow AI 代码

本仓库中所有原创代码（`backend/ frontend/ ai/ integrations/ risk/ reports/
datasets/ scripts/ deploy/ docs/`）以 **MIT License** 授权（见 `LICENSE`、
`NOTICE.md`）。

## 第三方组件

SecFlow AI **不包含**任何第三方源码副本；以下组件由 `deploy/` 脚本在安装时
从官方仓库克隆**指定版本**，各自保留独立许可证：

| 组件 | 用途 | 上游 | 许可证 | 部署方式 |
|------|------|------|--------|----------|
| Wazuh | SIEM 事件源 | [wazuh/wazuh-docker](https://github.com/wazuh/wazuh-docker) | GPL-2.0 | `deploy/wazuh/deploy.sh` @ `v4.14.7` |
| Nuclei | 漏洞扫描引擎 | [projectdiscovery/nuclei](https://github.com/projectdiscovery/nuclei) | MIT | Docker 镜像按任务启动 |
| MISP | 威胁情报平台 | [MISP/misp-docker](https://github.com/MISP/misp-docker) | AGPL-3.0 | `deploy/misp/deploy.sh` |

> 许可证隔离原则（规格 §63）：第三方组件不混入"原创代码"；本仓库只通过
> 公共 API / 容器与它们通信，因此不构成衍生作品。使用 SecFlow 部署 Wazuh /
> MISP / Nuclei 的组织应自行遵守各组件许可证（例如 Wazuh 的 GPL-2.0 义务
> 适用于其自身代码分发）。

## 依赖库

Python / Node 依赖清单见 `backend/pyproject.toml` 与 `frontend/package.json`，
均为各自许可证下的开源库（FastAPI、SQLAlchemy、React、Ant Design、ECharts 等）。

## 商标

Wazuh、Nuclei、MISP 等名称归各自所有者所有；本项目使用这些名称仅用于描述
互操作性，不表示背书或隶属关系。
