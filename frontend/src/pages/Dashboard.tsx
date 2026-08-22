import { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Space, Tag, Spin, Tooltip } from 'antd'
import {
  ThunderboltOutlined,
  BugOutlined,
  AlertOutlined,
  HddOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { api, healthApi } from '../services/api'
import type { Asset, Finding, Incident, SecurityEvent } from '../services/types'
import StatCard from '../components/StatCard'
import TrendChart from '../components/TrendChart'
import StatusTag from '../components/StatusTag'
import type { EChartsOption } from 'echarts'

export default function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [counts, setCounts] = useState({ events: 0, findings: 0, incidents: 0, assets: 0, critical: 0, high: 0, openFindings: 0 })
  const [health, setHealth] = useState<Record<string, { ok: boolean }>>({})
  const [events, setEvents] = useState<SecurityEvent[]>([])
  const [incidents, setIncidents] = useState<Incident[]>([])

  const load = async () => {
    setLoading(true)
    try {
      const [eventsR, findingsR, incidentsR, assetsR] = await Promise.all([
        api.get('/events', { params: { limit: 200 } }).catch(() => ({ data: [] as SecurityEvent[] })),
        api.get('/findings', { params: { limit: 200 } }).catch(() => ({ data: [] as Finding[] })),
        api.get('/incidents', { params: { limit: 200 } }).catch(() => ({ data: [] as Incident[] })),
        api.get('/assets', { params: { limit: 200 } }).catch(() => ({ data: [] as Asset[] })),
      ])
      const evs = eventsR.data as SecurityEvent[]
      const fnds = findingsR.data as Finding[]
      const inss = incidentsR.data as Incident[]
      setEvents(evs)
      setIncidents(inss)
      setCounts({
        events: evs.length,
        findings: fnds.length,
        incidents: inss.length,
        assets: (assetsR.data as Asset[]).length,
        critical: inss.filter((i) => i.severity === 'critical').length,
        high: inss.filter((i) => i.severity === 'high').length,
        openFindings: fnds.filter((f) => f.status === 'open').length,
      })
      setHealth(await healthApi.all())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 30000)
    return () => clearInterval(t)
  }, [])

  const sevCount = (sev: string) => events.filter((e) => e.severity === sev).length

  const eventTrend: EChartsOption = {
    title: { text: '安全事件趋势 (按严重性)' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['Critical', 'High', 'Medium', 'Low', 'Info'] },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: ['critical', 'high', 'medium', 'low', 'info'].map(sevCount), itemStyle: { color: '#cf1322' } }],
  }

  const incidentTrend: EChartsOption = {
    title: { text: '事件状态分布' },
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: '60%',
      data: ['new', 'triaging', 'investigating', 'awaiting_review', 'approved', 'resolved', 'closed'].map((s) => ({
        name: s,
        value: incidents.filter((i) => i.status === s).length,
      })),
    }],
  }

  const healthItems: [string, { ok: boolean; status?: string; error?: string }][] = [
    ['API', health.api ?? { ok: false }],
    ['Database', health.db ?? { ok: false }],
    ['Redis', health.redis ?? { ok: false }],
    ['Wazuh', health.wazuh ?? { ok: false }],
    ['MISP', health.misp ?? { ok: false }],
    ['AI', health.llm ?? { ok: false }],
  ]

  const renderHealth = (h: { ok: boolean; status?: string; error?: string }) => {
    if (h.ok) {
      return <Tag color="success" icon={<CheckCircleOutlined />}>✓ 正常</Tag>
    }
    if (h.status === 'not_configured') {
      return (
        <Tooltip title={h.error}>
          <Tag color="default" icon={<CloseCircleOutlined />}>未配置（可选）</Tag>
        </Tooltip>
      )
    }
    return (
      <Tooltip title={h.error}>
        <Tag color="error" icon={<CloseCircleOutlined />}>✗ 异常</Tag>
      </Tooltip>
    )
  }

  return (
    <Spin spinning={loading}>
      <Row gutter={[16, 16]}>
        <Col span={4}><StatCard title="Total Events" value={counts.events} icon={<ThunderboltOutlined />} /></Col>
        <Col span={4}><StatCard title="Critical" value={counts.critical} color="#cf1322" /></Col>
        <Col span={4}><StatCard title="High" value={counts.high} color="#fa541c" /></Col>
        <Col span={4}><StatCard title="Open Findings" value={counts.openFindings} icon={<BugOutlined />} /></Col>
        <Col span={4}><StatCard title="Open Incidents" value={counts.incidents} icon={<AlertOutlined />} /></Col>
        <Col span={4}><StatCard title="Assets" value={counts.assets} icon={<HddOutlined />} /></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}><Card size="small"><TrendChart option={eventTrend} height={280} /></Card></Col>
        <Col span={12}><Card size="small"><TrendChart option={incidentTrend} height={280} /></Card></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card size="small" title="系统健康状态">
            <Space direction="vertical" style={{ width: '100%' }}>
              {healthItems.map(([name, h]) => (
                <Space key={name} style={{ justifyContent: 'space-between', width: '100%' }}>
                  <Typography.Text>{name}</Typography.Text>
                  {renderHealth(h)}
                </Space>
              ))}
            </Space>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" title="最近安全事件" styles={{ body: { maxHeight: 280, overflow: 'auto' } }}>
            {events.slice(0, 8).map((e) => (
              <div key={e.id} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                <Space>
                  <StatusTag value={e.severity} />
                  <Typography.Text ellipsis style={{ maxWidth: 220 }}>{e.event_type || e.source}</Typography.Text>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>{e.src_ip}</Typography.Text>
                </Space>
              </div>
            ))}
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" title="最近事件 (Incidents)" styles={{ body: { maxHeight: 280, overflow: 'auto' } }}>
            {incidents.slice(0, 8).map((i) => (
              <div key={i.id} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                <Space>
                  <StatusTag value={i.severity} />
                  <StatusTag value={i.status} />
                  <Typography.Text ellipsis style={{ maxWidth: 200 }}>{i.title}</Typography.Text>
                </Space>
              </div>
            ))}
          </Card>
        </Col>
      </Row>
    </Spin>
  )
}
