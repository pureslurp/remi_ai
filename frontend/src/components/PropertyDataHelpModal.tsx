import { useEffect } from 'react'
import { createPortal } from 'react-dom'

type Props = { open: boolean; onClose: () => void }

export default function PropertyDataHelpModal({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const modal = (
    <div
      className="modal-backdrop-in fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-md"
      onClick={onClose}
      role="presentation"
    >
      <div className="flex min-h-full w-full items-center justify-center p-4 sm:p-6">
        <div
          onClick={e => e.stopPropagation()}
          className="w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-2xl border border-white/10 bg-gradient-to-br from-brand-navy to-brand-slate/95 text-brand-cloud shadow-2xl"
          role="dialog"
          aria-labelledby="chat-commands-help-title"
          aria-modal="true"
        >
        <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between shrink-0">
          <h2 id="chat-commands-help-title" className="text-lg font-semibold text-brand-cloud tracking-tight">
            Chat commands
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 w-8 h-8 rounded-lg text-brand-cloud/60 hover:text-brand-cloud hover:bg-white/[0.08] text-lg leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="px-4 py-3 text-[13px] text-brand-cloud/80 space-y-4 leading-relaxed">
          <p>
            <strong>reco-pilot</strong> can pull <strong>public and aggregated</strong> property data through
            RealEstateAPI in the system context and when you use chat commands. This is{' '}
            <strong>not a replacement for the MLS</strong> — always verify material facts, active status, and timing
            in your local MLS and records.
          </p>
          <div>
            <h3 className="text-xs font-semibold text-brand-mint/90 uppercase tracking-wide mb-1.5">Subject property</h3>
            <p>
              A default <strong>subject</strong> home is chosen from your project (e.g. open transaction or your sale
              listing) so the assistant is grounded. You can refine addresses with the address typeahead in the client
              panel.
            </p>
          </div>
          <div>
            <h3 className="text-xs font-semibold text-brand-mint/90 uppercase tracking-wide mb-1.5">
              <code className="text-[12px]">/search</code> — market list
            </h3>
            <p>
              On the <strong>same line</strong>, add natural language plus a <strong>5-digit U.S. ZIP</strong>, e.g.{' '}
              <code className="text-[11px] text-brand-cloud/60">/search 3 br for sale in 48067</code>. If you only send
              <code className="text-[11px]">/search</code> with no criteria, the app explains how to continue without
              spending a search call.
            </p>
          </div>
          <div>
            <h3 className="text-xs font-semibold text-brand-mint/90 uppercase tracking-wide mb-1.5">
              <code className="text-[12px]">/comps</code> — comparables
            </h3>
            <p>
              Put a <strong>full U.S. address</strong> after the command, or use <code>subject</code> / this property
              for this project’s subject. Optional: <code>radius=2</code> (miles), <code>days=180</code>,{' '}
              <code>max_results=20</code>. Bare <code>/comps</code> shows a short how-to without running comps.
            </p>
          </div>
        </div>
        <div className="px-4 py-3 border-t border-white/10">
          <button
            type="button"
            onClick={onClose}
            className="w-full py-2 rounded-lg bg-white/[0.08] text-sm text-brand-cloud/90 hover:bg-white/12 transition"
          >
            Done
          </button>
        </div>
        </div>
      </div>
    </div>
  )

  return typeof document !== 'undefined' && document.body ? createPortal(modal, document.body) : modal
}
