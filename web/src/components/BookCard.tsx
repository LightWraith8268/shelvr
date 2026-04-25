import type { Book } from '../api/types'
import { coverUrl } from '../api/books'
import { useAuthedBlob } from '../api/media'

interface Props {
  book: Book
  onClick?: (book: Book) => void
}

export function BookCard({ book, onClick }: Props) {
  const authors = book.authors.map((author) => author.name).join(', ')
  const remoteCover = book.cover_path ? coverUrl(book.id, 'medium') : null
  const objectUrl = useAuthedBlob(remoteCover)
  const showCover = !!book.cover_path && !!objectUrl

  return (
    <button
      type="button"
      onClick={() => onClick?.(book)}
      className="group flex flex-col text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 rounded-md"
    >
      <div className="aspect-[2/3] w-full overflow-hidden rounded-md border border-slate-200 bg-slate-100 shadow-sm group-hover:shadow-md transition-shadow">
        {showCover ? (
          <img
            src={objectUrl ?? ''}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center p-3 text-center text-xs text-slate-500">
            {book.title}
          </div>
        )}
      </div>
      <div className="mt-2 px-0.5">
        <div className="line-clamp-2 text-sm font-medium text-slate-900">{book.title}</div>
        {authors && (
          <div className="mt-0.5 line-clamp-1 text-xs text-slate-500">{authors}</div>
        )}
      </div>
    </button>
  )
}
