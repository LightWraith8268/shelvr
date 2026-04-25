import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listPlugins, setPluginEnabled } from '../api/plugins'
import type { PluginInfo } from '../api/plugins'

export function PluginsView() {
  const queryClient = useQueryClient()
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

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold tracking-tight">Plugins</h2>
        <Link to="/" className="text-sm text-slate-500 hover:text-slate-900">
          ← Back to library
        </Link>
      </div>

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
