export interface Author {
  id: number
  name: string
  sort_name: string | null
}

export interface Tag {
  id: number
  name: string
  color: string | null
}

export interface Format {
  id: number
  format: string
  file_path: string
  file_size: number
  file_hash: string
  source: string
  date_added: string
}

export interface Book {
  id: number
  title: string
  sort_title: string | null
  authors: Author[]
  series: string | null
  series_id: number | null
  series_index: number | null
  description: string | null
  language: string | null
  publisher: string | null
  published_date: string | null
  isbn: string | null
  rating: number | null
  tags: Tag[]
  identifiers: Record<string, string>
  formats: Format[]
  date_added: string
  date_modified: string
  cover_path: string | null
}

export interface BookList {
  items: Book[]
  total: number
  limit: number
  offset: number
}

export type BookSort = 'title' | 'added' | 'series'
