import { useEffect, useState } from 'react'
import { Table, Tag, Space, Input, Button, Modal, Form, Select, message, Popconfirm } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import type { IOC } from '../services/types'

const TYPES = ['ip', 'domain', 'url', 'hash', 'email']

export default function IOCs() {
  const [items, setItems] = useState<IOC[]>([])
  const [loading, setLoading] = useState(false)
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      setItems((await api.get('/iocs', { params: { q } })).data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const t = setTimeout(load, q ? 300 : 0)
    return () => clearTimeout(t)
  }, [q])

  const create = async () => {
    const values = await form.validateFields()
    await api.post('/iocs', values)
    message.success('IOC 已添加')
    setOpen(false)
    form.resetFields()
    load()
  }

  return (
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <Space>
          <h2 style={{ margin: 0 }}>IOCs 威胁情报</h2>
          <Input.Search placeholder="搜索 IOC 值" style={{ width: 240 }} onSearch={setQ} allowClear />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>添加 IOC</Button>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 15 }}
        columns={[
          { title: '类型', dataIndex: 'type', width: 90, render: (v) => <Tag color={v === 'ip' ? 'red' : 'blue'}>{v}</Tag> },
          { title: '值', dataIndex: 'value', ellipsis: true },
          { title: '来源', dataIndex: 'source', width: 100 },
          {
            title: '置信度',
            dataIndex: 'confidence',
            width: 100,
            render: (v: number) => <span style={{ color: v >= 0.8 ? '#cf1322' : undefined }}>{(v * 100).toFixed(0)}%</span>,
          },
          { title: '标签', dataIndex: 'tags', render: (v: string[]) => (v || []).map((t) => <Tag key={t}>{t}</Tag>) },
          { title: '最近发现', dataIndex: 'last_seen', width: 180 },
          {
            title: '操作',
            width: 90,
            render: (_, r: IOC) => (
              <Popconfirm title="删除该 IOC？" onConfirm={async () => {
                await api.delete(`/iocs/${r.id}`)
                load()
              }}>
                <Button danger size="small">删除</Button>
              </Popconfirm>
            ),
          },
        ]}
      />
      <Modal title="添加 IOC" open={open} onOk={create} onCancel={() => setOpen(false)}>
        <Form form={form} layout="vertical" initialValues={{ type: 'ip', source: 'manual', confidence: 0.8 }}>
          <Form.Item name="type" label="类型" rules={[{ required: true }]}>
            <Select options={TYPES.map((t) => ({ value: t, label: t }))} />
          </Form.Item>
          <Form.Item name="value" label="值" rules={[{ required: true }]}>
            <Input placeholder="例如 45.83.66.101 / bad.example.com" />
          </Form.Item>
          <Form.Item name="source" label="来源"><Input /></Form.Item>
          <Form.Item name="confidence" label="置信度"><Input type="number" min={0} max={1} step={0.1} /></Form.Item>
        </Form>
      </Modal>
    </>
  )
}
