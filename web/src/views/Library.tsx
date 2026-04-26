import { useMemo, useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { listBooks } from '../api/books'
import {
  listAuthorFacets,
  listLanguageFacets,
  listSeriesFacets,
  listTagFacets,
} from '../api/facets'
import { listMyProgress } from '../api/progress'
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
  const [tagFilter, setTagFilter] = useState<string>('')
  const [authorFilter, setAuthorFilter] = useState<number | ''>('')
  const [languageFilter, setLanguageFilter] = useState<string>('')
  const [seriesFilter, setSeriesFilter] = useState<number | ''>('')

  const offset = page * PAGE_SIZE
  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: [
      'books',
      {
        offset,
        limit: PAGE_SIZE,
        sort,
        q: query,
        tag: tagFilter,
        authorId: authorFilter,
        language: languageFilter,
        seriesId: seriesFilter,
      },
    ],
    queryFn: () =>
      listBooks({
        limit: PAGE_SIZE,
        offset,
        sort,
        q: query || undefined,
        tag: tagFilter || undefined,
        authorId: authorFilter === '' ? undefined : Number(authorFilter),
        language: languageFilter || undefined,
        seriesId: seriesFilter === '' ? undefined : Number(seriesFilter),
      }),
    placeholderData: keepPreviousData,
  })

  const tagFacets = useQuery({ queryKey: ['facets', 'tags'], queryFn: listTagFacets })
  const authorFacets = useQuery({ queryKey: ['facets', 'authors'], queryFn: listAuthorFacets })
  const languageFacets = useQuery({
    queryKey: ['facets', 'languages'],
    queryFn: listLanguageFacets,
  })
  const seriesFacets = useQuery({
    queryKey: ['facets', 'series'],
    queryFn: listSeriesFacets,
  })
  const myProgress = useQuery({
    queryKey: ['me', 'progress'],
    queryFn: listMyProgress,
  })

  const progressByBookId = useMemo(() => {
    const map = new Map<number, number>()
    for (const entry of myProgress.data ?? []) {
      map.set(entry.book_id, entry.percent)
    }
    return map
  }, [myProgress.data])

  const total = data?.total ?? 0
  const items = data?.items ?? []
  const lastPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1)
  const hasActiveFilter = !!(query || tagFilter || authorFilter || languageFilter || seriesFilter)

  function handleSearchSubmit(event: React.FormEvent) {
    event.preventDefault()
    setQuery(searchInput.trim())
    setPage(0)
  }

  function handleSortChange(event: React.ChangeEvent<HTMLSelectElement>) {
    setSort(event.target.value as BookSort)
    setPage(0)
  }

  function handleTagChange(event: React.ChangeEvent<HTMLSelectElement>) {
    setTagFilter(event.target.value)
    setPage(0)
  }

  function handleAuthorChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const raw = event.target.value
    setAuthorFilter(raw === '' ? '' : Number(raw))
    setPage(0)
  }

  function handleLanguageChange(event: React.ChangeEvent<HTMLSelectElement>) {
    setLanguageFilter(event.target.value)
    setPage(0)
  }

  function handleSeriesChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const raw = event.target.value
    setSeriesFilter(raw === '' ? '' : Number(raw))
    setPage(0)
  }

  function clearFilters() {
    setSearchInput('')
    setQuery('')
    setTagFilter('')
    setAuthorFilter('')
    setLanguageFilter('')
    setSeriesFilter('')
    setPage(0)
  }

  return (
    <div>
      <div className="mb-6 grid grid-cols-1 gap-3 md:grid-cols-[1fr_auto_auto_auto_auto]">
        <form onSubmit={handleSearchSubmit}>
          <label className="block text-xs font-medium text-slate-500" htmlFor="library-search">
            Search title or author
          </label>
          <input
            id="library-search"
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="The Hobbit"
            className={inputClass}
          />
        </form>
        <FacetSelect
          id="library-tag"
          label="Tag"
          value={tagFilter}
          onChange={handleTagChange}
          options={(tagFacets.data ?? []).map((tag) => ({
            value: tag.name,
            label: `${tag.name} (${tag.count})`,
          }))}
        />
        <FacetSelect
          id="library-author"
          label="Author"
          value={authorFilter === '' ? '' : String(authorFilter)}
          onChange={handleAuthorChange}
          options={(authorFacets.data ?? []).map((author) => ({
            value: String(author.id),
            label: `${author.name} (${author.count})`,
          }))}
        />
        <FacetSelect
          id="library-language"
          label="Language"
          value={languageFilter}
          onChange={handleLanguageChange}
          options={(languageFacets.data ?? []).map((language) => ({
            value: language.code,
            label: `${language.code} (${language.count})`,
          }))}
        />
        <FacetSelect
          id="library-series"
          label="Series"
          value={seriesFilter === '' ? '' : String(seriesFilter)}
          onChange={handleSeriesChange}
          options={(seriesFacets.data ?? []).map((series) => ({
            value: String(series.id),
            label: `${series.name} (${series.count})`,
          }))}
        />
        <div>
          <label className="block text-xs font-medium text-slate-500" htmlFor="library-sort">
            Sort
          </label>
          <select id="library-sort" value={sort} onChange={handleSortChange} className={inputClass}>
            <option value="added">Recently added</option>
            <option value="title">Title</option>
            <option value="series">Series</option>
          </select>
        </div>
      </div>

      {hasActiveFilter && (
        <div className="mb-4 flex items-center gap-2 text-xs text-slate-500">
          <span>{total} match{total === 1 ? '' : 'es'}</span>
          <button
            type="button"
            onClick={clearFilters}
            className="rounded-md border border-slate-300 bg-white px-2 py-0.5 hover:bg-slate-50"
          >
            Clear filters
          </button>
        </div>
      )}

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Error loading library: {error instanceof Error ? error.message : 'unknown'}
        </p>
      )}

      {isLoading ? (
        <p className="text-slate-500">Loading…</p>
      ) : items.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500">
          {hasActiveFilter ? 'No books match your filters.' : 'No books yet. Upload one to begin.'}
        </div>
      ) : (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {items.map((book) => (
            <li key={book.id}>
              <BookCard
                book={book}
                onClick={onBookSelect}
                progressPercent={progressByBookId.get(book.id) ?? null}
              />
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

const inputClass =
  'mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500'

interface FacetOption {
  value: string
  label: string
}

function FacetSelect({
  id,
  label,
  value,
  onChange,
  options,
}: {
  id: string
  label: string
  value: string
  onChange: (event: React.ChangeEvent<HTMLSelectElement>) => void
  options: FacetOption[]
}) {
  return (
    <div className="min-w-[140px]">
      <label className="block text-xs font-medium text-slate-500" htmlFor={id}>
        {label}
      </label>
      <select id={id} value={value} onChange={onChange} className={inputClass}>
        <option value="">All</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}
