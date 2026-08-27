import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../../services/api'
import Button from '../../components/common/Button'
import Badge from '../../components/common/Badge'
import Modal from '../../components/common/Modal'
import Input from '../../components/common/Input'
import Loading from '../../components/common/Loading'
import { SLATimerCompact } from '../../components/incidents/SLATimer'
import { formatDateOnly } from '../../utils/timezone'
import { useAuth } from '../../context/AuthContext'
import toast from 'react-hot-toast'

function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export default function IncidentListPage() {
  // Read URL query params for filters (from dashboard clicks)
  const [searchParams, setSearchParams] = useSearchParams()

  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get('priority') || '')
  const [showCreate, setShowCreate] = useState(false)
  const queryClient = useQueryClient()
  const { user } = useAuth()

  // Sync URL params when they change externally (e.g., clicking dashboard metric)
  useEffect(() => {
    const urlStatus = searchParams.get('status') || ''
    const urlPriority = searchParams.get('priority') || ''
    setStatusFilter(urlStatus)
    setPriorityFilter(urlPriority)
  }, [searchParams])

  const debouncedSearch = useDebounce(search, 400)

  // Reset to page 1 when filters change
  useEffect(() => { setPage(1) }, [debouncedSearch, statusFilter, priorityFilter])

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['incidents', page, debouncedSearch, statusFilter, priorityFilter],
    queryFn: () => api.get('/incidents/', {
      params: {
        page,
        page_size: 20,
        search: debouncedSearch || undefined,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
      }
    }).then((r) => r.data),
    keepPreviousData: true,
  })

  const { data: users = [] } = useQuery({
    queryKey: ['users-list'],
    queryFn: () => api.get('/auth/users').then((r) => r.data),
  })

  const getUserName = (userId) => {
    if (!userId) return null
    const user = users.find((u) => u.id === userId)
    return user ? user.full_name : null
  }

  const createMutation = useMutation({
    mutationFn: (data) => api.post('/incidents/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setShowCreate(false)
      toast.success('Ticket created')
    },
    onError: (err) => toast.error(err.response?.data?.message || 'Failed to create'),
  })

  const handleExportCSV = async () => {
    try {
      const params = new URLSearchParams()
      if (debouncedSearch) params.append('search', debouncedSearch)
      if (statusFilter) params.append('status', statusFilter)
      if (priorityFilter) params.append('priority', priorityFilter)

      const response = await api.get(`/incidents/export/csv?${params.toString()}`, {
        responseType: 'blob',
      })

      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'incidents_export.csv'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast.success('CSV exported successfully')
    } catch (err) {
      toast.error('Failed to export CSV')
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tickets</h1>
        <div className="flex items-center gap-2">
          {user?.role !== 'CUSTOMER' && (
            <Button variant="secondary" onClick={handleExportCSV}>Export CSV</Button>
          )}
          <Button onClick={() => setShowCreate(true)}>+ New Ticket</Button>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search by title, description, or ticket # ..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-600 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-600 dark:text-white"
        >
          <option value="">All Status</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="pending">Pending</option>
          <option value="hold">Hold</option>
          <option value="closed">Closed</option>
          <option value="escalated">Escalated</option>
        </select>
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-600 dark:text-white"
        >
          <option value="">All Priority</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        {(search || statusFilter || priorityFilter) && (
          <Button variant="secondary" size="sm" onClick={() => { setSearch(''); setStatusFilter(''); setPriorityFilter(''); setSearchParams({}) }}>
            Clear
          </Button>
        )}
      </div>

      {/* Loading indicator (subtle, doesn't replace content) */}
      {isFetching && (
        <div className="text-sm text-blue-500 dark:text-blue-400">Loading...</div>
      )}

      {/* Initial loading */}
      {isLoading && !data ? (
        <Loading />
      ) : (
        <>
          {/* Table */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
                <tr>
                  <th className="text-left px-4 py-3">Ticket #</th>
                  <th className="text-left px-4 py-3">Title</th>
                  <th className="text-center px-4 py-3">Created By</th>
                  <th className="text-center px-4 py-3">Priority</th>
                  <th className="text-center px-4 py-3">Status</th>
                  <th className="text-center px-4 py-3">Assigned To</th>
                  <th className="text-center px-4 py-3">SLA Remaining</th>
                  <th className="text-center px-4 py-3">Escalation</th>
                  <th className="text-right px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {data?.items?.map((incident) => (
                  <tr key={incident.id} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                    <td className="px-4 py-3">
                      <Link to={`/tickets/${incident.id}`} className="font-mono text-xs font-semibold text-gray-500 dark:text-gray-400 hover:text-blue-600">
                        #{incident.ticket_number || '—'}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <Link to={`/tickets/${incident.id}`} className="font-medium text-blue-600 hover:underline dark:text-blue-400">
                        {incident.title}
                      </Link>
                    </td>
                    <td className="text-center px-4 py-3 text-sm">
                      <span className="text-gray-900 dark:text-white">{getUserName(incident.created_by) || 'Unknown'}</span>
                    </td>
                    <td className="text-center px-4 py-3"><Badge variant={incident.priority}>{incident.priority}</Badge></td>
                    <td className="text-center px-4 py-3"><Badge variant={incident.status}>{incident.status.replace('_', ' ')}</Badge></td>
                    <td className="text-center px-4 py-3 text-sm">
                      {getUserName(incident.assigned_to) ? (
                        <span className="text-gray-900 dark:text-white font-medium">{getUserName(incident.assigned_to)}</span>
                      ) : (
                        <span className="text-gray-400 text-xs">Unassigned</span>
                      )}
                    </td>
                    <td className="text-center px-4 py-3">
                      <SLATimerCompact deadline={incident.sla_deadline} status={incident.status} />
                    </td>
                    <td className="text-center px-4 py-3 text-gray-600 dark:text-gray-400">{incident.escalation_level}</td>
                    <td className="text-right px-4 py-3 text-gray-500 dark:text-gray-400 text-xs">
                      {formatDateOnly(incident.created_at)}
                    </td>
                  </tr>
                ))}
                {data?.items?.length === 0 && (
                  <tr><td colSpan={9} className="text-center py-8 text-gray-500">No tickets found</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data?.total_pages > 1 && (
            <div className="flex justify-center gap-2">
              <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
              <span className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400">Page {page} of {data.total_pages}</span>
              <Button variant="secondary" size="sm" disabled={page >= data.total_pages} onClick={() => setPage(page + 1)}>Next</Button>
            </div>
          )}
        </>
      )}

      {/* Create Modal */}
      <CreateIncidentModal isOpen={showCreate} onClose={() => setShowCreate(false)} onSubmit={(d) => createMutation.mutate(d)} loading={createMutation.isPending} />
    </div>
  )
}

