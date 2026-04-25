import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import * as api from '../api/client'
import type { AccountEntitlements } from '../types'

type Plan = 'pro' | 'max' | 'ultra'

const TIER_ORDER: Plan[] = ['pro', 'max', 'ultra']

const TIER_META: Record<Plan, { label: string; price: number; tokens: string }> = {
  pro: { label: 'Pro', price: 20, tokens: '2M' },
  max: { label: 'Max', price: 60, tokens: '6M' },
  ultra: { label: 'Ultra', price: 100, tokens: '10M' },
}

const TIER_RANK: Record<Plan, number> = { pro: 1, max: 2, ultra: 3 }

function fmt(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`
  return String(n)
}

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}

export default function ManageBillingModal({
  open,
  onClose,
  entitlements,
  onUpdated,
}: {
  open: boolean
  onClose: () => void
  entitlements: AccountEntitlements
  onUpdated: () => void
}) {
  const overlayRef = useRef<HTMLDivElement>(null)
  const [confirmCancel, setConfirmCancel] = useState(false)
  const [confirmPlan, setConfirmPlan] = useState<Plan | null>(null)
  const [busy, setBusy] = useState(false)
  const [portalBusy, setPortalBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setConfirmCancel(false)
    setConfirmPlan(null)
    setBusy(false)
    setError(null)
    setSuccessMsg(null)
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const currentPlan = entitlements.subscription_tier as Plan | 'free' | 'trial'
  const isPaidPlan = TIER_ORDER.includes(currentPlan as Plan)
  const currentRank = isPaidPlan ? TIER_RANK[currentPlan as Plan] : 0
  const cancelAtEnd = entitlements.subscription_cancel_at_period_end
  const periodEnd = entitlements.subscription_current_period_end

  const used = entitlements.pro_tokens_used
  const cap = entitlements.pro_included_tokens_per_month
  const usagePct = cap > 0 ? Math.min(100, Math.round((used / cap) * 100)) : 0

  const handlePlanClick = (plan: Plan) => {
    setError(null)
    setSuccessMsg(null)
    const targetRank = TIER_RANK[plan]
    if (targetRank < currentRank) {
      // Downgrade — show confirmation first
      setConfirmPlan(plan)
    } else {
      // Upgrade — proceed immediately
      doChangePlan(plan)
    }
  }

  const doChangePlan = async (plan: Plan) => {
    setBusy(true)
    setError(null)
    setConfirmPlan(null)
    try {
      await api.changePlan(plan)
      setSuccessMsg(`Switched to ${TIER_META[plan].label}. Your plan has been updated.`)
      onUpdated()
    } catch {
      setError('Could not change plan. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const doCancel = async () => {
    setBusy(true)
    setError(null)
    setConfirmCancel(false)
    try {
      await api.cancelSubscription()
      setSuccessMsg(`Subscription will cancel on ${fmtDate(periodEnd)}. You'll keep access until then.`)
      onUpdated()
    } catch {
      setError('Could not cancel subscription. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const doReactivate = async () => {
    setBusy(true)
    setError(null)
    try {
      await api.reactivateSubscription()
      setSuccessMsg('Subscription reactivated. Your plan will continue after the current period.')
      onUpdated()
    } catch {
      setError('Could not reactivate subscription. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const openPortal = async () => {
    setPortalBusy(true)
    try {
      const { url } = await api.createPortalSession()
      window.location.href = url
    } catch {
      setError('Could not open payment portal. Please try again.')
    } finally {
      setPortalBusy(false)
    }
  }

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === overlayRef.current) onClose()
  }

  const otherPlans = TIER_ORDER.filter(p => p !== currentPlan)

  const modal = (
    <div
      ref={overlayRef}
      className="modal-backdrop-in fixed inset-0 z-50 flex items-end justify-center sm:items-center bg-black/70 backdrop-blur-md px-4 pb-4 sm:pb-0"
      onClick={handleOverlayClick}
    >
      <div
        className="modal-panel-in relative w-full max-w-[560px] rounded-3xl overflow-hidden"
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

        <div className="relative px-7 pt-8 pb-7 space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <p className="text-[10px] font-semibold tracking-[0.18em] uppercase text-brand-mint/60 mb-1">
                Billing
              </p>
              <h2 className="text-xl font-semibold tracking-tight text-brand-cloud">
                Manage your subscription
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

          {/* Success / error banners */}
          {successMsg && (
            <div className="rounded-xl px-4 py-3 text-sm text-green-300 bg-green-900/20 border border-green-500/20">
              {successMsg}
            </div>
          )}
          {error && (
            <div className="rounded-xl px-4 py-3 text-sm text-red-400 bg-red-900/20 border border-red-500/20">
              {error}
            </div>
          )}

          {/* Pending cancellation banner */}
          {cancelAtEnd && !successMsg && (
            <div className="rounded-xl px-4 py-3 text-sm text-yellow-300 bg-yellow-900/20 border border-yellow-500/20">
              Your plan cancels on <span className="font-semibold">{fmtDate(periodEnd)}</span>. You'll be downgraded to Free after that date.
            </div>
          )}

          {/* Current plan summary */}
          {isPaidPlan && (
            <div
              className="rounded-2xl p-5"
              style={{
                background: 'rgba(255,255,255,0.03)',
                boxShadow: '0 0 0 1px rgba(255,255,255,0.08)',
              }}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-[10px] font-bold tracking-[0.15em] uppercase text-brand-mint/60 mb-1">Current plan</p>
                  <p className="text-lg font-semibold text-brand-cloud">
                    {TIER_META[currentPlan as Plan].label} — ${TIER_META[currentPlan as Plan].price}<span className="text-sm font-normal text-brand-cloud/40">/mo</span>
                  </p>
                </div>
                {periodEnd && (
                  <div className="text-right">
                    <p className="text-[10px] text-brand-cloud/40 uppercase tracking-wider mb-0.5">
                      {cancelAtEnd ? 'Cancels' : 'Renews'}
                    </p>
                    <p className="text-xs text-brand-cloud/70">{fmtDate(periodEnd)}</p>
                  </div>
                )}
              </div>

              {/* Usage bar */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-[11px] text-brand-cloud/50">Monthly usage</p>
                  <p className="text-[11px] text-brand-cloud/60">
                    {fmt(used)} / {fmt(cap)} units
                  </p>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.07)' }}>
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${usagePct}%`,
                      background: usagePct > 85
                        ? 'linear-gradient(90deg, #f87171, #ef4444)'
                        : 'linear-gradient(90deg, #60a5fa, #93c5fd)',
                    }}
                  />
                </div>
                <p className="text-[10px] text-brand-cloud/35 mt-1">{usagePct}% used this billing period</p>
              </div>
            </div>
          )}

          {/* Change plan section */}
          {isPaidPlan && otherPlans.length > 0 && !confirmCancel && !confirmPlan && (
            <div>
              <p className="text-[10px] font-semibold tracking-[0.15em] uppercase text-brand-cloud/40 mb-3">Change plan</p>
              <div className="grid grid-cols-2 gap-2.5">
                {otherPlans.map(plan => {
                  const meta = TIER_META[plan]
                  const isUpgrade = TIER_RANK[plan] > currentRank
                  return (
                    <button
                      key={plan}
                      type="button"
                      disabled={busy}
                      onClick={() => handlePlanClick(plan)}
                      className="group flex flex-col rounded-xl p-4 text-left transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed hover:ring-1"
                      style={{
                        background: 'rgba(255,255,255,0.02)',
                        boxShadow: '0 0 0 1px rgba(255,255,255,0.07)',
                      }}
                      onMouseEnter={e => {
                        (e.currentTarget as HTMLElement).style.boxShadow = '0 0 0 1px rgba(96,165,250,0.3)'
                      }}
                      onMouseLeave={e => {
                        (e.currentTarget as HTMLElement).style.boxShadow = '0 0 0 1px rgba(255,255,255,0.07)'
                      }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-[10px] font-bold tracking-[0.12em] uppercase text-brand-cloud/50">{meta.label}</p>
                        <span
                          className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                          style={isUpgrade
                            ? { background: 'rgba(96,165,250,0.15)', color: 'rgb(147 197 253)' }
                            : { background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.4)' }
                          }
                        >
                          {isUpgrade ? 'Upgrade' : 'Downgrade'}
                        </span>
                      </div>
                      <p className="text-xl font-semibold text-brand-cloud/90">
                        ${meta.price}<span className="text-xs font-normal text-brand-cloud/35">/mo</span>
                      </p>
                      <p className="text-[11px] text-brand-cloud/40 mt-1">{meta.tokens} units/month</p>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Downgrade confirmation */}
          {confirmPlan && (
            <div
              className="rounded-2xl p-5"
              style={{ background: 'rgba(255,255,255,0.02)', boxShadow: '0 0 0 1px rgba(255,255,255,0.08)' }}
            >
              <p className="text-sm text-brand-cloud/80 mb-4">
                Switch to <span className="font-semibold text-brand-cloud">{TIER_META[confirmPlan].label}</span>? Your monthly allowance will change to <span className="font-semibold text-brand-cloud">{TIER_META[confirmPlan].tokens} units</span>. Stripe will credit any unused time from your current plan.
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => doChangePlan(confirmPlan)}
                  className="flex-1 rounded-xl py-2.5 text-sm font-semibold transition-all disabled:opacity-40"
                  style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.8)' }}
                >
                  {busy ? 'Switching…' : `Switch to ${TIER_META[confirmPlan].label}`}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmPlan(null)}
                  className="px-4 rounded-xl py-2.5 text-sm text-brand-cloud/50 hover:text-brand-cloud/70 transition-all"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Cancel confirmation */}
          {confirmCancel && (
            <div
              className="rounded-2xl p-5"
              style={{ background: 'rgba(239,68,68,0.06)', boxShadow: '0 0 0 1px rgba(239,68,68,0.2)' }}
            >
              <p className="text-sm text-brand-cloud/80 mb-1">Are you sure you want to cancel?</p>
              <p className="text-xs text-brand-cloud/50 mb-4">
                You'll keep full access until <span className="font-semibold text-brand-cloud/70">{fmtDate(periodEnd)}</span>, then be downgraded to the Free plan.
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={doCancel}
                  className="flex-1 rounded-xl py-2.5 text-sm font-semibold transition-all disabled:opacity-40"
                  style={{ background: 'rgba(239,68,68,0.2)', border: '1px solid rgba(239,68,68,0.3)', color: 'rgb(252,165,165)' }}
                >
                  {busy ? 'Canceling…' : 'Yes, cancel subscription'}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmCancel(false)}
                  className="px-4 rounded-xl py-2.5 text-sm text-brand-cloud/50 hover:text-brand-cloud/70 transition-all"
                >
                  Keep plan
                </button>
              </div>
            </div>
          )}

          {/* Reactivate button */}
          {cancelAtEnd && !confirmCancel && !successMsg && (
            <button
              type="button"
              disabled={busy}
              onClick={doReactivate}
              className="w-full rounded-xl py-2.5 text-sm font-semibold transition-all duration-150 disabled:opacity-40"
              style={{
                background: 'linear-gradient(135deg, #60a5fa 0%, #93c5fd 100%)',
                color: '#18181b',
                boxShadow: '0 2px 16px rgba(96,165,250,0.25)',
              }}
            >
              {busy ? 'Reactivating…' : 'Reactivate subscription'}
            </button>
          )}

          {/* Footer: payment method + cancel link */}
          <div className="flex items-center justify-between pt-1 border-t border-white/[0.06]">
            <button
              type="button"
              disabled={portalBusy}
              onClick={openPortal}
              className="text-xs text-brand-cloud/40 hover:text-brand-cloud/70 transition-colors disabled:opacity-40"
            >
              {portalBusy ? 'Opening…' : 'Update payment method →'}
            </button>

            {isPaidPlan && !cancelAtEnd && !confirmCancel && !successMsg && (
              <button
                type="button"
                onClick={() => { setConfirmPlan(null); setConfirmCancel(true) }}
                className="text-xs text-red-400/50 hover:text-red-400/80 transition-colors"
              >
                Cancel subscription
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )

  return typeof document !== 'undefined' && document.body
    ? createPortal(modal, document.body)
    : modal
}
