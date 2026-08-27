import { useState, useRef, useEffect } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { HomeIcon, ExclamationTriangleIcon, CogIcon, UserCircleIcon, SparklesIcon, SunIcon, MoonIcon, ArrowRightOnRectangleIcon, ClipboardDocumentListIcon, UserGroupIcon, Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline'
import NotificationBell from '../components/notifications/NotificationBell'

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: HomeIcon },
  { path: '/tickets', label: 'Tickets', icon: ExclamationTriangleIcon },
  { path: '/ai-assistant', label: 'AI Assistant', icon: SparklesIcon, roles: ['ADMIN', 'INCIDENT_MANAGER', 'TEAM_LEAD', 'ENGINEER'] },
  { path: '/admin', label: 'Admin', icon: CogIcon, roles: ['ADMIN', 'INCIDENT_MANAGER'] },
  { path: '/teams', label: 'Teams', icon: UserGroupIcon, roles: ['ADMIN', 'INCIDENT_MANAGER'] },
  { path: '/audit-logs', label: 'Audit Logs', icon: ClipboardDocumentListIcon, roles: ['ADMIN', 'INCIDENT_MANAGER'] },
]

export default function MainLayout() {
  const { user, logout } = useAuth()
  const { darkMode, toggleDarkMode } = useTheme()
  const navigate = useNavigate()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const menuRef = useRef(null)
  const sidebarRef = useRef(null)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // Close user menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowUserMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Close mobile sidebar when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (sidebarOpen && sidebarRef.current && !sidebarRef.current.contains(event.target)) {
        setSidebarOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [sidebarOpen])

  const filteredNav = navItems.filter(
    (item) => !item.roles || item.roles.includes(user?.role)
  )

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Mobile Top Bar */}
      <div className="md:hidden sticky top-0 z-50 flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setSidebarOpen(true)}
          className="p-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
          aria-label="Open menu"
        >
          <Bars3Icon className="h-6 w-6" />
        </button>
        <h1 className="text-lg font-bold text-gray-900 dark:text-white">⚡ ResolvIQ</h1>
        <NotificationBell />
      </div>

      {/* Mobile Overlay Backdrop */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-40 bg-black/50" aria-hidden="true" />
      )}

      {/* Sidebar */}
      <aside
        ref={sidebarRef}
        className={`fixed inset-y-0 left-0 w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 z-50 transform transition-transform duration-200 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0`}
      >
        <div className="flex flex-col h-full">
          {/* Logo + Close button on mobile */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">⚡ ResolvIQ</h1>
            <button
              onClick={() => setSidebarOpen(false)}
              className="md:hidden p-1 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              aria-label="Close menu"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {filteredNav.map(({ path, label, icon: Icon }) => (
              <NavLink
                key={path}
                to={path}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                      : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                  }`
                }
              >
                <Icon className="h-5 w-5" />
                {label}
              </NavLink>
            ))}
          </nav>

          {/* User Section — Bottom Left */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700 relative" ref={menuRef}>
            {/* Popup Menu */}
            {showUserMenu && (
              <div className="absolute bottom-full left-4 right-4 mb-2 bg-white dark:bg-gray-700 rounded-xl shadow-lg border border-gray-200 dark:border-gray-600 overflow-hidden z-50">
                {/* Profile Link */}
                <button
                  onClick={() => { navigate('/profile'); setShowUserMenu(false); setSidebarOpen(false) }}
                  className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                >
                  <UserCircleIcon className="h-5 w-5" />
                  <span>Profile</span>
                </button>

                {/* Dark/Light Mode Toggle */}
                <button
                  onClick={toggleDarkMode}
                  className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                >
                  {darkMode ? <SunIcon className="h-5 w-5" /> : <MoonIcon className="h-5 w-5" />}
                  <span>{darkMode ? 'Light Mode' : 'Dark Mode'}</span>
                </button>

                {/* Logout */}
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-3 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors border-t border-gray-100 dark:border-gray-600"
                >
                  <ArrowRightOnRectangleIcon className="h-5 w-5" />
                  <span>Logout</span>
                </button>
              </div>
            )}

            {/* User Avatar & Info (clickable) */}
            <div
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-3 p-2 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <div className="h-9 w-9 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold shrink-0">
                {user?.full_name?.[0]?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{user?.full_name}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{user?.role?.replace('_', ' ')}</p>
              </div>
              <svg className={`h-4 w-4 text-gray-400 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="md:ml-64">
        {/* Top Header Bar (desktop only) */}
        <div className="hidden md:flex sticky top-0 z-30 items-center justify-end px-6 py-3 bg-white/80 dark:bg-gray-800/80 backdrop-blur border-b border-gray-200 dark:border-gray-700">
          <NotificationBell />
        </div>
        <div className="p-4 md:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
