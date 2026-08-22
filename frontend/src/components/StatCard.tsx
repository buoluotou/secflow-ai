import { Card, Statistic } from 'antd'
import type { ReactNode } from 'react'

export default function StatCard({
  title,
  value,
  suffix,
  color,
  icon,
}: {
  title: string
  value: number | string
  suffix?: string
  color?: string
  icon?: ReactNode
}) {
  return (
    <Card size="small">
      <Statistic
        title={title}
        value={value}
        suffix={suffix}
        valueStyle={color ? { color } : undefined}
        prefix={icon}
      />
    </Card>
  )
}
