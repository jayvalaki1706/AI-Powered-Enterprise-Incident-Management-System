import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import Button from '../../components/common/Button'
import Badge from '../../components/common/Badge'
import Loading from '../../components/common/Loading'
import SLATimer from '../../components/incidents/SLATimer'
import FileUpload from '../../components/incidents/FileUpload'
import { useAuth } from '../../context/AuthContext'
import { formatDate, formatDateFull } from '../../utils/timezone'
import toast from 'react-hot-toast'

export default function IncidentDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()
  const [comment, setComment] = useState('')
  const [selectedAssignee, setSelectedAssignee] = useState('')

  const canAssign = currentUser?.role !== 'CUSTOMER'
  const canSelfAssign = false // Deprecated: using full dropdown for everyone

  const { data: incident, isLoading } = useQuery({
    queryKey: ['incident', id],
    queryFn: () => api.get(`/incidents/${id}`).then((r) => r.data),
  })

  const { data: users = [] } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get('/auth/users').then((r) => r.data),
  })

  const assignMutation = useMutation({
    mutationFn: (assigneeId) => api.post(`/incidents/${id}/assign/${assigneeId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] })
      queryClient.invalidateQueries({ queryKey: ['incident-history', id] })
      queryClient.invalidateQueries({ queryKey: ['incidents'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setSelectedAssignee('')
      toast.success('Ticket assigned successfully')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to assign ticket'),
  })

  const selfAssignMutation = useMutation({
    mutationFn: () => api.post(`/incidents/${id}/assign-me`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] })
      queryClient.invalidateQueries({ queryKey: ['incident-history', id] })
      queryClient.invalidateQueries({ queryKey: ['incidents'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Ticket assigned to you')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to self-assign'),
  })

  const { data: comments = [] } = useQuery({
    queryKey: ['incident-comments', id],
    queryFn: () => api.get(`/incidents/${id}/comments`).then((r) => r.data),
  })

  const { data: history = [] } = useQuery({
    queryKey: ['incident-history', id],
    queryFn: () => api.get(`/incidents/${id}/history`).then((r) => r.data),
  })

  const updateMutation = useMutation({
    mutationFn: (data) => api.patch(`/incidents/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] })
      queryClient.invalidateQueries({ queryKey: ['incident-history', id] })
      queryClient.invalidateQueries({ queryKey: ['incidents'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['sla-compliance'] })
      toast.success('Ticket updated')
    },
  })

  const commentMutation = useMutation({
    mutationFn: (data) => api.post(`/incidents/${id}/comments`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident-comments', id] })
      setComment('')
      toast.success('Comment added')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/incidents/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['sla-compliance'] })
      toast.success('Ticket deleted')
      navigate('/tickets')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to delete'),
  })

  const escalateMutation = useMutation({
    mutationFn: () => api.post(`/incidents/${id}/escalate`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] })
      queryClient.invalidateQueries({ queryKey: ['incident-history', id] })
      queryClient.invalidateQueries({ queryKey: ['incidents'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Ticket escalated')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to escalate'),
  })

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this ticket? This action cannot be undone.')) {
      deleteMutation.mutate()
    }
  }

  if (isLoading) return <Loading />
  if (!incident) return <p className="text-center text-gray-500 py-8">Ticket not found</p>

  return (
    <div className="space-y-6">
      {/* Title + Actions */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-mono font-semibold text-gray-400 dark:text-gray-500 mb-1">#{incident.ticket_number || '—'}</p>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{incident.title}</h1>
          {incident.escalation_level > 0 && (
            <span className="inline-block mt-2 text-xs px-2 py-1 rounded bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 font-medium">
              Escalation Level {incident.escalation_level}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {['ADMIN', 'INCIDENT_MANAGER', 'TEAM_LEAD'].includes(currentUser?.role) && incident.status !== 'closed' && (
            <Button size="sm" variant="secondary" onClick={() => escalateMutation.mutate()}>Escalate</Button>
          )}
          {currentUser?.role === 'ADMIN' && (
            <Button size="sm" variant="danger" onClick={handleDelete} loading={deleteMutation.isPending}>Delete</Button>
          )}
        </div>
      </div>

      {/* SLA & Timeline - Horizontal Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 items-center">
          <div>
            <SLATimer deadline={incident.sla_deadline} status={incident.status} />
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">SLA Deadline</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white mt-0.5">
              {incident.sla_deadline ? formatDate(incident.sla_deadline) : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Created</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white mt-0.5">{formatDate(incident.created_at)}</p>
          </div>
          <div>
            {incident.resolved_at ? (
              <>
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Resolved</p>
                <p className="text-sm font-medium text-green-600 dark:text-green-400 mt-0.5">{formatDate(incident.resolved_at)}</p>
              </>
            ) : (
              <>
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Resolved</p>
                <p className="text-sm text-gray-400 mt-0.5">—</p>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Content + Right Sidebar (Freshservice style) */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left: Description, Comments, Files, History */}
        <div className="lg:col-span-3 space-y-6">
          {/* Description */}
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
            <h2 className="font-semibold text-gray-900 dark:text-white mb-2">Description</h2>
            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{incident.description}</p>
          </div>

          {/* Comments */}
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
            <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Comments ({comments.length})</h2>
            <form onSubmit={(e) => { e.preventDefault(); if (comment.trim()) commentMutation.mutate({ content: comment }) }} className="flex gap-3 mb-5">
              <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                {currentUser?.full_name?.[0]?.toUpperCase()}
              </div>
              <input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Write a comment..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <Button type="submit" size="sm" loading={commentMutation.isPending}>Post</Button>
            </form>
            <div className="space-y-4">
              {comments.map((c) => (
                <div key={c.id} className="flex gap-3">
                  <div className="h-8 w-8 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center text-gray-700 dark:text-gray-200 text-xs font-bold shrink-0">
                    {c.user_name?.[0]?.toUpperCase() || '?'}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-900 dark:text-white">{c.user_name || 'Unknown'}</span>
                      <span className="text-xs text-gray-400">{formatDate(c.created_at)}</span>
                    </div>
                    <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{c.content}</p>
                  </div>
                </div>
              ))}
              {comments.length === 0 && <p className="text-sm text-gray-500 text-center py-4">No comments yet. Be the first to comment.</p>}
            </div>
          </div>

          {/* File Attachments */}
          <FileUpload incidentId={id} />

          {/* History */}
          {history.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
              <h2 className="font-semibold text-gray-900 dark:text-white mb-4">History</h2>
              <div className="space-y-2">
                {history.map((h) => {
                  const resolveValue = (field, value) => {
                    if (!value || value === '—') return '—'
                    if (field === 'assigned_to') {
                      const user = users.find((u) => u.id === value)
                      return user ? user.full_name : value
                    }
                    return value
                  }
                  return (
                    <div key={h.id} className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
                      <span className="text-xs text-gray-400 w-36">{formatDate(h.created_at)}</span>
                      <span><strong>{h.field_changed}</strong>: {resolveValue(h.field_changed, h.old_value)} → {resolveValue(h.field_changed, h.new_value)}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar: Properties (Freshservice style) */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-5 lg:sticky lg:top-6">
            {/* Status */}
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Status</label>
              <select
                value={incident.status}
                onChange={(e) => updateMutation.mutate({ status: e.target.value })}
                className="mt-1.5 w-full text-sm font-medium px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 dark:bg-gray-700 dark:text-white bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              >
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="pending">Pending</option>
                <option value="hold">Hold</option>
                <option value="closed">Closed</option>
              </select>
            </div>

            {/* Severity */}
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Severity</label>
              <select
                value={incident.priority}
                onChange={(e) => updateMutation.mutate({ priority: e.target.value })}
                className="mt-1.5 w-full text-sm font-medium px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 dark:bg-gray-700 dark:text-white bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <hr className="border-gray-100 dark:border-gray-700" />

            {/* Assignment */}
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Assigned To</label>
              <select
                value={incident.assigned_to || ''}
                onChange={(e) => { if (e.target.value) assignMutation.mutate(e.target.value) }}
                className="mt-1.5 w-full text-sm font-medium px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 dark:bg-gray-700 dark:text-white bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              >
                <option value="">Unassigned</option>
                {users.filter((u) => u.role !== 'CUSTOMER').map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name} ({u.role.replace('_', ' ')})</option>
                ))}
              </select>
            </div>

            <hr className="border-gray-100 dark:border-gray-700" />

            {/* Created By */}
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Created By</label>
              <p className="mt-1.5 text-sm font-medium text-gray-900 dark:text-white">
                {users.find((u) => u.id === incident.created_by)?.full_name || 'Unknown'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function AssigneeDropdown({ users, selectedAssignee, onSelect, onAssign, loading }) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const dropdownRef = useState(null)

  const filteredUsers = users.filter((u) =>
    u.full_name.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase()) ||
    u.role.toLowerCase().includes(search.toLowerCase())
  )

  const selectedUser = users.find((u) => u.id === selectedAssignee)

  return (
    <div className="flex gap-2 items-center">
      <div className="flex-1 relative">
        {/* Trigger Button */}
        <button
          type="button"
          onClick={() => { setIsOpen(!isOpen); setSearch('') }}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white text-sm text-left focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center justify-between"
        >
          <span className={selectedUser ? 'text-gray-900 dark:text-white' : 'text-gray-400'}>
            {selectedUser ? `${selectedUser.full_name} (${selectedUser.role.replace('_', ' ')})` : 'Select assignee...'}
          </span>
          <svg className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Dropdown */}
        {isOpen && (
          <div className="absolute z-20 mt-1 w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg overflow-hidden">
            {/* Search inside dropdown */}
            <div className="p-2 border-b border-gray-200 dark:border-gray-600">
              <input
                type="text"
                placeholder="🔍 Search by name, email, or role..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                autoFocus
                className="w-full px-3 py-1.5 border border-gray-300 rounded-md dark:bg-gray-800 dark:border-gray-600 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* User List */}
            <div className="max-h-48 overflow-y-auto">
              {filteredUsers.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => { onSelect(u.id); setIsOpen(false) }}
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-blue-50 dark:hover:bg-gray-600 transition-colors border-b border-gray-100 dark:border-gray-600 last:border-0 ${
                    selectedAssignee === u.id ? 'bg-blue-50 dark:bg-gray-600' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-medium text-gray-900 dark:text-white">{u.full_name}</span>
                      <span className="text-gray-500 dark:text-gray-400 ml-2 text-xs">{u.email}</span>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                      {u.role.replace('_', ' ')}
                    </span>
                  </div>
                </button>
              ))}
              {filteredUsers.length === 0 && (
                <p className="px-3 py-3 text-sm text-gray-500 text-center">No users found</p>
              )}
            </div>
          </div>
        )}

        {/* Click outside to close */}
        {isOpen && (
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
        )}
      </div>

      <Button
        size="sm"
        onClick={onAssign}
        loading={loading}
        disabled={!selectedAssignee}
      >
        Assign
      </Button>
    </div>
  )
}
