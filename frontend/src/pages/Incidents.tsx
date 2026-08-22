import { useEffect, useState } from 'react'
import { Table, Space, Tag, Button, message } from 'antd'
import { RobotOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { Incident } from '../services/types'
import StatusTag from '../components/StatusTag'

export default function Incidents() {
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
      message.error('AI 分析失败')
    } finally {
      setAnalyzing(null)
    }
  }

  return (
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <h2 style={{ margin: 0 }}>Incidents 安全事件</h2>
        <Tag color="volcano">{items.filter((i) => i.status !== 'closed' && i.status !== 'resolved').length} 个未闭环</Tag>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 15 }}
        onRow={(r) => ({ onClick: () => navigate(`/incidents/${r.id}`), style: { cursor: 'pointer' } })}
        columns={[
          { title: '编号', dataIndex: 'id', width: 100, render: (v: string) => <Tag>#{v.slice(0, 8)}</Tag> },
          { title: '标题', dataIndex: 'title', ellipsis: true },
          { title: '严重性', dataIndex: 'severity', width: 100, render: (v) => <StatusTag value={v} /> },
          { title: '状态', dataIndex: 'status', width: 120, render: (v) => <StatusTag value={v} /> },
          {
            title: '置信度',
            dataIndex: 'confidence',
            width: 90,
            render: (v: number) => `${((v || 0) * 100).toFixed(0)}%`,
          },
          { title: '攻击阶段', dataIndex: 'attack_stage', width: 130 },
          { title: '检测时间', dataIndex: 'detected_at', width: 170 },
          {
            title: '操作',
            width: 160,
            render: (_, r: Incident) => (
              <Space onClick={(e) => e.stopPropagation()}>
                <Button
                  size="small"
                  type="primary"
                  ghost
                  icon={<RobotOutlined />}
                  loading={analyzing === r.id}
                  onClick={() => analyze(r.id)}
                >
                  AI 研判
                </Button>
                <Button size="small" onClick={() => navigate(`/incidents/${r.id}`)}>详情</Button>
              </Space>
            ),
          },
        ]}
      />
    </>
  )
}
