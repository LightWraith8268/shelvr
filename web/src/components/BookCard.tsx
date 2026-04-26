import type { Book } from '../api/types'
import { coverUrl } from '../api/books'
import { useAuthedBlob } from '../api/media'

interface Props {
  book: Book
  onClick?: (book: Book) => void
  progressPercent?: number | null
  selectable?: boolean
  selected?: boolean
  onToggleSelected?: (book: Book) => void
}

export function BookCard({
  book,
  onClick,
  progressPercent,
  selectable,
  selected,
  onToggleSelected,
}: Props) {
  const authors = book.authors.map((author) => author.name).join(', ')
  const remoteCover = book.cover_path ? coverUrl(book.id, 'medium') : null
  const objectUrl = useAuthedBlob(remoteCover)
  const showCover = !!book.cover_path && !!objectUrl
  const clampedPercent =
    typeof progressPercent === 'number'
      ? Math.max(0, Math.min(1, progressPercent))
      : null

  function handleClick() {
    if (selectable) {
      onToggleSelected?.(book)
    } else {
      onClick?.(book)
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-pressed={selectable ? !!selected : undefined}
      className={`group flex flex-col text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 rounded-md ${
        selectable && selected ? 'ring-2 ring-emerald-500' : ''
      }`}
    >
      <div className="relative aspect-[2/3] w-full overflow-hidden rounded-md border border-slate-200 bg-slate-100 shadow-sm group-hover:shadow-md transition-shadow">
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
        {selectable && (
          <div
            className={`absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full border-2 border-white shadow ${
              selected ? 'bg-emerald-500 text-white' : 'bg-white/80 text-transparent'
            }`}
          >
            ✓
          </div>
        )}
        {clampedPercent !== null && clampedPercent > 0 && (
          <div className="absolute inset-x-0 bottom-0 h-1 bg-black/30">
            <div
              className="h-full bg-emerald-500"
              style={{ width: `${Math.round(clampedPercent * 100)}%` }}
              aria-label={`Reading progress: ${Math.round(clampedPercent * 100)}%`}
            />
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
