import { useEffect, useRef, useState } from 'react'
import * as api from '../api/client'
import { useGoogleOAuthRedirect } from '../hooks/useGoogleOAuthRedirect'
import LandingAppPreview from './LandingAppPreview'
import { RecoMark } from './RecoMark'

type Props = {
  /** Reserved: server linked Google but this browser has not completed OAuth. */
  needsDeviceLink?: boolean
  /** Called after successful email signup/login to re-bootstrap the app. */
  onEmailAuth?: () => void
}

function GoogleMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden>
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
  )
}

// ---------------------------------------------------------------------------
// Auth modal
// ---------------------------------------------------------------------------

type Plan = 'free' | 'pro' | 'max' | 'ultra'

function isConsumerGmailAddress(email: string): boolean {
  const d = email.trim().toLowerCase().split('@').pop()
  return d === 'gmail.com' || d === 'googlemail.com'
}

const PLAN_OPTIONS: { id: Plan; label: string; price: string }[] = [
  { id: 'free', label: 'Free', price: '$0' },
  { id: 'pro', label: 'Pro', price: '$20/mo' },
  { id: 'max', label: 'Max', price: '$60/mo' },
  { id: 'ultra', label: 'Ultra', price: '$100/mo' },
]

type AuthModalProps = {
  mode: 'signup' | 'signin'
  initialPlan?: Plan
  onClose: () => void
  onModeChange: (m: 'signup' | 'signin') => void
  onEmailAuth?: () => void
}

