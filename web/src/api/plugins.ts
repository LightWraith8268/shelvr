import { apiJson } from './client'

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
