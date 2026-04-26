import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import ePub from 'epubjs'
import type { Book as EpubBook, Rendition } from 'epubjs'
import { formatFileUrl, getBook } from '../api/books'
import { apiFetch } from '../api/client'
import { getReadingProgress, putReadingProgress } from '../api/progress'
import { PdfReader } from './PdfReader'

type Theme = 'light' | 'sepia' | 'dark'

const THEME_STORAGE_KEY = 'shelvr.reader.theme'
const FONT_SIZE_STORAGE_KEY = 'shelvr.reader.fontSize'
const MIN_FONT = 80
const MAX_FONT = 180
const FONT_STEP = 10

const THEME_STYLES: Record<Theme, Record<string, Record<string, string>>> = {
  light: {
    body: { color: '#0f172a', background: '#ffffff' },
    a: { color: '#0f766e' },
  },
  sepia: {
    body: { color: '#3a2f17', background: '#f4ecd8' },
    a: { color: '#7c5b1e' },
  },
  dark: {
    body: { color: '#e2e8f0', background: '#0f172a' },
    a: { color: '#5eead4' },
  },
}

const CONTAINER_BG: Record<Theme, string> = {
  light: 'bg-white',
  sepia: 'bg-[#f4ecd8]',
  dark: 'bg-slate-900',
}

function loadStoredTheme(): Theme {
  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  if (stored === 'light' || stored === 'sepia' || stored === 'dark') return stored
  return 'light'
}

function loadStoredFontSize(): number {
  const stored = Number(localStorage.getItem(FONT_SIZE_STORAGE_KEY))
  if (Number.isFinite(stored) && stored >= MIN_FONT && stored <= MAX_FONT) return stored
  return 100
}

interface TocEntry {
  label: string
  href: string
  depth: number
}

function flattenToc(
  items: ReadonlyArray<{ label?: string; href?: string; subitems?: unknown }>,
  depth = 0,
  out: TocEntry[] = [],
): TocEntry[] {
  for (const item of items) {
    if (item?.href && item?.label) {
      out.push({ label: item.label.trim(), href: item.href, depth })
    }
    const subitems = (item as { subitems?: unknown }).subitems
    if (Array.isArray(subitems)) {
      flattenToc(subitems as ReadonlyArray<{ label?: string; href?: string }>, depth + 1, out)
    }
  }
  return out
}

