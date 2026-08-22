import { useEffect, useState } from 'react'
import {
  Card, Descriptions, Tag, Typography, Space, Alert, Table, Button, message,
  Collapse,
} from 'antd'
import { CopyOutlined, ReloadOutlined, CheckCircleOutlined, RobotOutlined } from '@ant-design/icons'
import { api, healthApi } from '../services/api'
import type { HealthStatus } from '../services/types'

interface AiConfig {
  provider: string
  model: string
  base_url: string
  configured: boolean
}

export default function Settings() {
  const [health, setHealth] = useState<Record<string, HealthStatus>>({})
  const [aiConfig, setAiConfig] = useState<AiConfig | null>(null)
  const [testing, setTesting] = useState(false)

  const load = async () => {
    const [h, c] = await Promise.all([
      healthApi.all(),
      api.get('/health/config').catch(() => null),
    ])
    setHealth(h)
    if (c?.data?.llm) setAiConfig(c.data.llm)
  }

  useEffect(() => {
    load()
  }, [])

  const testConnection = async () => {
    setTesting(true)
    try {
      const r = await api.get('/health/llm')
      const ok = r.data?.ok
      if (ok) message.success('AI 连接正常')
      else message.warning(`连接异常: ${r.data?.error || '未知错误'}`)
      setHealth((h) => ({ ...h, llm: r.data }))
    } finally {
      setTesting(false)
    }
  }

  const rows = [
    ['API 服务', health.api],
    ['PostgreSQL', health.db],
    ['Redis', health.redis],
    ['Wazuh', health.wazuh],
    ['MISP', health.misp],
    ['LLM / AI', health.llm],
  ] as const

  const configSnippet = (provider: string) => {
    if (provider === 'ollama') {
      return `LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b`
    }
    if (provider === 'openai') {
      return `LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxxxxxxx
LLM_MODEL=gpt-4o-mini`
    }
    return 'LLM_PROVIDER=mock   # 离线规则研判，无需任何 Key'
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        title={<Space><RobotOutlined />AI 接入向导</Space>}
        extra={<Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>}
      >
        {aiConfig && (
          <>
            <Descriptions column={2} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="当前 Provider">
                <Tag color={aiConfig.provider === 'mock' ? 'default' : 'blue'}>{aiConfig.provider}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="模型">{aiConfig.model || '—'}</Descriptions.Item>
              <Descriptions.Item label="API 地址">{aiConfig.base_url || '—（mock 无需地址）'}</Descriptions.Item>
              <Descriptions.Item label="状态">
                {health.llm?.ok ? (
                  <Tag color="success" icon={<CheckCircleOutlined />}>✓ 可用</Tag>
                ) : (
                  <Tag color="warning">待配置/异常</Tag>
                )}
              </Descriptions.Item>
            </Descriptions>
            <Button type="primary" loading={testing} onClick={testConnection} style={{ marginBottom: 16 }}>
              测试 AI 连接
            </Button>
          </>
        )}

        <Alert
          style={{ marginBottom: 16 }}
          type={aiConfig?.provider === 'mock' ? 'info' : 'success'}
          showIcon
          message={aiConfig?.provider === 'mock'
            ? '当前为内置 Mock 模式（离线规则研判）—— 不需要任何 API Key 即可体验全流程，但研判能力有限'
            : `当前使用 ${aiConfig?.provider} 真实模型`}
          description="配置方法：编辑 .env 后重启容器（./scripts/linux/restart 或 docker compose up -d --build）。改动生效需重启 API 与 Worker。"
        />

        <Collapse
          items={[
            {
              key: 'ollama',
              label: '方式一：本地 Ollama（免费、隐私）',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Typography.Paragraph>
                    1. 安装 Ollama：<code>curl -fsSL https://ollama.com/install.sh | sh</code><br />
                    2. 拉取模型：<code>ollama pull qwen2.5:7b</code><br />
                    3. 在 .env 中配置：
                  </Typography.Paragraph>
                  <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 8 }}>
{configSnippet('ollama')}
                    <Button size="small" type="text" icon={<CopyOutlined />} onClick={() => {
                      navigator.clipboard.writeText(configSnippet('ollama'))
                      message.success('已复制')
                    }} />
                  </pre>
                </Space>
              ),
            },
            {
              key: 'openai',
              label: '方式二：OpenAI 兼容云端 API（DeepSeek / OpenAI / 通义等）',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Typography.Paragraph>
                    任意 OpenAI 兼容接口均可（含 DeepSeek、Moonshot、通义等），仅需 Base URL、Key 与模型名：
                  </Typography.Paragraph>
                  <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 8 }}>
{configSnippet('openai')}
                    <Button size="small" type="text" icon={<CopyOutlined />} onClick={() => {
                      navigator.clipboard.writeText(configSnippet('openai'))
                      message.success('已复制')
                    }} />
                  </pre>
                  <Typography.Paragraph type="secondary">
                    例如 DeepSeek：LLM_BASE_URL=https://api.deepseek.com/v1，LLM_MODEL=deepseek-chat
                  </Typography.Paragraph>
                </Space>
              ),
            },
            {
              key: 'mock',
              label: '方式三：Mock 离线模式（零配置，仅演示）',
              children: <Typography.Paragraph>{configSnippet('mock')}</Typography.Paragraph>,
            },
          ]}
        />
      </Card>

      <Card title="组件健康状态（未配置 ≠ 异常）">
        <Table
          rowKey="name"
          size="small"
          pagination={false}
          dataSource={rows.map(([name, h]) => ({ name, ...(h ?? { ok: false, status: 'error' }) }))}
          columns={[
            { title: '组件', dataIndex: 'name', width: 200 },
            {
              title: '状态',
              dataIndex: 'status',
              width: 160,
              render: (s: string, r: { ok: boolean; error?: string }) => {
                if (r.ok) return <Tag color="success">✓ 正常</Tag>
                if (s === 'not_configured') return <Tag>未配置（可选）</Tag>
                return <Tag color="error">✗ 异常</Tag>
              },
            },
            { title: '说明', dataIndex: 'error', render: (v?: string) => v ?? '—' },
            { title: 'Provider', dataIndex: 'provider', render: (v?: string) => v ?? '—' },
          ]}
        />
        <Alert
          style={{ marginTop: 12 }}
          type="info"
          showIcon
          message="Wazuh / MISP 为可选组件"
          description="不配置时系统仍可完整使用：手动录入事件、Nuclei 扫描（mock/docker/binary）、AI 研判、风险评分、人工审核与报告生成均不依赖它们。"
        />
      </Card>
    </Space>
  )
}
