import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import Button from '../../components/common/Button'
import Input from '../../components/common/Input'
import toast from 'react-hot-toast'
import api from '../../services/api'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const [token, setToken] = useState(searchParams.get('token') || '')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }

    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }

    setLoading(true)
    try {
      await api.post('/auth/reset-password', {
        token,
        new_password: newPassword,
      })
      toast.success('Password reset successfully! Please sign in.')
      navigate('/login')
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Reset Password</h2>
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Enter your reset token and new password below.
      </p>
      <Input
        label="Reset Token"
        type="text"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        placeholder="Paste your reset token here"
        required
      />
      <Input
        label="New Password"
        type="password"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        placeholder="••••••••"
        required
      />
      <Input
        label="Confirm New Password"
        type="password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        placeholder="••••••••"
        required
      />
      <Button type="submit" loading={loading} className="w-full">
        Reset Password
      </Button>
      <p className="text-center text-sm text-gray-600 dark:text-gray-400">
        <Link to="/login" className="text-blue-600 hover:underline">Back to Sign In</Link>
      </p>
    </form>
  )
}
