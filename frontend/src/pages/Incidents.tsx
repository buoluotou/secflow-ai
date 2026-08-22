import { useEffect, useState } from 'react'
import { Table, Space, Button, message, Tabs, Typography } from 'antd'
import { RobotOutlined, AlertOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { Incident, SecurityEvent } from '../services/types'
import StatusTag from '../components/StatusTag'

export default function Incidents() {
  return (
    <Tabs
      defaultActiveKey="incidents"
      items={[
        { key: 'incidents', label: <span><AlertOutlined /> 安全事件</span>, children: <IncidentList /> },
        { key: 'events', label: <span><ThunderboltOutlined /> 原始告警</span>, children: <RawEvents /> },
      ]}
    />
  )
}

// ---------------------------------------------------------------------
// 安全事件（Incidents）—— 关联引擎自动生成，AI 研判入口
// ---------------------------------------------------------------------
function IncidentList() {
  const navigate = useNavigate()
  const [items, setItems] = useState<Incident[]>([])
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      setItems((await api.get('/incidents', { params: { limit: 200 } })).data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const analyze = async (id: string) => {
    setAnalyzing(id)
    try {
      const r = await api.post(`/incidents/${id}/analyze`, { force: true })
      message.success(`AI 分析完成，风险等级：${r.data?.results?.risk?.risk_level ?? '—'}`)
      load()
    } catch {
      message.error('AI 分析失败（请先在设置中配置 AI 密钥）')
    } finally {
      setAnalyzing(null)
    }
  }

  return (
    <>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 15 }}
        locale={{ emptyText: '暂无安全事件 —— 注入告警或发起扫描后，关联引擎会自动生成' }}
        onRow={(r) => ({ onClick: () => navigate(`/incidents/${r.id}`), style: { cursor: 'pointer' } })}
        columns={[
          { title: '标题', dataIndex: 'title', ellipsis: true },
          { title: '严重性', dataIndex: 'severity', width: 90, render: (v) => <StatusTag value={v} /> },
          { title: '状态', dataIndex: 'status', width: 110, render: (v) => <StatusTag value={v} /> },
          { title: '置信度', dataIndex: 'confidence', width: 80, render: (v: number) => `${((v || 0) * 100).toFixed(0)}%` },
          { title: '时间', dataIndex: 'detected_at', width: 160 },
          {
            title: '操作', width: 150,
            render: (_, r: Incident) => (
              <Space onClick={(e) => e.stopPropagation()}>
                <Button size="small" type="primary" ghost icon={<RobotOutlined />} loading={analyzing === r.id} onClick={() => analyze(r.id)}>
                  AI 研判
                </Button>
                <Button size="small" onClick={() => navigate(`/incidents/${r.id}`)}>详情</Button>
              </Space>
            ),
          },
        ]}
      />
      <Typography.Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
        💡 点击"AI 研判"：AI 自动分析事件 → 风险评分 → 人工审核 → 生成报告。需先在「设置 → AI 接入」配置密钥。
      </Typography.Text>
    </>
  )
}

// ---------------------------------------------------------------------
// 原始告警（Wazuh Events）—— 精简只读列表
// ---------------------------------------------------------------------
function RawEvents() {
  const [items, setItems] = useState<SecurityEvent[]>([])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      setItems((await api.get('/events', { params: { limit: 100 } })).data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [])

  return (
    <Table
      rowKey="id" size="small" loading={loading} dataSource={items} pagination={{ pageSize: 15 }}
      locale={{ emptyText: '暂无告警 —— Wazuh 接入后自动同步（也可在 API 中手动注入）' }}
      columns={[
        { title: '时间', dataIndex: 'timestamp', width: 160 },
        { title: '严重性', dataIndex: 'severity', width: 90, render: (v) => <StatusTag value={v} /> },
        { title: '告警类型', dataIndex: 'event_type', ellipsis: true },
        { title: '源 IP', dataIndex: 'src_ip', width: 130 },
        { title: '目标', dataIndex: 'dst_ip', width: 130 },
        { title: '置信度', dataIndex: 'confidence', width: 80, render: (v: number) => `${((v || 0) * 100).toFixed(0)}%` },
      ]}
    />
  )
}
