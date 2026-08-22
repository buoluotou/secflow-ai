import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, Space, message, Popconfirm } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import type { Project } from '../services/types'
import StatusTag from '../components/StatusTag'

export default function Projects() {
  const [items, setItems] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      setItems((await api.get('/projects')).data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const create = async () => {
    const values = await form.validateFields()
    await api.post('/projects', values)
    message.success('项目已创建')
    setOpen(false)
    form.resetFields()
    load()
  }

  return (
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <h2 style={{ margin: 0 }}>Projects 项目管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>新建项目</Button>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 10 }}
        columns={[
          { title: '名称', dataIndex: 'name' },
          { title: '描述', dataIndex: 'description', ellipsis: true },
          { title: '状态', dataIndex: 'status', render: (v) => <StatusTag value={v} /> },
          { title: '创建时间', dataIndex: 'created_at', width: 200 },
          {
            title: '操作',
            width: 120,
            render: (_, r: Project) => (
              <Popconfirm
                title="确认删除该项目及其全部数据？"
                onConfirm={async () => {
                  await api.delete(`/projects/${r.id}`)
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
      <Modal title="新建项目" open={open} onOk={create} onCancel={() => setOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="项目名称" rules={[{ required: true }]}>
            <Input placeholder="例如：Demo 01 — Web 入侵事件自动研判" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
