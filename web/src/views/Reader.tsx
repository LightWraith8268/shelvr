import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import ePub from 'epubjs'
import type { Book as EpubBook, Rendition } from 'epubjs'
import { formatFileUrl, getBook } from '../api/books'
import { apiFetch } from '../api/client'

export function ReaderView() {
  const { bookId } = useParams<{ bookId: string }>()
  const numericId = Number(bookId)
  const containerRef = useRef<HTMLDivElement>(null)
  const renditionRef = useRef<Rendition | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const { data: book } = useQuery({
    queryKey: ['book', numericId],
    queryFn: () => getBook(numericId),
    enabled: Number.isFinite(numericId) && numericId > 0,
  })

  const epubFormat = book?.formats.find((format) => format.format.toLowerCase() === 'epub')

  useEffect(() => {
    if (!epubFormat || !containerRef.current) return
    let cancelled = false
    let bookInstance: EpubBook | null = null

    setIsLoading(true)
    setError(null)

    apiFetch(formatFileUrl(epubFormat.id))
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return await response.arrayBuffer()
      })
      .then((buffer) => {
        if (cancelled || !containerRef.current) return
        bookInstance = ePub(buffer)
        const rendition = bookInstance.renderTo(containerRef.current, {
          width: '100%',
          height: '100%',
          flow: 'paginated',
          spread: 'auto',
        })
        renditionRef.current = rendition
        return rendition.display().then(() => {
          if (!cancelled) setIsLoading(false)
        })
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : 'Failed to load book.')
          setIsLoading(false)
        }
      })

    return () => {
      cancelled = true
      if (renditionRef.current) {
        renditionRef.current.destroy()
        renditionRef.current = null
      }
      if (bookInstance) {
        bookInstance.destroy()
      }
    }
  }, [epubFormat])

  // Keyboard navigation: ←/→ for prev/next page.
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (!renditionRef.current) return
      if (event.key === 'ArrowLeft') {
        renditionRef.current.prev()
      } else if (event.key === 'ArrowRight') {
        renditionRef.current.next()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [])

  if (!Number.isFinite(numericId) || numericId <= 0) {
    return <p className="text-red-600">Invalid book id.</p>
  }
  if (book && !epubFormat) {
    return (
      <div className="max-w-2xl">
        <Link to={`/books/${numericId}`} className="text-sm text-slate-500 hover:text-slate-900">
          ← Back to book
        </Link>
        <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          In-browser reader supports EPUB only for now. This book has no EPUB format —
          download a copy and read it in your preferred app.
        </p>
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="mb-3 flex items-center justify-between">
        <Link to={`/books/${numericId}`} className="text-sm text-slate-500 hover:text-slate-900">
          ← Back to book
        </Link>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => renditionRef.current?.prev()}
            className="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs hover:bg-slate-50"
          >
            ← Previous
          </button>
          <button
            type="button"
            onClick={() => renditionRef.current?.next()}
            className="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs hover:bg-slate-50"
          >
            Next →
          </button>
        </div>
      </div>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}
      {isLoading && !error && <p className="text-slate-500">Loading book…</p>}

      <div
        ref={containerRef}
        className={`flex-1 overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm ${
          isLoading ? 'opacity-0' : ''
        }`}
      />
    </div>
  )
}