export function ReaderView() {
  const { bookId } = useParams<{ bookId: string }>()
  const numericId = Number(bookId)
  const containerRef = useRef<HTMLDivElement>(null)
  const renditionRef = useRef<Rendition | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [theme, setTheme] = useState<Theme>(() => loadStoredTheme())
  const [fontSize, setFontSize] = useState<number>(() => loadStoredFontSize())
  const [toc, setToc] = useState<TocEntry[]>([])
  const [isTocOpen, setIsTocOpen] = useState(false)

  const { data: book } = useQuery({
    queryKey: ['book', numericId],
    queryFn: () => getBook(numericId),
    enabled: Number.isFinite(numericId) && numericId > 0,
  })

  const epubFormat = book?.formats.find((format) => format.format.toLowerCase() === 'epub')
  const pdfFormat = book?.formats.find((format) => format.format.toLowerCase() === 'pdf')

  useEffect(() => {
    if (!epubFormat || !containerRef.current || !Number.isFinite(numericId)) return
    let cancelled = false
    let bookInstance: EpubBook | null = null
    let saveTimer: number | null = null
    let lastSavedLocator: string | null = null

    setIsLoading(true)
    setError(null)

    Promise.all([
      apiFetch(formatFileUrl(epubFormat.id)).then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return await response.arrayBuffer()
      }),
      getReadingProgress(numericId).catch(() => null),
    ])
      .then(([buffer, progress]) => {
        if (cancelled || !containerRef.current) return
        bookInstance = ePub(buffer)
        const rendition = bookInstance.renderTo(containerRef.current, {
          width: '100%',
          height: '100%',
          flow: 'paginated',
          spread: 'auto',
        })
        renditionRef.current = rendition

        // Register all themes up front so toggling later is one select call.
        for (const [name, rules] of Object.entries(THEME_STYLES)) {
          rendition.themes.register(name, rules)
        }
        rendition.themes.select(theme)
        rendition.themes.fontSize(`${fontSize}%`)

        const handleRelocated = (location: { start?: { cfi?: string; percentage?: number } }) => {
          const cfi = location?.start?.cfi
          const percent = location?.start?.percentage
          if (typeof cfi !== 'string' || typeof percent !== 'number') return
          if (cfi === lastSavedLocator) return
          if (saveTimer !== null) window.clearTimeout(saveTimer)
          saveTimer = window.setTimeout(() => {
            lastSavedLocator = cfi
            putReadingProgress(numericId, cfi, Math.max(0, Math.min(1, percent))).catch(() => {
              // Saving is best-effort; surface nothing if the network is flaky.
            })
          }, 750)
        }
        rendition.on('relocated', handleRelocated)

        // Populate TOC once the book is parsed.
        bookInstance.loaded.navigation
          .then((navigation: { toc?: unknown }) => {
            if (cancelled) return
            const items = Array.isArray(navigation?.toc) ? navigation.toc : []
            setToc(flattenToc(items as ReadonlyArray<{ label?: string; href?: string }>))
          })
          .catch(() => {
            // Books without navigation are fine — TOC stays empty.
          })

        const target = progress?.locator || undefined
        return rendition.display(target).then(() => {
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
      if (saveTimer !== null) window.clearTimeout(saveTimer)
      if (renditionRef.current) {
        renditionRef.current.destroy()
        renditionRef.current = null
      }
      if (bookInstance) {
        bookInstance.destroy()
      }
      setToc([])
    }
    // theme + fontSize intentionally omitted: change handlers below apply
    // them to the live rendition so we don't need a full reinit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [epubFormat, numericId])

  // Apply theme changes to the existing rendition.
  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, theme)
    if (renditionRef.current) {
      renditionRef.current.themes.select(theme)
    }
  }, [theme])

  // Apply font-size changes to the existing rendition.
  useEffect(() => {
    localStorage.setItem(FONT_SIZE_STORAGE_KEY, String(fontSize))
    if (renditionRef.current) {
      renditionRef.current.themes.fontSize(`${fontSize}%`)
    }
  }, [fontSize])

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
  // Prefer EPUB (paginated reader with progress sync, themes, font scaling);
  // fall back to native PDF viewer when only a PDF is available.
  if (book && !epubFormat && pdfFormat) {
    return <PdfReader bookId={numericId} format={pdfFormat} />
  }
  if (book && !epubFormat && !pdfFormat) {
    return (
      <div className="max-w-2xl">
        <Link to={`/books/${numericId}`} className="text-sm text-slate-500 hover:text-slate-900">
          ← Back to book
        </Link>
        <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          In-browser reader supports EPUB and PDF. This book has neither — download a copy
          and read it in your preferred app.
        </p>
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <Link to={`/books/${numericId}`} className="text-sm text-slate-500 hover:text-slate-900">
          ← Back to book
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          {toc.length > 0 && (
            <button
              type="button"
              onClick={() => setIsTocOpen((current) => !current)}
              aria-expanded={isTocOpen}
              className="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs hover:bg-slate-50"
            >
              {isTocOpen ? 'Hide contents' : 'Contents'}
            </button>
          )}
          <label className="flex items-center gap-1 text-xs text-slate-600">
            Theme
            <select
              value={theme}
              onChange={(event) => setTheme(event.target.value as Theme)}
              className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
            >
              <option value="light">Light</option>
              <option value="sepia">Sepia</option>
              <option value="dark">Dark</option>
            </select>
          </label>
          <div className="flex items-center gap-1 text-xs text-slate-600">
            <span>Aa</span>
            <button
              type="button"
              onClick={() => setFontSize((current) => Math.max(MIN_FONT, current - FONT_STEP))}
              disabled={fontSize <= MIN_FONT}
              className="rounded-md border border-slate-300 bg-white px-2 py-1 disabled:opacity-50"
              aria-label="Decrease font size"
            >
              −
            </button>
            <span className="w-10 text-center font-mono text-[10px]">{fontSize}%</span>
            <button
              type="button"
              onClick={() => setFontSize((current) => Math.min(MAX_FONT, current + FONT_STEP))}
              disabled={fontSize >= MAX_FONT}
              className="rounded-md border border-slate-300 bg-white px-2 py-1 disabled:opacity-50"
              aria-label="Increase font size"
            >
              +
            </button>
          </div>
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

      <div className="flex flex-1 gap-3 overflow-hidden">
        {isTocOpen && toc.length > 0 && (
          <aside className="w-64 shrink-0 overflow-y-auto rounded-md border border-slate-200 bg-white p-3 text-sm shadow-sm">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Contents
            </h3>
            <ul className="space-y-0.5">
              {toc.map((entry, index) => (
                <li key={`${entry.href}-${index}`}>
                  <button
                    type="button"
                    onClick={() => {
                      renditionRef.current?.display(entry.href)
                    }}
                    className="block w-full truncate rounded px-2 py-1 text-left text-slate-700 hover:bg-slate-100"
                    style={{ paddingLeft: `${0.5 + entry.depth * 0.75}rem` }}
                    title={entry.label}
                  >
                    {entry.label || '—'}
                  </button>
                </li>
              ))}
            </ul>
          </aside>
        )}
        <div
          ref={containerRef}
          className={`flex-1 overflow-hidden rounded-md border border-slate-200 shadow-sm transition-colors ${
            CONTAINER_BG[theme]
          } ${isLoading ? 'opacity-0' : ''}`}
        />
      </div>
    </div>
  )
}
