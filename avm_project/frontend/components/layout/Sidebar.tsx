'use client'

import React from 'react'
import {
  LayoutDashboard,
  BarChart3,
  Database,
  Settings,
  LogOut,
  ChevronDown,
  Activity,
} from 'lucide-react'

interface SidebarProps {
  activePage: string
  setActivePage: (page: string) => void
}

export default function Sidebar({ activePage, setActivePage }: SidebarProps) {
  const menuItems = [
    {
      id: 'dashboard',
      label: '대시보드',
      icon: LayoutDashboard,
      description: '모델 성능 모니터링',
    },
    {
      id: 'monitoring',
      label: '실시간 모니터링',
      icon: Activity,
      description: '시스템 상태 및 알림',
    },
    {
      id: 'models',
      label: '모델 상세',
      icon: BarChart3,
      description: '개별 모델 분석',
    },
    {
      id: 'data',
      label: '데이터 분석',
      icon: Database,
      description: '데이터 품질 분석',
    },
    {
      id: 'settings',
      label: '설정',
      icon: Settings,
      description: '시스템 설정',
    },
  ]

  return (
    <aside className="w-sidebar bg-white border-r border-neutral-300 flex flex-col">
      {/* Logo Section */}
      <div className="h-16 flex items-center px-4 border-b border-neutral-300">
        <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-lg">A</span>
        </div>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 px-3 py-6 space-y-2 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon
          const isActive = activePage === item.id

          return (
            <button
              key={item.id}
              onClick={() => setActivePage(item.id)}
              className={`w-full flex items-start gap-3 px-3 py-3 rounded-lg transition-all group ${
                isActive
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-neutral-600 hover:bg-neutral-100'
              }`}
            >
              <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
                isActive ? 'text-primary-500' : 'group-hover:text-primary-400'
              }`} />
              <div className="text-left flex-1">
                <div className={`text-sm font-medium ${isActive ? 'text-primary-700' : 'text-neutral-900'}`}>
                  {item.label}
                </div>
                <div className="text-xs text-neutral-500 hidden group-hover:block">
                  {item.description}
                </div>
              </div>
              {isActive && (
                <ChevronDown className="w-4 h-4 text-primary-500" />
              )}
            </button>
          )
        })}
      </nav>

      {/* Bottom Section */}
      <div className="px-3 py-4 border-t border-neutral-300 space-y-2">
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-error-500 hover:bg-error-50 transition-colors">
          <LogOut className="w-5 h-5" />
          <span className="text-sm font-medium">로그아웃</span>
        </button>
        <div className="px-3 py-2 text-xs text-neutral-500">
          <p>v1.0.0</p>
          <p>© 2026 AVM</p>
        </div>
      </div>
    </aside>
  )
}
