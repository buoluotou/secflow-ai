import { useEffect, useState } from 'react'
import { Table, Tag, Space, Input, Select, Button, Typography, Card, Statistic, Row, Col, message } from 'antd'
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import type { AuditLog } from '../services/types'

// =====================================================================
// 日志审查：操作日志（筛选 / 统计 / 导出）
// =====================================================================
export default function Audit() {
  const [items, setItems] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(false)
  const [action, setAction] = useState<string | undefined>()
  const [q, setQ] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { limit: 300 }
      if (action) params.action = action
      setItems((await api.get('/audit/logs', { params })).data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [action])

  const filtered = q ? items.filter((i) => JSON.stringify(i).includes(q)) : items

  // 操作类型统计（去前缀归类）
  const stats = new Map<string, number>()
  for (const i of filtered) {
    const cat = i.action.split('.')[0] ?? i.action
    stats.set(cat, (stats.get(cat) ?? 0) + 1)
  }

  const exportCsv = () => {
    const header = ['时间', '用户', '操作', '资源类型', '资源ID', 'IP', '详情']
    const lines = filtered.map((i) => [
      i.timestamp ?? '', i.username ?? '', i.action ?? '',
      i.resource_type ?? '', i.resource_id ?? '', i.ip ?? '',
      JSON.stringify(i.detail ?? {}),
    ].map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))
    const csv = '\ufeff' + [header.join(','), ...lines].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `secflow_audit_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    message.success(`已导出 ${filtered.length} 条日志`)
  }

  const actionOptions = [...new Set(items.map((i) => i.action))].sort()

  return (
    <Space direction="vertical" size={14} style={{ width: '100%' }}>
      <Row gutter={[12, 12]}>
        {['auth', 'project', 'asset', 'event', 'scan', 'ai', 'incident', 'report', 'correlation', 'settings', 'user', 'maintenance']
          .map((cat) => (
            <Col span={4} key={cat}>
              <Card size="small">
                <Statistic title={cat} value={stats.get(cat) ?? 0} />
              </Card>
            </Col>
          ))}
      </Row>

      <Space wrap>
        <Select
          allowClear placeholder="按操作类型筛选" style={{ width: 240 }} value={action} onChange={setAction}
          options={actionOptions.map((a) => ({ value: a, label: a }))}
        />
        <Input.Search placeholder="搜索用户 / 资源 / 内容" style={{ width: 260 }} onSearch={setQ} allowClear />
        <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
        <Button type="primary" icon={<DownloadOutlined />} onClick={exportCsv}>导出 CSV</Button>
      </Space>

      <Table
        rowKey="id" size="small" loading={loading} dataSource={filtered} pagination={{ pageSize: 20 }}
        locale={{ emptyText: '暂无操作日志 —— 登录、扫描、AI 分析、审核等操作会自动记录' }}
        columns={[
          { title: '时间', dataIndex: 'timestamp', width: 170 },
          { title: '用户', dataIndex: 'username', width: 110 },
          { title: '操作', dataIndex: 'action', width: 190, render: (v: string) => <Tag color="blue">{v}</Tag> },
          { title: '资源', dataIndex: 'resource_id', width: 110, render: (v?: string) => (v ? <Tag>#{v.slice(0, 8)}</Tag> : '—') },
          { title: 'IP', dataIndex: 'ip', width: 120 },
          { title: '详情', dataIndex: 'detail', render: (v: Record<string, unknown>) => JSON.stringify(v ?? {}) },
        ]}
      />
      <Typography.Text type="secondary">
        💡 日志自动记录：登录、资产/事件/漏洞操作、扫描、AI 分析、人工审核、报告生成、配置修改与数据维护。可用于安服合规审查与溯源。
      </Typography.Text>
    </Space>
  )
}
