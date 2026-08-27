import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import AuthLayout from './layouts/AuthLayout'
import ProtectedRoute from './components/auth/ProtectedRoute'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage'
import ResetPasswordPage from './pages/auth/ResetPasswordPage'
import DashboardPage from './pages/analytics/DashboardPage'
import IncidentListPage from './pages/incidents/IncidentListPage'
import IncidentDetailPage from './pages/incidents/IncidentDetailPage'
import AdminPanel from './pages/admin/AdminPanel'
import TeamsPage from './pages/admin/TeamsPage'
import ProfilePage from './pages/profile/ProfilePage'
import AIAssistantPage from './pages/ai/AIAssistantPage'
import AuditLogsPage from './pages/admin/AuditLogsPage'

function App() {
  return (
    <Routes>
      {/* Auth Routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>

      {/* Protected Routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/tickets" element={<IncidentListPage />} />
          <Route path="/tickets/:id" element={<IncidentDetailPage />} />
          <Route path="/admin" element={<AdminPanel />} />
          <Route path="/teams" element={<TeamsPage />} />
          <Route path="/audit-logs" element={<AuditLogsPage />} />
          <Route path="/ai-assistant" element={<AIAssistantPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
