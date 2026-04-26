import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { coverUrl, getBook } from '../api/books'
import { replaceBookCover, updateBook } from '../api/admin'
import { useAuthedBlob } from '../api/media'
import type { BookUpdate } from '../api/admin'

interface FormState {
  title: string
  authors: string
  tags: string
  series: string
  series_index: string
  language: string
  publisher: string
  published_date: string
  isbn: string
  rating: string
  description: string
}

const EMPTY_FORM: FormState = {
  title: '',
  authors: '',
  tags: '',
  series: '',
  series_index: '',
  language: '',
  publisher: '',
  published_date: '',
  isbn: '',
  rating: '',
  description: '',
}

function buildPayload(form: FormState): BookUpdate {
  const payload: BookUpdate = {}
  if (form.title.trim()) payload.title = form.title.trim()
  payload.authors = form.authors
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean)
  payload.tags = form.tags
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean)
  payload.series = form.series.trim() || null
  payload.series_index = form.series_index ? Number(form.series_index) : null
  payload.language = form.language.trim() || null
  payload.publisher = form.publisher.trim() || null
  payload.published_date = form.published_date || null
  payload.isbn = form.isbn.trim() || null
  payload.rating = form.rating ? Number(form.rating) : null
  payload.description = form.description.trim() || null
  return payload
}

