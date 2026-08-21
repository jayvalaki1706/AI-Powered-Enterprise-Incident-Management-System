import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import Button from '../../components/common/Button'
import Input from '../../components/common/Input'
import toast from 'react-hot-toast'

export default function RegisterPage() {
  const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'ENGINEER' })
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await register(form)
      toast.success('Registration successful! Please sign in.')
      navigate('/login')
    } catch (error) {
      toast.error(error.response?.data?.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Create Account</h2>
      <Input label="Full Name" name="full_name" value={form.full_name} onChange={handleChange} placeholder="John Doe" required />
      <Input label="Email" type="email" name="email" value={form.email} onChange={handleChange} placeholder="you@example.com" required />
      <Input label="Password" type="password" name="password" value={form.password} onChange={handleChange} placeholder="Min 8 characters" required minLength={8} />
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Role</label>
        <select name="role" value={form.role} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-600 dark:text-white">
          <option value="ENGINEER">Engineer</option>
          <option value="TEAM_LEAD">Team Lead</option>
          <option value="INCIDENT_MANAGER">Incident Manager</option>
          <option value="CUSTOMER">Customer</option>
        </select>
      </div>
      <Button type="submit" loading={loading} className="w-full">Create Account</Button>
      <p className="text-center text-sm text-gray-600 dark:text-gray-400">
        Already have an account?{' '}
        <Link to="/login" className="text-blue-600 hover:underline">Sign In</Link>
      </p>
    </form>
  )
}
