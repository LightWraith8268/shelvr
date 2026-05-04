import { apiFetch, apiJson } from './client'

export interface Bookmark {
  id: number
  book_id: number
  locator: string
  label: string | null
  created_at: string
}

export async function listBookmarks(bookId: number): Promise<Bookmark[]> {
  return apiJson<Bookmark[]>(`/api/v1/books/${bookId}/bookmarks`)
}

export async function createBookmark(
  bookId: number,
  locator: string,
  label: string | null,
): Promise<Bookmark> {
  return apiJson<Bookmark>(`/api/v1/books/${bookId}/bookmarks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ locator, label }),
  })
}

export async function deleteBookmark(bookId: number, bookmarkId: number): Promise<void> {
  const response = await apiFetch(
    `/api/v1/books/${bookId}/bookmarks/${bookmarkId}`,
    { method: 'DELETE' },
  )
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
}
