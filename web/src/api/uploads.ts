import { apiFetch } from './client'
import type { Book } from './types'

export interface UploadResult {
  status: number
  book: Book
}

/**
 * Upload a single book file to ``POST /api/v1/books``.
 *
 * Returns the parsed book plus the HTTP status (201 = new, 200 = dedup hit on
 * an existing book). Throws on any non-2xx response with the server's detail
 * message when present.
 */
export async function uploadBook(file: File): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file, file.name)

  const response = await apiFetch('/api/v1/books', { method: 'POST', body: form })
  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // body wasn't JSON — keep generic message
    }
    throw new Error(detail)
  }

  const book = (await response.json()) as Book
  return { status: response.status, book }
}
