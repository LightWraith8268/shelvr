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
