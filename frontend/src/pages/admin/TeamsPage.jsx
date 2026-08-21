import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import Loading from '../../components/common/Loading'
import Button from '../../components/common/Button'
import Modal from '../../components/common/Modal'
import toast from 'react-hot-toast'
import { formatDateOnly } from '../../utils/timezone'

export default function TeamsPage() {
  const [showAddDepartment, setShowAddDepartment] = useState(false)
  const [showAddTeam, setShowAddTeam] = useState(false)
  const queryClient = useQueryClient()

  // ─── Queries ──────────────────────────────────────────────────────────────────

  const { data: departments, isLoading: depsLoading } = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get('/teams/departments').then((r) => r.data),
  })

  const { data: teams, isLoading: teamsLoading } = useQuery({
    queryKey: ['teams'],
    queryFn: () => api.get('/teams/').then((r) => r.data),
  })

  // ─── Department Mutations ─────────────────────────────────────────────────────

  const createDepartmentMutation = useMutation({
    mutationFn: (data) => api.post('/teams/departments', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['departments'] })
      setShowAddDepartment(false)
      toast.success('Department created successfully')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to create department'),
  })

  const deleteDepartmentMutation = useMutation({
    mutationFn: (id) => api.delete(`/teams/departments/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['departments'] })
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      toast.success('Department deleted successfully')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to delete department'),
  })

  // ─── Team Mutations ───────────────────────────────────────────────────────────

  const createTeamMutation = useMutation({
    mutationFn: (data) => api.post('/teams/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      setShowAddTeam(false)
      toast.success('Team created successfully')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to create team'),
  })

  const deleteTeamMutation = useMutation({
    mutationFn: (id) => api.delete(`/teams/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      toast.success('Team deleted successfully')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to delete team'),
  })

  // ─── Handlers ─────────────────────────────────────────────────────────────────

  const handleDeleteDepartment = (dept) => {
    if (window.confirm(`Are you sure you want to delete department "${dept.name}"? This will also remove associated teams.`)) {
      deleteDepartmentMutation.mutate(dept.id)
    }
  }

  const handleDeleteTeam = (team) => {
    if (window.confirm(`Are you sure you want to delete team "${team.name}"?`)) {
      deleteTeamMutation.mutate(team.id)
    }
  }

  const getDepartmentName = (departmentId) => {
    const dept = departments?.find((d) => d.id === departmentId)
    return dept?.name || 'Unknown'
  }

  if (depsLoading || teamsLoading) return <Loading />

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Teams & Departments</h1>

      {/* Departments Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Departments ({departments?.length || 0})
          </h2>
          <Button onClick={() => setShowAddDepartment(true)}>+ Add Department</Button>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
            <tr>
              <th className="text-left px-4 py-3">Name</th>
              <th className="text-right px-4 py-3">Created</th>
              <th className="text-center px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {departments?.length === 0 && (
              <tr>
                <td colSpan="3" className="px-4 py-6 text-center text-gray-500 dark:text-gray-400">
                  No departments yet. Create one to get started.
                </td>
              </tr>
            )}
            {departments?.map((dept) => (
              <tr key={dept.id}>
                <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{dept.name}</td>
                <td className="text-right px-4 py-3 text-gray-500 text-xs">{formatDateOnly(dept.created_at)}</td>
                <td className="text-center px-4 py-3">
                  <button
                    onClick={() => handleDeleteDepartment(dept)}
                    disabled={deleteDepartmentMutation.isPending}
                    className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 text-xs font-medium disabled:opacity-50"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Teams Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Teams ({teams?.length || 0})
          </h2>
          <Button onClick={() => setShowAddTeam(true)} disabled={!departments?.length}>
            + Add Team
          </Button>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
            <tr>
              <th className="text-left px-4 py-3">Name</th>
              <th className="text-left px-4 py-3">Department</th>
              <th className="text-right px-4 py-3">Created</th>
              <th className="text-center px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {teams?.length === 0 && (
              <tr>
                <td colSpan="4" className="px-4 py-6 text-center text-gray-500 dark:text-gray-400">
                  No teams yet. Create a department first, then add teams.
                </td>
              </tr>
            )}
            {teams?.map((team) => (
              <tr key={team.id}>
                <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{team.name}</td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{getDepartmentName(team.department_id)}</td>
                <td className="text-right px-4 py-3 text-gray-500 text-xs">{formatDateOnly(team.created_at)}</td>
                <td className="text-center px-4 py-3">
                  <button
                    onClick={() => handleDeleteTeam(team)}
                    disabled={deleteTeamMutation.isPending}
                    className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 text-xs font-medium disabled:opacity-50"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add Department Modal */}
      <AddDepartmentModal
        isOpen={showAddDepartment}
        onClose={() => setShowAddDepartment(false)}
        onSubmit={(data) => createDepartmentMutation.mutate(data)}
        loading={createDepartmentMutation.isPending}
      />

      {/* Add Team Modal */}
      <AddTeamModal
        isOpen={showAddTeam}
        onClose={() => setShowAddTeam(false)}
        onSubmit={(data) => createTeamMutation.mutate(data)}
        loading={createTeamMutation.isPending}
        departments={departments || []}
      />
    </div>
  )
}

function AddDepartmentModal({ isOpen, onClose, onSubmit, loading }) {
  const [name, setName] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({ name: name.trim() })
  }

  const handleClose = () => {
    setName('')
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Add Department">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Department Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            minLength={2}
            placeholder="e.g. Engineering"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-600 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={handleClose}>Cancel</Button>
          <Button type="submit" loading={loading}>Create Department</Button>
        </div>
      </form>
    </Modal>
  )
}

function AddTeamModal({ isOpen, onClose, onSubmit, loading, departments }) {
  const [form, setForm] = useState({ name: '', department_id: '' })

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({ name: form.name.trim(), department_id: form.department_id })
  }

  const handleClose = () => {
    setForm({ name: '', department_id: '' })
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Add Team">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Team Name
          </label>
          <input
            type="text"
            name="name"
            value={form.name}
            onChange={handleChange}
            required
            minLength={2}
            placeholder="e.g. Backend Team"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-600 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Department
          </label>
          <select
            name="department_id"
            value={form.department_id}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-600 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select a department</option>
            {departments.map((dept) => (
              <option key={dept.id} value={dept.id}>{dept.name}</option>
            ))}
          </select>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={handleClose}>Cancel</Button>
          <Button type="submit" loading={loading}>Create Team</Button>
        </div>
      </form>
    </Modal>
  )
}
