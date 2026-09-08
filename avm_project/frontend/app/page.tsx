'use client'

import React from 'react'
import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import Dashboard from '@/components/pages/Dashboard'
import RealtimeMonitoring from '@/components/pages/RealtimeMonitoring'
import DataAnalysis from '@/components/pages/DataAnalysis'

export default function Home() {
  const [activePage, setActivePage] = React.useState('dashboard')

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <Sidebar activePage={activePage} setActivePage={setActivePage} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <Header />

        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          {activePage === 'dashboard' && <Dashboard />}
          {activePage === 'monitoring' && <RealtimeMonitoring />}
          {activePage === 'data' && <DataAnalysis />}
          {/* Other pages will be added here */}
        </main>
      </div>
    </div>
  )
}