function AuthModal({ mode, initialPlan = 'free', onClose, onModeChange, onEmailAuth }: AuthModalProps) {
  const { busy: googleBusy, startGoogleAuth } = useGoogleOAuthRedirect()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [selectedPlan, setSelectedPlan] = useState<Plan>(initialPlan)
  const [emailBusy, setEmailBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const overlayRef = useRef<HTMLDivElement>(null)
  const firstInputRef = useRef<HTMLInputElement>(null)

  // Sync plan if parent changes initialPlan (e.g. user clicks different pricing CTA while modal is open)
  useEffect(() => { setSelectedPlan(initialPlan) }, [initialPlan])

  const busy = googleBusy || emailBusy

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  // Focus first input on open
  useEffect(() => {
    setTimeout(() => firstInputRef.current?.focus(), 50)
  }, [mode])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (isConsumerGmailAddress(email)) {
      setError(
        'Gmail addresses must use Continue with Google. Email and password are not available for @gmail.com.',
      )
      return
    }
    setEmailBusy(true)
    try {
      if (mode === 'signup') {
        await api.signup({ email, password, name: name || undefined })
        // If a paid plan was chosen, redirect to Stripe Checkout immediately after account creation
        if (selectedPlan !== 'free') {
          const { url } = await api.createCheckoutSession(selectedPlan as 'pro' | 'max' | 'ultra')
          window.location.href = url
          return // don't call onEmailAuth — Stripe will redirect back
        }
      } else {
        await api.login({ email, password })
      }
      onEmailAuth?.()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      try {
        const parsed = JSON.parse(msg.slice(msg.indexOf(':') + 1).trim())
        setError(parsed.detail || msg)
      } catch {
        setError(msg)
      }
    } finally {
      setEmailBusy(false)
    }
  }

  const handleGoogleAuth = () => {
    // If signing up with a paid plan, save it so we can redirect to checkout after OAuth completes
    if (mode === 'signup' && selectedPlan !== 'free') {
      sessionStorage.setItem('pendingPlan', selectedPlan)
    }
    startGoogleAuth()
  }

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-[200] flex items-center justify-center p-4"
      onClick={e => { if (e.target === overlayRef.current) onClose() }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" aria-hidden />

      {/* Panel */}
      <div className="relative w-full max-w-sm rounded-2xl border border-white/10 bg-gradient-to-b from-[#1c1f2e] to-[#16181f] p-7 shadow-2xl shadow-black/60">
        {/* Close */}
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-1.5 text-brand-cloud/40 hover:text-brand-cloud/80 transition"
          aria-label="Close"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <h2 id="auth-modal-title" className="font-landing-display text-xl font-semibold text-brand-cloud">
          {mode === 'signup' ? 'Create your account' : 'Welcome back'}
        </h2>
        <p className="mt-1 text-sm text-brand-cloud/50">
          {mode === 'signup' ? 'Start for free — no credit card required.' : 'Sign in to your reco-pilot workspace.'}
        </p>

        {/* Plan selector — signup only */}
        {mode === 'signup' && (
          <div className="mt-5">
            <p className="mb-2 text-xs font-medium text-brand-cloud/50 uppercase tracking-wider">Plan</p>
            <div className="grid grid-cols-4 gap-1 rounded-xl border border-white/10 bg-black/25 p-1">
              {PLAN_OPTIONS.map(plan => {
                const sel = selectedPlan === plan.id
                return (
                  <button
                    key={plan.id}
                    type="button"
                    onClick={() => setSelectedPlan(plan.id)}
                    className={`flex flex-col items-center rounded-lg px-1 py-2 text-center transition ${
                      sel
                        ? 'bg-white/[0.12] text-brand-cloud shadow-sm ring-1 ring-white/15'
                        : 'text-brand-cloud/50 hover:bg-white/[0.05] hover:text-brand-cloud/80'
                    }`}
                  >
                    <span className="text-xs font-semibold">{plan.label}</span>
                    <span className={`text-[10px] mt-0.5 ${sel ? 'text-brand-mint/80' : 'text-brand-cloud/35'}`}>{plan.price}</span>
                  </button>
                )
              })}
            </div>
            {selectedPlan !== 'free' && (
              <p className="mt-1.5 text-[11px] text-brand-cloud/40">
                You&apos;ll set up billing after your account is created.
              </p>
            )}
          </div>
        )}

        {/* Google — recommended */}
        <button
          type="button"
          onClick={handleGoogleAuth}
          disabled={busy}
          className="mt-5 w-full inline-flex items-center justify-center gap-2.5 rounded-xl bg-white/[0.07] border border-white/15 px-4 py-3 text-sm font-semibold text-brand-cloud transition hover:bg-white/[0.12] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {googleBusy ? (
            <>
              <span className="inline-block h-4 w-4 shrink-0 rounded-full border-2 border-white/25 border-t-brand-cloud animate-spin" />
              Connecting...
            </>
          ) : (
            <>
              <GoogleMark className="h-5 w-5 shrink-0" />
              Continue with Google
            </>
          )}
        </button>
        <p className="mt-1.5 text-center text-[11px] text-brand-mint/60">
          Recommended — enables Gmail and Drive sync
        </p>

        {/* Divider */}
        <div className="my-5 flex items-center gap-3">
          <div className="h-px flex-1 bg-white/10" />
          <span className="text-xs text-brand-cloud/35">or continue with email</span>
          <div className="h-px flex-1 bg-white/10" />
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-100" role="alert">
            {error}
          </div>
        )}

        {/* Email form */}
        <form onSubmit={handleSubmit} className="space-y-3">
          {mode === 'signup' && (
            <input
              ref={firstInputRef}
              type="text"
              placeholder="Name (optional)"
              value={name}
              onChange={e => setName(e.target.value)}
              disabled={busy}
              className="w-full rounded-xl border border-white/12 bg-white/[0.04] px-4 py-2.5 text-sm text-brand-cloud placeholder:text-brand-cloud/30 outline-none focus:border-white/25 focus:bg-white/[0.07] transition disabled:opacity-50"
            />
          )}
          <input
            ref={mode === 'signin' ? firstInputRef : undefined}
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            disabled={busy}
            className="w-full rounded-xl border border-white/12 bg-white/[0.04] px-4 py-2.5 text-sm text-brand-cloud placeholder:text-brand-cloud/30 outline-none focus:border-white/25 focus:bg-white/[0.07] transition disabled:opacity-50"
          />
          {isConsumerGmailAddress(email) && (
            <p className="text-xs leading-relaxed text-brand-mint/75">
              Use <strong className="text-brand-mint">Continue with Google</strong> for @gmail.com — email and password
              sign-in is not available for consumer Gmail.
            </p>
          )}
          <input
            type="password"
            placeholder="Password (8+ characters)"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            minLength={8}
            disabled={busy}
            className="w-full rounded-xl border border-white/12 bg-white/[0.04] px-4 py-2.5 text-sm text-brand-cloud placeholder:text-brand-cloud/30 outline-none focus:border-white/25 focus:bg-white/[0.07] transition disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-xl bg-brand-cloud py-2.5 text-sm font-semibold text-brand-navy shadow-md transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {emailBusy ? 'Please wait...' : mode === 'signup' ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-brand-cloud/40">
          {mode === 'signup' ? (
            <>Already have an account?{' '}
              <button type="button" onClick={() => onModeChange('signin')} className="text-brand-mint/80 hover:text-brand-mint transition">
                Sign in
              </button>
            </>
          ) : (
            <>Need an account?{' '}
              <button type="button" onClick={() => onModeChange('signup')} className="text-brand-mint/80 hover:text-brand-mint transition">
                Sign up free
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  )
}

