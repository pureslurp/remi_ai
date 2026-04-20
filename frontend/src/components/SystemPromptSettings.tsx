import { useEffect, useState } from 'react'
import * as api from '../api/client'
import type { SystemPromptsSettings } from '../api/client'

type Tab = 'buyer' | 'seller' | 'buyer_seller'

interface Props {
  open: boolean
  onClose: () => void
}

function effective(
  def: string,
  override: string | null | undefined,
): string {
  return (override != null && override.trim() !== '') ? override : def
}

export default function SystemPromptSettings({ open, onClose }: Props) {
  const [tab, setTab] = useState<Tab>('buyer')
  const [data, setData] = useState<SystemPromptsSettings | null>(null)
  const [buyer, setBuyer] = useState('')
  const [seller, setSeller] = useState('')
  const [both, setBoth] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    setError('')
    api
      .getSystemPrompts()
      .then((d) => {
        if (cancelled) return
        setData(d)
        setBuyer(effective(d.default_buyer, d.override_buyer))
        setSeller(effective(d.default_seller, d.override_seller))
        setBoth(effective(d.default_buyer_seller, d.override_buyer_seller))
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message || 'Failed to load settings')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open])

  const resetCurrentTab = () => {
    if (!data) return
    if (tab === 'buyer') setBuyer(data.default_buyer)
    if (tab === 'seller') setSeller(data.default_seller)
    if (tab === 'buyer_seller') setBoth(data.default_buyer_seller)
  }

  const save = async () => {
    if (!data) return
    setSaving(true)
    setError('')
    const norm = (s: string, def: string) => {
      const t = s.trim()
      return t === def.trim() ? null : t
    }
    try {
      const updated = await api.updateSystemPrompts({
        override_buyer: norm(buyer, data.default_buyer),
        override_seller: norm(seller, data.default_seller),
        override_buyer_seller: norm(both, data.default_buyer_seller),
      })
      setData(updated)
      setBuyer(effective(updated.default_buyer, updated.override_buyer))
      setSeller(effective(updated.default_seller, updated.override_seller))
      setBoth(effective(updated.default_buyer_seller, updated.override_buyer_seller))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const currentTextarea =
    tab === 'buyer' ? buyer : tab === 'seller' ? seller : both
  const setCurrent =
    tab === 'buyer' ? setBuyer : tab === 'seller' ? setSeller : setBoth

  if (!open) return null

  return (
    <div
      className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-[100] p-4 overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget && !saving) onClose()
      }}
    >
      <div
        className="bg-gradient-to-br from-brand-navy to-brand-slate/95 rounded-2xl border border-white/10 shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col"
        role="dialog"
        aria-labelledby="prompt-settings-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4 border-b border-white/10 shrink-0">
          <h2 id="prompt-settings-title" className="text-lg font-semibold text-brand-cloud tracking-tight">
            AI system prompts
          </h2>
          <p className="text-xs text-brand-cloud/55 mt-1 leading-relaxed">
            Defaults follow your client&apos;s transaction type (buying, selling, or both). Edit below to
            override your account defaults; Kova still receives client context, documents, and emails in
            addition to this guidance.
          </p>
        </div>

        <div className="px-5 pt-3 shrink-0 flex gap-2 border-b border-white/10 pb-3">
          {(
            [
              ['buyer', 'Buying'],
              ['seller', 'Selling'],
              ['buyer_seller', 'Buying & selling'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`flex-1 py-2 rounded-lg text-xs font-medium transition border ${
                tab === id
                  ? 'bg-brand-mint/15 border-brand-mint/60 text-brand-cloud'
                  : 'bg-white/[0.03] border-white/10 text-brand-cloud/70 hover:bg-white/[0.06]'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex-1 min-h-0 px-5 py-4 flex flex-col gap-3">
          {loading && <p className="text-sm text-brand-cloud/55">Loading…</p>}
          {error && (
            <p className="text-sm text-red-200 bg-red-500/10 border border-red-400/30 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
          {!loading && data && (
            <>
              <label className="text-[11px] font-medium uppercase tracking-wider text-brand-cloud/50">
                Strategy text for this role
              </label>
              <textarea
                value={currentTextarea}
                onChange={(e) => setCurrent(e.target.value)}
                className="flex-1 min-h-[200px] w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-brand-cloud placeholder-brand-cloud/35 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50 resize-y font-mono leading-relaxed"
                spellCheck={false}
              />
              <div className="flex flex-wrap gap-2 justify-between items-center shrink-0">
                <button
                  type="button"
                  onClick={resetCurrentTab}
                  className="text-xs text-brand-cloud/55 hover:text-brand-cloud underline-offset-2 hover:underline"
                >
                  Reset this tab to app default
                </button>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 rounded-lg bg-white/[0.05] border border-white/10 text-sm text-brand-cloud hover:bg-white/[0.08] transition"
                  >
                    Close
                  </button>
                  <button
                    type="button"
                    onClick={() => void save()}
                    disabled={saving}
                    className="px-4 py-2 rounded-lg bg-brand-mint text-brand-navy text-sm font-semibold hover:bg-brand-mint/90 transition disabled:opacity-50"
                  >
                    {saving ? 'Saving…' : 'Save changes'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
