'use client'

import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface LineChartProps {
  data: Array<{
    week: string
    r2: number
  }>
}

export default function R2LineChart({ data }: LineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart
        data={data}
        margin={{
          top: 5,
          right: 30,
          left: 0,
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
        <XAxis
          dataKey="week"
          stroke="#757575"
          style={{ fontSize: '12px' }}
        />
        <YAxis
          domain={[0.80, 0.85]}
          stroke="#757575"
          style={{ fontSize: '12px' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E0E0E0',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}
          formatter={(value: number) => value.toFixed(4)}
          labelFormatter={(label: string) => `${label}`}
        />
        <Legend
          wrapperStyle={{ paddingTop: '20px' }}
          formatter={() => 'R² 점수'}
        />
        <Line
          type="monotone"
          dataKey="r2"
          stroke="#2196F3"
          strokeWidth={3}
          dot={{
            fill: '#2196F3',
            r: 5,
          }}
          activeDot={{
            r: 7,
            fill: '#1565C0',
          }}
          name="R² 점수"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
