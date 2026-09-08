import React from 'react'
import { TrendingUp, TrendingDown, BarChart3, Target, Zap } from 'lucide-react'

interface SummaryCardProps {
  title: string
  value: string
  change?: number | null
  icon: 'chart' | 'trending' | 'target'
  color: 'blue' | 'green' | 'purple'
}

export default function SummaryCard({
  title,
  value,
  change,
  icon,
  color,
}: SummaryCardProps) {
  const bgColor = {
    blue: 'bg-blue-50 border-blue-200',
    green: 'bg-green-50 border-green-200',
    purple: 'bg-purple-50 border-purple-200',
  }[color]

  const textColor = {
    blue: 'text-blue-700',
    green: 'text-green-700',
    purple: 'text-purple-700',
  }[color]

  const iconColor = {
    blue: 'text-blue-500',
    green: 'text-green-500',
    purple: 'text-purple-500',
  }[color]

  const IconComponent = {
    chart: BarChart3,
    trending: TrendingUp,
    target: Target,
  }[icon]

  const isPositive = (change ?? 0) >= 0

  return (
    <div className={`rounded-lg border p-6 ${bgColor} hover:shadow-md transition-shadow`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <p className="text-body-sm text-neutral-600 font-medium">{title}</p>
          <p className="text-h3 text-neutral-900 font-bold mt-2">{value}</p>
        </div>
        <div className={`p-3 rounded-lg bg-white ${textColor}`}>
          <IconComponent className="w-6 h-6" />
        </div>
      </div>

      {/* Change Indicator — 이전 학습 기록이 없으면(change == null) 지어낸
          비교값을 보여주지 않고 그냥 생략한다. */}
      {change != null && (
        <div className="flex items-center gap-2">
          {isPositive ? (
            <>
              <TrendingUp className="w-4 h-4 text-success-500" />
              <span className="text-sm font-medium text-success-700">
                +{change.toFixed(2)}%
              </span>
            </>
          ) : (
            <>
              <TrendingDown className="w-4 h-4 text-error-500" />
              <span className="text-sm font-medium text-error-700">
                {change.toFixed(2)}%
              </span>
            </>
          )}
          <span className="text-sm text-neutral-600">이전 대비</span>
        </div>
      )}
    </div>
  )
}
