import { useState } from 'react'
import * as api from '../api/client'

export default function LoginScreen() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const signIn = async () => {
    setError(null)
    setBusy(true)
    try {
      const data = await api.getGoogleAuthUrl()
      window.location.assign(data.url)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes('credentials.json')) {
        setError(
          'This server is not configured for Google sign-in yet (missing web OAuth or credentials).'
        )
      } else {
        setError(msg)
      }
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-md text-center">
        <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-3xl font-bold text-white mx-auto mb-6">
          R
        </div>
        <h1 className="text-2xl font-semibold text-white mb-2">REMI AI</h1>
        <p className="text-gray-400 text-sm mb-8">
          Sign in with Google to access your clients, chat, and Gmail / Drive sync. Your data stays
          available after this one-time connect.
        </p>

        {error && (
          <div className="mb-4 rounded-lg bg-red-950/60 border border-red-800/60 px-3 py-2 text-left text-xs text-red-200">
            {error}
          </div>
        )}

        <button
          type="button"
          onClick={signIn}
          disabled={busy}
          className="w-full py-3 rounded-xl bg-white text-gray-900 text-sm font-semibold hover:bg-gray-100 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {busy ? (
            <>
              <span className="inline-block h-4 w-4 border-2 border-gray-400 border-t-gray-900 rounded-full animate-spin" />
              Connecting…
            </>
          ) : (
            <>
              <svg className="w-5 h-5" viewBox="0 0 24 24" aria-hidden>
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Sign in with Google
            </>
          )}
        </button>

        <p className="mt-6 text-[11px] text-gray-600">
          You will be asked to grant Gmail and Drive access so REMI can sync on your behalf.
        </p>
      </div>
    </div>
  )
}
