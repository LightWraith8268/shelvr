import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { ReactNode } from 'react'

type ToastVariant = 'success' | 'error' | 'info'

interface ToastEntry {
  id: number
  variant: ToastVariant
  message: string
}

interface ConfirmOptions {
  title: string
  message?: string
  confirmLabel?: string
  cancelLabel?: string
  danger?: boolean
}

interface PromptOptions {
  title: string
  message?: string
  placeholder?: string
  initialValue?: string
  confirmLabel?: string
  cancelLabel?: string
  multiline?: boolean
}

interface ConfirmState extends ConfirmOptions {
  resolve: (ok: boolean) => void
}

interface PromptState extends PromptOptions {
  resolve: (value: string | null) => void
}

interface ToastApi {
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
  confirm: (options: ConfirmOptions) => Promise<boolean>
  prompt: (options: PromptOptions) => Promise<string | null>
}

const ToastContext = createContext<ToastApi | null>(null)

const TOAST_TIMEOUT_MS = 4000

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastEntry[]>([])
  const [confirmState, setConfirmState] = useState<ConfirmState | null>(null)
  const [promptState, setPromptState] = useState<PromptState | null>(null)
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((entry) => entry.id !== id))
  }, [])

  const push = useCallback(
    (variant: ToastVariant, message: string) => {
      const id = nextId.current++
      setToasts((current) => [...current, { id, variant, message }])
      window.setTimeout(() => dismiss(id), TOAST_TIMEOUT_MS)
    },
    [dismiss],
  )

  const api = useMemo<ToastApi>(
    () => ({
      success: (message) => push('success', message),
      error: (message) => push('error', message),
      info: (message) => push('info', message),
      confirm: (options) =>
        new Promise<boolean>((resolve) => {
          setConfirmState({ ...options, resolve })
        }),
      prompt: (options) =>
        new Promise<string | null>((resolve) => {
          setPromptState({ ...options, resolve })
        }),
    }),
    [push],
  )

  function resolveConfirm(ok: boolean) {
    if (!confirmState) return
    confirmState.resolve(ok)
    setConfirmState(null)
  }

  function resolvePrompt(value: string | null) {
    if (!promptState) return
    promptState.resolve(value)
    setPromptState(null)
  }

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastStack toasts={toasts} onDismiss={dismiss} />
      {confirmState && <ConfirmModal state={confirmState} onResolve={resolveConfirm} />}
      {promptState && <PromptModal state={promptState} onResolve={resolvePrompt} />}
    </ToastContext.Provider>
  )
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: ToastEntry[]
  onDismiss: (id: number) => void
}) {
  if (toasts.length === 0) return null
  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2"
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`pointer-events-auto flex items-start justify-between gap-3 rounded-md border px-3 py-2 text-sm shadow-md ${variantClass(
            toast.variant,
          )}`}
        >
          <span className="flex-1">{toast.message}</span>
          <button
            type="button"
            onClick={() => onDismiss(toast.id)}
            aria-label="Dismiss notification"
            className="text-slate-500 hover:text-slate-900"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}

function variantClass(variant: ToastVariant): string {
  switch (variant) {
    case 'success':
      return 'border-emerald-200 bg-emerald-50 text-emerald-900'
    case 'error':
      return 'border-red-200 bg-red-50 text-red-900'
    case 'info':
      return 'border-slate-200 bg-white text-slate-900'
  }
}

function ConfirmModal({
  state,
  onResolve,
}: {
  state: ConfirmState
  onResolve: (ok: boolean) => void
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onResolve(false)
      if (event.key === 'Enter') onResolve(true)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onResolve])

  return (
    <ModalShell onCancel={() => onResolve(false)}>
      <h3 className="text-base font-semibold text-slate-900">{state.title}</h3>
      {state.message && <p className="mt-2 text-sm text-slate-600">{state.message}</p>}
      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={() => onResolve(false)}
          className="rounded-md border border-slate-300 bg-white px-3 py-1 text-sm hover:bg-slate-50"
        >
          {state.cancelLabel ?? 'Cancel'}
        </button>
        <button
          type="button"
          autoFocus
          onClick={() => onResolve(true)}
          className={
            state.danger
              ? 'rounded-md border border-red-300 bg-red-600 px-3 py-1 text-sm text-white hover:bg-red-700'
              : 'rounded-md border border-slate-300 bg-slate-900 px-3 py-1 text-sm text-white hover:bg-slate-800'
          }
        >
          {state.confirmLabel ?? 'OK'}
        </button>
      </div>
    </ModalShell>
  )
}

function PromptModal({
  state,
  onResolve,
}: {
  state: PromptState
  onResolve: (value: string | null) => void
}) {
  const [value, setValue] = useState(state.initialValue ?? '')
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    onResolve(value)
  }

  return (
    <ModalShell onCancel={() => onResolve(null)}>
      <form onSubmit={handleSubmit}>
        <h3 className="text-base font-semibold text-slate-900">{state.title}</h3>
        {state.message && <p className="mt-2 text-sm text-slate-600">{state.message}</p>}
        {state.multiline ? (
          <textarea
            ref={(el) => {
              inputRef.current = el
            }}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder={state.placeholder}
            rows={4}
            className="mt-3 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          />
        ) : (
          <input
            ref={(el) => {
              inputRef.current = el
            }}
            type="text"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder={state.placeholder}
            className="mt-3 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          />
        )}
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => onResolve(null)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1 text-sm hover:bg-slate-50"
          >
            {state.cancelLabel ?? 'Cancel'}
          </button>
          <button
            type="submit"
            className="rounded-md border border-slate-300 bg-slate-900 px-3 py-1 text-sm text-white hover:bg-slate-800"
          >
            {state.confirmLabel ?? 'OK'}
          </button>
        </div>
      </form>
    </ModalShell>
  )
}

function ModalShell({
  children,
  onCancel,
}: {
  children: ReactNode
  onCancel: () => void
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel()
      }}
    >
      <div className="w-full max-w-md rounded-md border border-slate-200 bg-white p-5 shadow-lg">
        {children}
      </div>
    </div>
  )
}
