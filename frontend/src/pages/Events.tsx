import { useEffect, useState } from 'react'
import { Table, Space, Tag, Drawer, Descriptions, Typography } from 'antd'
import { api } from '../services/api'
import type { SecurityEvent } from '../services/types'
import StatusTag from '../components/StatusTag'

export default function Events() {
  const [items, setItems] = useState<SecurityEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<SecurityEvent | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      setItems((await api.get('/events', { params: { limit: 200 } })).data)
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
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <h2 style={{ margin: 0 }}>Events 安全事件（Wazuh）</h2>
        <Tag color="blue">每 15 秒自动刷新</Tag>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 15 }}
        onRow={(r) => ({ onClick: () => setSelected(r), style: { cursor: 'pointer' } })}
        columns={[
          { title: '时间', dataIndex: 'timestamp', width: 180 },
          { title: '严重性', dataIndex: 'severity', width: 100, render: (v) => <StatusTag value={v} /> },
          { title: '事件类型', dataIndex: 'event_type', ellipsis: true },
          { title: '来源', dataIndex: 'src_ip', width: 140 },
          { title: '目标', dataIndex: 'dst_ip', width: 140 },
          { title: '用户', dataIndex: 'user', width: 120 },
          { title: '置信度', dataIndex: 'confidence', width: 90, render: (v: number) => `${(v * 100).toFixed(0)}%` },
          {
            title: 'ATT&CK',
            dataIndex: 'techniques',
            width: 150,
            render: (v: string[]) => (v || []).map((t) => <Tag key={t}>{t}</Tag>),
          },
        ]}
      />
      <Drawer
        title={`事件详情 ${selected?.id ?? ''}`}
        open={!!selected}
        onClose={() => setSelected(null)}
        width={560}
      >
        {selected && (
          <>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="来源">{selected.source}</Descriptions.Item>
              <Descriptions.Item label="类型">{selected.event_type}</Descriptions.Item>
              <Descriptions.Item label="时间">{selected.timestamp}</Descriptions.Item>
              <Descriptions.Item label="严重性"><StatusTag value={selected.severity} /></Descriptions.Item>
              <Descriptions.Item label="置信度">{(selected.confidence * 100).toFixed(0)}%</Descriptions.Item>
              <Descriptions.Item label="源 IP">{selected.src_ip}:{selected.src_port}</Descriptions.Item>
              <Descriptions.Item label="目标 IP">{selected.dst_ip}:{selected.dst_port}</Descriptions.Item>
              <Descriptions.Item label="用户">{selected.user}</Descriptions.Item>
              <Descriptions.Item label="指示器">{(selected.indicators || []).join(', ') || '—'}</Descriptions.Item>
              <Descriptions.Item label="ATT&CK">{(selected.techniques || []).join(', ') || '—'}</Descriptions.Item>
            </Descriptions>
            <Typography.Title level={5} style={{ marginTop: 16 }}>原始数据 (raw)</Typography.Title>
            <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 8, fontSize: 12, overflow: 'auto', maxHeight: 300 }}>
              {JSON.stringify(selected, null, 2)}
            </pre>
          </>
        )}
      </Drawer>
    </>
  )
}
