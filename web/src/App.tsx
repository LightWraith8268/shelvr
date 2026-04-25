import { Library } from './views/Library'

function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <h1 className="text-xl font-semibold tracking-tight">Shelvr</h1>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">
        <Library />
      </main>
    </div>
  )
}

export default App
