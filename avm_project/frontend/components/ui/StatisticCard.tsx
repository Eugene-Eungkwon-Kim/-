import React from 'react'
import {
  BarChart3,
  TrendingUp,
  ArrowUp,
  Activity,
} from 'lucide-react'

interface StatisticCardProps {
  label: string
  value: string
  subtext: string
  icon: 'chart' | 'trending' | 'up' | 'activity'
}

export default function StatisticCard({
  label,
  value,
  subtext,
  icon,
}: StatisticCardProps) {
  const icons = {
    chart: BarChart3,
    trending: TrendingUp,
    up: ArrowUp,
    activity: Activity,
  }

  const Icon = icons[icon]
  const iconColors = {
    chart: 'text-primary-500',
    trending: 'text-success-500',
    up: 'text-info-500',
    activity: 'text-warning-500',
  }

  return (
    <div className="bg-white rounded-lg border border-neutral-300 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-body-sm text-neutral-600 font-medium">{label}</p>
          <p className="text-h4 text-neutral-900 font-bold mt-1">{value}</p>
        </div>
        <Icon className={`w-6 h-6 ${iconColors[icon]}`} />
      </div>
      <p className="text-body-sm text-neutral-500">{subtext}</p>
    </div>
  )
}
