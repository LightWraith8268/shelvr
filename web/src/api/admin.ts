import { apiFetch, apiJson } from './client'
import type { Book } from './types'

export interface BookUpdate {
  title?: string
  sort_title?: string | null
  series?: string | null
  series_index?: number | null
  description?: string | null
  language?: string | null
  publisher?: string | null
  published_date?: string | null
  isbn?: string | null
  rating?: number | null
  authors?: string[]
  tags?: string[]
}

export async function updateBook(bookId: number, update: BookUpdate): Promise<Book> {
  return apiJson<Book>(`/api/v1/books/${bookId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  })
}

export async function deleteBook(bookId: number): Promise<void> {
  const response = await apiFetch(`/api/v1/books/${bookId}`, { method: 'DELETE' })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
}

export interface BulkDeleteResult {
  deleted: number[]
  not_found: number[]
}

export async function bulkDeleteBooks(ids: number[]): Promise<BulkDeleteResult> {
  return apiJson<BulkDeleteResult>('/api/v1/books/bulk-delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  })
}

export interface BulkTagResult {
  updated: number[]
  not_found: number[]
}

export async function bulkTagBooks(
  ids: number[],
  add: string[],
  remove: string[],
): Promise<BulkTagResult> {
  return apiJson<BulkTagResult>('/api/v1/books/bulk-tag', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, add, remove }),
  })
}

export async function replaceBookCover(bookId: number, file: File): Promise<Book> {
  const form = new FormData()
  form.append('file', file, file.name)
  const response = await apiFetch(`/api/v1/books/${bookId}/cover`, {
    method: 'PUT',
    body: form,
  })
  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // body wasn't JSON
    }
    throw new Error(detail)
  }
  return (await response.json()) as Book
}
