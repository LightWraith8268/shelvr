import { Link, Route, Routes, useNavigate } from 'react-router-dom'
import { Library } from './views/Library'
import { BookDetail } from './views/BookDetail'

function LibraryRoute() {
  const navigate = useNavigate()
  return <Library onBookSelect={(book) => navigate(`/books/${book.id}`)} />
}

function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-xl font-semibold tracking-tight">
            Shelvr
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">
        <Routes>
          <Route path="/" element={<LibraryRoute />} />
          <Route path="/books/:bookId" element={<BookDetail />} />
          <Route path="*" element={<p className="text-slate-500">Not found.</p>} />
        </Routes>
      </main>
    </div>
  )
}

export default App
