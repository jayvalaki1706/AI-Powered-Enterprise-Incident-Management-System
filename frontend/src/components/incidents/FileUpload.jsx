import { useState, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import { formatDate } from '../../utils/timezone'
import toast from 'react-hot-toast'

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10 MB

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${units[i]}`
}

export default function FileUpload({ incidentId }) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)

  const { data: attachmentsData, isLoading } = useQuery({
    queryKey: ['incident-attachments', incidentId],
    queryFn: () => api.get(`/files/incident/${incidentId}`).then((r) => r.data),
  })

  const attachments = attachmentsData?.items || []

  const uploadMutation = useMutation({
    mutationFn: (file) => {
      const formData = new FormData()
      formData.append('file', file)
      return api.post(`/files/upload/${incidentId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident-attachments', incidentId] })
      toast.success('File uploaded successfully')
    },
    onError: (err) => {
      const message = err.response?.data?.detail || err.response?.data?.message || 'Failed to upload file'
      toast.error(message)
    },
  })

  const handleFile = useCallback((file) => {
    if (!file) return
    if (file.size > MAX_FILE_SIZE) {
      toast.error('File size exceeds 10MB limit')
      return
    }
    uploadMutation.mutate(file)
  }, [uploadMutation])

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    handleFile(file)
    // Reset input so the same file can be re-selected
    e.target.value = ''
  }

  const handleDownload = async (attachmentId, fileName) => {
    try {
      const res = await api.get(`/files/download/${attachmentId}`)
      const link = document.createElement('a')
      link.href = res.data.download_url
      link.download = fileName
      link.target = '_blank'
      link.rel = 'noopener noreferrer'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch {
      toast.error('Failed to get download link')
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
      <h2 className="font-semibold text-gray-900 dark:text-white mb-4">
        Attachments ({attachments.length})
      </h2>

      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 hover:bg-gray-50 dark:hover:bg-gray-700/50'
        }`}
        role="button"
        tabIndex={0}
        aria-label="Upload file"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            fileInputRef.current?.click()
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileSelect}
          className="hidden"
          aria-hidden="true"
        />
        {uploadMutation.isPending ? (
          <div className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="text-sm text-gray-600 dark:text-gray-400">Uploading...</span>
          </div>
        ) : (
          <>
            <svg className="mx-auto h-10 w-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 16v-8m0 0l-3 3m3-3l3 3M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
            </svg>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              <span className="font-medium text-blue-600 dark:text-blue-400">Click to upload</span> or drag and drop
            </p>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">Max 10MB per file</p>
          </>
        )}
      </div>

      {/* Attachment List */}
      {isLoading ? (
        <p className="text-sm text-gray-500 mt-4">Loading attachments...</p>
      ) : attachments.length > 0 ? (
        <ul className="mt-4 divide-y divide-gray-200 dark:divide-gray-700">
          {attachments.map((attachment) => (
            <li key={attachment.id} className="py-3 flex items-center justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {attachment.file_name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {formatFileSize(attachment.file_size)} · {formatDate(attachment.created_at)}
                </p>
              </div>
              <button
                onClick={() => handleDownload(attachment.id, attachment.file_name)}
                className="shrink-0 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
                aria-label={`Download ${attachment.file_name}`}
              >
                Download
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-gray-500 mt-4">No attachments yet</p>
      )}
    </div>
  )
}
