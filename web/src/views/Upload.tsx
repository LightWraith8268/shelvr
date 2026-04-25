import { useCallback, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { uploadBook } from '../api/uploads'
import type { Book } from '../api/types'

type ItemStatus = 'pending' | 'uploading' | 'ok' | 'duplicate' | 'error'

interface QueuedItem {
  id: string
  file: File
  status: ItemStatus
  message?: string
  book?: Book
}

const ACCEPTED_EXTENSIONS = ['epub', 'pdf', 'mobi', 'azw3'] as const

function isAcceptedFile(file: File): boolean {
  const lower = file.name.toLowerCase()
  return ACCEPTED_EXTENSIONS.some((extension) => lower.endsWith(`.${extension}`))
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

export function UploadView() {
  const queryClient = useQueryClient()
  const [items, setItems] = useState<QueuedItem[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const enqueue = useCallback((files: FileList | File[]) => {
    const next: QueuedItem[] = []
    for (const file of Array.from(files)) {
      next.push({
        id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2, 8)}`,
        file,
        status: isAcceptedFile(file) ? 'pending' : 'error',
        message: isAcceptedFile(file)
          ? undefined
          : `Unsupported extension. Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}`,
      })
    }
    setItems((current) => [...current, ...next])
  }, [])

  function handleFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files) enqueue(event.target.files)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragOver(false)
    if (event.dataTransfer?.files) enqueue(event.dataTransfer.files)
  }

  function updateItem(id: string, patch: Partial<QueuedItem>) {
    setItems((current) =>
      current.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    )
  }

  async function startUploads() {
    if (isUploading) return
    setIsUploading(true)
    try {
      // Upload sequentially. The server's per-request work (parsing,
      // hashing, file writes) is heavy enough that parallelism would mainly
      // create contention, not throughput.
      for (const item of items) {
        if (item.status !== 'pending') continue
        updateItem(item.id, { status: 'uploading', message: undefined })
        try {
          const result = await uploadBook(item.file)
          updateItem(item.id, {
            status: result.status === 201 ? 'ok' : 'duplicate',
            book: result.book,
          })
        } catch (caught) {
          updateItem(item.id, {
            status: 'error',
            message: caught instanceof Error ? caught.message : 'Upload failed',
          })
        }
      }
      queryClient.invalidateQueries({ queryKey: ['books'] })
    } finally {
      setIsUploading(false)
    }
  }

  function clearFinished() {
    setItems((current) => current.filter((item) => item.status === 'pending'))
  }

  const pendingCount = items.filter((item) => item.status === 'pending').length

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold tracking-tight">Upload books</h2>
        <Link to="/" className="text-sm text-slate-500 hover:text-slate-900">
          ← Back to library
        </Link>
      </div>

      <div
        onDragOver={(event) => {
          event.preventDefault()
          setIsDragOver(true)
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        className={`rounded-md border-2 border-dashed p-10 text-center transition-colors ${
          isDragOver
            ? 'border-slate-500 bg-slate-100'
            : 'border-slate-300 bg-white'
        }`}
      >
        <p className="text-sm text-slate-600">
          Drop EPUB, PDF, MOBI, or AZW3 files here, or
        </p>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="mt-3 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
        >
          Choose files
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".epub,.pdf,.mobi,.azw3"
          onChange={handleFileInputChange}
          className="hidden"
        />
      </div>

      {items.length > 0 && (
        <div className="mt-6">
          <ul className="divide-y divide-slate-200 rounded-md border border-slate-200 bg-white">
            {items.map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium text-slate-900">{item.file.name}</div>
                  <div className="text-xs text-slate-500">{formatBytes(item.file.size)}</div>
                  {item.message && (
                    <div className="mt-0.5 text-xs text-red-600">{item.message}</div>
                  )}
                </div>
                <StatusBadge item={item} />
              </li>
            ))}
          </ul>

          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              onClick={startUploads}
              disabled={isUploading || pendingCount === 0}
              className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:opacity-50"
            >
              {isUploading ? 'Uploading…' : `Upload ${pendingCount} file${pendingCount === 1 ? '' : 's'}`}
            </button>
            <button
              type="button"
              onClick={clearFinished}
              disabled={isUploading}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
            >
              Clear finished
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

function StatusBadge({ item }: { item: QueuedItem }) {
  switch (item.status) {
    case 'pending':
      return <span className="text-xs text-slate-500">Pending</span>
    case 'uploading':
      return <span className="text-xs text-slate-700">Uploading…</span>
    case 'ok':
      return (
        <Link
          to={item.book ? `/books/${item.book.id}` : '/'}
          className="rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
        >
          Added
        </Link>
      )
    case 'duplicate':
      return (
        <Link
          to={item.book ? `/books/${item.book.id}` : '/'}
          className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800 hover:bg-amber-100"
        >
          Already in library
        </Link>
      )
    case 'error':
      return <span className="rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700">Error</span>
  }
}
