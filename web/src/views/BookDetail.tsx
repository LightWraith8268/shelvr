import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { coverUrl, formatFileUrl, getBook } from '../api/books'
import { downloadAuthedFile, useAuthedBlob } from '../api/media'
import type { Format } from '../api/types'

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function suggestedFilename(format: Format, title: string): string {
  const safeTitle = title.replace(/[^A-Za-z0-9_\-. ]+/g, '_').slice(0, 80)
  return `${safeTitle}.${format.format}`
}

export function BookDetail() {
  const { bookId } = useParams<{ bookId: string }>()
  const numericId = Number(bookId)

  const { data: book, isLoading, error } = useQuery({
    queryKey: ['book', numericId],
    queryFn: () => getBook(numericId),
    enabled: Number.isFinite(numericId) && numericId > 0,
  })

  const remoteCover = book?.cover_path ? coverUrl(book.id, 'original') : null
  const coverObjectUrl = useAuthedBlob(remoteCover)

  if (!Number.isFinite(numericId) || numericId <= 0) {
    return <p className="text-red-600">Invalid book id.</p>
  }
  if (isLoading) return <p className="text-slate-500">Loading…</p>
  if (error) {
    return (
      <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
        Error: {error instanceof Error ? error.message : 'unknown'}
      </p>
    )
  }
  if (!book) return null

  const authors = book.authors.map((author) => author.name).join(', ')
  const showCover = !!book.cover_path && !!coverObjectUrl
  const publishedYear = book.published_date?.slice(0, 4)

  async function handleDownload(format: Format) {
    if (!book) return
    await downloadAuthedFile(formatFileUrl(format.id), suggestedFilename(format, book.title))
  }

  return (
    <article>
      <Link to="/" className="text-sm text-slate-500 hover:text-slate-900">
        ← Back to library
      </Link>

      <div className="mt-4 grid gap-8 md:grid-cols-[220px_1fr]">
        <div>
          <div className="aspect-[2/3] w-full overflow-hidden rounded-md border border-slate-200 bg-slate-100 shadow-sm">
            {showCover ? (
              <img src={coverObjectUrl ?? ''} alt="" className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full w-full items-center justify-center p-4 text-center text-sm text-slate-500">
                {book.title}
              </div>
            )}
          </div>
        </div>

        <div>
          <h2 className="text-2xl font-semibold tracking-tight">{book.title}</h2>
          {authors && <p className="mt-1 text-slate-600">{authors}</p>}

          <dl className="mt-6 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
            {book.series && (
              <>
                <dt className="text-slate-500">Series</dt>
                <dd>
                  {book.series}
                  {book.series_index !== null && ` #${book.series_index}`}
                </dd>
              </>
            )}
            {book.publisher && (
              <>
                <dt className="text-slate-500">Publisher</dt>
                <dd>{book.publisher}</dd>
              </>
            )}
            {publishedYear && (
              <>
                <dt className="text-slate-500">Published</dt>
                <dd>{publishedYear}</dd>
              </>
            )}
            {book.language && (
              <>
                <dt className="text-slate-500">Language</dt>
                <dd>{book.language}</dd>
              </>
            )}
            {book.isbn && (
              <>
                <dt className="text-slate-500">ISBN</dt>
                <dd className="font-mono">{book.isbn}</dd>
              </>
            )}
          </dl>

          {book.tags.length > 0 && (
            <ul className="mt-4 flex flex-wrap gap-1.5">
              {book.tags.map((tag) => (
                <li
                  key={tag.id}
                  className="rounded-full border border-slate-300 bg-white px-2.5 py-0.5 text-xs text-slate-700"
                >
                  {tag.name}
                </li>
              ))}
            </ul>
          )}

          {book.description && (
            <section className="mt-6">
              <h3 className="text-sm font-medium text-slate-500">Description</h3>
              <p className="mt-1 whitespace-pre-line text-sm text-slate-800">{book.description}</p>
            </section>
          )}

          <section className="mt-6">
            <h3 className="text-sm font-medium text-slate-500">Files</h3>
            <ul className="mt-2 divide-y divide-slate-200 rounded-md border border-slate-200 bg-white">
              {book.formats.map((format) => (
                <li key={format.id} className="flex items-center justify-between px-3 py-2 text-sm">
                  <div>
                    <span className="font-mono uppercase">{format.format}</span>
                    <span className="ml-2 text-slate-500">{formatBytes(format.file_size)}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDownload(format)}
                    className="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs hover:bg-slate-50"
                  >
                    Download
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </article>
  )
}
