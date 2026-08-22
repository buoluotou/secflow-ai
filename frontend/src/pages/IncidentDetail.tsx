import { useEffect, useState } from 'react'
import {
  Card, Descriptions, Tabs, Timeline, Table, Tag, Button, Space, Typography,
  message, Modal, Input, Alert, Spin, List, Result,
} from 'antd'
import {
  RobotOutlined, CheckOutlined, CloseOutlined, FilePdfOutlined, EditOutlined,
} from '@ant-design/icons'
import { useParams } from 'react-router-dom'
import { api } from '../services/api'
import type {
  AIAnalysis, Finding, Incident, IOC, Report, RiskAssessment, SecurityEvent,
} from '../services/types'
import StatusTag from '../components/StatusTag'

export default function IncidentDetail() {
  const { id } = useParams<{ id: string }>()
  const [incident, setIncident] = useState<Incident | null>(null)
  const [events, setEvents] = useState<SecurityEvent[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [iocs, setIocs] = useState<IOC[]>([])
  const [analyses, setAnalyses] = useState<AIAnalysis[]>([])
  const [risks, setRisks] = useState<RiskAssessment[]>([])
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewComment, setReviewComment] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [inc, evs, fnds, iocsR, anR, riskR, repR] = await Promise.all([
        api.get(`/incidents/${id}`),
        api.get('/events', { params: { limit: 200 } }),
        api.get('/findings', { params: { limit: 300 } }),
        api.get('/iocs', { params: { limit: 200 } }),
        api.get('/analysis', { params: { incident_id: id } }),
        api.get(`/analysis/incident/${id}/risk`),
        api.get('/reports'),
      ])
      setIncident(inc.data)
      const incData = inc.data as Incident
      setEvents((evs.data as SecurityEvent[]).filter((e) => (incData.related_event_ids || []).includes(e.id)))
      setFindings((fnds.data as Finding[]).filter((f) => (incData.related_finding_ids || []).includes(f.id)))
      setIocs((iocsR.data as IOC[]).filter((i) => (incData.related_ioc_ids || []).includes(i.id)))
      setAnalyses(anR.data)
      setRisks(riskR.data)
      setReports((repR.data as Report[]).filter((r) => r.incident_id === id))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (id) load()
  }, [id])

  const analyze = async () => {
    setAnalyzing(true)
    try {
      const r = await api.post(`/incidents/${id}/analyze`)
      message.success(`AI 研判完成，风险等级：${r.data?.results?.risk?.risk_level ?? '—'}`)
      load()
    } catch {
      message.error('AI 研判失败')
    } finally {
      setAnalyzing(false)
    }
  }

  const review = async (decision: 'approve' | 'reject') => {
    await api.post(`/incidents/${id}/${decision}`, { decision, comment: reviewComment })
    message.success(decision === 'approve' ? '已批准' : '已驳回')
    setReviewOpen(false)
    setReviewComment('')
    load()
  }

  const genReport = async () => {
    await api.post('/reports', { incident_id: id, report_type: 'incident' })
    message.success('报告已生成')
    load()
  }

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
  if (!incident) return <Result status="404" title="事件不存在" />

  const triage = analyses.find((a) => a.agent_type === 'triage')
  const threat = analyses.find((a) => a.agent_type === 'threat')
  const vuln = analyses.find((a) => a.agent_type === 'vuln')
  const reportAgent = analyses.find((a) => a.agent_type === 'report')
  const risk = risks[0]
  const out = triage?.output ?? {}

  const timelineItems = [
    ...events.map((e) => ({ time: e.timestamp, children: `${e.source} 告警: ${e.event_type} (${e.src_ip} → ${e.dst_ip})` })),
    ...findings.map((f) => ({ time: f.first_seen, children: `Nuclei 发现: ${f.title} [${f.severity}]` })),
    ...iocs.map((i) => ({ time: i.last_seen, children: `MISP IOC 命中: ${i.type} ${i.value}` })),
  ].sort((a, b) => String(a.time).localeCompare(String(b.time)))

  return (
    <Spin spinning={analyzing}>
      <Card
        title={<Space><Tag color="volcano">Incident #{incident.id.slice(0, 8)}</Tag>{incident.title}</Space>}
        extra={
          <Space>
            <Button type="primary" icon={<RobotOutlined />} loading={analyzing} onClick={analyze}>
              AI 研判
            </Button>
            <Button icon={<CheckOutlined />} onClick={() => setReviewOpen(true)}>人工审核</Button>
            <Button icon={<FilePdfOutlined />} onClick={genReport}>生成报告</Button>
          </Space>
        }
      >
        <Descriptions column={3} size="small" bordered>
          <Descriptions.Item label="状态"><StatusTag value={incident.status} /></Descriptions.Item>
          <Descriptions.Item label="严重性"><StatusTag value={incident.severity} /></Descriptions.Item>
          <Descriptions.Item label="置信度">{(incident.confidence * 100).toFixed(0)}%</Descriptions.Item>
          <Descriptions.Item label="攻击阶段">{incident.attack_stage || '—'}</Descriptions.Item>
          <Descriptions.Item label="检测时间">{incident.detected_at}</Descriptions.Item>
          <Descriptions.Item label="AI 决策">{incident.ai_decision || '—'}</Descriptions.Item>
          <Descriptions.Item label="人工决策" span={2}>
            {incident.human_decision ? <StatusTag value={incident.human_decision} /> : '待审核'}
          </Descriptions.Item>
          <Descriptions.Item label="审核人">{incident.reviewer || '—'}</Descriptions.Item>
        </Descriptions>
        {incident.correlation_reason && (
          <Alert
            style={{ marginTop: 12 }}
            type="info"
            showIcon
            message="关联依据"
            description={incident.correlation_reason}
          />
        )}

        <Tabs
          style={{ marginTop: 16 }}
          items={[
            {
              key: 'overview',
              label: 'Overview 概述',
              children: <Typography.Paragraph>{incident.description || '暂无描述'}</Typography.Paragraph>,
            },
            {
              key: 'timeline',
              label: 'Timeline 时间线',
              children: <Timeline items={timelineItems.length ? timelineItems : [{ children: '暂无时间线' }]} />,
            },
            {
              key: 'evidence',
              label: `Evidence 证据 (${incident.evidence_ids.length})`,
              children: (
                <List
                  size="small"
                  dataSource={incident.evidence_ids}
                  renderItem={(eid) => (
                    <List.Item>
                      <Tag color="blue">{eid}</Tag>
                      <Typography.Text>由关联引擎生成 — 详见 AI 研判证据绑定</Typography.Text>
                    </List.Item>
                  )}
                />
              ),
            },
            {
              key: 'ioc',
              label: `IOC (${iocs.length})`,
              children: (
                <Table rowKey="id" size="small" dataSource={iocs} pagination={false}
                  columns={[
                    { title: '类型', dataIndex: 'type', width: 90 },
                    { title: '值', dataIndex: 'value' },
                    { title: '置信度', dataIndex: 'confidence', width: 100, render: (v: number) => `${(v * 100).toFixed(0)}%` },
                  ]} />
              ),
            },
            {
              key: 'findings',
              label: `Findings (${findings.length})`,
              children: (
                <Table rowKey="id" size="small" dataSource={findings} pagination={false}
                  columns={[
                    { title: '模板', dataIndex: 'template_id', width: 220 },
                    { title: '标题', dataIndex: 'title' },
                    { title: '严重性', dataIndex: 'severity', width: 90, render: (v) => <StatusTag value={v} /> },
                    { title: 'CVSS', dataIndex: 'cvss', width: 70 },
                  ]} />
              ),
            },
            {
              key: 'attack_chain',
              label: 'Attack Chain 攻击链',
              children: (
                <Space wrap>
                  {events.map((e) => (
                    <Tag key={e.id} color="orange">{e.event_type}</Tag>
                  ))}
                  {findings.map((f) => (
                    <Tag key={f.id} color="red">{f.template_id}</Tag>
                  ))}
                  {iocs.map((i) => (
                    <Tag key={i.id} color="purple">{i.value}</Tag>
                  ))}
                  {!events.length && !findings.length && !iocs.length && <Typography.Text type="secondary">暂无攻击链数据</Typography.Text>}
                </Space>
              ),
            },
            {
              key: 'mitre',
              label: 'MITRE ATT&CK',
              children: (
                <Space wrap>
                  {(incident.related_event_ids || []).length >= 0 &&
                    [...new Set(events.flatMap((e) => e.techniques || []))].map((t) => (
                      <Tag key={t} color="geekblue">{t}</Tag>
                    ))}
                  {!events.some((e) => (e.techniques || []).length) && <Typography.Text type="secondary">暂无 ATT&CK 技术</Typography.Text>}
                </Space>
              ),
            },
            {
              key: 'ai',
              label: 'AI Analysis',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {triage && (
                    <Card size="small" title={`Triage Agent${reportAgent ? ' + Report Agent' : ''} (${triage.model ?? 'mock'})`}>
                      <Descriptions column={2} size="small">
                        <Descriptions.Item label="分类"><StatusTag value={out.classification} /></Descriptions.Item>
                        <Descriptions.Item label="严重性"><StatusTag value={out.severity} /></Descriptions.Item>
                        <Descriptions.Item label="置信度">{((out.confidence ?? 0) * 100).toFixed(0)}%</Descriptions.Item>
                        <Descriptions.Item label="攻击阶段">{out.attack_stage || '—'}</Descriptions.Item>
                        <Descriptions.Item label="ATT&CK" span={2}>
                          {(out.mitre_techniques ?? []).map((t) => <Tag key={t}>{t}</Tag>)}
                        </Descriptions.Item>
                        <Descriptions.Item label="证据绑定" span={2}>
                          {(out.evidence_ids ?? []).map((eid) => <Tag color="blue" key={eid}>{eid}</Tag>)}
                        </Descriptions.Item>
                        <Descriptions.Item label="研判摘要" span={2}>{out.reasoning_summary}</Descriptions.Item>
                        <Descriptions.Item label="处置建议" span={2}>
                          {(out.recommendations ?? []).map((r) => <Tag color="green" key={r}>{r}</Tag>)}
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>
                  )}
                  {threat && (
                    <Card size="small" title="Threat Agent">
                      <Descriptions column={2} size="small">
                        <Descriptions.Item label="恶意判定">{threat.output.malicious ? '是' : '否'}</Descriptions.Item>
                        <Descriptions.Item label="置信度">{((threat.output.confidence ?? 0) * 100).toFixed(0)}%</Descriptions.Item>
                        <Descriptions.Item label="标签" span={2}>
                          {(threat.output.tags ?? []).map((t) => <Tag key={t}>{t}</Tag>)}
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>
                  )}
                  {vuln && (
                    <Card size="small" title="Vulnerability Agent">
                      <Descriptions column={2} size="small">
                        <Descriptions.Item label="真实性">{vuln.output.authenticity}</Descriptions.Item>
                        <Descriptions.Item label="修复优先级"><StatusTag value={vuln.output.remediation_priority} /></Descriptions.Item>
                        <Descriptions.Item label="利用风险">{((vuln.output.exploit_risk ?? 0) * 100).toFixed(0)}%</Descriptions.Item>
                        <Descriptions.Item label="影响范围">{(vuln.output.impact_scope ?? []).join(', ') || '—'}</Descriptions.Item>
                      </Descriptions>
                    </Card>
                  )}
                  {!triage && !threat && !vuln && (
                    <Alert type="info" message="尚未执行 AI 研判 — 点击右上角「AI 研判」开始" />
                  )}
                </Space>
              ),
            },
            {
              key: 'risk',
              label: 'Risk 风险评估',
              children: risk ? (
                <Descriptions column={2} size="small" bordered>
                  <Descriptions.Item label="风险评分">
                    <Typography.Text strong style={{ fontSize: 20, color: risk.risk_level === 'critical' ? '#cf1322' : '#fa8c16' }}>
                      {risk.risk_score}
                    </Typography.Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="风险等级"><StatusTag value={risk.risk_level} /></Descriptions.Item>
                  {(Object.entries((risk.factors.factors as Record<string, unknown>) ?? {})).map(([k, v]) => (
                    <Descriptions.Item key={k} label={k}>{String(v)}</Descriptions.Item>
                  ))}
                </Descriptions>
              ) : (
                <Alert type="info" message="尚未执行风险评估 — 先执行 AI 研判" />
              ),
            },
            {
              key: 'review',
              label: 'Recommendations / 审核',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {(out.recommendations ?? []).map((r) => (
                    <Alert key={r} type="warning" message={r} showIcon />
                  ))}
                  <Alert
                    type={incident.human_decision ? 'success' : 'info'}
                    message={incident.human_decision
                      ? `已${incident.human_decision} (${incident.reviewer})：${incident.review_comment || '无备注'}`
                      : 'AI 建议已生成，等待安全工程师人工审核'}
                  />
                </Space>
              ),
            },
            {
              key: 'report',
              label: `Report (${reports.length})`,
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {reports.map((r) => (
                    <Card key={r.id} size="small" title={r.title} extra={<StatusTag value={r.status} />}>
                      <Space>
                        <Button
                          size="small"
                          onClick={() => window.open(`/api/reports/${r.id}/markdown`, '_blank')}
                        >
                          Markdown
                        </Button>
                        {r.content_pdf_path && (
                          <Button size="small" type="primary" onClick={() => window.open(`/api/reports/${r.id}/pdf`, '_blank')}>
                            PDF 下载
                          </Button>
                        )}
                      </Space>
                    </Card>
                  ))}
                  {!reports.length && <Alert type="info" message="尚未生成报告 — 点击右上角「生成报告」" />}
                </Space>
              ),
            },
            {
              key: 'audit',
              label: 'Audit 审计',
              children: <Typography.Text type="secondary">事件操作审计记录见「Audit 审计」页面（按事件 ID 过滤）。</Typography.Text>,
            },
          ]}
        />
      </Card>

      <Modal
        title="人工审核（高风险动作必须人工批准）"
        open={reviewOpen}
        onCancel={() => setReviewOpen(false)}
        footer={
          <Space>
            <Button danger icon={<CloseOutlined />} onClick={() => review('reject')}>驳回</Button>
            <Button icon={<EditOutlined />} onClick={() => message.info('修改功能即将上线，请使用驳回+备注')}>修改</Button>
            <Button type="primary" icon={<CheckOutlined />} onClick={() => review('approve')}>批准</Button>
          </Space>
        }
      >
        <Input.TextArea
          rows={3}
          placeholder="审核意见（可选）"
          value={reviewComment}
          onChange={(e) => setReviewComment(e.target.value)}
        />
      </Modal>
    </Spin>
  )
}