const FEATURES = [
  {
    title: 'Client workspaces',
    body: 'A space per client. Profile, role (buyer, seller, or both), and notes the assistant actually hangs onto between sessions.',
  },
  {
    title: 'Context-aware chat',
    body: 'Answers come from this client\u2019s file only. Not a generic chatbot thread with no memory of what you\u2019re working on.',
  },
  {
    title: 'Deals & key dates',
    body: 'Offers, status, contingencies, and deadlines in one spot, so nothing slips between email and closing.',
  },
  {
    title: 'Email in the loop',
    body: 'Threads that involve the client\u2019s address sync in. Negotiations and lender back-and-forth are there when you ask.',
  },
  {
    title: 'Documents & folders',
    body: 'Sync a folder from cloud storage, or drop in a PDF, DOCX, or TXT. Chat reads them alongside everything else for that client.',
  },
  {
    title: 'Negotiation & drafting',
    body: 'Help with counters, addenda, and inspection or financing timelines, tied to the actual deal in front of you.',
  },
] as const

type IndividualTierId = 'pro' | 'max' | 'ultra'

const INDIVIDUAL_TIERS: Record<
  IndividualTierId,
  {
    label: string
    price: number
    bullets: readonly string[]
    intro: string
    ctaVariant: 'solid' | 'outline'
    recommended?: boolean
  }
> = {
  pro: {
    label: 'Pro',
    price: 20,
    intro: 'Everything in Free, plus:',
    bullets: ['4× more AI usage than Free', 'Advanced AI models', 'Unlimited clients'],
    ctaVariant: 'outline',
  },
  max: {
    label: 'Max',
    price: 60,
    intro: 'Everything in Pro, plus:',
    bullets: ['3× more AI usage than Pro', 'Frontier models where available', 'Best fit for daily deal volume'],
    ctaVariant: 'solid',
    recommended: true,
  },
  ultra: {
    label: 'Ultra',
    price: 100,
    intro: 'Everything in Max, plus:',
    bullets: ['Highest included AI usage', 'Priority access to new capabilities', 'For power users across many clients'],
    ctaVariant: 'outline',
  },
}

const INDIVIDUAL_TIER_ORDER: IndividualTierId[] = ['pro', 'max', 'ultra']

