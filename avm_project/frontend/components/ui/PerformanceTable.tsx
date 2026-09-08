import React from 'react'
import { CheckCircle, AlertCircle, Eye, Download } from 'lucide-react'

interface PerformanceTableProps {
  data: Array<{
    date: string
    status: string
    r2: number | null
    rmse: number | null
    duration: string | null
  }>
}

export default function PerformanceTable({ data }: PerformanceTableProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-success-500" />
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-warning-500" />
      case 'error':
        return <AlertCircle className="w-5 h-5 text-error-500" />
      default:
        return null
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'success':
        return '✅ 성공'
      case 'warning':
        return '⚠️ 주의'
      case 'error':
        return '❌ 실패'
      default:
        return '-'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'text-success-700'
      case 'warning':
        return 'text-warning-700'
      case 'error':
        return 'text-error-700'
      default:
        return 'text-neutral-700'
    }
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-neutral-300 bg-neutral-50">
            <th className="px-4 py-3 text-left text-sm font-semibold text-neutral-700">
              학습 날짜
            </th>
            <th className="px-4 py-3 text-left text-sm font-semibold text-neutral-700">
              상태
            </th>
            <th className="px-4 py-3 text-right text-sm font-semibold text-neutral-700">
              R² 점수
            </th>
            <th className="px-4 py-3 text-right text-sm font-semibold text-neutral-700">
              RMSE (원)
            </th>
            <th className="px-4 py-3 text-left text-sm font-semibold text-neutral-700">
              소요시간
            </th>
            <th className="px-4 py-3 text-center text-sm font-semibold text-neutral-700">
              액션
            </th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => (
            <tr
              key={index}
              className="border-b border-neutral-200 hover:bg-neutral-50 transition-colors"
            >
              <td className="px-4 py-3 text-sm text-neutral-900 font-medium">
                {row.date}
              </td>
              <td className="px-4 py-3">
                <div className={`flex items-center gap-2 text-sm font-medium ${getStatusColor(row.status)}`}>
                  {getStatusIcon(row.status)}
                  {getStatusText(row.status)}
                </div>
              </td>
              <td className="px-4 py-3 text-sm text-right font-semibold text-neutral-900">
                {row.r2 != null ? row.r2.toFixed(4) : '—'}
              </td>
              <td className="px-4 py-3 text-sm text-right text-neutral-700">
                {row.rmse != null ? Math.round(row.rmse).toLocaleString() : '—'}
              </td>
              <td className="px-4 py-3 text-sm text-neutral-700">
                {row.duration ?? '—'}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center justify-center gap-2">
                  <button className="p-2 hover:bg-primary-100 rounded-lg transition-colors text-primary-500">
                    <Eye className="w-4 h-4" />
                  </button>
                  <button className="p-2 hover:bg-primary-100 rounded-lg transition-colors text-primary-500">
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
