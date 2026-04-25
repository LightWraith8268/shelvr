import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { listBooks } from '../api/books'
import type { Book, BookSort } from '../api/types'
import { BookCard } from '../components/BookCard'

const PAGE_SIZE = 50

interface Props {
  onBookSelect?: (book: Book) => void
}

export function Library({ onBookSelect }: Props) {
  const [page, setPage] = useState(0)
  const [sort, setSort] = useState<BookSort>('added')
  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState('')

  const offset = page * PAGE_SIZE
  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ['books', { offset, limit: PAGE_SIZE, sort, q: query }],
    queryFn: () => listBooks({ limit: PAGE_SIZE, offset, sort, q: query || undefined }),
    placeholderData: keepPreviousData,
  })

  const total = data?.total ?? 0
  const items = data?.items ?? []
  const lastPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1)

  function handleSearchSubmit(event: React.FormEvent) {
    event.preventDefault()
    setQuery(searchInput.trim())
    setPage(0)
  }

  function handleSortChange(event: React.ChangeEvent<HTMLSelectElement>) {
    setSort(event.target.value as BookSort)
    setPage(0)
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end gap-3">
        <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[240px]">
          <label className="block text-xs font-medium text-slate-500" htmlFor="library-search">
            Search title or author
          </label>
          <input
            id="library-search"
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="The Hobbit"
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          />
        </form>
        <div>
          <label className="block text-xs font-medium text-slate-500" htmlFor="library-sort">
            Sort
          </label>
          <select
            id="library-sort"
            value={sort}
            onChange={handleSortChange}
            className="mt-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          >
            <option value="added">Recently added</option>
            <option value="title">Title</option>
          </select>
        </div>
      </div>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Error loading library: {error instanceof Error ? error.message : 'unknown'}
        </p>
      )}

      {isLoading ? (
        <p className="text-slate-500">Loading…</p>
      ) : items.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500">
          {query ? 'No books match your search.' : 'No books yet. Upload one via POST /api/v1/books.'}
        </div>
      ) : (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {items.map((book) => (
            <li key={book.id}>
              <BookCard book={book} onClick={onBookSelect} />
            </li>
          ))}
        </ul>
      )}

      {total > PAGE_SIZE && (
        <div className="mt-6 flex items-center justify-between text-sm text-slate-600">
          <div>
            Showing {offset + 1}–{Math.min(offset + items.length, total)} of {total}
            {isFetching && !isLoading && <span className="ml-2 text-slate-400">refreshing…</span>}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((current) => Math.max(0, current - 1))}
              disabled={page === 0}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => setPage((current) => Math.min(lastPage, current + 1))}
              disabled={page >= lastPage}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
