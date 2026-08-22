import { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Space, Tag, List } from 'antd'
import {
  AlertOutlined, BugOutlined, ScanOutlined,
  FileTextOutlined, RobotOutlined, CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api, healthApi } from '../services/api'
import type { Incident, HealthStatus } from '../services/types'

// =====================================================================
// 总览：核心指标 + 系统状态 + 快捷操作 + 最近事件
// =====================================================================
export default function Dashboard() {
  const navigate = useNavigate()
  const [counts, setCounts] = useState({ incidents: 0, findings: 0, events: 0, reports: 0 })
  const [health, setHealth] = useState<Record<string, HealthStatus>>({})
  const [recent, setRecent] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const [inc, fnd, ev, rep, h] = await Promise.all([
        api.get('/incidents', { params: { limit: 200 } }).catch(() => ({ data: [] as Incident[] })),
        api.get('/findings', { params: { limit: 200 } }).catch(() => ({ data: [] })),
        api.get('/events', { params: { limit: 200 } }).catch(() => ({ data: [] })),
        api.get('/reports').catch(() => ({ data: [] })),
        healthApi.all(),
      ])
      setCounts({
        incidents: (inc.data as Incident[]).length,
        findings: fnd.data.length,
        events: ev.data.length,
        reports: rep.data.length,
      })
      setRecent((inc.data as Incident[]).slice(0, 8))
      setHealth(h)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 30000)
    return () => clearInterval(t)
  }, [])

  const openIncidents = recent.filter((i) => !['closed', 'resolved'].includes(i.status)).length
  const critical = recent.filter((i) => i.severity === 'critical' || i.severity === 'high').length

  const statusLine: [string, HealthStatus | undefined][] = [
    ['API', health.api], ['数据库', health.db], ['Redis', health.redis],
    ['AI', health.llm], ['Wazuh', health.wazuh], ['MISP', health.misp],
  ]

  const renderStatus = (h?: HealthStatus) => {
    if (!h) return <Tag>…</Tag>
    if (h.status === 'mock') return <Tag color="blue" icon={<RobotOutlined />}>Mock</Tag>
    if (h.ok) return <Tag color="success" icon={<CheckCircleOutlined />}>正常</Tag>
    if (h.status === 'not_configured') return <Tag>未配置</Tag>
    return <Tag color="error" icon={<CloseCircleOutlined />}>异常</Tag>
  }

  const shortcuts = [
    { label: '发起扫描', icon: <ScanOutlined />, to: '/findings?tab=scans' },
    { label: '查看事件', icon: <AlertOutlined />, to: '/incidents' },
    { label: '漏洞管理', icon: <BugOutlined />, to: '/findings' },
    { label: '安全报告', icon: <FileTextOutlined />, to: '/reports' },
  ]

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {/* 核心指标 */}
      <Row gutter={[12, 12]}>
        <Col span={6}>
          <Card size="small">
            <Typography.Text type="secondary">安全事件</Typography.Text>
            <div style={{ fontSize: 26, fontWeight: 700 }}>{counts.incidents}</div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              未闭环 {openIncidents} · 高危 {critical}
            </Typography.Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Typography.Text type="secondary">漏洞</Typography.Text>
            <div style={{ fontSize: 26, fontWeight: 700 }}>{counts.findings}</div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>Nuclei 扫描发现</Typography.Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Typography.Text type="secondary">告警</Typography.Text>
            <div style={{ fontSize: 26, fontWeight: 700 }}>{counts.events}</div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>Wazuh / 手动录入</Typography.Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Typography.Text type="secondary">报告</Typography.Text>
            <div style={{ fontSize: 26, fontWeight: 700 }}>{counts.reports}</div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>可下载 PDF</Typography.Text>
          </Card>
        </Col>
      </Row>

      {/* 快捷操作 */}
      <Row gutter={[12, 12]}>
        {shortcuts.map((s) => (
          <Col span={6} key={s.label}>
            <Card size="small" hoverable onClick={() => navigate(s.to)} style={{ textAlign: 'center', cursor: 'pointer' }}>
              <Space>{s.icon}{s.label}</Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[12, 12]}>
        {/* 系统状态 */}
        <Col span={10}>
          <Card size="small" title="系统状态" loading={loading}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {statusLine.map(([name, h]) => (
                <Space key={name} style={{ justifyContent: 'space-between', width: '100%' }}>
                  <Typography.Text>{name}</Typography.Text>
                  {renderStatus(h)}
                </Space>
              ))}
            </Space>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              AI 显示 Mock 表示未接入真实模型 —— 到「系统维护 → AI 接入」配置密钥
            </Typography.Text>
          </Card>
        </Col>
        {/* 最近事件 */}
        <Col span={14}>
          <Card size="small" title="最近安全事件" loading={loading} styles={{ body: { maxHeight: 320, overflow: 'auto' } }}>
            <List
              size="small"
              dataSource={recent}
              locale={{ emptyText: '暂无事件 —— 发起扫描或注入告警后自动生成' }}
              renderItem={(i) => (
                <List.Item style={{ cursor: 'pointer' }} onClick={() => navigate(`/incidents/${i.id}`)}>
                  <Space>
                    <Tag color={i.severity === 'critical' ? 'red' : i.severity === 'high' ? 'volcano' : i.severity === 'medium' ? 'orange' : 'blue'}>
                      {i.severity}
                    </Tag>
                    <Tag>{i.status}</Tag>
                    <Typography.Text ellipsis style={{ maxWidth: 420 }}>{i.title}</Typography.Text>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>{i.detected_at?.slice(0, 16)}</Typography.Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </Space>
  )
}
