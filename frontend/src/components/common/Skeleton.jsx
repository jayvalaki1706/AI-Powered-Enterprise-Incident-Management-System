/**
 * SkeletonText - Single line text placeholder
 */
export function SkeletonText({ width = 'w-full', height = 'h-4' }) {
  return <div className={`animate-pulse rounded bg-gray-200 dark:bg-gray-700 ${width} ${height}`} />
}

/**
 * SkeletonCard - Animated pulse placeholder for stat cards (dashboard)
 */
export function SkeletonCard() {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="animate-pulse space-y-4">
        {/* Icon placeholder */}
        <div className="flex items-center justify-between">
          <div className="h-10 w-10 rounded-lg bg-gray-200 dark:bg-gray-700" />
          <div className="h-4 w-16 rounded bg-gray-200 dark:bg-gray-700" />
        </div>
        {/* Value placeholder */}
        <div className="h-8 w-20 rounded bg-gray-200 dark:bg-gray-700" />
        {/* Label placeholder */}
        <div className="h-4 w-32 rounded bg-gray-200 dark:bg-gray-700" />
      </div>
    </div>
  )
}

/**
 * SkeletonTable - Animated pulse placeholder for tables
 */
export function SkeletonTable({ rows = 5, columns = 4 }) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Table header */}
      <div className="border-b border-gray-200 bg-gray-50 px-6 py-3 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex gap-4">
          {Array.from({ length: columns }).map((_, i) => (
            <div
              key={`header-${i}`}
              className="h-4 flex-1 animate-pulse rounded bg-gray-200 dark:bg-gray-700"
            />
          ))}
        </div>
      </div>
      {/* Table rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={`row-${rowIndex}`}
          className="border-b border-gray-100 px-6 py-4 last:border-b-0 dark:border-gray-700"
        >
          <div className="flex gap-4">
            {Array.from({ length: columns }).map((_, colIndex) => (
              <div
                key={`cell-${rowIndex}-${colIndex}`}
                className="h-4 flex-1 animate-pulse rounded bg-gray-200 dark:bg-gray-700"
                style={{ width: `${60 + Math.random() * 40}%` }}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
