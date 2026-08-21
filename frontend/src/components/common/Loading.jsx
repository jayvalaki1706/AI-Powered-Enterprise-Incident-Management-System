import { SkeletonCard, SkeletonTable, SkeletonText } from './Skeleton'

export { SkeletonCard, SkeletonTable, SkeletonText }

export default function Loading({ fullScreen = false, variant = 'spinner' }) {
  let content

  switch (variant) {
    case 'cards':
      content = (
        <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )
      break

    case 'table':
      content = (
        <div className="w-full">
          <SkeletonTable />
        </div>
      )
      break

    case 'spinner':
    default:
      content = (
        <div className="flex flex-col items-center justify-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading...</p>
        </div>
      )
      break
  }

  if (fullScreen) {
    return <div className="flex items-center justify-center min-h-screen">{content}</div>
  }
  return <div className="flex items-center justify-center py-12">{content}</div>
}
