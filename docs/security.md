# 安全说明

## 设计约束（规格 §4）

1. **AI 不做最终风险决策** —— 风险由 Risk Engine 确定性计算
2. **高风险动作必须人工批准** —— `ai/reasoning/decision.py` 中的
   `is_high_risk()` 列表（封禁 IP、隔离资产、禁用账号等）永远不自动执行
3. **AI 结论必须绑定证据** —— 引用不存在的证据 ID 会被拒绝
4. **只做防御研判** —— 平台定位是 Security Service Copilot，不是攻击平台

## 部署安全

- 默认凭据 `admin / Admin@123456` 首次登录后**必须修改**（或部署时通过
  `SECFLOW_ADMIN_USER / SECFLOW_ADMIN_PASSWORD` 环境变量覆盖）
- `.env` 绝不提交；`SECRET_KEY`、`POSTGRES_PASSWORD`、`MISP_API_KEY` 均需替换
- 生产环境置于反向代理 + TLS 之后；内部组件只进内部网络（规格 §12）
- Wazuh / MISP 默认凭据部署后立即修改

## 报告漏洞

请勿在公开 issue 中提交漏洞细节。联系仓库维护者进行负责任披露。
