import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '../store/appStore'
import * as api from '../api/client'
import SystemPromptSettings from './SystemPromptSettings'

export default function UserProfile({ compact = false }: { compact?: boolean }) {
  const { googleUser } = useAppStore()
  const [open, setOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
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
    window.location.assign('/')
  }

  const avatar = googleUser?.picture ? (
    <img
      src={googleUser.picture}
      alt=""
      className={`rounded-full object-cover shrink-0 border border-white/15 ${compact ? 'h-10 w-10' : 'h-9 w-9'}`}
      referrerPolicy="no-referrer"
    />
  ) : (
    <div
      className={`rounded-full bg-gradient-to-br from-brand-navy to-brand-slate border border-white/10 flex items-center justify-center font-semibold text-brand-cloud shrink-0 ${
        compact ? 'h-10 w-10 text-sm' : 'h-9 w-9 text-sm'
      }`}
    >
      {initial}
    </div>
  )

  return (
    <div
      className={`relative border-t border-white/5 shrink-0 ${compact ? 'p-2 flex justify-center' : 'p-2'}`}
      ref={ref}
    >
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        title={label}
        className={
          compact
            ? 'flex items-center justify-center rounded-xl p-0.5 hover:bg-white/[0.06] transition'
            : 'w-full flex items-center gap-2 rounded-lg px-2 py-2 hover:bg-white/[0.04] transition text-left'
        }
      >
        {avatar}
        {!compact && (
          <>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-brand-cloud truncate">{label}</p>
              <p className="text-[10px] text-brand-cloud/45 truncate uppercase tracking-wide">Google account</p>
            </div>
            <span className="text-brand-cloud/40 text-xs shrink-0">{open ? '▲' : '▼'}</span>
          </>
        )}
      </button>

      {open && (
        <div
          className={`absolute bottom-full mb-1 rounded-xl border border-white/10 bg-gradient-to-br from-brand-navy to-brand-slate/95 backdrop-blur-sm shadow-2xl py-1 z-50 min-w-[200px] ${
            compact ? 'right-0 left-auto' : 'left-2 right-2'
          }`}
        >
          <div className="px-3 py-2 border-b border-white/10">
            <p className="text-[11px] text-brand-cloud/50 uppercase tracking-wider">Profile</p>
            {googleUser?.name && <p className="text-sm text-brand-cloud mt-1">{googleUser.name}</p>}
            {googleUser?.email && <p className="text-xs text-brand-cloud/60 break-all">{googleUser.email}</p>}
          </div>
          <button
            type="button"
            onClick={() => {
              setOpen(false)
              setSettingsOpen(true)
            }}
            className="w-full text-left px-3 py-2 text-sm text-brand-cloud/90 hover:bg-white/[0.06] transition"
          >
            AI prompt settings…
          </button>
          <button
            type="button"
            onClick={signOut}
            className="w-full text-left px-3 py-2 text-sm text-red-300 hover:bg-white/[0.06] transition border-t border-white/10"
          >
            Sign out
          </button>
        </div>
      )}
      <SystemPromptSettings open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
