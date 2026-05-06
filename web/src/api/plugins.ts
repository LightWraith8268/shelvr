import { apiFetch, apiJson } from './client'

export interface PluginInfo {
  id: string
  name: string
  version: string
  api_version: string
  priority: number
  enabled: boolean
  hooks: string[]
}

export async function listPlugins(): Promise<PluginInfo[]> {
  const body = await apiJson<{ items: PluginInfo[] }>('/api/v1/plugins')
  return body.items
}

export async function setPluginEnabled(pluginId: string, enabled: boolean): Promise<PluginInfo> {
  return apiJson<PluginInfo>(`/api/v1/plugins/${encodeURIComponent(pluginId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  })
}

export interface PluginUploadResult {
  id: string
  name: string
  version: string
  install_path: string
  restart_required: boolean
}

export async function uploadPlugin(
  file: File,
  overwrite: boolean,
): Promise<PluginUploadResult> {
  const body = new FormData()
  body.append('file', file)
  const url = `/api/v1/plugins/upload${overwrite ? '?overwrite=true' : ''}`
  const response = await apiFetch(url, { method: 'POST', body })
  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const errorBody = await response.json()
      if (errorBody?.detail) detail = errorBody.detail
    } catch {
      // body wasn't JSON
    }
    throw new Error(detail)
  }
  return (await response.json()) as PluginUploadResult
}

export async function uninstallPlugin(pluginId: string): Promise<void> {
  const response = await apiFetch(
    `/api/v1/plugins/${encodeURIComponent(pluginId)}/install`,
    { method: 'DELETE' },
  )
  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const errorBody = await response.json()
      if (errorBody?.detail) detail = errorBody.detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }
}
