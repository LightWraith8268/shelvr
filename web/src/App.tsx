import { Link, Route, Routes, useNavigate } from 'react-router-dom'
import { Library } from './views/Library'
import { BookDetail } from './views/BookDetail'
import { BookEdit } from './views/BookEdit'
import { LoginView } from './views/Login'
import { UploadView } from './views/Upload'
import { PluginsView } from './views/Plugins'
import { AccountView } from './views/Account'
import { RequireAuth } from './auth/RequireAuth'
import { RequireAdmin } from './auth/RequireAdmin'
import { useAuth } from './auth/AuthProvider'

function LibraryRoute() {
  const navigate = useNavigate()
  return <Library onBookSelect={(book) => navigate(`/books/${book.id}`)} />
}

function HeaderUser() {
  const { status, user, logout } = useAuth()
  if (status !== 'authenticated' || !user) return null
  return (
    <div className="flex items-center gap-3 text-sm text-slate-600">
      {user.role === 'admin' && (
        <>
          <Link
            to="/upload"
            className="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs hover:bg-slate-50"
          >
            Upload
          </Link>
          <Link
            to="/plugins"
            className="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs hover:bg-slate-50"
          >
            Plugins
          </Link>
        </>
      )}
      <Link
        to="/account"
        className="font-medium text-slate-900 hover:underline"
      >
        {user.username}
      </Link>
      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs uppercase tracking-wide text-slate-600">
        {user.role}
      </span>
      <button
        type="button"
        onClick={() => {
          logout()
        }}
        className="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs hover:bg-slate-50"
      >
        Sign out
      </button>
    </div>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-xl font-semibold tracking-tight">
            Shelvr
          </Link>
          <HeaderUser />
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">
        <Routes>
          <Route path="/login" element={<LoginView />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <LibraryRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/books/:bookId"
            element={
              <RequireAuth>
                <BookDetail />
              </RequireAuth>
            }
          />
          <Route
            path="/upload"
            element={
              <RequireAdmin>
                <UploadView />
              </RequireAdmin>
            }
          />
          <Route
            path="/books/:bookId/edit"
            element={
              <RequireAdmin>
                <BookEdit />
              </RequireAdmin>
            }
          />
          <Route
            path="/plugins"
            element={
              <RequireAdmin>
                <PluginsView />
              </RequireAdmin>
            }
          />
          <Route
            path="/account"
            element={
              <RequireAuth>
                <AccountView />
              </RequireAuth>
            }
          />
          <Route path="*" element={<p className="text-slate-500">Not found.</p>} />
        </Routes>
      </main>
    </div>
  )
}

export default App
