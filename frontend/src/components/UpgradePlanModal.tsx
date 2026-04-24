import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import * as api from '../api/client'

type Plan = 'pro' | 'max' | 'ultra'

const TIERS: Record<Plan, {
  label: string
  price: number
  intro: string
  bullets: readonly string[]
  recommended?: boolean
}> = {
  pro: {
    label: 'Pro',
    price: 20,
    intro: 'Everything in Free, plus:',
    bullets: ['4× more AI usage than Free', 'Advanced AI models', 'Unlimited clients'],
  },
  max: {
    label: 'Max',
    price: 60,
    intro: 'Everything in Pro, plus:',
    bullets: ['3× more AI usage than Pro', 'Frontier models where available', 'Best fit for daily deal volume'],
    recommended: true,
  },
  ultra: {
    label: 'Ultra',
    price: 100,
    intro: 'Everything in Max, plus:',
    bullets: ['Highest included AI usage', 'Priority access to new capabilities', 'For power users across many clients'],
  },
}

const TIER_ORDER: Plan[] = ['pro', 'max', 'ultra']
const CARD_ANIM = ['modal-card-in-1', 'modal-card-in-2', 'modal-card-in-3'] as const

function CheckIcon() {
  return (
    <svg
      className="shrink-0 mt-[1px]"
      width="13"
      height="13"
      viewBox="0 0 13 13"
      fill="none"
      aria-hidden
    >
      <circle cx="6.5" cy="6.5" r="6" stroke="currentColor" strokeOpacity="0.25" />
      <path d="M4 6.5l1.8 1.8L9 4.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function UpgradePlanModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [busy, setBusy] = useState<Plan | null>(null)
  const [error, setError] = useState<string | null>(null)
  const overlayRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const select = async (plan: Plan) => {
    setBusy(plan)
    setError(null)
    try {
      const { url } = await api.createCheckoutSession(plan)
      window.location.href = url
    } catch {
      setError('Could not start checkout. Please try again.')
      setBusy(null)
    }
  }

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === overlayRef.current) onClose()
  }

  const modal = (
    <div
      ref={overlayRef}
      className="modal-backdrop-in fixed inset-0 z-50 flex items-end justify-center sm:items-center bg-black/70 backdrop-blur-md px-4 pb-4 sm:pb-0"
      onClick={handleOverlayClick}
    >
      <div
        className="modal-panel-in relative w-full max-w-[680px] rounded-3xl overflow-hidden"
        style={{
          background: 'linear-gradient(160deg, #1c1c21 0%, #18181b 60%, #161619 100%)',
          boxShadow: '0 0 0 1px rgba(255,255,255,0.07), 0 32px 80px rgba(0,0,0,0.7), 0 0 120px rgba(96,165,250,0.04)',
        }}
      >
        {/* Top edge glow */}
        <div
          aria-hidden
          className="absolute inset-x-0 top-0 h-px"
          style={{ background: 'linear-gradient(90deg, transparent 5%, rgba(96,165,250,0.5) 35%, rgba(96,165,250,0.8) 50%, rgba(96,165,250,0.5) 65%, transparent 95%)' }}
        />

        {/* Ambient glow blob behind Max card */}
        <div
          aria-hidden
          className="pointer-events-none absolute"
          style={{
            top: '-40px',
            left: '50%',
            transform: 'translateX(-50%)',
            width: '340px',
            height: '220px',
            background: 'radial-gradient(ellipse at center, rgba(96,165,250,0.10) 0%, transparent 70%)',
          }}
        />

        <div className="relative px-7 pt-8 pb-7">
          {/* Header */}
          <div className="flex items-start justify-between mb-7">
            <div>
              <p className="text-[10px] font-semibold tracking-[0.18em] uppercase text-brand-mint/60 mb-2">
                Upgrade
              </p>
              <h2 className="text-2xl font-semibold tracking-tight text-brand-cloud">
                Choose your plan
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="flex items-center justify-center w-8 h-8 rounded-full border border-white/[0.08] text-brand-cloud/35 hover:text-brand-cloud/70 hover:border-white/15 hover:bg-white/[0.04] transition-all duration-150 text-sm mt-0.5"
            >
              ✕
            </button>
          </div>

          {/* Plan cards — pt-4 gives floating badge room above Max */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4">
            {TIER_ORDER.map((id, i) => {
              const tier = TIERS[id]
              const isMax = tier.recommended
              const isBusy = busy === id
              const anyBusy = busy !== null

              return (
                <div
                  key={id}
                  className={`${CARD_ANIM[i]} relative flex flex-col rounded-2xl p-5 transition-all duration-200`}
                  style={isMax ? {
                    background: 'linear-gradient(160deg, rgba(96,165,250,0.09) 0%, rgba(96,165,250,0.03) 60%, transparent 100%)',
                    boxShadow: '0 0 0 1px rgba(96,165,250,0.22), 0 4px 32px rgba(96,165,250,0.06)',
                  } : {
                    background: 'rgba(255,255,255,0.02)',
                    boxShadow: '0 0 0 1px rgba(255,255,255,0.07)',
                  }}
                >
                  {/* Badge floats above the card's top edge */}
                  {isMax && (
                    <span
                      className="absolute left-1/2 -translate-x-1/2 -translate-y-1/2 top-0 inline-flex items-center px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest whitespace-nowrap"
                      style={{
                        background: 'linear-gradient(135deg, rgba(96,165,250,0.30) 0%, rgba(96,165,250,0.18) 100%)',
                        boxShadow: '0 0 0 1px rgba(96,165,250,0.30)',
                        color: 'rgb(147 197 253)',
                      }}
                    >
                      Most popular
                    </span>
                  )}

                  <div>
                    {/* Plan name */}
                    <p className={`text-[10px] font-bold tracking-[0.15em] uppercase mb-3 ${isMax ? 'text-brand-mint/80' : 'text-brand-cloud/40'}`}>
                      {tier.label}
                    </p>

                    {/* Price */}
                    <div className="flex items-baseline gap-1 mb-1">
                      <span className={`text-3xl font-semibold tracking-tight ${isMax ? 'text-brand-cloud' : 'text-brand-cloud/80'}`}>
                        ${tier.price}
                      </span>
                      <span className="text-xs text-brand-cloud/35 font-normal">/mo</span>
                    </div>

                    {/* Divider */}
                    <div
                      className="my-4 h-px"
                      style={{ background: isMax ? 'rgba(96,165,250,0.18)' : 'rgba(255,255,255,0.07)' }}
                    />

                    {/* Features */}
                    <ul className="space-y-2 mb-5 flex-1">
                      <li className={`flex items-start gap-2 text-[11px] font-medium ${isMax ? 'text-brand-cloud/70' : 'text-brand-cloud/45'}`}>
                        <CheckIcon />
                        {tier.intro}
                      </li>
                      {tier.bullets.map(b => (
                        <li key={b} className={`flex items-start gap-2 text-[11px] ${isMax ? 'text-brand-cloud/65' : 'text-brand-cloud/40'}`}>
                          <CheckIcon />
                          {b}
                        </li>
                      ))}
                    </ul>

                    {/* CTA */}
                    <button
                      type="button"
                      onClick={() => select(id)}
                      disabled={anyBusy}
                      className="w-full rounded-xl py-2.5 text-sm font-semibold transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
                      style={isMax ? {
                        background: isBusy
                          ? 'rgba(96,165,250,0.5)'
                          : 'linear-gradient(135deg, #60a5fa 0%, #93c5fd 100%)',
                        color: '#18181b',
                        boxShadow: isBusy ? 'none' : '0 2px 16px rgba(96,165,250,0.25)',
                      } : {
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        color: 'rgb(var(--brand-cloud-rgb) / 0.75)',
                      }}
                    >
                      {isBusy ? 'Redirecting…' : 'Get started'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Footer */}
          <p className="mt-5 text-center text-[11px] text-brand-cloud/25 tracking-wide">
            Billed monthly · Cancel anytime · Stripe-secured checkout
          </p>

          {error && (
            <p className="mt-3 text-center text-xs text-red-400/90">{error}</p>
          )}
        </div>
      </div>
    </div>
  )

  return typeof document !== 'undefined' && document.body
    ? createPortal(modal, document.body)
    : modal
}
