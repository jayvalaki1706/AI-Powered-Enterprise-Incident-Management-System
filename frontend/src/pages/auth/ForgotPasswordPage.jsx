import { useState } from 'react'
import { Link } from 'react-router-dom'
import Button from '../../components/common/Button'
import Input from '../../components/common/Input'
import toast from 'react-hot-toast'
import api from '../../services/api'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [resetToken, setResetToken] = useState(null)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const response = await api.post('/auth/forgot-password', { email })
      setSubmitted(true)
      toast.success('Reset link sent!')
      // For testing: display the token (in production this would be emailed)
      if (response.data.reset_token) {
        setResetToken(response.data.reset_token)
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send reset link')
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Check Your Email</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          If an account with that email exists, a password reset link has been sent.
        </p>
        {resetToken && (
          <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-xs font-medium text-yellow-800 dark:text-yellow-200 mb-1">
              🧪 Testing Mode — Reset Token:
            </p>
            <code className="text-xs break-all text-yellow-700 dark:text-yellow-300 block">
              {resetToken}
            </code>
            <Link
              to={`/reset-password?token=${encodeURIComponent(resetToken)}`}
              className="mt-2 inline-block text-sm text-blue-600 hover:underline"
            >
              → Go to Reset Password Page
            </Link>
          </div>
        )}
        <p className="text-center text-sm text-gray-600 dark:text-gray-400">
          <Link to="/login" className="text-blue-600 hover:underline">Back to Sign In</Link>
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Forgot Password</h2>
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Enter your email address and we'll send you a link to reset your password.
      </p>
      <Input
        label="Email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
        required
      />
      <Button type="submit" loading={loading} className="w-full">
        Send Reset Link
      </Button>
      <p className="text-center text-sm text-gray-600 dark:text-gray-400">
        Remember your password?{' '}
        <Link to="/login" className="text-blue-600 hover:underline">Sign In</Link>
      </p>
    </form>
  )
}
