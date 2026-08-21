import { Outlet, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Loading from '../components/common/Loading'

export default function AuthLayout() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) return <Loading fullScreen />
  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">🚨 Incident Management</h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">Enterprise Incident Management & AI Assistant</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
