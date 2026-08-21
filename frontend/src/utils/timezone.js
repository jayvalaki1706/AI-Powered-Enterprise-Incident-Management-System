/**
 * Timezone utility for formatting dates in user's timezone
 */

/**
 * Get the user's timezone from localStorage or default to UTC
 */
export function getUserTimezone() {
  try {
    const userData = localStorage.getItem('user_timezone')
    return userData || 'Asia/Kolkata'
  } catch {
    return 'Asia/Kolkata'
  }
}

/**
 * Set the user's timezone in localStorage
 */
export function setUserTimezone(timezone) {
  localStorage.setItem('user_timezone', timezone)
}

/**
 * Format a date string in the user's timezone
 * @param {string|Date} date - The date to format
 * @param {object} options - Intl.DateTimeFormat options override
 * @returns {string} Formatted date string
 */
export function formatDate(date, options = {}) {
  if (!date) return 'N/A'
  const tz = getUserTimezone()

  const defaultOptions = {
    timeZone: tz,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  }

  try {
    return new Date(date).toLocaleString('en-US', defaultOptions)
  } catch {
    return new Date(date).toLocaleString()
  }
}

/**
 * Format date only (no time)
 */
export function formatDateOnly(date) {
  if (!date) return 'N/A'
  const tz = getUserTimezone()

  try {
    return new Date(date).toLocaleDateString('en-US', {
      timeZone: tz,
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return new Date(date).toLocaleDateString()
  }
}

/**
 * Format time only
 */
export function formatTime(date) {
  if (!date) return 'N/A'
  const tz = getUserTimezone()

  try {
    return new Date(date).toLocaleTimeString('en-US', {
      timeZone: tz,
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return new Date(date).toLocaleTimeString()
  }
}

/**
 * Format date with full detail (used for incident detail pages)
 */
export function formatDateFull(date) {
  if (!date) return 'N/A'
  const tz = getUserTimezone()

  try {
    return new Date(date).toLocaleString('en-US', {
      timeZone: tz,
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return new Date(date).toLocaleString()
  }
}
