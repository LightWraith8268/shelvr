import { useEffect, useState } from 'react'
import { apiFetch } from './client'

/**
 * Load an authenticated URL into an object URL so it can be used as ``<img
 * src>``. The browser's image loader can't carry our bearer header on its
 * own, so we fetch the bytes through ``apiFetch`` and hand React a blob URL.
 */
export function useAuthedBlob(url: string | null): string | null {
  const [objectUrl, setObjectUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!url) {
      setObjectUrl(null)
      return
    }
    let cancelled = false
    let createdUrl: string | null = null

    apiFetch(url)
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const blob = await response.blob()
        if (cancelled) return
        createdUrl = URL.createObjectURL(blob)
        setObjectUrl(createdUrl)
      })
      .catch(() => {
        if (!cancelled) setObjectUrl(null)
      })

    return () => {
      cancelled = true
      if (createdUrl) URL.revokeObjectURL(createdUrl)
    }
  }, [url])

  return objectUrl
}

/**
 * Download an authenticated file by fetching it through ``apiFetch`` and
 * triggering a save via a temporary anchor tag. Used because ``<a download>``
 * cannot attach an Authorization header on its own.
 */
export async function downloadAuthedFile(url: string, suggestedFilename: string): Promise<void> {
  const response = await apiFetch(url)
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  try {
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = suggestedFilename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
  } finally {
    URL.revokeObjectURL(objectUrl)
  }
}