function CreateIncidentModal({ isOpen, onClose, onSubmit, loading }) {
  const [form, setForm] = useState({ title: '', description: '', priority: 'medium' })
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
    if (!form.title.trim()) {
      newErrors.title = 'Title is required'
    } else if (form.title.trim().length < 5) {
      newErrors.title = 'Title must be at least 5 characters'
    } else if (form.title.trim().length > 200) {
      newErrors.title = 'Title must be at most 200 characters'
    }

    if (!form.description.trim()) {
      newErrors.description = 'Description is required'
    } else if (form.description.trim().length < 20) {
      newErrors.description = 'Description must be at least 20 characters'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return
    onSubmit(form)
  }

  const hasErrors = Object.values(errors).some((e) => e)

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Ticket">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Input label="Title" name="title" value={form.title} onChange={handleChange} required />
          {errors.title && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.title}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
          <textarea name="description" value={form.description} onChange={handleChange} rows={4} required
            className={`w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.description ? 'border-red-500 dark:border-red-500' : 'border-gray-300 dark:border-gray-600'}`} />
          {errors.description && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.description}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Priority</label>
          <select name="priority" value={form.priority} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-600 dark:text-white">
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={loading} disabled={hasErrors}>Create</Button>
        </div>
      </form>
    </Modal>
  )
}
