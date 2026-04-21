import { useState, useCallback } from 'react'
import * as api from '../api/client'

export function useGoogleOAuthRedirect() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const startGoogleAuth = useCallback(async () => {
    setError(null)
    setBusy(true)
    try {
      const data = await api.getGoogleAuthUrl()
      window.location.assign(data.url)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes('credentials.json')) {
        setError(
          'This server is not configured for Google sign-in yet (missing web OAuth or credentials).',
        )
      } else {
        setError(msg)
      }
      setBusy(false)
    }
  }, [])

  return { busy, error, startGoogleAuth }
}
