import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { coverUrl } from '../api/books'
import { useAuthedBlob } from '../api/media'
import { listMyRecentBooks } from '../api/progress'
import type { RecentBook } from '../api/progress'

export function ContinueReading() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['me', 'recent-books'],
    queryFn: listMyRecentBooks,
  })

  if (isLoading) return null
  if (!data || data.length === 0) return null

  return (
    <section className="mb-6">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
        Continue reading
      </h2>
      <ul className="flex gap-3 overflow-x-auto pb-2">
        {data.map((book) => (
          <li key={book.id} className="w-32 shrink-0">
            <ContinueReadingCard book={book} onOpen={() => navigate(`/books/${book.id}/read`)} />
          </li>
        ))}
      </ul>
    </section>
  )
}

function ContinueReadingCard({ book, onOpen }: { book: RecentBook; onOpen: () => void }) {
  const remoteCover = book.cover_path ? coverUrl(book.id, 'small') : null
  const objectUrl = useAuthedBlob(remoteCover)
  const showCover = !!book.cover_path && !!objectUrl
  const percent = Math.max(0, Math.min(1, book.percent))
  const authors = book.authors.map((author) => author.name).join(', ')

  return (
    <button
      type="button"
      onClick={onOpen}
      className="group flex w-full flex-col text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 rounded-md"
    >
      <div className="relative aspect-[2/3] w-full overflow-hidden rounded-md border border-slate-200 bg-slate-100 shadow-sm group-hover:shadow-md transition-shadow">
        {showCover ? (
          <img src={objectUrl ?? ''} alt="" loading="lazy" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center p-2 text-center text-[10px] text-slate-500">
            {book.title}
          </div>
        )}
        {percent > 0 && (
          <div className="absolute inset-x-0 bottom-0 h-1 bg-black/30">
            <div
              className="h-full bg-emerald-500"
              style={{ width: `${Math.round(percent * 100)}%` }}
            />
          </div>
        )}
      </div>
      <div className="mt-1.5 line-clamp-2 text-xs font-medium text-slate-900">{book.title}</div>
      {authors && <div className="mt-0.5 line-clamp-1 text-[10px] text-slate-500">{authors}</div>}
    </button>
  )
}
