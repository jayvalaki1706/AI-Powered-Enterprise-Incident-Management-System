import { useState, useEffect } from 'react'

/**
 * Real-time SLA Timer component
 * Shows countdown in D:H:M format with color-coded status
 */
export default function SLATimer({ deadline, status }) {
  const [timeLeft, setTimeLeft] = useState(calculateTimeLeft(deadline))

  useEffect(() => {
    // Don't tick if resolved/closed
    if (status === 'resolved' || status === 'closed') return

    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft(deadline))
    }, 1000) // Update every second for real-time feel

    return () => clearInterval(timer)
  }, [deadline, status])

  if (!deadline) return <span className="text-sm text-gray-400">No SLA</span>

  // If resolved/closed, show final status
  if (status === 'resolved' || status === 'closed') {
    return (
      <div className="flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
        <span className="text-sm font-medium text-green-600 dark:text-green-400">Resolved — SLA Met</span>
      </div>
    )
  }

  const { breached, days, hours, minutes, percentage } = timeLeft

  // Color based on urgency
  const getStatusConfig = () => {
    if (breached) {
      return {
        color: 'text-red-600 dark:text-red-400',
        bg: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
        dot: 'bg-red-500 animate-pulse',
        label: 'SLA BREACHED',
      }
    }
    if (percentage <= 10) {
      return {
        color: 'text-red-600 dark:text-red-400',
        bg: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
        dot: 'bg-red-500 animate-pulse',
        label: 'Critical',
      }
    }
    if (percentage <= 25) {
      return {
        color: 'text-orange-600 dark:text-orange-400',
        bg: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
        dot: 'bg-orange-500',
        label: 'Warning',
      }
    }
    if (percentage <= 50) {
      return {
        color: 'text-yellow-600 dark:text-yellow-400',
        bg: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
        dot: 'bg-yellow-500',
        label: 'On Track',
      }
    }
    return {
      color: 'text-green-600 dark:text-green-400',
      bg: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
      dot: 'bg-green-500',
      label: 'Healthy',
    }
  }

  const config = getStatusConfig()
  const timeString = formatTime(breached, days, hours, minutes)

  return (
    <div className={`rounded-lg border px-3 py-2 ${config.bg}`}>
      <div className="flex items-center gap-2">
        <span className={`inline-block w-2 h-2 rounded-full ${config.dot}`} />
        <span className={`text-xs font-medium ${config.color}`}>{config.label}</span>
      </div>
      <p className={`text-lg font-mono font-bold mt-1 ${config.color}`}>
        {timeString}
      </p>
      {!breached && (
        <div className="mt-1.5">
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
            <div
              className={`h-1.5 rounded-full transition-all duration-1000 ${
                percentage <= 10 ? 'bg-red-500' :
                percentage <= 25 ? 'bg-orange-500' :
                percentage <= 50 ? 'bg-yellow-500' : 'bg-green-500'
              }`}
              style={{ width: `${Math.max(percentage, 2)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Compact version for use in tables/lists
 */
export function SLATimerCompact({ deadline, status }) {
  const [timeLeft, setTimeLeft] = useState(calculateTimeLeft(deadline))

  useEffect(() => {
    if (status === 'resolved' || status === 'closed') return
    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft(deadline))
    }, 60000) // Update every minute for list view
    return () => clearInterval(timer)
  }, [deadline, status])

  if (!deadline) return <span className="text-xs text-gray-400">—</span>

  if (status === 'resolved' || status === 'closed') {
    return <span className="text-xs text-green-600 dark:text-green-400 font-medium">✓ Done</span>
  }

  const { breached, days, hours, minutes, percentage } = timeLeft
  const timeString = formatTime(breached, days, hours, minutes)

  const colorClass = breached
    ? 'text-red-600 dark:text-red-400'
    : percentage <= 10
    ? 'text-red-600 dark:text-red-400'
    : percentage <= 25
    ? 'text-orange-600 dark:text-orange-400'
    : percentage <= 50
    ? 'text-yellow-600 dark:text-yellow-400'
    : 'text-green-600 dark:text-green-400'

  return (
    <span className={`text-xs font-mono font-medium ${colorClass}`}>
      {timeString}
    </span>
  )
}

// ─── Helpers ────────────────────────────────────────────────────────────────────

function calculateTimeLeft(deadline) {
  if (!deadline) return { breached: false, days: 0, hours: 0, minutes: 0, percentage: 100 }

  const now = new Date()
  const deadlineDate = new Date(deadline)
  const diff = deadlineDate - now // milliseconds

  if (diff <= 0) {
    // Breached — show how much time over
    const overMs = Math.abs(diff)
    const days = Math.floor(overMs / (1000 * 60 * 60 * 24))
    const hours = Math.floor((overMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const minutes = Math.floor((overMs % (1000 * 60 * 60)) / (1000 * 60))
    return { breached: true, days, hours, minutes, percentage: 0 }
  }

  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

  // Estimate percentage remaining (assume max SLA is 72h for low priority)
  // We use the ratio of remaining time to total SLA window
  const totalSlaMs = 72 * 60 * 60 * 1000 // fallback to 72h
  const percentage = Math.min(Math.max((diff / totalSlaMs) * 100, 0), 100)

  return { breached: false, days, hours, minutes, percentage }
}

function formatTime(breached, days, hours, minutes) {
  const parts = []
  if (days > 0) parts.push(`${days}D`)
  parts.push(`${hours}H`)
  parts.push(`${String(minutes).padStart(2, '0')}M`)

  const timeStr = parts.join(':')
  return breached ? `−${timeStr} overdue` : timeStr
}
