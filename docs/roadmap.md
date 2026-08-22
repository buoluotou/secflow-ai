# 路线图

## V1（当前版本）

- [x] 统一安全数据模型（15 表）
- [x] Wazuh / Nuclei / MISP 适配器
- [x] Correlation Engine（资产 / IP / 域名 / 用户 / IOC / 时间 关联）
- [x] Evidence Engine（内容寻址证据链 + AI 结论证据绑定校验）
- [x] Context Engine（统一上下文）
- [x] AI Agents：Triage / Threat / Vulnerability / Report
- [x] Risk Engine（六因子确定性计算，可校准）
- [x] Human Review（Approve / Reject / Modify）
- [x] Report Engine（Markdown + PDF）
- [x] Dashboard（统计 + 趋势 + 健康状态）
- [x] 审计日志（JSON 结构化）
- [x] 异步任务（Celery + Redis）
- [x] Docker Compose（base / dev / prod）+ Windows / Linux 脚本
- [x] AI 评测集与指标（Precision / Recall / F1 / FPR / 证据覆盖率 / 幻觉率）
- [x] Demo 01：Web 入侵事件自动研判

## V2（规格 §65）

- [ ] DefectDojo —— 漏洞生命周期管理
- [ ] Shuffle —— SOAR / 自动化工作流
- [ ] 通知：Email / Webhook / 即时消息
- [ ] Playbook 编排
- [ ] Attack Graph 攻击图
- [ ] Threat Hunting 主动狩猎
- [ ] scan_jobs / audit_logs 深度报表（表已预留）

## V3（规格 §66）

- [ ] Evidence-Grounded Agent（更严格证据接地）
- [ ] Context-Aware Risk（上下文感知风险）
- [ ] AI Evaluation 常态化（CI 中跑评测集）
- [ ] Human Feedback 闭环（用人工审核结果持续校准）
- [ ] Risk Calibration（基于评测集自动调参）
- [ ] Agent Memory（长期记忆）
- [ ] 论文 / 技术文章 / 安全社区投稿材料

## 研究指标（规格 §55）

核心研究价值：**人工 vs AI 辅助**对比

| 指标 | 人工 | AI 辅助 |
|------|------|---------|
| Mean Triage Time | ~20 分钟/事件 | ~5 分钟/事件 |
| Mean Report Time | ~30 分钟 | ~8 分钟 |
| MTTR | 基准 | 显著下降 |
