import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Select, Input, Space, message, Tag, Tabs, Popconfirm, Typography } from 'antd'
import { PlusOutlined, ScanOutlined, HddOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import type { Asset, Project, ScanJob } from '../services/types'
import StatusTag from '../components/StatusTag'

export default function Scans() {
  return (
    <Tabs
      defaultActiveKey="scans"
      items={[
        { key: 'scans', label: <span><ScanOutlined /> 扫描任务</span>, children: <ScanJobs /> },
        { key: 'assets', label: <span><HddOutlined /> 资产库</span>, children: <AssetList /> },
      ]}
    />
  )
}

// 自动确保存在一个项目（前端不再要求用户先建项目）
async function ensureProject(): Promise<string> {
  const projects = (await api.get('/projects')).data as Project[]
  if (projects.length) return projects[0].id
  const r = await api.post('/projects', { name: '默认项目', description: '系统自动创建' })
  return r.data.id
}

// ---------------------------------------------------------------------
// 扫描任务
// ---------------------------------------------------------------------
function ScanJobs() {
  const [items, setItems] = useState<ScanJob[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      setItems((await api.get('/scans')).data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 8000)
    return () => clearInterval(t)
  }, [])

  const create = async () => {
    const values = await form.validateFields()
    const targets = String(values.targets || '')
      .split(/[\n,]/)
      .map((s: string) => s.trim())
      .filter(Boolean)
    if (!targets.length) {
      message.warning('请输入至少一个目标')
      return
    }
    const projectId = await ensureProject()
    await api.post('/scans', {
      project_id: projectId,
      scan_type: values.scan_type ?? 'nuclei',
      targets,
      options: { severity: values.severity },
    })
    message.success('扫描任务已创建')
    setOpen(false)
    form.resetFields()
    load()
  }

  return (
    <>
      <Space style={{ marginBottom: 14, justifyContent: 'space-between', width: '100%' }}>
        <Typography>输入目标 → 自动扫描 → 发现漏洞 → 自动关联安全事件</Typography>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>发起扫描</Button>
      </Space>
      <Table
        rowKey="id" size="small" loading={loading} dataSource={items} pagination={{ pageSize: 10 }}
        locale={{ emptyText: '暂无扫描任务 —— 点击右上角"发起扫描"' }}
        columns={[
          { title: '目标', dataIndex: 'targets', render: (v: string[]) => v.join(', ') },
          { title: '状态', dataIndex: 'status', width: 110, render: (v) => <StatusTag value={v} /> },
          { title: '时间', dataIndex: 'created_at', width: 160 },
          {
            title: '结果', width: 220,
            render: (_, r: ScanJob) => {
              if (r.status === 'failed') return <Tag color="error">{r.error?.slice(0, 50)}</Tag>
              const s = r.result_summary as { findings_created?: number; incidents?: unknown[] } | undefined
              if (s && s.findings_created != null) {
                return <span>发现 {s.findings_created} 个漏洞{s.incidents?.length ? `，生成 ${s.incidents.length} 个事件` : ''}</span>
              }
              return '—'
            },
          },
        ]}
      />
      <Modal title="发起 Nuclei 扫描" open={open} onOk={create} onCancel={() => setOpen(false)}>
        <Form form={form} layout="vertical" initialValues={{ scan_type: 'nuclei' }}>
          <Form.Item name="targets" label="扫描目标（每行一个：URL / IP / 网段）" rules={[{ required: true }]}>
            <Input.TextArea rows={4} placeholder={'http://demo.local\n10.10.10.0/24'} />
          </Form.Item>
          <Form.Item name="severity" label="仅显示严重性 ≥（可选）">
            <Select allowClear options={['info', 'low', 'medium', 'high', 'critical'].map((s) => ({ value: s, label: s }))} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

// ---------------------------------------------------------------------
// 资产库（精简）
// ---------------------------------------------------------------------
function AssetList() {
  const [items, setItems] = useState<Asset[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      setItems((await api.get('/assets')).data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const add = async () => {
    const values = await form.validateFields()
    const projectId = await ensureProject()
    await api.post('/assets', { project_id: projectId, ...values })
    message.success('已添加')
    setOpen(false)
    form.resetFields()
    load()
  }

  return (
    <>
      <Space style={{ marginBottom: 14, justifyContent: 'space-between', width: '100%' }}>
        <Typography>登记业务资产 —— 漏洞与告警会自动关联到对应资产</Typography>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>添加资产</Button>
      </Space>
      <Table
        rowKey="id" size="small" loading={loading} dataSource={items} pagination={{ pageSize: 10 }}
        locale={{ emptyText: '暂无资产' }}
        columns={[
          { title: '名称', dataIndex: 'name', width: 140 },
          { title: 'IP', dataIndex: 'ip', width: 130 },
          { title: '域名', dataIndex: 'domain', width: 160 },
          { title: '类型', dataIndex: 'asset_type', width: 100, render: (v: string) => <Tag>{v}</Tag> },
          { title: '关键性', dataIndex: 'criticality', width: 90, render: (v: number) => '★'.repeat(v || 1) },
          {
            title: '', width: 60,
            render: (_, r: Asset) => (
              <Popconfirm title="删除？" onConfirm={async () => { await api.delete(`/assets/${r.id}`); load() }}>
                <Button danger size="small" type="text">删</Button>
              </Popconfirm>
            ),
          },
        ]}
      />
      <Modal title="添加资产" open={open} onOk={add} onCancel={() => setOpen(false)}>
        <Form form={form} layout="vertical" initialValues={{ asset_type: 'server', criticality: 3 }}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input placeholder="web-01" /></Form.Item>
          <Form.Item name="ip" label="IP"><Input placeholder="10.10.10.10" /></Form.Item>
          <Form.Item name="domain" label="域名"><Input /></Form.Item>
          <Space>
            <Form.Item name="asset_type" label="类型">
              <Select style={{ width: 160 }} options={['server', 'webapp', 'database', 'network', 'workstation', 'cloud', 'iot'].map((t) => ({ value: t, label: t }))} />
            </Form.Item>
            <Form.Item name="criticality" label="关键性">
              <Select style={{ width: 140 }} options={[1, 2, 3, 4, 5].map((v) => ({ value: v, label: '★'.repeat(v) }))} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </>
  )
}
