import { apiFetch, apiJson } from './client'

export type HighlightColor = 'yellow' | 'green' | 'blue' | 'pink'

export interface Highlight {
  id: number
  book_id: number
  locator_range: string
  text: string
  color: HighlightColor
  note: string | null
  created_at: string
  updated_at: string
}

export async function listHighlights(bookId: number): Promise<Highlight[]> {
  return apiJson<Highlight[]>(`/api/v1/books/${bookId}/highlights`)
}

export async function createHighlight(
  bookId: number,
  locatorRange: string,
  text: string,
  color: HighlightColor,
  note: string | null,
): Promise<Highlight> {
  return apiJson<Highlight>(`/api/v1/books/${bookId}/highlights`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ locator_range: locatorRange, text, color, note }),
  })
}

export async function updateHighlight(
  bookId: number,
  highlightId: number,
  body: { color?: HighlightColor; note?: string | null; clear_note?: boolean },
): Promise<Highlight> {
  return apiJson<Highlight>(`/api/v1/books/${bookId}/highlights/${highlightId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deleteHighlight(bookId: number, highlightId: number): Promise<void> {
  const response = await apiFetch(
    `/api/v1/books/${bookId}/highlights/${highlightId}`,
    { method: 'DELETE' },
  )
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
}
