import { useState } from 'react'
import type { Book } from '../api/types'
import { coverUrl } from '../api/books'

interface Props {
  book: Book
  onClick?: (book: Book) => void
}

export function BookCard({ book, onClick }: Props) {
  const [coverFailed, setCoverFailed] = useState(false)
  const authors = book.authors.map((author) => author.name).join(', ')
  const hasCover = !!book.cover_path && !coverFailed

  return (
    <button
      type="button"
      onClick={() => onClick?.(book)}
      className="group flex flex-col text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 rounded-md"
    >
      <div className="aspect-[2/3] w-full overflow-hidden rounded-md border border-slate-200 bg-slate-100 shadow-sm group-hover:shadow-md transition-shadow">
        {hasCover ? (
          <img
            src={coverUrl(book.id, 'medium')}
            alt=""
            loading="lazy"
            onError={() => setCoverFailed(true)}
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
