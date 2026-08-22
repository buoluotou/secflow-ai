import { useEffect, useState } from 'react'
import { Table, Tag, Space, Drawer, Descriptions, Select, message } from 'antd'
import { api } from '../services/api'
import type { Finding } from '../services/types'
import StatusTag from '../components/StatusTag'

const STATUSES = ['open', 'confirmed', 'false_positive', 'remediated', 'accepted_risk', 'closed']

export default function Findings() {
  const [items, setItems] = useState<Finding[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Finding | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      setItems((await api.get('/findings', { params: { limit: 300 } })).data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const changeStatus = async (id: string, status: string) => {
    await api.patch(`/findings/${id}`, { status })
    message.success(`状态已更新为 ${status}`)
    load()
  }

  return (
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <h2 style={{ margin: 0 }}>Findings 漏洞发现（Nuclei）</h2>
        <Tag color="blue">{items.length} 条</Tag>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 15 }}
        onRow={(r) => ({ onClick: () => setSelected(r), style: { cursor: 'pointer' } })}
        columns={[
          { title: '模板', dataIndex: 'template_id', width: 220, ellipsis: true },
          { title: '标题', dataIndex: 'title', ellipsis: true },
          { title: '严重性', dataIndex: 'severity', width: 100, render: (v) => <StatusTag value={v} /> },
          { title: 'CVSS', dataIndex: 'cvss', width: 80, render: (v?: number) => (v ? v.toFixed(1) : '—') },
          { title: 'CWE', dataIndex: 'cwe', width: 100 },
          {
            title: '状态',
            dataIndex: 'status',
            width: 150,
            render: (v: string, r: Finding) => (
              <Select
                size="small"
                value={v}
                options={STATUSES.map((s) => ({ value: s, label: s }))}
                onChange={(nv) => changeStatus(r.id, nv)}
                onClick={(e) => e.stopPropagation()}
              />
            ),
          },
        ]}
      />
      <Drawer title={`漏洞详情 ${selected?.id ?? ''}`} open={!!selected} onClose={() => setSelected(null)} width={620}>
        {selected && (
          <>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="模板">{selected.template_id}</Descriptions.Item>
              <Descriptions.Item label="标题">{selected.title}</Descriptions.Item>
              <Descriptions.Item label="描述">{selected.description}</Descriptions.Item>
              <Descriptions.Item label="严重性"><StatusTag value={selected.severity} /></Descriptions.Item>
              <Descriptions.Item label="CVSS">{selected.cvss}</Descriptions.Item>
              <Descriptions.Item label="CWE">{selected.cwe}</Descriptions.Item>
              <Descriptions.Item label="修复建议">{selected.remediation || '—'}</Descriptions.Item>
              <Descriptions.Item label="首次发现">{selected.first_seen}</Descriptions.Item>
              <Descriptions.Item label="最近发现">{selected.last_seen}</Descriptions.Item>
            </Descriptions>
            {selected.evidence && (
              <>
                <h4>匹配证据</h4>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 8, fontSize: 12, overflow: 'auto' }}>
                  {selected.evidence}
                </pre>
              </>
            )}
          </>
        )}
      </Drawer>
    </>
  )
}
