import { useEffect, useState } from 'react'
import {
  Card, Tag, Typography, Space, Alert, Table, Button, message, Select, Input,
  Tabs, Popconfirm, Result,
} from 'antd'
import { RobotOutlined, SafetyCertificateOutlined, AuditOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import type { AuditLog, IOC } from '../services/types'

interface ProviderInfo {
  label: string
  base_url: string
  model: string
  needs_key: boolean
}

// =====================================================================
// 设置页 —— 极简三块：AI 接入（一键密钥）/ 威胁情报 / 审计
// =====================================================================
export default function Settings() {
  return (
    <Tabs
      defaultActiveKey="ai"
      items={[
        { key: 'ai', label: <span><RobotOutlined /> AI 接入</span>, children: <AiSetup /> },
        { key: 'ioc', label: <span><SafetyCertificateOutlined /> 威胁情报</span>, children: <IocManager /> },
        { key: 'audit', label: <span><AuditOutlined /> 审计日志</span>, children: <AuditLogs /> },
      ]}
    />
  )
}

// ---------------------------------------------------------------------
// AI 接入：选服务商 → 填密钥 → 保存（立即生效，无需重启）
// ---------------------------------------------------------------------
function AiSetup() {
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({})
  const [current, setCurrent] = useState<{ provider: string; model?: string; base_url?: string; key_configured?: boolean } | null>(null)
  const [provider, setProvider] = useState('mock')
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; status?: string; provider?: string; model?: string; error?: string } | null>(null)

  const load = async () => {
    const [p, c] = await Promise.all([
      api.get('/settings/llm/providers').then((r) => r.data.providers as Record<string, ProviderInfo>),
      api.get('/settings/llm').then((r) => r.data),
    ])
    setProviders(p)
    setCurrent(c)
    if (c?.provider && p[c.provider]) {
      setProvider(c.provider)
      if (!c.key_configured) setBaseUrl(c.base_url || p[c.provider].base_url)
      if (!c.model) setModel(c.model || p[c.provider].model)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const info = providers[provider]

  const save = async () => {
    setSaving(true)
    setTestResult(null)
    try {
      const r = await api.post('/settings/llm', {
        provider,
        api_key: apiKey,
        base_url: baseUrl,
        model,
      })
      message.success(`已保存：${r.data.provider} —— 立即生效，无需重启`)
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
    <Space direction="vertical" size={14} style={{ width: '100%', maxWidth: 760 }}>
      <Alert
        type="info"
        showIcon
        message="三步接入 AI：选服务商 → 粘贴密钥 → 保存（立即生效）"
        description="保存后无需修改 .env、无需重启服务。支持 DeepSeek / OpenAI / 通义千问 / Ollama 本地模型。"
      />

      <Card size="small" title="① 选择服务商">
        <Select
          style={{ width: 320 }}
          value={provider}
          onChange={(v) => {
            setProvider(v)
            setBaseUrl(providers[v]?.base_url || '')
            setModel(providers[v]?.model || '')
            setTestResult(null)
          }}
          options={Object.entries(providers).map(([k, v]) => ({ value: k, label: `${v.label}${current?.provider === k ? '（当前）' : ''}` }))}
        />
        <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
          {info?.label}：{info?.base_url || '无需地址'} · 默认模型 {info?.model || '—'}
        </Typography.Paragraph>
      </Card>

      <Card size="small" title={isMock ? '' : '② 填写密钥'}>
        {isMock ? (
          <Alert type="success" showIcon message="Mock 离线模式：无需任何密钥，规则研判可直接使用" />
        ) : isOllama ? (
          <Alert type="info" showIcon message="Ollama 本地模型：无需密钥。请确认 Ollama 已安装并运行（ollama pull qwen2.5:7b）" />
        ) : (
          <Space direction="vertical" style={{ width: '100%' }}>
            {isCustom && (
              <>
                <Input placeholder="Base URL（如 https://api.xxx.com/v1）" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
                <Input placeholder="模型名（如 deepseek-chat）" value={model} onChange={(e) => setModel(e.target.value)} />
              </>
            )}
            <Input.Password
              placeholder={current?.key_configured ? `已配置密钥 ${current.key_configured}（留空则保持不变）` : '粘贴 API 密钥（sk-...）'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
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
          message={testResult.ok
            ? `✅ 真实模型连接正常：${testResult.provider} / ${testResult.model}`
            : testResult.status === 'mock'
              ? '未接入真实模型（当前为 Mock 离线模式）'
              : `连接失败：${testResult.error}`}
        />
      )}

      {current && (
        <Alert
          type={current.provider === 'mock' ? 'warning' : 'success'}
          showIcon
          message={current.provider === 'mock'
            ? '当前状态：Mock 离线模式（未接入真实 AI）'
            : `当前状态：已接入 ${providers[current.provider]?.label ?? current.provider}${current.model ? `（${current.model}）` : ''}`}
          description={current.provider === 'mock'
            ? '系统 AI 功能可用（内置规则），但未调用任何真实模型。配置服务商与密钥后即可获得真实 AI 研判。'
            : 'AI 研判将调用该真实模型；若密钥失效或额度不足，分析会返回错误提示。'}
        />
      )}
    </Space>
  )
}

// ---------------------------------------------------------------------
// 威胁情报（IOC）—— 精简管理
// ---------------------------------------------------------------------
function IocManager() {
  const [items, setItems] = useState<IOC[]>([])
  const [loading, setLoading] = useState(false)
  const [value, setValue] = useState('')
  const [type, setType] = useState('ip')

  const load = async () => {
    setLoading(true)
    try {
      setItems((await api.get('/iocs', { params: { limit: 100 } })).data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const add = async () => {
    if (!value.trim()) return
    await api.post('/iocs', { type, value: value.trim(), source: 'manual', confidence: 0.8 })
    message.success('已添加')
    setValue('')
    load()
  }

  return (
    <Space direction="vertical" style={{ width: '100%', maxWidth: 760 }}>
      <Space>
        <Select style={{ width: 100 }} value={type} onChange={setType}
          options={['ip', 'domain', 'url', 'hash', 'email'].map((t) => ({ value: t, label: t }))} />
        <Input style={{ width: 280 }} placeholder="输入恶意指标，如 45.83.66.101" value={value} onChange={(e) => setValue(e.target.value)} onPressEnter={add} />
        <Button type="primary" onClick={add}>添加</Button>
      </Space>
      <Table
        rowKey="id" size="small" loading={loading} dataSource={items} pagination={{ pageSize: 10 }}
        columns={[
          { title: '类型', dataIndex: 'type', width: 80, render: (v: string) => <Tag color={v === 'ip' ? 'red' : 'blue'}>{v}</Tag> },
          { title: '指标值', dataIndex: 'value' },
          { title: '来源', dataIndex: 'source', width: 90 },
          { title: '置信度', dataIndex: 'confidence', width: 90, render: (v: number) => `${((v ?? 0) * 100).toFixed(0)}%` },
          {
            title: '', width: 60,
            render: (_, r: IOC) => (
              <Popconfirm title="删除？" onConfirm={async () => { await api.delete(`/iocs/${r.id}`); load() }}>
                <Button danger size="small" type="text">删</Button>
              </Popconfirm>
            ),
          },
        ]}
      />
      <Typography.Text type="secondary">关联引擎会自动匹配事件来源 IP/域名是否命中这些 IOC。</Typography.Text>
    </Space>
  )
}

// ---------------------------------------------------------------------
// 审计日志
// ---------------------------------------------------------------------
function AuditLogs() {
  const [items, setItems] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.get('/audit/logs', { params: { limit: 50 } })
      .then((r) => setItems(r.data))
      .finally(() => setLoading(false))
  }, [])

  if (!items.length && !loading) {
    return <Result status="success" title="暂无审计记录" subTitle="登录、扫描、AI 分析、审核等操作会自动记录在这里" />
  }
  return (
    <Table
      rowKey="id" size="small" loading={loading} dataSource={items} pagination={{ pageSize: 10 }}
      columns={[
        { title: '时间', dataIndex: 'timestamp', width: 170 },
        { title: '用户', dataIndex: 'username', width: 110 },
        { title: '操作', dataIndex: 'action', width: 180, render: (v: string) => <Tag color="blue">{v}</Tag> },
        { title: '详情', dataIndex: 'detail', render: (v: Record<string, unknown>) => JSON.stringify(v ?? {}) },
      ]}
    />
  )
}
