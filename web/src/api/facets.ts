import { apiJson } from './client'

export interface TagFacet {
  id: number
  name: string
  color: string | null
  count: number
}

export interface AuthorFacet {
  id: number
  name: string
  sort_name: string | null
  count: number
}

export interface LanguageFacet {
  code: string
  count: number
}

export async function listTagFacets(): Promise<TagFacet[]> {
  const body = await apiJson<{ items: TagFacet[] }>('/api/v1/tags')
  return body.items
}

export async function listAuthorFacets(): Promise<AuthorFacet[]> {
  const body = await apiJson<{ items: AuthorFacet[] }>('/api/v1/authors')
  return body.items
}

export async function listLanguageFacets(): Promise<LanguageFacet[]> {
  const body = await apiJson<{ items: LanguageFacet[] }>('/api/v1/languages')
  return body.items
}
