import { useEffect, useState } from 'react'
import {
  Table, Tag, Space, Drawer, Descriptions, Select, message, Tabs, Button, Modal,
  Form, Input, Popconfirm, Typography,
} from 'antd'
import { PlusOutlined, BugOutlined, ScanOutlined, HddOutlined } from '@ant-design/icons'
import { useSearchParams } from 'react-router-dom'
import { api } from '../services/api'
import type { Asset, Project, Finding, ScanJob } from '../services/types'
import StatusTag from '../components/StatusTag'

const STATUSES = ['open', 'confirmed', 'false_positive', 'remediated', 'accepted_risk', 'closed']

// =====================================================================
// 漏洞管理：漏洞 / 扫描 / 资产
// =====================================================================
export default function Findings() {
  const [params] = useSearchParams()
  const tab = params.get('tab') === 'scans' ? 'scans' : params.get('tab') === 'assets' ? 'assets' : 'findings'
  return (
    <Tabs
      defaultActiveKey={tab}
      items={[
        { key: 'findings', label: <span><BugOutlined /> 漏洞</span>, children: <FindingList /> },
        { key: 'scans', label: <span><ScanOutlined /> 扫描</span>, children: <ScanJobs /> },
        { key: 'assets', label: <span><HddOutlined /> 资产</span>, children: <AssetList /> },
      ]}
    />
  )
}

// 自动确保存在一个项目（前端不再要求先建项目）
async function ensureProject(): Promise<string> {
  const projects = (await api.get('/projects')).data as Project[]
  if (projects.length) return projects[0].id
  const r = await api.post('/projects', { name: '默认项目', description: '系统自动创建' })
  return r.data.id
}

// ---------------------------------------------------------------------
// 漏洞列表
// ---------------------------------------------------------------------
function FindingList() {
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

  useEffect(() => { load() }, [])

  const changeStatus = async (id: string, status: string) => {
    await api.patch(`/findings/${id}`, { status })
    message.success(`状态已更新为 ${status}`)
    load()
  }

  return (
    <>
      <Table
        rowKey="id" size="small" loading={loading} dataSource={items} pagination={{ pageSize: 15 }}
        locale={{ emptyText: '暂无漏洞 —— 在「扫描」页发起扫描自动发现' }}
        onRow={(r) => ({ onClick: () => setSelected(r), style: { cursor: 'pointer' } })}
        columns={[
          { title: '模板', dataIndex: 'template_id', width: 200, ellipsis: true },
          { title: '标题', dataIndex: 'title', ellipsis: true },
          { title: '严重性', dataIndex: 'severity', width: 90, render: (v) => <StatusTag value={v} /> },
          { title: 'CVSS', dataIndex: 'cvss', width: 70, render: (v?: number) => (v ? v.toFixed(1) : '—') },
          { title: '首次发现', dataIndex: 'first_seen', width: 160 },
          {
            title: '状态', dataIndex: 'status', width: 140,
            render: (v: string, r: Finding) => (
              <Select size="small" value={v}
                options={STATUSES.map((s) => ({ value: s, label: s }))}
                onChange={(nv) => changeStatus(r.id, nv)}
                onClick={(e) => e.stopPropagation()} />
            ),
          },
        ]}
      />
      <Drawer title={`漏洞详情 ${selected?.id ?? ''}`} open={!!selected} onClose={() => setSelected(null)} width={560}>
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
            </Descriptions>
            {selected.evidence && (
              <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 8, fontSize: 12, overflow: 'auto', marginTop: 12 }}>
                {selected.evidence}
              </pre>
            )}
          </>
        )}
      </Drawer>
    </>
  )
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
    await api.post('/scans', {
      project_id: await ensureProject(),
      scan_type: 'nuclei',
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
        <Typography>输入目标 → 自动扫描 → 漏洞自动入库并关联安全事件</Typography>
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
        <Form form={form} layout="vertical">
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
// 资产
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

  useEffect(() => { load() }, [])

  const add = async () => {
    const values = await form.validateFields()
    await api.post('/assets', { project_id: await ensureProject(), ...values })
    message.success('已添加')
    setOpen(false)
    form.resetFields()
    load()
  }

  return (
    <>
      <Space style={{ marginBottom: 14, justifyContent: 'space-between', width: '100%' }}>
        <Typography>登记资产 —— 漏洞与告警自动关联到资产</Typography>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>添加资产</Button>
      </Space>
      <Table
        rowKey="id" size="small" loading={loading} dataSource={items} pagination={{ pageSize: 10 }}
        locale={{ emptyText: '暂无资产' }}
        columns={[
          { title: '名称', dataIndex: 'name', width: 140 },
          { title: 'IP', dataIndex: 'ip', width: 130 },
          { title: '域名', dataIndex: 'domain', width: 170 },
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
