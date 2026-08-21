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
      toast.success('Incident assigned successfully')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to assign incident'),
  })

  const selfAssignMutation = useMutation({
    mutationFn: () => api.post(`/incidents/${id}/assign-me`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] })
      queryClient.invalidateQueries({ queryKey: ['incident-history', id] })
      queryClient.invalidateQueries({ queryKey: ['incidents'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Incident assigned to you')
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
      toast.success('Incident updated')
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
      toast.success('Incident deleted')
      navigate('/incidents')
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
      toast.success('Incident escalated')
    },
    onError: (err) => toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to escalate'),
  })

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this incident? This action cannot be undone.')) {
      deleteMutation.mutate()
    }
  }

  if (isLoading) return <Loading />
  if (!incident) return <p className="text-center text-gray-500 py-8">Incident not found</p>

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{incident.title}</h1>
          <div className="flex gap-2 mt-2 items-center">
            <select
              value={incident.priority}
              onChange={(e) => updateMutation.mutate({ priority: e.target.value })}
              className="text-xs font-medium px-2 py-1 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            <Badge variant={incident.status}>{incident.status.replace('_', ' ')}</Badge>
            {incident.escalation_level > 0 && <Badge variant="escalated">Level {incident.escalation_level}</Badge>}
          </div>
        </div>
        <div className="flex gap-2">
          {incident.status === 'open' && (
            <Button size="sm" onClick={() => updateMutation.mutate({ status: 'in_progress' })}>Start</Button>
          )}
          {incident.status === 'in_progress' && (
            <Button size="sm" variant="success" onClick={() => updateMutation.mutate({ status: 'resolved' })}>Resolve</Button>
          )}
          {['ADMIN', 'INCIDENT_MANAGER', 'TEAM_LEAD'].includes(currentUser?.role) && incident.status !== 'resolved' && incident.status !== 'closed' && (
            <Button size="sm" variant="secondary" onClick={() => escalateMutation.mutate()}>⬆ Escalate</Button>
          )}
          {currentUser?.role === 'ADMIN' && (
            <Button size="sm" variant="danger" onClick={handleDelete} loading={deleteMutation.isPending}>Delete</Button>
          )}
        </div>
      </div>

      {/* SLA Timer */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-1">
          <SLATimer deadline={incident.sla_deadline} status={incident.status} />
        </div>
        <div className="md:col-span-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-gray-500 dark:text-gray-400">SLA Deadline</p>
              <p className="font-medium text-gray-900 dark:text-white">
                {incident.sla_deadline ? formatDate(incident.sla_deadline) : 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Created</p>
              <p className="font-medium text-gray-900 dark:text-white">{formatDate(incident.created_at)}</p>
            </div>
            {incident.resolved_at && (
              <div>
                <p className="text-gray-500 dark:text-gray-400">Resolved</p>
                <p className="font-medium text-green-600 dark:text-green-400">{formatDate(incident.resolved_at)}</p>
              </div>
            )}
            <div>
              <p className="text-gray-500 dark:text-gray-400">Escalation Level</p>
              <p className="font-medium text-gray-900 dark:text-white">{incident.escalation_level}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Assignment */}
      {(canAssign) && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Assignment</h2>
          <div className="space-y-3">
            {incident.assigned_to && (
              <div className="text-sm">
                <span className="text-gray-500 dark:text-gray-400">Current Assignee: </span>
                <span className="font-medium text-blue-600 dark:text-blue-400">
                  {incident.assigned_to === currentUser?.id
                    ? '👤 You'
                    : users.find((u) => u.id === incident.assigned_to)?.full_name || 'Assigned'}
                </span>
              </div>
            )}
            {!incident.assigned_to && (
              <p className="text-sm text-gray-500 dark:text-gray-400">No assignee</p>
            )}

            {/* Searchable assignment */}
            <AssigneeDropdown
              users={users.filter((u) => u.role !== 'CUSTOMER')}
              selectedAssignee={selectedAssignee}
              onSelect={(id) => setSelectedAssignee(id)}
              onAssign={() => { if (selectedAssignee) assignMutation.mutate(selectedAssignee) }}
              loading={assignMutation.isPending}
            />
          </div>
        </div>
      )}

      {/* Details */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-2">Description</h2>
        <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{incident.description}</p>
      </div>

      {/* Comments */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Comments ({comments.length})</h2>
        <form onSubmit={(e) => { e.preventDefault(); if (comment.trim()) commentMutation.mutate({ content: comment }) }} className="flex gap-2 mb-4">
          <input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Add a comment..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
          <Button type="submit" size="sm" loading={commentMutation.isPending}>Post</Button>
        </form>
        <div className="space-y-3">
          {comments.map((c) => (
            <div key={c.id} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <p className="text-sm text-gray-800 dark:text-gray-200">{c.content}</p>
              <p className="text-xs text-gray-500 mt-1">{formatDate(c.created_at)}</p>
            </div>
          ))}
          {comments.length === 0 && <p className="text-sm text-gray-500">No comments yet</p>}
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
