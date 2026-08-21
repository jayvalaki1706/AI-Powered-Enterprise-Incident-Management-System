import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'
import { formatDate } from '../../utils/timezone'
import Loading from '../../components/common/Loading'
import { ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline'

const RESOURCE_TYPES = [
  { value: '', label: 'All Resources' },
  { value: 'incident', label: 'Incident' },
  { value: 'user', label: 'User' },
  { value: 'team', label: 'Team' },
  { value: 'comment', label: 'Comment' },
  { value: 'attachment', label: 'Attachment' },
]

export default function AuditLogsPage() {
  const [filters, setFilters] = useState({
    resource_type: '',
    start_date: '',
    end_date: '',
  })
  const [page, setPage] = useState(1)
  const [expandedRow, setExpandedRow] = useState(null)
  const pageSize = 20

  const queryParams = {
    page,
    page_size: pageSize,
    ...(filters.resource_type && { resource_type: filters.resource_type }),
  }

  const { data, isLoading, isError } = useQuery({
    queryKey: ['audit-logs', queryParams],
    queryFn: () => api.get('/audit-logs/', { params: queryParams }).then((r) => r.data),
    keepPreviousData: true,
  })

  const logs = Array.isArray(data) ? data : data?.items || []
  const totalPages = data?.total_pages || Math.ceil((data?.total || logs.length) / pageSize) || 1

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const toggleRow = (id) => {
    setExpandedRow(expandedRow === id ? null : id)
  }

  // Filter by date range on client side (if API doesn't support date params directly)
  const filteredLogs = logs.filter((log) => {
    if (filters.start_date && new Date(log.created_at) < new Date(filters.start_date)) return false
    if (filters.end_date && new Date(log.created_at) > new Date(filters.end_date + 'T23:59:59')) return false
    return true
  })

  if (isLoading) return <Loading />

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Audit Logs</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Track all changes and actions performed in the system
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex flex-col">
          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Resource Type</label>
          <select
            value={filters.resource_type}
            onChange={(e) => handleFilterChange('resource_type', e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {RESOURCE_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col">
          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Start Date</label>
          <input
            type="date"
            value={filters.start_date}
            onChange={(e) => handleFilterChange('start_date', e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div className="flex flex-col">
          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">End Date</label>
          <input
            type="date"
            value={filters.end_date}
            onChange={(e) => handleFilterChange('end_date', e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {(filters.resource_type || filters.start_date || filters.end_date) && (
          <div className="flex items-end">
            <button
              onClick={() => {
                setFilters({ resource_type: '', start_date: '', end_date: '' })
                setPage(1)
              }}
              className="px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Clear Filters
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isError ? (
          <div className="p-8 text-center text-red-500 dark:text-red-400">
            Failed to load audit logs. Please try again.
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            No audit logs found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50">
                <tr>
                  <th className="w-8 px-4 py-3"></th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">Time</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">User</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">Action</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">Resource Type</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">Resource ID</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {filteredLogs.map((log) => (
                  <LogRow
                    key={log.id}
                    log={log}
                    isExpanded={expandedRow === log.id}
                    onToggle={() => toggleRow(log.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between bg-white dark:bg-gray-800 px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function LogRow({ log, isExpanded, onToggle }) {
  const hasDetails = log.old_value || log.new_value

  return (
    <>
      <tr
        className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${hasDetails ? 'cursor-pointer' : ''}`}
        onClick={hasDetails ? onToggle : undefined}
      >
        <td className="px-4 py-3">
          {hasDetails && (
            isExpanded ? (
              <ChevronDownIcon className="h-4 w-4 text-gray-400" />
            ) : (
              <ChevronRightIcon className="h-4 w-4 text-gray-400" />
            )
          )}
        </td>
        <td className="px-4 py-3 text-gray-900 dark:text-white whitespace-nowrap">
          {formatDate(log.created_at)}
        </td>
        <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
          {log.user_id || '—'}
        </td>
        <td className="px-4 py-3">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300">
            {log.action}
          </span>
        </td>
        <td className="px-4 py-3 text-gray-700 dark:text-gray-300 capitalize">
          {log.resource_type || '—'}
        </td>
        <td className="px-4 py-3 text-gray-700 dark:text-gray-300 font-mono text-xs">
          {log.resource_id || '—'}
        </td>
        <td className="px-4 py-3 text-gray-500 dark:text-gray-400 font-mono text-xs">
          {log.ip_address || '—'}
        </td>
      </tr>
      {isExpanded && hasDetails && (
        <tr className="bg-gray-50 dark:bg-gray-700/30">
          <td colSpan={7} className="px-8 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">Old Value</h4>
                <pre className="text-xs bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300 p-3 rounded-lg overflow-x-auto max-h-48 whitespace-pre-wrap">
                  {log.old_value ? (typeof log.old_value === 'string' ? log.old_value : JSON.stringify(log.old_value, null, 2)) : 'N/A'}
                </pre>
              </div>
              <div>
                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">New Value</h4>
                <pre className="text-xs bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300 p-3 rounded-lg overflow-x-auto max-h-48 whitespace-pre-wrap">
                  {log.new_value ? (typeof log.new_value === 'string' ? log.new_value : JSON.stringify(log.new_value, null, 2)) : 'N/A'}
                </pre>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
