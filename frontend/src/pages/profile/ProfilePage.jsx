import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import Button from '../../components/common/Button'
import { useAuth } from '../../context/AuthContext'
import toast from 'react-hot-toast'

const TIMEZONES = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
  { value: 'America/New_York', label: 'Eastern Time (US & Canada)' },
  { value: 'America/Chicago', label: 'Central Time (US & Canada)' },
  { value: 'America/Denver', label: 'Mountain Time (US & Canada)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (US & Canada)' },
  { value: 'America/Toronto', label: 'Toronto (Eastern)' },
  { value: 'America/Sao_Paulo', label: 'São Paulo (Brazil)' },
  { value: 'Europe/London', label: 'London (GMT/BST)' },
  { value: 'Europe/Paris', label: 'Paris (CET/CEST)' },
  { value: 'Europe/Berlin', label: 'Berlin (CET/CEST)' },
  { value: 'Europe/Moscow', label: 'Moscow (MSK)' },
  { value: 'Asia/Dubai', label: 'Dubai (GST)' },
  { value: 'Asia/Kolkata', label: 'India (IST)' },
  { value: 'Asia/Bangkok', label: 'Bangkok (ICT)' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT)' },
  { value: 'Asia/Shanghai', label: 'China (CST)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEST/AEDT)' },
  { value: 'Pacific/Auckland', label: 'Auckland (NZST/NZDT)' },
]

export default function ProfilePage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const [fullName, setFullName] = useState(user?.full_name || '')
  const [timezone, setTimezone] = useState(user?.timezone || 'Asia/Kolkata')
  const [isEditing, setIsEditing] = useState(false)

  const updateMutation = useMutation({
    mutationFn: (data) => api.patch('/auth/me/profile', data),
    onSuccess: (response) => {
      // Update the cached user data
      queryClient.invalidateQueries({ queryKey: ['auth-user'] })
      // Force a page reload to apply timezone changes everywhere
      toast.success('Profile updated successfully')
      setIsEditing(false)
      // Reload to refresh user context
      setTimeout(() => window.location.reload(), 500)
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to update profile'),
  })

  const handleSave = () => {
    const updates = {}
    if (fullName !== user?.full_name) updates.full_name = fullName
    if (timezone !== user?.timezone) updates.timezone = timezone

    if (Object.keys(updates).length === 0) {
      setIsEditing(false)
      return
    }
    updateMutation.mutate(updates)
  }

  const handleCancel = () => {
    setFullName(user?.full_name || '')
    setTimezone(user?.timezone || 'UTC')
    setIsEditing(false)
  }

  // Get current time in user's timezone
  const currentTime = new Date().toLocaleString('en-US', {
    timeZone: timezone,
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Profile</h1>

      {/* Profile Card */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="h-16 w-16 rounded-full bg-white/20 flex items-center justify-center text-white text-2xl font-bold">
                {user?.full_name?.[0]?.toUpperCase()}
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">{user?.full_name}</h2>
                <p className="text-blue-100">{user?.email}</p>
              </div>
            </div>
            {!isEditing && (
              <button
                onClick={() => setIsEditing(true)}
                className="px-4 py-2 bg-white/20 hover:bg-white/30 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Edit Profile
              </button>
            )}
          </div>
        </div>

        {/* Info */}
        <div className="p-6 space-y-5">
          {/* Full Name */}
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Full Name</label>
            {isEditing ? (
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            ) : (
              <p className="text-gray-900 dark:text-white font-medium">{user?.full_name}</p>
            )}
          </div>

          {/* Email (read only) */}
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Email</label>
            <p className="text-gray-900 dark:text-white">{user?.email}</p>
          </div>

          {/* Role (read only) */}
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Role</label>
            <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 rounded-full text-sm font-medium">
              {user?.role?.replace('_', ' ')}
            </span>
          </div>

          {/* Timezone */}
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Timezone</label>
            {isEditing ? (
              <select
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz.value} value={tz.value}>{tz.label}</option>
                ))}
              </select>
            ) : (
              <p className="text-gray-900 dark:text-white">{TIMEZONES.find(t => t.value === user?.timezone)?.label || user?.timezone || 'UTC'}</p>
            )}
          </div>

          {/* Current Time in Timezone */}
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Current Time</label>
            <p className="text-gray-900 dark:text-white font-mono text-sm">{currentTime}</p>
          </div>

          {/* Member Since (read only) */}
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Member Since</label>
            <p className="text-gray-900 dark:text-white">
              {user?.created_at ? new Date(user.created_at).toLocaleString('en-US', { timeZone: timezone, dateStyle: 'long' }) : 'N/A'}
            </p>
          </div>

          {/* Account Status */}
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Account Status</label>
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${user?.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'}`}>
              <span className={`inline-block w-2 h-2 rounded-full ${user?.is_active ? 'bg-green-500' : 'bg-red-500'}`} />
              {user?.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>

          {/* Actions */}
          {isEditing && (
            <div className="flex gap-3 pt-2 border-t dark:border-gray-700">
              <Button onClick={handleSave} loading={updateMutation.isPending}>Save Changes</Button>
              <Button variant="secondary" onClick={handleCancel}>Cancel</Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
