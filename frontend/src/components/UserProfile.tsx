import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '../store/appStore'
import * as api from '../api/client'
import { clearDeviceSession } from '../auth/session'

export default function UserProfile() {
  const { googleUser } = useAppStore()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const label = googleUser?.email || googleUser?.name || 'Signed in'
  const initial = (googleUser?.email?.[0] || googleUser?.name?.[0] || '?').toUpperCase()

  const signOut = async () => {
    try {
      await api.disconnectGoogle()
    } catch {
      /* still clear local session */
    }
    clearDeviceSession()
    window.location.assign('/')
  }

  return (
    <div className="relative border-t border-gray-800 p-2 shrink-0" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 rounded-lg px-2 py-2 hover:bg-gray-800/80 transition text-left"
      >
        {googleUser?.picture ? (
          <img
            src={googleUser.picture}
            alt=""
            className="h-9 w-9 rounded-full object-cover shrink-0 border border-gray-700"
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="h-9 w-9 rounded-full bg-blue-700 flex items-center justify-center text-sm font-semibold text-white shrink-0">
            {initial}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-white truncate">{label}</p>
          <p className="text-[10px] text-gray-500 truncate">Google account</p>
        </div>
        <span className="text-gray-500 text-xs shrink-0">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="absolute bottom-full left-2 right-2 mb-1 rounded-lg border border-gray-700 bg-gray-800 shadow-xl py-1 z-50">
          <div className="px-3 py-2 border-b border-gray-700">
            <p className="text-[11px] text-gray-400 uppercase tracking-wide">Profile</p>
            {googleUser?.name && <p className="text-sm text-white mt-1">{googleUser.name}</p>}
            {googleUser?.email && <p className="text-xs text-gray-400 break-all">{googleUser.email}</p>}
          </div>
          <button
            type="button"
            onClick={signOut}
            className="w-full text-left px-3 py-2 text-sm text-red-300 hover:bg-gray-700/80 transition"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}
