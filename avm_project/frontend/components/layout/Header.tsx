import React from 'react'
import { Menu, Bell, Settings, LogOut } from 'lucide-react'

export default function Header() {
  return (
    <header className="h-16 bg-white shadow-sm border-b border-neutral-300 flex items-center justify-between px-6">
      {/* Left Section */}
      <div className="flex items-center gap-4">
        <button className="p-2 hover:bg-neutral-100 rounded-lg transition-colors">
          <Menu className="w-6 h-6 text-neutral-700" />
        </button>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">AVM</span>
          </div>
          <span className="font-semibold text-neutral-900">AVM Dashboard</span>
        </div>
      </div>

      {/* Right Section - User Menu */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button className="relative p-2 hover:bg-neutral-100 rounded-lg transition-colors">
          <Bell className="w-6 h-6 text-neutral-700" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-error-500 rounded-full"></span>
        </button>

        {/* Settings */}
        <button className="p-2 hover:bg-neutral-100 rounded-lg transition-colors">
          <Settings className="w-6 h-6 text-neutral-700" />
        </button>

        {/* User Profile */}
        <div className="flex items-center gap-3 pl-4 border-l border-neutral-300">
          <div className="text-right">
            <p className="font-medium text-sm text-neutral-900">관리자</p>
            <p className="text-xs text-neutral-500">admin@avm.com</p>
          </div>
          <div className="w-10 h-10 bg-primary-500 rounded-full flex items-center justify-center text-white font-semibold">
            A
          </div>
        </div>

        {/* Logout */}
        <button className="p-2 hover:bg-neutral-100 rounded-lg transition-colors text-error-500">
          <LogOut className="w-6 h-6" />
        </button>
      </div>
    </header>
  )
}
