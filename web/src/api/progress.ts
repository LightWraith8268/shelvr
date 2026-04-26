import { apiFetch, apiJson } from './client'

export interface ReadingProgress {
  book_id: number
  locator: string
  percent: number
  updated_at: string
}

export async function getReadingProgress(bookId: number): Promise<ReadingProgress | null> {
  const response = await apiFetch(`/api/v1/books/${bookId}/progress`)
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  const body = (await response.json()) as ReadingProgress | null
  return body
}

export async function putReadingProgress(
  bookId: number,
  locator: string,
  percent: number,
): Promise<ReadingProgress> {
  return apiJson<ReadingProgress>(`/api/v1/books/${bookId}/progress`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ locator, percent }),
  })
}

export async function clearReadingProgress(bookId: number): Promise<void> {
  const response = await apiFetch(`/api/v1/books/${bookId}/progress`, { method: 'DELETE' })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
}

export async function listMyProgress(): Promise<ReadingProgress[]> {
  const body = await apiJson<{ items: ReadingProgress[] }>('/api/v1/auth/me/progress')
  return body.items
}

export interface RecentBook {
  id: number
  title: string
  authors: { id: number; name: string; sort_name: string | null }[]
  cover_path: string | null
  percent: number
}

export async function listMyRecentBooks(): Promise<RecentBook[]> {
  const body = await apiJson<{ items: RecentBook[] }>('/api/v1/auth/me/recent-books')
  return body.items
}
