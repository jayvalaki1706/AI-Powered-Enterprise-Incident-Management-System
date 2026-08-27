import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import Loading from '../../components/common/Loading'

export default function DashboardPage() {
  const navigate = useNavigate()
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Real-time overview of your ticket management system</p>
        </div>
        <div className="text-xs text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 px-3 py-1.5 rounded-full">
          Auto-refreshing
        </div>
      </div>

      {/* Key Metrics — 4 primary KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Open Tickets"
          value={stats.open_incidents}
          trend={stats.open_incidents > 5 ? 'up' : 'stable'}
          color="amber"
          onClick={() => navigate('/tickets?status=open')}
          icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <MetricCard
          label="In Progress"
          value={stats.in_progress_incidents}
          trend="stable"
          color="emerald"
          onClick={() => navigate('/tickets?status=in_progress')}
          icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>}
        />
        <MetricCard
          label="Critical Tickets"
          value={stats.critical_incidents}
          trend={stats.critical_incidents > 0 ? 'up' : 'stable'}
          color="rose"
          onClick={() => navigate('/tickets?priority=critical')}
          icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
        />
        <MetricCard
          label="Closed"
          value={stats.closed_incidents}
          trend="stable"
          color="orange"
          onClick={() => navigate('/tickets?status=closed')}
          icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 sm:grid-cols-3 gap-3">
        <MiniStat label="Total Tickets" value={stats.total_incidents} onClick={() => navigate('/tickets')} />
        <MiniStat label="Escalated" value={stats.escalated_incidents} onClick={() => navigate('/tickets?status=escalated')} />
        <MiniStat label="Avg Resolution" value={stats.avg_resolution_hours ? `${stats.avg_resolution_hours}h` : '—'} />
      </div>

      {/* Charts Row: Recent Activity + Priority */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity - takes 2 columns */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white">Recent Tickets</h2>
            <button onClick={() => navigate('/tickets')} className="text-xs text-blue-600 dark:text-blue-400 hover:underline">View all →</button>
          </div>
          <RecentTickets />
        </div>

        {/* Priority Breakdown - donut-style */}
        {data?.priority_breakdown && (
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-5">Priority Distribution</h2>
            <div className="space-y-4">
              <PriorityBar label="Critical" value={data.priority_breakdown.critical} total={stats.total_incidents} color="bg-red-500" />
              <PriorityBar label="High" value={data.priority_breakdown.high} total={stats.total_incidents} color="bg-orange-500" />
              <PriorityBar label="Medium" value={data.priority_breakdown.medium} total={stats.total_incidents} color="bg-amber-400" />
              <PriorityBar label="Low" value={data.priority_breakdown.low} total={stats.total_incidents} color="bg-green-500" />
            </div>
          </div>
        )}
      </div>

      {/* Teams & Engineers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Teams */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4">Top Teams</h2>
          {data?.top_teams?.length > 0 ? (
            <div className="space-y-3">
              {data.top_teams.map((team, idx) => (
                <div key={team.team_name} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors">
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white ${idx === 0 ? 'bg-amber-500' : idx === 1 ? 'bg-gray-400' : 'bg-orange-700'}`}>
                    {idx + 1}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{team.team_name}</p>
                    <p className="text-xs text-gray-500">{team.total_incidents} tickets · {team.resolved} resolved</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-emerald-600">{team.total_incidents > 0 ? Math.round((team.resolved / team.total_incidents) * 100) : 0}%</p>
                    <p className="text-xs text-gray-400">resolution</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-sm text-gray-400">No team data yet</p>
              <p className="text-xs text-gray-400 mt-1">Assign engineers to departments</p>
            </div>
          )}
        </div>

        {/* Top Engineers */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4">Top Engineers</h2>
          {data?.top_engineers?.length > 0 ? (
            <div className="space-y-3">
              {data.top_engineers.map((eng, idx) => (
                <div key={eng.engineer_id} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors">
                  <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 text-xs font-bold">
                    {eng.engineer_name?.[0]?.toUpperCase()}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{eng.engineer_name}</p>
                    <p className="text-xs text-gray-500">{eng.total_assigned} assigned · {eng.avg_resolution_hours ? `${eng.avg_resolution_hours}h avg` : 'N/A'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-emerald-600">{eng.total_resolved}</p>
                    <p className="text-xs text-gray-400">resolved</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-sm text-gray-400">No engineer data yet</p>
              <p className="text-xs text-gray-400 mt-1">Assign tickets to engineers</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Components ──────────────────────────────────────────────────────────────────

function MetricCard({ label, value, color, icon, trend, onClick }) {
  const colors = {
    amber: { bg: 'bg-amber-50 dark:bg-amber-900/10', border: 'border-amber-200 dark:border-amber-800', icon: 'text-amber-600 dark:text-amber-400', value: 'text-amber-700 dark:text-amber-300' },
    emerald: { bg: 'bg-emerald-50 dark:bg-emerald-900/10', border: 'border-emerald-200 dark:border-emerald-800', icon: 'text-emerald-600 dark:text-emerald-400', value: 'text-emerald-700 dark:text-emerald-300' },
    rose: { bg: 'bg-rose-50 dark:bg-rose-900/10', border: 'border-rose-200 dark:border-rose-800', icon: 'text-rose-600 dark:text-rose-400', value: 'text-rose-700 dark:text-rose-300' },
    orange: { bg: 'bg-orange-50 dark:bg-orange-900/10', border: 'border-orange-200 dark:border-orange-800', icon: 'text-orange-600 dark:text-orange-400', value: 'text-orange-700 dark:text-orange-300' },
  }

  const c = colors[color]

  return (
    <div onClick={onClick} className={`${c.bg} border ${c.border} rounded-2xl p-5 transition-all hover:shadow-md cursor-pointer`}>
      <div className="flex items-center justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl ${c.bg} border ${c.border} flex items-center justify-center ${c.icon}`}>
          {icon}
        </div>
        {/* {trend === 'up' && value > 0 && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 font-medium">
            Active
          </span>
        )} */}
      </div>
      <p className={`text-3xl font-bold ${c.value}`}>{value ?? 0}</p>
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{label}</p>
    </div>
  )
}

function MiniStat({ label, value, onClick }) {
  return (
    <div onClick={onClick} className={`bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl px-4 py-3 text-center ${onClick ? 'cursor-pointer hover:shadow-md transition-all' : ''}`}>
      <p className="text-lg font-bold text-gray-900 dark:text-white">{value ?? 0}</p>
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
    </div>
  )
}

function PriorityBar({ label, value, total, color }) {
  const percentage = total > 0 ? Math.round((value / total) * 100) : 0
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
        <span className="text-sm font-bold text-gray-900 dark:text-white">{value} <span className="text-xs text-gray-400 font-normal">({percentage}%)</span></span>
      </div>
      <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
        <div className={`${color} h-full rounded-full transition-all duration-700`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  )
}

function RecentTickets() {
  const { data } = useQuery({
    queryKey: ['recent-tickets'],
    queryFn: () => api.get('/incidents/', { params: { page: 1, page_size: 5 } }).then((r) => r.data.items),
    staleTime: 0,
  })

  const statusColors = {
    open: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    pending: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    hold: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
    closed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    escalated: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  }

  const priorityDots = {
    critical: 'bg-red-500',
    high: 'bg-orange-500',
    medium: 'bg-amber-400',
    low: 'bg-green-500',
  }

  if (!data || data.length === 0) {
    return <p className="text-sm text-gray-400 text-center py-8">No tickets yet</p>
  }

  return (
    <div className="space-y-3">
      {data.map((ticket) => (
        <a key={ticket.id} href={`/tickets/${ticket.id}`} className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors group">
          <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${priorityDots[ticket.priority] || 'bg-gray-400'}`} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 dark:text-white truncate group-hover:text-blue-600 dark:group-hover:text-blue-400">{ticket.title}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{new Date(ticket.created_at).toLocaleDateString()}</p>
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${statusColors[ticket.status] || 'bg-gray-100 text-gray-600'}`}>
            {ticket.status?.replace('_', ' ')}
          </span>
        </a>
      ))}
    </div>
  )
}
