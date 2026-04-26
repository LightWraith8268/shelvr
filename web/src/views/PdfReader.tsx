import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { formatFileUrl } from '../api/books'
import { apiFetch } from '../api/client'
import type { Format } from '../api/types'

interface Props {
  bookId: number
  format: Format
}

export function PdfReader({ bookId, format }: Props) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    let createdUrl: string | null = null

    apiFetch(formatFileUrl(format.id))
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return await response.blob()
      })
      .then((blob) => {
        if (cancelled) return
        createdUrl = URL.createObjectURL(blob)
        setObjectUrl(createdUrl)
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : 'Failed to load PDF.')
        }
      })

    return () => {
      cancelled = true
      if (createdUrl) URL.revokeObjectURL(createdUrl)
    }
  }, [format.id])

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="mb-3 flex items-center justify-between">
        <Link to={`/books/${bookId}`} className="text-sm text-slate-500 hover:text-slate-900">
          ← Back to book
        </Link>
      </div>
      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}
      {!error && !objectUrl && <p className="text-slate-500">Loading PDF…</p>}
      {objectUrl && (
        <iframe
          title="PDF reader"
          src={objectUrl}
          className="flex-1 rounded-md border border-slate-200 bg-white shadow-sm"
        />
      )}
    </div>
  )
}
