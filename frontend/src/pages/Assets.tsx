import { useEffect, useMemo, useState } from 'react'
import { Table, Button, Modal, Form, Input, Select, Space, message, Tag, Popconfirm, Slider } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import type { Asset, Project } from '../services/types'

const TYPES = ['server', 'workstation', 'network', 'webapp', 'database', 'cloud', 'iot', 'other']
const ENVS = ['production', 'staging', 'development', 'test', 'dmz', 'internal']

export default function Assets() {
  const [items, setItems] = useState<Asset[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      const [assets, proj] = await Promise.all([
        api.get('/assets', { params: { q } }),
        api.get('/projects'),
      ])
      setItems(assets.data)
      setProjects(proj.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const t = setTimeout(load, q ? 300 : 0)
    return () => clearTimeout(t)
  }, [q])

  const projectName = useMemo(() => {
    const m = new Map(projects.map((p) => [p.id, p.name]))
    return (id?: string) => (id ? m.get(id) ?? id : '—')
  }, [projects])

  const create = async () => {
    const values = await form.validateFields()
    await api.post('/assets', values)
    message.success('资产已添加')
    setOpen(false)
    form.resetFields()
    load()
  }

  return (
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <Space>
          <h2 style={{ margin: 0 }}>Assets 资产</h2>
          <Input.Search placeholder="搜索名称/IP/域名" style={{ width: 240 }} onSearch={setQ} allowClear />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>添加资产</Button>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 10 }}
        columns={[
          { title: '名称', dataIndex: 'name' },
          { title: '项目', dataIndex: 'project_id', render: projectName },
          { title: 'IP', dataIndex: 'ip' },
          { title: '域名', dataIndex: 'domain' },
          { title: '类型', dataIndex: 'asset_type', render: (v) => <Tag>{v}</Tag> },
          { title: '环境', dataIndex: 'environment' },
          {
            title: '关键性',
            dataIndex: 'criticality',
            render: (v: number) => (
              <span style={{ color: v >= 4 ? '#cf1322' : v === 3 ? '#fa8c16' : undefined }}>{'★'.repeat(v)}</span>
            ),
          },
          { title: '状态', dataIndex: 'status' },
          {
            title: '操作',
            width: 110,
            render: (_, r: Asset) => (
              <Popconfirm
                title="确认删除？"
                onConfirm={async () => {
                  await api.delete(`/assets/${r.id}`)
                  message.success('已删除')
                  load()
                }}
              >
                <Button danger size="small">删除</Button>
              </Popconfirm>
            ),
          },
        ]}
      />
      <Modal title="添加资产" open={open} onOk={create} onCancel={() => setOpen(false)} width={520}>
        <Form form={form} layout="vertical" initialValues={{ asset_type: 'server', environment: 'production', criticality: 3 }}>
          <Form.Item name="project_id" label="所属项目" rules={[{ required: true }]}>
            <Select options={projects.map((p) => ({ label: p.name, value: p.id }))} placeholder="选择项目" />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="web-01" />
          </Form.Item>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="hostname" label="主机名"><Input /></Form.Item>
            <Form.Item name="ip" label="IP"><Input placeholder="10.10.10.10" /></Form.Item>
            <Form.Item name="domain" label="域名"><Input /></Form.Item>
          </Space>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="asset_type" label="类型"><Select options={TYPES.map((t) => ({ value: t, label: t }))} /></Form.Item>
            <Form.Item name="environment" label="环境"><Select options={ENVS.map((t) => ({ value: t, label: t }))} /></Form.Item>
          </Space>
          <Form.Item name="criticality" label="关键性 (1-5)">
            <Slider min={1} max={5} marks={{ 1: '低', 5: '高' }} />
          </Form.Item>
          <Form.Item name="owner" label="负责人"><Input /></Form.Item>
        </Form>
      </Modal>
    </>
  )
}
