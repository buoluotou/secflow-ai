import { useEffect, useState } from 'react'
import { Table, Tag, Space, Input } from 'antd'
import { api } from '../services/api'
import type { AuditLog } from '../services/types'

export default function Audit() {
  const [items, setItems] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(false)
  const [q, setQ] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      setItems((await api.get('/audit/logs', { params: { limit: 300 } })).data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const filtered = q ? items.filter((i) => JSON.stringify(i).includes(q)) : items

  return (
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <h2 style={{ margin: 0 }}>Audit 审计日志</h2>
        <Input.Search placeholder="搜索操作/资源" style={{ width: 260 }} onSearch={setQ} allowClear />
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={filtered}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: '时间', dataIndex: 'timestamp', width: 180 },
          { title: '用户', dataIndex: 'username', width: 120 },
          { title: '操作', dataIndex: 'action', width: 200, render: (v) => <Tag color="blue">{v}</Tag> },
          { title: '资源类型', dataIndex: 'resource_type', width: 130 },
          { title: '资源 ID', dataIndex: 'resource_id', width: 110, render: (v?: string) => (v ? <Tag>#{v.slice(0, 8)}</Tag> : '—') },
          { title: 'IP', dataIndex: 'ip', width: 130 },
          { title: '详情', dataIndex: 'detail', render: (v: Record<string, unknown>) => JSON.stringify(v ?? {}) },
        ]}
      />
    </>
  )
}
