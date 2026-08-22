import { useEffect, useState } from 'react'
import { Table, Tag, Drawer, Descriptions, Typography, Space, Select } from 'antd'
import { api } from '../services/api'
import type { AIAnalysis } from '../services/types'
import StatusTag from '../components/StatusTag'

const AGENTS = ['triage', 'threat', 'vuln', 'report']

export default function Analysis() {
  const [items, setItems] = useState<AIAnalysis[]>([])
  const [loading, setLoading] = useState(false)
  const [agent, setAgent] = useState<string | undefined>()
  const [selected, setSelected] = useState<AIAnalysis | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      setItems((await api.get('/analysis', { params: { agent_type: agent } })).data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [agent])

  return (
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <h2 style={{ margin: 0 }}>AI Analysis 研判记录</h2>
        <Select
          allowClear
          placeholder="按 Agent 过滤"
          style={{ width: 200 }}
          value={agent}
          onChange={setAgent}
          options={AGENTS.map((a) => ({ value: a, label: a }))}
        />
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 15 }}
        onRow={(r) => ({ onClick: () => setSelected(r), style: { cursor: 'pointer' } })}
        columns={[
          { title: '时间', dataIndex: 'created_at', width: 170 },
          { title: '事件', dataIndex: 'incident_id', width: 110, render: (v?: string) => (v ? <Tag>#{v.slice(0, 8)}</Tag> : '—') },
          { title: 'Agent', dataIndex: 'agent_type', width: 100, render: (v) => <Tag color="geekblue">{v}</Tag> },
          { title: '状态', dataIndex: 'status', width: 110, render: (v) => <StatusTag value={v} /> },
          { title: '模型', dataIndex: 'model', width: 120 },
          {
            title: '结果摘要',
            render: (_, r: AIAnalysis) => {
              if (r.status !== 'completed') return r.error || r.status
              const o = r.output
              if (r.agent_type === 'triage') return `${o.classification ?? '—'} / ${o.severity ?? '—'} / 置信 ${((o.confidence ?? 0) * 100).toFixed(0)}%`
              if (r.agent_type === 'threat') return o.malicious ? `恶意 (${((o.confidence ?? 0) * 100).toFixed(0)}%)` : '非恶意'
              if (r.agent_type === 'vuln') return `${o.authenticity ?? '—'} / 优先级 ${o.remediation_priority ?? '—'}`
              return o.summary?.slice(0, 80) || '—'
            },
          },
        ]}
      />
      <Drawer title={`AI 分析详情 ${selected?.id ?? ''}`} open={!!selected} onClose={() => setSelected(null)} width={640}>
        {selected && (
          <>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="Agent">{selected.agent_type}</Descriptions.Item>
              <Descriptions.Item label="模型">{selected.model}</Descriptions.Item>
              <Descriptions.Item label="提示词版本">{selected.prompt_version}</Descriptions.Item>
              <Descriptions.Item label="状态"><StatusTag value={selected.status} /></Descriptions.Item>
              {selected.error && <Descriptions.Item label="错误">{selected.error}</Descriptions.Item>}
            </Descriptions>
            <Typography.Title level={5} style={{ marginTop: 16 }}>输出 (Output)</Typography.Title>
            <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 8, fontSize: 12, overflow: 'auto', maxHeight: 400 }}>
              {JSON.stringify(selected.output, null, 2)}
            </pre>
          </>
        )}
      </Drawer>
    </>
  )
}
