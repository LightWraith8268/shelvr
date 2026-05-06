import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  listPlugins,
  setPluginEnabled,
  uninstallPlugin,
  uploadPlugin,
} from '../api/plugins'
import type { PluginInfo } from '../api/plugins'
import { useToast } from '../components/ToastProvider'

export function PluginsView() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [overwrite, setOverwrite] = useState(false)
  const { data: plugins, isLoading, error } = useQuery({
    queryKey: ['plugins'],
    queryFn: listPlugins,
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      setPluginEnabled(id, enabled),
    onSuccess: (updated) => {
      queryClient.setQueryData<PluginInfo[]>(['plugins'], (current) =>
        current?.map((plugin) => (plugin.id === updated.id ? updated : plugin)),
      )
    },
  })

  const uploadMutation = useMutation({
    mutationFn: ({ file, overwrite: replace }: { file: File; overwrite: boolean }) =>
      uploadPlugin(file, replace),
    onSuccess: (result) => {
      toast.success(
        `Installed ${result.name} v${result.version}. Restart server to load.`,
      )
      if (fileInputRef.current) fileInputRef.current.value = ''
    },
    onError: (caught) => {
      toast.error(caught instanceof Error ? caught.message : 'Upload failed.')
    },
  })

  const uninstallMutation = useMutation({
    mutationFn: (pluginId: string) => uninstallPlugin(pluginId),
    onSuccess: () => {
      toast.success('Plugin files removed. Restart server to drop from registry.')
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
    },
    onError: (caught) => {
      toast.error(caught instanceof Error ? caught.message : 'Uninstall failed.')
    },
  })

  function handleUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      toast.error('Pick a .zip file first.')
      return
    }
    uploadMutation.mutate({ file, overwrite })
  }

  async function handleUninstall(plugin: PluginInfo) {
    const ok = await toast.confirm({
      title: `Uninstall ${plugin.name}?`,
      message: 'Removes the plugin directory. Already-loaded code keeps running until restart.',
      confirmLabel: 'Uninstall',
      danger: true,
    })
    if (ok) uninstallMutation.mutate(plugin.id)
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold tracking-tight">Plugins</h2>
        <Link to="/" className="text-sm text-slate-500 hover:text-slate-900">
          ← Back to library
        </Link>
      </div>

      <form
        onSubmit={handleUpload}
        className="mb-6 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
      >
        <h3 className="text-sm font-semibold">Install plugin</h3>
        <p className="mt-1 text-xs">
          Plugins run in-process with full server privileges. Only upload zips
          from sources you trust. Server restart required to load a new plugin.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,application/zip"
            className="text-xs"
          />
          <label className="inline-flex items-center gap-1 text-xs">
            <input
              type="checkbox"
              checked={overwrite}
              onChange={(event) => setOverwrite(event.target.checked)}
              className="h-3.5 w-3.5"
            />
            Overwrite existing
          </label>
          <button
            type="submit"
            disabled={uploadMutation.isPending}
            className="rounded-md border border-amber-300 bg-white px-3 py-1 text-xs hover:bg-amber-100 disabled:opacity-50"
          >
            {uploadMutation.isPending ? 'Uploading…' : 'Upload'}
          </button>
        </div>
      </form>

      {isLoading && <p className="text-slate-500">Loading…</p>}
      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Error: {error instanceof Error ? error.message : 'unknown'}
        </p>
      )}

      {plugins && plugins.length === 0 && (
        <p className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
          No plugins loaded.
        </p>
      )}

      {plugins && plugins.length > 0 && (
        <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">Plugin</th>
                <th className="px-3 py-2">Version</th>
                <th className="px-3 py-2">Hooks</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {plugins.map((plugin) => (
                <tr key={plugin.id}>
                  <td className="px-3 py-2 align-top">
                    <div className="font-medium text-slate-900">{plugin.name}</div>
                    <div className="font-mono text-xs text-slate-500">{plugin.id}</div>
                  </td>
                  <td className="px-3 py-2 align-top font-mono text-xs text-slate-700">
                    {plugin.version}
                    <div className="text-slate-400">api {plugin.api_version}</div>
                  </td>
                  <td className="px-3 py-2 align-top">
                    {plugin.hooks.length === 0 ? (
                      <span className="text-xs text-slate-400">—</span>
                    ) : (
                      <ul className="flex flex-wrap gap-1">
                        {plugin.hooks.map((hook) => (
                          <li
                            key={hook}
                            className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 font-mono text-[10px] text-slate-600"
                          >
                            {hook}
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                  <td className="px-3 py-2 align-top">
                    <label className="inline-flex cursor-pointer items-center gap-2">
                      <input
                        type="checkbox"
                        checked={plugin.enabled}
                        disabled={toggleMutation.isPending}
                        onChange={(event) =>
                          toggleMutation.mutate({
                            id: plugin.id,
                            enabled: event.target.checked,
                          })
                        }
                        className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
                      />
                      <span className={plugin.enabled ? 'text-emerald-700' : 'text-slate-500'}>
                        {plugin.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </label>
                  </td>
                  <td className="px-3 py-2 align-top text-right">
                    <button
                      type="button"
                      onClick={() => handleUninstall(plugin)}
                      disabled={uninstallMutation.isPending}
                      className="rounded-md border border-red-200 bg-white px-2 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50"
                    >
                      Uninstall
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {toggleMutation.isError && (
        <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Toggle failed:{' '}
          {toggleMutation.error instanceof Error ? toggleMutation.error.message : 'unknown'}
        </p>
      )}
    </section>
  )
}
