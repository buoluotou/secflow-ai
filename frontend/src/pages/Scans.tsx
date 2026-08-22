import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Select, Input, Space, message, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import type { Project, ScanJob } from '../services/types'
import StatusTag from '../components/StatusTag'

export default function Scans() {
  const [items, setItems] = useState<ScanJob[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      const [scans, proj] = await Promise.all([api.get('/scans'), api.get('/projects')])
      setItems(scans.data)
      setProjects(proj.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
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
      project_id: values.project_id,
      scan_type: values.scan_type ?? 'nuclei',
      targets,
      options: { severity: values.severity, tags: values.tags },
    })
    message.success('扫描任务已创建（异步执行）')
    setOpen(false)
    form.resetFields()
    load()
  }

  return (
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <h2 style={{ margin: 0 }}>Scans 扫描任务（Nuclei）</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>发起扫描</Button>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 15 }}
        columns={[
          { title: '编号', dataIndex: 'id', width: 110, render: (v: string) => <Tag>#{v.slice(0, 8)}</Tag> },
          { title: '类型', dataIndex: 'scan_type', width: 100 },
          { title: '目标', dataIndex: 'targets', render: (v: string[]) => v.join(', ') },
          { title: '状态', dataIndex: 'status', width: 110, render: (v) => <StatusTag value={v} /> },
          { title: '创建人', dataIndex: 'created_by', width: 110 },
          { title: '创建时间', dataIndex: 'created_at', width: 170 },
          {
            title: '结果',
            dataIndex: 'result_summary',
            width: 180,
            render: (v: Record<string, unknown>) =>
              v && v.findings_created != null
                ? `发现 ${v.findings_created} 个漏洞, ${((v.incidents as unknown[]) ?? []).length} 个事件`
                : v?.raw_results != null
                  ? `${v.raw_results} 条原始结果`
                  : '—',
          },
        ]}
      />
      <Modal title="发起 Nuclei 扫描" open={open} onOk={create} onCancel={() => setOpen(false)}>
        <Form form={form} layout="vertical" initialValues={{ scan_type: 'nuclei' }}>
          <Form.Item name="project_id" label="所属项目" rules={[{ required: true }]}>
            <Select options={projects.map((p) => ({ label: p.name, value: p.id }))} placeholder="选择项目" />
          </Form.Item>
          <Form.Item name="targets" label="扫描目标（每行一个：URL / IP / CIDR）" rules={[{ required: true }]}>
            <Input.TextArea rows={3} placeholder={'http://demo.local\n10.10.10.0/24'} />
          </Form.Item>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="scan_type" label="扫描类型">
              <Select options={[{ value: 'nuclei', label: 'nuclei' }, { value: 'nuclei_single', label: 'nuclei_single' }]} />
            </Form.Item>
            <Form.Item name="severity" label="严重性过滤">
              <Select allowClear options={['info', 'low', 'medium', 'high', 'critical'].map((s) => ({ value: s, label: s }))} />
            </Form.Item>
          </Space>
          <Form.Item name="tags" label="模板标签（可选）">
            <Input placeholder="例如 cve, rce" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
