import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import Loading from '../../components/common/Loading'
import Badge from '../../components/common/Badge'
import Button from '../../components/common/Button'
import Modal from '../../components/common/Modal'
import { useAuth } from '../../context/AuthContext'
import { formatDateOnly } from '../../utils/timezone'
import toast from 'react-hot-toast'

export default function AdminPanel() {
  const [showAddUser, setShowAddUser] = useState(false)
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()

  // NOTE: Users are fetched without pagination. This is acceptable for a demo environment
  // where user counts are unlikely to exceed 100. If the user base grows significantly,
  // consider adding server-side pagination similar to AuditLogsPage.
  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.get('/auth/users').then((r) => r.data),
  })

  const { data: sla } = useQuery({
    queryKey: ['sla-compliance'],
    queryFn: () => api.get('/analytics/sla-compliance').then((r) => r.data),
    staleTime: 0,
    refetchOnWindowFocus: true,
  })

  const { data: departments = [] } = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get('/teams/departments').then((r) => r.data),
  })

  const assignDepartmentMutation = useMutation({
    mutationFn: ({ userId, departmentId }) => api.patch(`/auth/users/${userId}`, { department_id: departmentId || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('Department updated')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to update department'),
  })

  const createUserMutation = useMutation({
    mutationFn: (data) => api.post('/auth/register', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setShowAddUser(false)
      toast.success('User created successfully')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to create user'),
  })

  const deleteUserMutation = useMutation({
    mutationFn: (userId) => api.delete(`/auth/users/${userId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('User deactivated successfully')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to deactivate user'),
  })

  const activateUserMutation = useMutation({
    mutationFn: (userId) => api.patch(`/auth/users/${userId}`, { is_active: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('User activated successfully')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to activate user'),
  })

  const handleDeleteUser = (user) => {
    if (user.id === currentUser?.id) {
      toast.error('You cannot deactivate your own account')
      return
    }
    if (window.confirm(`Are you sure you want to deactivate "${user.full_name}"? They will no longer be able to log in.`)) {
      deleteUserMutation.mutate(user.id)
    }
  }

  if (isLoading) return <Loading />

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin Panel</h1>

      {/* SLA Compliance */}
      {sla && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">SLA Compliance</h2>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{sla.total_incidents}</p>
              <p className="text-sm text-gray-500">Total</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600">{sla.within_sla}</p>
              <p className="text-sm text-gray-500">Within SLA</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-red-600">{sla.breached_sla}</p>
              <p className="text-sm text-gray-500">Breached</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-blue-600">{sla.compliance_rate}%</p>
              <p className="text-sm text-gray-500">Rate</p>
            </div>
          </div>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Users ({users?.length || 0})</h2>
          <Button onClick={() => setShowAddUser(true)}>+ Add User</Button>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
            <tr>
              <th className="text-left px-4 py-3">Name</th>
              <th className="text-left px-4 py-3">Email</th>
              <th className="text-center px-4 py-3">Role</th>
              <th className="text-center px-4 py-3">Department</th>
              <th className="text-center px-4 py-3">Status</th>
              <th className="text-right px-4 py-3">Joined</th>
              <th className="text-center px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {users?.map((user) => (
              <tr key={user.id}>
                <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{user.full_name}</td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{user.email}</td>
                <td className="text-center px-4 py-3"><Badge variant={user.role === 'ADMIN' ? 'critical' : 'medium'}>{user.role}</Badge></td>
                <td className="text-center px-4 py-3">
                  <select
                    value={user.department_id || ''}
                    onChange={(e) => assignDepartmentMutation.mutate({ userId: user.id, departmentId: e.target.value || null })}
                    className="text-xs px-2 py-1 border border-gray-300 rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  >
                    <option value="">No Department</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                </td>
                <td className="text-center px-4 py-3">
                  <span className={`inline-block h-2 w-2 rounded-full ${user.is_active ? 'bg-green-500' : 'bg-red-500'}`} />
                </td>
                <td className="text-right px-4 py-3 text-gray-500 text-xs">{formatDateOnly(user.created_at)}</td>
                <td className="text-center px-4 py-3">
                  {user.id !== currentUser?.id ? (
                    user.is_active ? (
                      <button
                        onClick={() => handleDeleteUser(user)}
                        disabled={deleteUserMutation.isPending}
                        className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 text-xs font-medium disabled:opacity-50"
                      >
                        Deactivate
                      </button>
                    ) : (
                      <button
                        onClick={() => activateUserMutation.mutate(user.id)}
                        disabled={activateUserMutation.isPending}
                        className="text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-300 text-xs font-medium disabled:opacity-50"
                      >
                        Activate
                      </button>
                    )
                  ) : (
                    <span className="text-xs text-gray-400">You</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add User Modal */}
      <AddUserModal
        isOpen={showAddUser}
        onClose={() => setShowAddUser(false)}
        onSubmit={(data) => createUserMutation.mutate(data)}
        loading={createUserMutation.isPending}
      />
    </div>
  )
}

function AddUserModal({ isOpen, onClose, onSubmit, loading }) {
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'ENGINEER',
  })
  const [errors, setErrors] = useState({})

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
    // Clear error for the field being edited
    if (errors[e.target.name]) {
      setErrors({ ...errors, [e.target.name]: '' })
    }
  }

  const validate = () => {
    const newErrors = {}

    if (!form.full_name.trim()) {
      newErrors.full_name = 'Full name is required'
    } else if (form.full_name.trim().length < 2) {
      newErrors.full_name = 'Full name must be at least 2 characters'
    }

    if (!form.email.trim()) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      newErrors.email = 'Please enter a valid email address'
    }

    if (!form.password) {
      newErrors.password = 'Password is required'
    } else if (form.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters'
    } else if (!/\d/.test(form.password)) {
      newErrors.password = 'Password must contain at least one number'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return
    onSubmit(form)
  }

  // Reset form when modal opens
  const handleClose = () => {
    setForm({ full_name: '', email: '', password: '', role: 'ENGINEER' })
    setErrors({})
    onClose()
  }

  const hasErrors = Object.values(errors).some((e) => e)

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Add New User">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Full Name</label>
          <input
            type="text"
            name="full_name"
            value={form.full_name}
            onChange={handleChange}
            required
            placeholder="John Doe"
            className={`w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.full_name ? 'border-red-500 dark:border-red-500' : 'border-gray-300 dark:border-gray-600'}`}
          />
          {errors.full_name && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.full_name}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
          <input
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
            required
            placeholder="user@company.com"
            className={`w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.email ? 'border-red-500 dark:border-red-500' : 'border-gray-300 dark:border-gray-600'}`}
          />
          {errors.email && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.email}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
          <input
            type="password"
            name="password"
            value={form.password}
            onChange={handleChange}
            required
            placeholder="Minimum 8 characters with a number"
            className={`w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.password ? 'border-red-500 dark:border-red-500' : 'border-gray-300 dark:border-gray-600'}`}
          />
          {errors.password && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.password}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Role</label>
          <select
            name="role"
            value={form.role}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-600 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="ENGINEER">Engineer</option>
            <option value="TEAM_LEAD">Team Lead</option>
            <option value="INCIDENT_MANAGER">Incident Manager</option>
            <option value="ADMIN">Admin</option>
            <option value="CUSTOMER">Customer</option>
          </select>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={handleClose}>Cancel</Button>
          <Button type="submit" loading={loading} disabled={hasErrors}>Create User</Button>
        </div>
      </form>
    </Modal>
  )
}
