import { useEffect, useState } from 'react'
import {
  Card, Tag, Typography, Space, Alert, Table, Button, message, Select, Input,
  Tabs, Popconfirm, Descriptions, Form, Statistic, Row, Col,
} from 'antd'
import {
  HeartOutlined, RobotOutlined, DatabaseOutlined, LockOutlined,
  ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons'
import { api, healthApi } from '../services/api'
import type { HealthStatus } from '../services/types'

// =====================================================================
// 系统维护：健康诊断 / AI 接入 / 数据管理 / 账号
// =====================================================================
export default function Maintenance() {
  return (
    <Tabs
      defaultActiveKey="health"
      items={[
        { key: 'health', label: <span><HeartOutlined /> 健康诊断</span>, children: <HealthCheck /> },
        { key: 'ai', label: <span><RobotOutlined /> AI 接入</span>, children: <AiSetup /> },
        { key: 'data', label: <span><DatabaseOutlined /> 数据管理</span>, children: <DataManager /> },
        { key: 'account', label: <span><LockOutlined /> 账号</span>, children: <AccountPanel /> },
      ]}
    />
  )
}

// ---------------------------------------------------------------------
// 健康诊断
// ---------------------------------------------------------------------
function HealthCheck() {
  const [health, setHealth] = useState<Record<string, HealthStatus>>({})
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      setHealth(await healthApi.all())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const rows = [
    ['API 服务', health.api],
    ['PostgreSQL', health.db],
    ['Redis', health.redis],
    ['Wazuh', health.wazuh],
    ['MISP', health.misp],
    ['LLM / AI', health.llm],
  ] as const

  return (
    <Space direction="vertical" style={{ width: '100%', maxWidth: 760 }}>
      <Table
        rowKey="name" size="small" loading={loading} pagination={false}
        dataSource={rows.map(([name, h]) => ({ name, ...(h ?? { ok: false, status: 'error' }) }))}
        columns={[
          { title: '组件', dataIndex: 'name', width: 180 },
          {
            title: '状态', dataIndex: 'status', width: 220,
            render: (s: string, r: { ok: boolean; error?: string; provider?: string }) => {
              if (s === 'mock') return <Tag color="blue" icon={<RobotOutlined />}>Mock 模式（未接入真实 AI）</Tag>
              if (r.ok) return <Tag color="success" icon={<CheckCircleOutlined />}>✓ 正常</Tag>
              if (s === 'not_configured') return <Tag>未配置（可选）</Tag>
              return <Tag color="error" icon={<CloseCircleOutlined />}>✗ 异常</Tag>
            },
          },
          { title: '说明', dataIndex: 'error', render: (v?: string) => v ?? '—' },
        ]}
      />
      <Alert
        type="info" showIcon
        message="Wazuh / MISP 为可选组件"
        description="不配置也可完整使用：手动事件录入、漏洞扫描、AI 研判、风险评分、报告生成均不依赖它们。"
      />
    </Space>
  )
}

// ---------------------------------------------------------------------
// AI 接入（一键密钥）
// ---------------------------------------------------------------------
interface ProviderInfo { label: string; base_url: string; model: string; needs_key: boolean }

function AiSetup() {
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({})
  const [current, setCurrent] = useState<{ provider: string; model?: string; key_configured?: boolean } | null>(null)
  const [provider, setProvider] = useState('mock')
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; status?: string; error?: string } | null>(null)

  const load = async () => {
    const [p, c] = await Promise.all([
      api.get('/settings/llm/providers').then((r) => r.data.providers as Record<string, ProviderInfo>),
      api.get('/settings/llm').then((r) => r.data),
    ])
    setProviders(p)
    setCurrent(c)
    if (c?.provider && p[c.provider]) setProvider(c.provider)
  }

  useEffect(() => { load() }, [])

  const info = providers[provider]

  const save = async () => {
    setSaving(true)
    setTestResult(null)
    try {
      const r = await api.post('/settings/llm', {
        provider, api_key: apiKey,
        base_url: baseUrl || info?.base_url || '',
        model: model || info?.model || '',
      })
      message.success(`已启用：${r.data.provider}（立即生效，无需重启）`)
      setApiKey('')
      setCurrent(r.data)
    } catch (e: unknown) {
      message.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const test = async () => {
    setTesting(true)
    try {
      const r = await api.post('/settings/llm/test')
      setTestResult(r.data)
      if (r.data.ok) message.success('✅ 真实模型连接正常')
      else if (r.data.status === 'mock') message.warning('未接入真实模型（当前为 Mock 模式）')
      else message.warning(`连接失败：${r.data.error}`)
    } catch {
      setTestResult({ ok: false, error: '请求失败' })
    } finally {
      setTesting(false)
    }
  }

  const reset = async () => {
    await api.delete('/settings/llm')
    message.success('已恢复默认（mock 离线模式）')
    load()
  }

  const isMock = provider === 'mock'
  const isOllama = provider === 'ollama'
  const isCustom = provider === 'custom'

  return (
    <Space direction="vertical" size={14} style={{ width: '100%', maxWidth: 700 }}>
      <Alert
        type="info" showIcon
        message="三步接入：选服务商 → 粘贴密钥 → 保存（立即生效，无需重启）"
        description="支持 DeepSeek / OpenAI / 通义千问 / Ollama 本地 / 自定义兼容接口。"
      />
      <Card size="small" title="① 服务商">
        <Select
          style={{ width: 320 }} value={provider}
          onChange={(v) => { setProvider(v); setTestResult(null) }}
          options={Object.entries(providers).map(([k, v]) => ({ value: k, label: `${v.label}${current?.provider === k ? '（当前）' : ''}` }))}
        />
        <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
          {info?.label} · {info?.base_url || '无需地址'} · 默认模型 {info?.model || '—'}
        </Typography.Paragraph>
      </Card>
      <Card size="small" title="② 密钥">
        {isMock ? (
          <Alert type="success" showIcon message="Mock 离线模式：无需密钥，规则研判可直接使用" />
        ) : isOllama ? (
          <Alert type="info" showIcon message="Ollama 本地模型：无需密钥。请确认已安装并运行（ollama pull qwen2.5:7b）" />
        ) : (
          <Space direction="vertical" style={{ width: '100%' }}>
            {isCustom && (
              <>
                <Input placeholder="Base URL（如 https://api.xxx.com/v1）" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
                <Input placeholder="模型名" value={model} onChange={(e) => setModel(e.target.value)} />
              </>
            )}
            <Input.Password
              placeholder={current?.key_configured ? `已配置密钥（留空保持不变）` : '粘贴 API 密钥（sk-...）'}
              value={apiKey} onChange={(e) => setApiKey(e.target.value)}
            />
          </Space>
        )}
      </Card>
      <Space>
        <Button type="primary" loading={saving} onClick={save}>保存并启用</Button>
        <Button loading={testing} onClick={test}>测试连接</Button>
        <Popconfirm title="恢复为默认 mock 模式？" onConfirm={reset}>
          <Button danger>重置</Button>
        </Popconfirm>
      </Space>
      {testResult && (
        <Alert
          type={testResult.ok ? 'success' : testResult.status === 'mock' ? 'warning' : 'error'}
          showIcon
          message={testResult.ok ? '✅ 真实模型连接正常' : testResult.status === 'mock' ? '未接入真实模型（Mock 模式）' : `连接失败：${testResult.error}`}
        />
      )}
      {current && (
        <Alert
          type={current.provider === 'mock' ? 'warning' : 'success'} showIcon
          message={current.provider === 'mock'
            ? '当前：Mock 离线模式（未接入真实 AI）'
            : `当前：已接入 ${providers[current.provider]?.label ?? current.provider}${current.model ? `（${current.model}）` : ''}`}
          description={current.provider === 'mock'
            ? 'AI 功能可用（内置规则）。配置服务商与密钥后获得真实 AI 研判。'
            : 'AI 研判将调用该真实模型；密钥失效或额度不足时分析会返回错误提示。'}
        />
      )}
    </Space>
  )
}

// ---------------------------------------------------------------------
// 数据管理
// ---------------------------------------------------------------------
function DataManager() {
  const [stats, setStats] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      setStats((await api.get('/maintenance/stats')).data.tables)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const resetData = async () => {
    await api.post('/maintenance/reset-data')
    message.success('已清空全部业务数据')
    load()
  }

  const labels: Record<string, string> = {
    security_events: '安全事件', incidents: '安全事件(Incidents)', findings: '漏洞',
    iocs: '威胁情报', scans: '扫描任务', reports: '报告', audit_logs: '审计日志',
    assets: '资产', ai_analyses: 'AI 分析', evidence: '证据',
  }

  const rows = Object.entries(stats)
    .filter(([k]) => k !== 'users' && k !== 'projects')
    .map(([k, v]) => ({ name: labels[k] ?? k, count: v }))

  return (
    <Space direction="vertical" style={{ width: '100%', maxWidth: 760 }}>
      <Row gutter={[12, 12]}>
        {Object.entries(stats).filter(([k]) => k === 'users' || k === 'projects').map(([k, v]) => (
          <Col span={6} key={k}>
            <Card size="small"><Statistic title={k === 'users' ? '用户账号' : '项目' } value={v} /></Card>
          </Col>
        ))}
      </Row>
      <Table
        rowKey="name" size="small" loading={loading} pagination={false}
        dataSource={rows}
        columns={[
          { title: '数据类型', dataIndex: 'name' },
          { title: '数量', dataIndex: 'count', width: 120 },
        ]}
      />
      <Alert
        type="warning" showIcon
        message="清空数据将删除全部事件、漏洞、扫描、报告与审计记录（用户账号和 AI 配置保留），不可恢复！"
      />
      <Space>
        <Button icon={<ReloadOutlined />} onClick={load}>刷新统计</Button>
        <Popconfirm title="确认清空全部业务数据？此操作不可恢复！" onConfirm={resetData}>
          <Button danger>清空全部数据</Button>
        </Popconfirm>
      </Space>
    </Space>
  )
}

// ---------------------------------------------------------------------
// 账号
// ---------------------------------------------------------------------
function AccountPanel() {
  const [form] = Form.useForm()
  const [saving, setSaving] = useState(false)
  const [me, setMe] = useState<{ username?: string; role?: string } | null>(null)

  useEffect(() => {
    api.get('/auth/me').then((r) => setMe(r.data)).catch(() => null)
  }, [])

  const changePwd = async () => {
    const v = await form.validateFields()
    setSaving(true)
    try {
      await api.post('/auth/change-password', { old_password: v.old_password, new_password: v.new_password })
      message.success('密码已修改')
      form.resetFields()
    } catch (e: unknown) {
      message.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '修改失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Space direction="vertical" style={{ width: '100%', maxWidth: 520 }}>
      {me && (
        <Card size="small" title="当前账号">
          <Descriptions column={2} size="small">
            <Descriptions.Item label="用户名">{me.username}</Descriptions.Item>
            <Descriptions.Item label="角色">{me.role}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}
      <Card size="small" title="修改密码">
        <Form form={form} layout="vertical">
          <Form.Item name="old_password" label="原密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="new_password" label="新密码（至少 8 位）" rules={[{ required: true, min: 8 }]}>
            <Input.Password />
          </Form.Item>
          <Button type="primary" loading={saving} onClick={changePwd}>修改密码</Button>
        </Form>
      </Card>
    </Space>
  )
}