export function BookEdit() {
  const { bookId } = useParams<{ bookId: string }>()
  const numericId = Number(bookId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: book, isLoading, error } = useQuery({
    queryKey: ['book', numericId],
    queryFn: () => getBook(numericId),
    enabled: Number.isFinite(numericId) && numericId > 0,
  })

  const [form, setForm] = useState<FormState>(EMPTY_FORM)

  useEffect(() => {
    if (!book) return
    setForm({
      title: book.title,
      authors: book.authors.map((author) => author.name).join(', '),
      tags: book.tags.map((tag) => tag.name).join(', '),
      series: book.series ?? '',
      series_index: book.series_index !== null ? String(book.series_index) : '',
      language: book.language ?? '',
      publisher: book.publisher ?? '',
      published_date: book.published_date ?? '',
      isbn: book.isbn ?? '',
      rating: book.rating !== null ? String(book.rating) : '',
      description: book.description ?? '',
    })
  }, [book])

  const mutation = useMutation({
    mutationFn: (payload: BookUpdate) => updateBook(numericId, payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(['book', numericId], updated)
      queryClient.invalidateQueries({ queryKey: ['books'] })
      navigate(`/books/${numericId}`)
    },
  })

  const coverFileRef = useRef<HTMLInputElement>(null)
  const [coverError, setCoverError] = useState<string | null>(null)
  const [coverCacheBuster, setCoverCacheBuster] = useState(0)

  const coverPreviewUrl = useAuthedBlob(
    book?.cover_path ? `${coverUrl(book.id, 'medium')}&_=${coverCacheBuster}` : null,
  )

  const coverMutation = useMutation({
    mutationFn: (file: File) => replaceBookCover(numericId, file),
    onSuccess: (updated) => {
      queryClient.setQueryData(['book', numericId], updated)
      queryClient.invalidateQueries({ queryKey: ['books'] })
      // Bust the blob cache so the new cover renders without a hard reload.
      setCoverCacheBuster((current) => current + 1)
      setCoverError(null)
    },
    onError: (err) => {
      setCoverError(err instanceof Error ? err.message : 'Cover replace failed.')
    },
  })

  function handleCoverPick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file) coverMutation.mutate(file)
    if (coverFileRef.current) coverFileRef.current.value = ''
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate(buildPayload(form))
  }

  if (!Number.isFinite(numericId) || numericId <= 0) {
    return <p className="text-red-600">Invalid book id.</p>
  }
  if (isLoading) return <p className="text-slate-500">Loading…</p>
  if (error || !book) {
    return (
      <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
        Error: {error instanceof Error ? error.message : 'unknown'}
      </p>
    )
  }

  return (
    <article className="max-w-2xl">
      <Link to={`/books/${numericId}`} className="text-sm text-slate-500 hover:text-slate-900">
        ← Back to book
      </Link>
      <h2 className="mt-2 text-xl font-semibold tracking-tight">Edit metadata</h2>

      <section className="mt-4 flex items-start gap-4 rounded-md border border-slate-200 bg-white p-3">
        <div className="aspect-[2/3] w-24 shrink-0 overflow-hidden rounded-md border border-slate-200 bg-slate-100">
          {coverPreviewUrl ? (
            <img src={coverPreviewUrl} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center p-2 text-center text-[10px] text-slate-500">
              No cover
            </div>
          )}
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-900">Cover image</p>
          <p className="text-xs text-slate-500">
            JPEG, PNG, WebP, GIF, or AVIF. The server regenerates small + medium thumbnails.
          </p>
          <input
            ref={coverFileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif,image/avif"
            onChange={handleCoverPick}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => coverFileRef.current?.click()}
            disabled={coverMutation.isPending}
            className="mt-2 rounded-md border border-slate-300 bg-white px-3 py-1 text-xs hover:bg-slate-50 disabled:opacity-50"
          >
            {coverMutation.isPending ? 'Uploading…' : 'Replace cover'}
          </button>
          {coverError && (
            <p className="mt-2 rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700">
              {coverError}
            </p>
          )}
        </div>
      </section>

      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <Field label="Title" required>
          <input
            type="text"
            required
            value={form.title}
            onChange={(event) => setForm({ ...form, title: event.target.value })}
            className={inputClass}
          />
        </Field>
        <Field label="Authors (comma-separated)">
          <input
            type="text"
            value={form.authors}
            onChange={(event) => setForm({ ...form, authors: event.target.value })}
            className={inputClass}
          />
        </Field>
        <Field label="Tags (comma-separated)">
          <input
            type="text"
            value={form.tags}
            onChange={(event) => setForm({ ...form, tags: event.target.value })}
            className={inputClass}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Series">
            <input
              type="text"
              value={form.series}
              onChange={(event) => setForm({ ...form, series: event.target.value })}
              className={inputClass}
            />
          </Field>
          <Field label="Series index">
            <input
              type="number"
              step="0.1"
              value={form.series_index}
              onChange={(event) => setForm({ ...form, series_index: event.target.value })}
              className={inputClass}
            />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Language">
            <input
              type="text"
              value={form.language}
              onChange={(event) => setForm({ ...form, language: event.target.value })}
              className={inputClass}
            />
          </Field>
          <Field label="Publisher">
            <input
              type="text"
              value={form.publisher}
              onChange={(event) => setForm({ ...form, publisher: event.target.value })}
              className={inputClass}
            />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Published date">
            <input
              type="date"
              value={form.published_date}
              onChange={(event) => setForm({ ...form, published_date: event.target.value })}
              className={inputClass}
            />
          </Field>
          <Field label="ISBN">
            <input
              type="text"
              value={form.isbn}
              onChange={(event) => setForm({ ...form, isbn: event.target.value })}
              className={inputClass}
            />
          </Field>
        </div>
        <Field label="Rating (0–10)">
          <input
            type="number"
            min={0}
            max={10}
            value={form.rating}
            onChange={(event) => setForm({ ...form, rating: event.target.value })}
            className={inputClass}
          />
        </Field>
        <Field label="Description">
          <textarea
            rows={5}
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
            className={inputClass}
          />
        </Field>

        {mutation.isError && (
          <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {mutation.error instanceof Error ? mutation.error.message : 'Save failed'}
          </p>
        )}

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:opacity-50"
          >
            {mutation.isPending ? 'Saving…' : 'Save'}
          </button>
          <Link
            to={`/books/${numericId}`}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
          >
            Cancel
          </Link>
        </div>
      </form>
    </article>
  )
}

const inputClass =
  'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500'

function Field({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-slate-500">
        {label}
        {required && <span className="ml-0.5 text-red-500">*</span>}
      </span>
      <span className="mt-1 block">{children}</span>
    </label>
  )
}
