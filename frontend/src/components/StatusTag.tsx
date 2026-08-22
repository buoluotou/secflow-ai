import { Tag } from 'antd'

const COLORS: Record<string, string> = {
  critical: 'red',
  high: 'volcano',
  medium: 'orange',
  low: 'blue',
  info: 'default',
  open: 'processing',
  closed: 'default',
  approved: 'success',
  rejected: 'error',
  new: 'cyan',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  queued: 'default',
  true_positive: 'red',
  false_positive: 'default',
  likely_true_positive: 'volcano',
  likely_false_positive: 'default',
}

export default function StatusTag({ value }: { value?: string | null }) {
  if (!value) return <Tag>—</Tag>
  return <Tag color={COLORS[value] ?? 'default'}>{value}</Tag>
}
