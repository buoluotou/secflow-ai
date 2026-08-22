import { useEffect, useState } from 'react'
import { Table, Button, Space, Tag, Select, message, Card, Typography } from 'antd'
import { FilePdfOutlined, FileTextOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import type { Project, Report } from '../services/types'
import StatusTag from '../components/StatusTag'

const TYPES = ['incident', 'vulnerability', 'inspection']

export default function Reports() {
  const [items, setItems] = useState<Report[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [type, setType] = useState<string | undefined>()
  const [projectId, setProjectId] = useState<string | undefined>()

  const load = async () => {
    setLoading(true)
    try {
      const [reports, proj] = await Promise.all([
        api.get('/reports', { params: { report_type: type } }),
        api.get('/projects'),
      ])
      setItems(reports.data)
      setProjects(proj.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [type])

  const genVulnReport = async () => {
    if (!projectId) {
      message.warning('请先选择项目')
      return
    }
    await api.post('/reports', { project_id: projectId, report_type: 'vulnerability' })
    message.success('漏洞报告已生成')
    load()
  }

  return (
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <h2 style={{ margin: 0 }}>Reports 安全报告</h2>
        <Space>
          <Select
            allowClear placeholder="报告类型" style={{ width: 150 }} value={type} onChange={setType}
            options={TYPES.map((t) => ({ value: t, label: t }))}
          />
          <Select
            allowClear placeholder="生成漏洞报告的项目" style={{ width: 220 }} value={projectId} onChange={setProjectId}
            options={projects.map((p) => ({ value: p.id, label: p.name }))}
          />
          <Button type="primary" onClick={genVulnReport}>生成漏洞报告</Button>
        </Space>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 15 }}
        columns={[
          { title: '标题', dataIndex: 'title', ellipsis: true },
          { title: '类型', dataIndex: 'report_type', width: 120, render: (v) => <Tag>{v}</Tag> },
          { title: '状态', dataIndex: 'status', width: 110, render: (v) => <StatusTag value={v} /> },
          { title: '创建人', dataIndex: 'created_by', width: 110 },
          { title: '创建时间', dataIndex: 'created_at', width: 170 },
          {
            title: '操作',
            width: 220,
            render: (_, r: Report) => (
              <Space>
                <Button size="small" icon={<FileTextOutlined />} onClick={() => window.open(`/api/reports/${r.id}/markdown`, '_blank')}>
                  Markdown
                </Button>
                <Button
                  size="small"
                  type="primary"
                  icon={<FilePdfOutlined />}
                  disabled={!r.content_pdf_path}
                  onClick={() => window.open(`/api/reports/${r.id}/pdf`, '_blank')}
                >
                  PDF
                </Button>
              </Space>
            ),
          },
        ]}
      />
      <Card size="small" style={{ marginTop: 16 }}>
        <Typography.Text type="secondary">
          💡 报告包含：事件概述 / 时间线 / 资产 / 漏洞 / IOC / MITRE / 证据链 / AI 研判 / 风险 / 处置建议 / 人工审核 / 整改建议。
          事件报告在 Incident 详情页「生成报告」按钮创建。
        </Typography.Text>
      </Card>
    </>
  )
}
