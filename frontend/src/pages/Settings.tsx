import { useEffect, useState } from 'react'
import { Card, Descriptions, Tag, Typography, Space, Alert, Table } from 'antd'
import { healthApi } from '../services/api'
import type { HealthStatus } from '../services/types'

export default function Settings() {
  const [health, setHealth] = useState<Record<string, HealthStatus>>({})

  useEffect(() => {
    healthApi.all().then(setHealth)
  }, [])

  const rows = [
    ['API 服务', health.api],
    ['PostgreSQL', health.db],
    ['Redis', health.redis],
    ['Wazuh', health.wazuh],
    ['MISP', health.misp],
    ['LLM / AI', health.llm],
  ] as const

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card title="Settings 系统设置">
        <Typography.Paragraph type="secondary">
          SecFlow AI — AI 驱动的网络安全服务智能化平台。所有配置通过环境变量提供
          （<code>.env</code>），请勿在前端修改敏感配置。
        </Typography.Paragraph>
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="默认管理员">admin / Admin@123456（首次登录后请立即修改！）</Descriptions.Item>
          <Descriptions.Item label="LLM Provider">默认 mock（离线规则研判）；配置 LLM_PROVIDER=openai/ollama 启用真实模型</Descriptions.Item>
          <Descriptions.Item label="架构原则">
            资产 → Wazuh/Nuclei → 事件/漏洞 → 标准化 → IOC/威胁情报 → 事件关联 → 证据链 → AI 研判 → 风险评分 → 人工审核 → 安全报告
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="组件健康状态">
        <Table
          rowKey="name"
          size="small"
          pagination={false}
          dataSource={rows.map(([name, h]) => ({ name, ...(h ?? { ok: false }) }))}
          columns={[
            { title: '组件', dataIndex: 'name', width: 200 },
            {
              title: '状态',
              dataIndex: 'ok',
              width: 140,
              render: (ok: boolean) => (ok ? <Tag color="success">✓ 正常</Tag> : <Tag color="error">✗ 异常</Tag>),
            },
            { title: '详情', dataIndex: 'error', render: (v?: string) => v ?? '—' },
            { title: 'Provider', dataIndex: 'provider', render: (v?: string) => v ?? '—' },
          ]}
        />
        {!health.llm?.ok && (
          <Alert
            style={{ marginTop: 12 }}
            type="info"
            showIcon
            message="LLM 未配置时使用内置 mock 模式"
            description="设置 LLM_PROVIDER / LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 后可切换到 OpenAI-compatible 或 Ollama。"
          />
        )}
      </Card>
    </Space>
  )
}
