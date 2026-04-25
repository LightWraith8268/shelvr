import { apiJson } from './client'
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
  return apiJson<BookList>(`/api/v1/books${qs ? `?${qs}` : ''}`)
}

export async function getBook(id: number): Promise<Book> {
  return apiJson<Book>(`/api/v1/books/${id}`)
}

export function coverUrl(bookId: number, size: 'small' | 'medium' | 'original' = 'medium'): string {
  return `/api/v1/books/${bookId}/cover?size=${size}`
}

export function formatFileUrl(formatId: number): string {
  return `/api/v1/formats/${formatId}/file`
}