export default function LandingPage({ needsDeviceLink, onEmailAuth }: Props) {
  const [authModal, setAuthModal] = useState<'signup' | 'signin' | null>(null)
  const [signupPlan, setSignupPlan] = useState<Plan>('free')
  const [individualTier, setIndividualTier] = useState<IndividualTierId>('max')

  const openSignup = (plan: Plan = 'free') => { setSignupPlan(plan); setAuthModal('signup') }
  const openSignin = () => setAuthModal('signin')
  const closeModal = () => setAuthModal(null)

  const salesRaw = import.meta.env.VITE_SALES_EMAIL
  const salesEmail = typeof salesRaw === 'string' ? salesRaw.trim() : ''
  const brokerageMailto = salesEmail
    ? `mailto:${salesEmail}?subject=${encodeURIComponent('reco-pilot — Brokerage inquiry')}`
    : null

  return (
    <>
    {authModal && (
      <AuthModal
        mode={authModal}
        initialPlan={signupPlan}
        onClose={closeModal}
        onModeChange={setAuthModal}
        onEmailAuth={() => { closeModal(); onEmailAuth?.() }}
      />
    )}
    <div
      className="fixed inset-0 z-[100] overflow-y-auto overflow-x-hidden font-landing-sans text-brand-cloud/90 antialiased"
      style={{
        background: `
          radial-gradient(900px 520px at 88% 8%, rgb(var(--page-glow-rgb) / 0.09), transparent 55%),
          radial-gradient(700px 480px at 0% 100%, rgb(var(--page-glow-rgb) / 0.05), transparent 50%),
          linear-gradient(165deg, var(--page-bg-a) 0%, var(--page-bg-b) 45%, #1c1917 100%)
        `,
      }}
    >
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.035]"
        aria-hidden
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
        }}
      />

      <header className="sticky top-0 z-[110] border-b border-white/[0.06] bg-[rgb(24_24_27_/0.82)] backdrop-blur-lg backdrop-saturate-150">
        <div className="mx-auto flex min-h-[3.25rem] max-w-6xl items-center justify-between gap-2 px-3 py-2.5 sm:min-h-0 sm:gap-4 sm:px-8 sm:py-4">
          <div
            className="landing-rise flex min-w-0 items-center gap-2 sm:gap-3"
            style={{ animationDelay: '0ms' }}
          >
            <RecoMark variant="landing" />
            <span className="font-wordmark whitespace-nowrap text-lg font-semibold tracking-[0.06em] text-brand-cloud sm:text-xl sm:tracking-[0.07em] md:text-2xl">
              reco-pilot
            </span>
          </div>
          <nav
            className="landing-rise flex shrink-0 items-center gap-1.5 sm:gap-3"
            style={{ animationDelay: '60ms' }}
            aria-label="Account"
          >
            <button
              type="button"
              onClick={openSignin}
              className="whitespace-nowrap rounded-lg border border-white/15 px-2.5 py-1.5 text-xs font-medium text-brand-cloud/90 transition hover:bg-white/[0.06] sm:px-3 sm:py-2 sm:text-sm"
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => openSignup()}
              className="whitespace-nowrap rounded-lg bg-brand-cloud px-2.5 py-1.5 text-xs font-semibold text-brand-navy shadow-md shadow-black/20 transition hover:bg-white sm:px-3 sm:py-2 sm:text-sm"
            >
              Sign up
            </button>
          </nav>
        </div>
      </header>

      <main className="relative mx-auto max-w-6xl px-5 pb-20 pt-12 sm:px-8 sm:pt-16">
        {needsDeviceLink && (
          <div
            className="landing-rise mb-10 rounded-xl border border-amber-400/25 bg-amber-500/[0.08] px-4 py-3 text-sm text-amber-100/95"
            style={{ animationDelay: '0ms' }}
            role="status"
          >
            This workspace is linked to Google on the server, but <strong className="text-brand-cloud">this browser</strong> hasn&apos;t
            finished sign-in yet. Use Sign up or Sign in below to finish with Google once.
          </div>
        )}

        <section className="grid gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:items-start" aria-labelledby="hero-heading">
          <div>
            <p
              className="landing-rise mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-brand-mint/90"
              style={{ animationDelay: '40ms' }}
            >
              Real estate copilot
            </p>
            <h1
              id="hero-heading"
              className="landing-rise font-landing-display text-4xl font-semibold leading-[1.08] tracking-tight text-brand-cloud sm:text-5xl lg:text-[3.25rem]"
              style={{ animationDelay: '100ms' }}
            >
              Every deal gets its own room.
            </h1>
            <p
              className="landing-rise mt-6 max-w-xl text-base leading-relaxed text-brand-cloud/65 sm:text-lg"
              style={{ animationDelay: '160ms' }}
            >
              reco-pilot gives each client their own memory. It answers from your email and synced documents, so you
              aren&apos;t explaining the deal from scratch every time you open a chat.
            </p>
            <div
              className="landing-rise mt-10 flex flex-col gap-3 sm:flex-row sm:items-center"
              style={{ animationDelay: '220ms' }}
            >
              <button
                type="button"
                onClick={() => openSignup()}
                className="inline-flex items-center justify-center rounded-xl bg-brand-cloud px-6 py-3.5 text-sm font-semibold text-brand-navy shadow-lg shadow-black/25 transition hover:bg-white motion-reduce:transition-none"
              >
                Get started free
              </button>
              <a
                href="#pricing-heading"
                className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-white/15 px-6 py-3.5 text-sm font-medium text-brand-cloud/80 transition hover:border-white/25 hover:text-brand-cloud motion-reduce:transition-none"
              >
                See plans
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </a>
            </div>
            <p className="landing-rise mt-4 text-xs text-brand-cloud/40" style={{ animationDelay: '280ms' }}>
              Free plan available · No credit card required
            </p>
          </div>

          <aside
            className="landing-rise relative rounded-2xl border border-white/[0.08] bg-black/25 p-6 shadow-2xl shadow-black/40 backdrop-blur-md sm:p-8"
            style={{ animationDelay: '180ms' }}
          >
            <div className="absolute -right-6 -top-6 hidden h-28 w-28 rounded-full border border-white/[0.06] lg:block" aria-hidden />
            <p className="font-landing-display text-lg font-medium italic text-brand-cloud/85">
              For agents who want to get the most out of AI
            </p>
            <ul className="mt-6 space-y-4 text-sm leading-relaxed text-brand-cloud/60">
              <li className="flex gap-3">
                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-mint/80" aria-hidden />
                Stop re-explaining each client every time you open a new chat.
              </li>
              <li className="flex gap-3">
                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-mint/80" aria-hidden />
                Offers, amendments, and email threads stay attached to the deal they came from.
              </li>
              <li className="flex gap-3">
                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-mint/80" aria-hidden />
                Counter, addendum, and inspection questions get answered from the actual file, not a guess.
              </li>
            </ul>
          </aside>
        </section>

        <section
          className="landing-rise mt-16 border-y border-white/[0.06] bg-white/[0.02] py-10 sm:mt-20 sm:py-12"
          style={{ animationDelay: '260ms' }}
          aria-label="Why AI literacy matters for agents"
        >
          <blockquote className="mx-auto max-w-3xl space-y-0.5 px-1 text-center sm:space-y-1">
            <p className="font-landing-sans text-lg font-medium leading-snug text-brand-cloud/85 sm:text-xl md:text-2xl md:leading-snug">
              AI won&apos;t replace real estate agents,
            </p>
            <p className="font-landing-sans text-lg font-medium leading-snug text-brand-cloud/85 sm:text-xl md:text-2xl md:leading-snug">
              it will replace agents who don&apos;t learn to use it.
            </p>
          </blockquote>
        </section>

        <section className="mt-24 sm:mt-28" aria-labelledby="features-heading">
          <div className="mb-10 max-w-2xl">
            <h2 id="features-heading" className="font-landing-display text-3xl font-semibold tracking-tight text-brand-cloud sm:text-4xl">
              Everything tied to the client
            </h2>
            <p className="mt-3 text-brand-cloud/55">Fewer tabs. Less searching for what you already have.</p>
          </div>
          <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(f => (
              <li
                key={f.title}
                className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-6 transition hover:border-white/12 hover:bg-white/[0.04] motion-reduce:transition-none"
              >
                <h3 className="font-landing-display text-xl font-semibold text-brand-cloud">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-brand-cloud/55">{f.body}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="mt-24 sm:mt-28" aria-labelledby="preview-heading">
          <LandingAppPreview />
        </section>

        <section className="mt-24 sm:mt-28" aria-labelledby="pricing-heading">
          <h2 id="pricing-heading" className="font-landing-display text-3xl font-semibold tracking-tight text-brand-cloud sm:text-4xl">
            Pricing
          </h2>
          <p className="mt-3 max-w-2xl text-brand-cloud/55">
            Start free, no credit card required. AI is included — no API keys to manage.
          </p>

          <div className="mt-10 grid gap-6 lg:grid-cols-3">
            <article className="flex flex-col rounded-2xl border border-white/[0.08] bg-white/[0.02] p-7">
              <h3 className="font-landing-display text-2xl font-semibold text-brand-cloud">Free</h3>
              <p className="mt-1 text-3xl font-semibold tracking-tight text-brand-cloud">$0</p>
              <p className="mt-1 text-xs text-brand-cloud/40">No credit card needed</p>
              <ul className="mt-6 flex-1 space-y-2 text-sm text-brand-cloud/55">
                <li>Limited AI usage</li>
                <li>Standard AI models</li>
                <li>1 active client workspace</li>
                <li>All features unlocked</li>
              </ul>
              <button
                type="button"
                onClick={() => openSignup('free')}
                className="mt-8 w-full rounded-xl border border-white/15 py-3 text-sm font-semibold text-brand-cloud transition hover:bg-white/[0.06]"
              >
                Start for free
              </button>
            </article>

            <article
              className={`relative flex flex-col rounded-2xl p-7 transition-colors motion-reduce:transition-none ${
                individualTier === 'max'
                  ? 'border border-brand-mint/35 bg-gradient-to-b from-brand-mint/10 to-transparent shadow-lg shadow-brand-mint/5 ring-1 ring-brand-mint/20'
                  : 'border border-white/[0.08] bg-white/[0.02]'
              }`}
              aria-labelledby="individual-plans-heading"
            >
              {INDIVIDUAL_TIERS[individualTier].recommended && (
                <span className="absolute right-5 top-5 rounded-full bg-brand-mint/20 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-brand-mint">
                  Most popular
                </span>
              )}
              <h3
                id="individual-plans-heading"
                className="font-landing-display text-2xl font-semibold text-brand-cloud pr-24 sm:pr-28"
              >
                Individual
              </h3>

              <div
                className="mt-5 rounded-xl border border-white/12 bg-black/25 p-1"
                role="tablist"
                aria-label="Individual plan tier"
              >
                <div className="grid grid-cols-3 gap-1">
                  {INDIVIDUAL_TIER_ORDER.map(id => {
                    const sel = individualTier === id
                    return (
                      <button
                        key={id}
                        type="button"
                        role="tab"
                        aria-selected={sel}
                        id={`individual-tab-${id}`}
                        aria-controls="individual-plan-panel"
                        onClick={() => setIndividualTier(id)}
                        className={`rounded-lg px-2 py-2 text-center text-xs font-semibold transition sm:text-sm ${
                          sel
                            ? 'bg-white/[0.12] text-brand-cloud shadow-sm ring-1 ring-white/15'
                            : 'text-brand-cloud/55 hover:bg-white/[0.05] hover:text-brand-cloud/85'
                        }`}
                      >
                        {INDIVIDUAL_TIERS[id].label}
                      </button>
                    )
                  })}
                </div>
              </div>

              <div
                id="individual-plan-panel"
                role="tabpanel"
                aria-labelledby={`individual-tab-${individualTier}`}
                className="mt-5 flex min-h-[14rem] flex-col"
              >
                <p className="font-landing-display text-xl font-semibold text-brand-cloud sm:text-2xl">
                  {INDIVIDUAL_TIERS[individualTier].label}
                </p>
                <p className="mt-1 text-3xl font-semibold tracking-tight text-brand-cloud">
                  ${INDIVIDUAL_TIERS[individualTier].price}
                  <span className="text-base font-normal text-brand-cloud/50">/mo</span>
                </p>
                <p className="mt-1 text-xs text-brand-cloud/40">Billed monthly, cancel anytime</p>
                <ul className="mt-5 flex-1 space-y-2 text-sm text-brand-cloud/70">
                  <li>{INDIVIDUAL_TIERS[individualTier].intro}</li>
                  {INDIVIDUAL_TIERS[individualTier].bullets.map(line => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
                {INDIVIDUAL_TIERS[individualTier].ctaVariant === 'solid' ? (
                  <button
                    type="button"
                    onClick={() => openSignup(individualTier)}
                    className="mt-8 w-full rounded-xl bg-brand-cloud py-3 text-sm font-semibold text-brand-navy shadow-md transition hover:bg-white"
                  >
                    Get started
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => openSignup(individualTier)}
                    className="mt-8 w-full rounded-xl border border-white/15 py-3 text-sm font-semibold text-brand-cloud transition hover:bg-white/[0.06]"
                  >
                    Get started
                  </button>
                )}
              </div>
            </article>

            <article className="flex flex-col rounded-2xl border border-white/[0.08] bg-white/[0.02] p-7">
              <h3 className="font-landing-display text-2xl font-semibold text-brand-cloud">Brokerage</h3>
              <p className="mt-1 text-lg text-brand-cloud/60">Brokerage-wide</p>
              <ul className="mt-6 flex-1 space-y-2 text-sm text-brand-cloud/55">
                <li>Volume pricing, security review, and onboarding for your firm</li>
                <li>Custom token limits and terms</li>
                <li>Dedicated rollout support</li>
              </ul>
              {brokerageMailto ? (
                <a
                  href={brokerageMailto}
                  className="mt-8 inline-flex w-full items-center justify-center rounded-xl border border-white/15 py-3 text-sm font-semibold text-brand-cloud transition hover:bg-white/[0.06]"
                >
                  Contact sales
                </a>
              ) : (
                <p className="mt-8 rounded-xl border border-dashed border-white/15 py-3 text-center text-xs text-brand-cloud/45">
                  Set <code className="text-brand-mint/90">VITE_SALES_EMAIL</code> for the contact button.
                </p>
              )}
            </article>
          </div>
        </section>
      </main>

      <footer className="relative border-t border-white/[0.06] px-5 py-10 sm:px-8">
        <div className="mx-auto max-w-6xl text-center text-xs leading-relaxed text-brand-cloud/40">
          <p>
            Email and document sync are optional and only bring in what you choose. reco-pilot is not affiliated with Google,
            Anthropic, OpenAI, or Google DeepMind.
          </p>
          <p className="mt-3 font-wordmark text-sm font-medium tracking-[0.1em] text-brand-cloud/50">reco-pilot</p>
          <p className="mt-2 flex items-center justify-center gap-4">
            <a href="/privacy" className="hover:text-brand-cloud/70 transition">Privacy Policy</a>
            <span aria-hidden>·</span>
            <a href="/terms" className="hover:text-brand-cloud/70 transition">Terms of Service</a>
          </p>
        </div>
      </footer>
    </div>
    </>
  )
}
