import { useQuery } from '@tanstack/react-query'

interface ServerInfo {
  name: string
  version: string
  api_version: string
}

async function fetchServerInfo(): Promise<ServerInfo> {
  const res = await fetch('/api/v1/server/info')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

function App() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['server-info'],
    queryFn: fetchServerInfo,
  })

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-5xl px-6 py-4">
          <h1 className="text-2xl font-semibold">Shelvr</h1>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-lg font-medium">Server</h2>
          {isLoading && <p className="text-slate-500">Loading…</p>}
          {error && (
            <p className="text-red-600">
              Error: {error instanceof Error ? error.message : 'unknown'}
            </p>
          )}
          {data && (
            <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
              <dt className="text-slate-500">Name</dt>
              <dd className="font-mono">{data.name}</dd>
              <dt className="text-slate-500">Version</dt>
              <dd className="font-mono">{data.version}</dd>
              <dt className="text-slate-500">API</dt>
              <dd className="font-mono">{data.api_version}</dd>
            </dl>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
