import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'
import Loading from '../../components/common/Loading'
import Badge from '../../components/common/Badge'

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/analytics/dashboard').then((r) => r.data),
    staleTime: 0,
    refetchOnWindowFocus: true,
  })

  if (isLoading) return <Loading />

  const stats = data?.stats || {}

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>

      {/* Key Metrics — 4 cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Open Incidents" value={stats.open_incidents} color="yellow" icon="🔓" />
        <StatCard label="Resolved Today" value={stats.resolved_today} color="green" icon="✅" />
        <StatCard label="Critical Incidents" value={stats.critical_incidents} color="red" icon="🔥" />
        <StatCard label="SLA Breached" value={stats.sla_breached} color="orange" icon="⚠️" />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Incidents" value={stats.total_incidents} color="blue" icon="📋" />
        <StatCard label="In Progress" value={stats.in_progress_incidents} color="purple" icon="🔄" />
        <StatCard label="Escalated" value={stats.escalated_incidents} color="orange" icon="⬆️" />
        <StatCard label="Avg Resolution Time" value={stats.avg_resolution_hours ? `${stats.avg_resolution_hours}h` : 'N/A'} color="blue" icon="⏱️" />
      </div>

      {/* Incident Trend */}
      {data?.monthly_trends?.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">📈 Incident Trend</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                <tr>
                  <th className="text-left py-2">Month</th>
                  <th className="text-center py-2">Created</th>
                  <th className="text-center py-2">Resolved</th>
                  <th className="text-left py-2">Trend</th>
                </tr>
              </thead>
              <tbody className="text-gray-700 dark:text-gray-300">
                {data.monthly_trends.map((t) => (
                  <tr key={t.month} className="border-b dark:border-gray-700">
                    <td className="py-2 font-medium">{t.month}</td>
                    <td className="text-center py-2">{t.total_created}</td>
                    <td className="text-center py-2">{t.total_resolved}</td>
                    <td className="py-2">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2 max-w-32">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${Math.min((t.total_created / Math.max(stats.total_incidents, 1)) * 100, 100)}%` }}
                          />
                        </div>
                        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2 max-w-32">
                          <div
                            className="bg-green-500 h-2 rounded-full"
                            style={{ width: `${Math.min((t.total_resolved / Math.max(t.total_created, 1)) * 100, 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex gap-4 mt-3 text-xs text-gray-500">
              <span className="flex items-center gap-1"><span className="inline-block w-3 h-2 bg-blue-500 rounded" /> Created</span>
              <span className="flex items-center gap-1"><span className="inline-block w-3 h-2 bg-green-500 rounded" /> Resolved</span>
            </div>
          </div>
        </div>
      )}

      {/* Top Teams & Top Engineers side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Teams */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">👥 Top Teams</h2>
          {data?.top_teams?.length > 0 ? (
            <div className="space-y-3">
              {data.top_teams.map((team, idx) => (
                <div key={team.team_name} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-bold text-gray-400 w-5">{idx + 1}</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">{team.team_name}</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
                    <span>{team.total_incidents} assigned</span>
                    <span className="text-green-600 font-medium">{team.resolved} resolved</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No team data yet. Assign engineers to teams to see performance.</p>
          )}
        </div>

        {/* Top Engineers */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">🏆 Top Engineers</h2>
          {data?.top_engineers?.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                  <tr>
                    <th className="text-left py-2">Engineer</th>
                    <th className="text-center py-2">Assigned</th>
                    <th className="text-center py-2">Resolved</th>
                    <th className="text-center py-2">Avg Hours</th>
                  </tr>
                </thead>
                <tbody className="text-gray-700 dark:text-gray-300">
                  {data.top_engineers.map((eng) => (
                    <tr key={eng.engineer_id} className="border-b dark:border-gray-700">
                      <td className="py-2 font-medium">{eng.engineer_name}</td>
                      <td className="text-center py-2">{eng.total_assigned}</td>
                      <td className="text-center py-2 text-green-600 font-medium">{eng.total_resolved}</td>
                      <td className="text-center py-2">{eng.avg_resolution_hours || 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-500">No engineer data yet. Assign incidents to engineers.</p>
          )}
        </div>
      </div>

      {/* Priority Breakdown */}
      {data?.priority_breakdown && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">📊 Priority Breakdown</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <PriorityCard label="Low" value={data.priority_breakdown.low} color="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" />
            <PriorityCard label="Medium" value={data.priority_breakdown.medium} color="bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400" />
            <PriorityCard label="High" value={data.priority_breakdown.high} color="bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400" />
            <PriorityCard label="Critical" value={data.priority_breakdown.critical} color="bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400" />
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, color, icon }) {
  const colors = {
    blue: 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
    green: 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800',
    yellow: 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800',
    red: 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800',
    purple: 'bg-purple-50 border-purple-200 dark:bg-purple-900/20 dark:border-purple-800',
    orange: 'bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800',
    gray: 'bg-gray-50 border-gray-200 dark:bg-gray-900/20 dark:border-gray-700',
  }

  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`}>
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600 dark:text-gray-400">{label}</p>
        <span className="text-lg">{icon}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value ?? 0}</p>
    </div>
  )
}

function PriorityCard({ label, value, color }) {
  return (
    <div className={`rounded-lg p-4 text-center ${color}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm font-medium mt-1">{label}</p>
    </div>
  )
}
