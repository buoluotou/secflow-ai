import { useEffect, useRef, useState } from 'react'
import { Card, Input, Button, Space, Typography, Tag, List, Spin, Empty } from 'antd'
import { SendOutlined, RobotOutlined, UserOutlined, BulbOutlined } from '@ant-design/icons'
import { api } from '../services/api'

interface AgentStep { thought: string; action?: string; result?: string; ok?: boolean }

interface Msg {
  role: 'user' | 'assistant'
  content: string
  tool?: string
  data?: Record<string, unknown>
  steps?: AgentStep[]
}

interface ToolInfo { name: string; label: string; example: string }

// =====================================================================
// AI 安全助手 —— 对话框直接下达安全任务
// =====================================================================
export default function Copilot() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [tools, setTools] = useState<ToolInfo[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get('/copilot/tools').then((r) => setTools(r.data.tools)).catch(() => null)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  const send = async (text?: string) => {
    const content = (text ?? input).trim()
    if (!content || busy) return
    const history = messages.slice(-8).map((m) => ({ role: m.role, content: m.content }))
    setMessages((ms) => [...ms, { role: 'user', content }])
    setInput('')
    setBusy(true)
    try {
      const r = await api.post('/copilot/chat', { message: content, history })
      setMessages((ms) => [...ms, {
        role: 'assistant',
        content: r.data.reply,
        tool: r.data.tool,
        data: r.data.data,
        steps: r.data.steps,
      }])
    } catch (e: unknown) {
      setMessages((ms) => [...ms, {
        role: 'assistant',
        content: (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '助手执行失败，请重试',
      }])
    } finally {
      setBusy(false)
    }
  }

  // 工具结果结构化展示（事件/漏洞/报告列表）
  const renderData = (m: Msg) => {
    if (!m.data) return null
    const d = m.data as { incidents?: unknown[]; findings?: unknown[]; reports?: unknown[]; iocs?: unknown[] }
    const sevColor = (s: string) => s === 'critical' ? 'red' : s === 'high' ? 'volcano' : s === 'medium' ? 'orange' : 'blue'
    if (d.incidents?.length) {
      return (
        <List size="small" dataSource={d.incidents as Array<{ title: string; severity: string; status: string }>} renderItem={(i) => (
          <List.Item>
            <Space><Tag color={sevColor(i.severity)}>{i.severity}</Tag><Tag>{i.status}</Tag>{i.title}</Space>
          </List.Item>
        )} />
      )
    }
    if (d.findings?.length) {
      return (
        <List size="small" dataSource={d.findings as Array<{ title: string; severity: string; template_id?: string }>} renderItem={(f) => (
          <List.Item>
            <Space><Tag color={sevColor(f.severity)}>{f.severity}</Tag>{f.title}<Typography.Text type="secondary" style={{ fontSize: 12 }}>{f.template_id}</Typography.Text></Space>
          </List.Item>
        )} />
      )
    }
    if (d.reports?.length) {
      return (
        <List size="small" dataSource={d.reports as Array<{ title: string; status: string }>} renderItem={(r) => (
          <List.Item><Space><Tag color="geekblue">{r.status}</Tag>{r.title}</Space></List.Item>
        )} />
      )
    }
    if (d.iocs?.length) {
      return (
        <List size="small" dataSource={d.iocs as Array<{ type: string; value: string; confidence: number }>} renderItem={(i) => (
          <List.Item><Space><Tag color="purple">{i.type}</Tag>{i.value}<Typography.Text type="secondary" style={{ fontSize: 12 }}>{(i.confidence * 100).toFixed(0)}%</Typography.Text></Space></List.Item>
        )} />
      )
    }
    return null
  }

  return (
    <Card
      title={<Space><RobotOutlined style={{ color: '#1677ff' }} />AI 安全助手 <Typography.Text type="secondary" style={{ fontSize: 12 }}>下指令即可完成扫描/审查/响应/报告</Typography.Text></Space>}
      styles={{ body: { display: 'flex', flexDirection: 'column', height: 'calc(100vh - 140px)' } }}
    >
      {/* 快捷指令 */}
      <Space wrap style={{ marginBottom: 10 }}>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>快捷指令：</Typography.Text>
        {tools.filter((t) => t.name !== 'help').map((t) => (
          <Button key={t.name} size="small" icon={<BulbOutlined />} disabled={busy} onClick={() => send(t.example)}>
            {t.label}
          </Button>
        ))}
      </Space>

      {/* 消息区 */}
      <div style={{ flex: 1, overflow: 'auto', background: '#fafafa', borderRadius: 8, padding: 14 }}>
        {messages.length === 0 && !busy && (
          <Empty
            description={
              <Space direction="vertical" style={{ textAlign: 'left', maxWidth: 520 }}>
                <Typography.Text>你好，我是 SecFlow AI 安全助手。我会像真实安全工程师一样：先思考、再调用系统工具执行、观察结果后继续，直到完成任务。试试：</Typography.Text>
                <Typography.Text>🔍 “扫描 http://demo.local” —— 发起漏洞扫描</Typography.Text>
                <Typography.Text>🚨 “应急响应，查看未处理事件” —— 列出待处置事件</Typography.Text>
                <Typography.Text>📄 “为最近的事件生成报告” —— 自动撰写安全报告</Typography.Text>
                <Typography.Text>🔏 “审查今天的操作日志” —— 日志合规审查</Typography.Text>
                <Typography.Text>🛡️ “系统安全吗？给防护建议” —— 安全防护评估</Typography.Text>
                <Typography.Text>🧭 “全面安全巡检” —— 我会自动拆解：健康检查→事件→漏洞→日志，多步完成</Typography.Text>
              </Space>
            }
          />
        )}
        {messages.map((m, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: 12 }}>
            <div style={{ maxWidth: '80%' }}>
              <Space size={6} style={{ marginBottom: 4 }}>
                {m.role === 'assistant' ? <RobotOutlined style={{ color: '#1677ff' }} /> : <UserOutlined style={{ color: '#52c41a' }} />}
                <Typography.Text strong style={{ fontSize: 12 }}>{m.role === 'assistant' ? 'AI 助手' : '我'}</Typography.Text>
                {m.tool && <Tag color="blue" style={{ fontSize: 11 }}>{m.tool}</Tag>}
              </Space>
              <div
                style={{
                  background: m.role === 'user' ? '#1677ff' : '#fff',
                  color: m.role === 'user' ? '#fff' : 'inherit',
                  padding: '8px 12px', borderRadius: 10, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                  border: m.role === 'user' ? 'none' : '1px solid #f0f0f0',
                }}
              >
                {m.steps && m.steps.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    {m.steps.map((st, j) => (
                      <div key={j} style={{ marginBottom: 4, fontSize: 12 }}>
                        <Tag color={st.ok ? 'green' : 'red'} style={{ marginRight: 6, fontSize: 11 }}>
                          {st.action ?? '思考'}
                        </Tag>
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          {st.thought}
                          {st.result ? ` → ${st.result.slice(0, 90)}${st.result.length > 90 ? '…' : ''}` : ''}
                        </Typography.Text>
                      </div>
                    ))}
                  </div>
                )}
                {m.content}
                {renderData(m)}
              </div>
            </div>
          </div>
        ))}
        {busy && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Spin size="small" /><Typography.Text type="secondary" style={{ fontSize: 12 }}>助手正在执行...</Typography.Text>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 输入区 */}
      <Space.Compact style={{ marginTop: 10, width: '100%' }}>
        <Input.TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入安全任务指令，例如：扫描 http://demo.local 或 应急响应"
          autoSize={{ minRows: 1, maxRows: 4 }}
          onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); send() } }}
          disabled={busy}
        />
        <Button type="primary" icon={<SendOutlined />} loading={busy} onClick={() => send()} style={{ height: 'auto' }}>
          发送
        </Button>
      </Space.Compact>
    </Card>
  )
}
