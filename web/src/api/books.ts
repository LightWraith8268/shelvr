import type { Book, BookList, BookSort } from './types'

export interface ListBooksParams {
  limit?: number
  offset?: number
  sort?: BookSort
  q?: string
}

export async function listBooks(params: ListBooksParams = {}): Promise<BookList> {
  const search = new URLSearchParams()
  if (params.limit !== undefined) search.set('limit', String(params.limit))
  if (params.offset !== undefined) search.set('offset', String(params.offset))
  if (params.sort) search.set('sort', params.sort)
  if (params.q) search.set('q', params.q)
  const qs = search.toString()
  const res = await fetch(`/api/v1/books${qs ? `?${qs}` : ''}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getBook(id: number): Promise<Book> {
  const res = await fetch(`/api/v1/books/${id}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function coverUrl(bookId: number, size: 'small' | 'medium' | 'original' = 'medium'): string {
  return `/api/v1/books/${bookId}/cover?size=${size}`
}

export function formatFileUrl(formatId: number): string {
  return `/api/v1/formats/${formatId}/file`
}
