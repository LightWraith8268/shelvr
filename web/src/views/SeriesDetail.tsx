import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listBooks } from '../api/books'
import { listSeriesFacets } from '../api/facets'
import { BookCard } from '../components/BookCard'

export function SeriesDetail() {
  const { seriesId } = useParams<{ seriesId: string }>()
  const numericId = Number(seriesId)
  const navigate = useNavigate()

  const seriesQuery = useQuery({
    queryKey: ['facets', 'series'],
    queryFn: listSeriesFacets,
  })

  const booksQuery = useQuery({
    queryKey: ['books', { seriesId: numericId, sort: 'series' as const, limit: 200 }],
    queryFn: () => listBooks({ seriesId: numericId, sort: 'series', limit: 200 }),
    enabled: Number.isFinite(numericId) && numericId > 0,
  })

  if (!Number.isFinite(numericId) || numericId <= 0) {
    return <p className="text-red-600">Invalid series id.</p>
  }

  const series = seriesQuery.data?.find((entry) => entry.id === numericId)
  const items = booksQuery.data?.items ?? []

  return (
    <article>
      <Link to="/" className="text-sm text-slate-500 hover:text-slate-900">
        ← Back to library
      </Link>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight">
        {series?.name ?? 'Series'}
      </h2>
      {series && (
        <p className="mt-1 text-sm text-slate-500">
          {series.count} book{series.count === 1 ? '' : 's'}
        </p>
      )}

      {booksQuery.isLoading && <p className="mt-4 text-slate-500">Loading…</p>}
      {booksQuery.error && (
        <p className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Error: {booksQuery.error instanceof Error ? booksQuery.error.message : 'unknown'}
        </p>
      )}

      {!booksQuery.isLoading && items.length === 0 && (
        <p className="mt-4 rounded-md border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500">
          No books in this series yet.
        </p>
      )}

      {items.length > 0 && (
        <ul className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {items.map((book) => (
            <li key={book.id}>
              <BookCard book={book} onClick={() => navigate(`/books/${book.id}`)} />
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}
