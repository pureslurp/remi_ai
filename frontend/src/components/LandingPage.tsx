import { useGoogleOAuthRedirect } from '../hooks/useGoogleOAuthRedirect'
import LandingAppPreview from './LandingAppPreview'

type Props = {
  /** Reserved: server linked Google but this browser has not completed OAuth. */
  needsDeviceLink?: boolean
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

export default function LandingPage({ needsDeviceLink }: Props) {
  const { busy, error, startGoogleAuth } = useGoogleOAuthRedirect()

  const salesRaw = import.meta.env.VITE_SALES_EMAIL
  const salesEmail = typeof salesRaw === 'string' ? salesRaw.trim() : ''
  const enterpriseMailto = salesEmail
    ? `mailto:${salesEmail}?subject=${encodeURIComponent('Kova — Enterprise / brokerage')}`
    : null

  return (
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
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
          <div className="landing-rise flex items-center gap-3" style={{ animationDelay: '0ms' }}>
            <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-gradient-to-br from-brand-navy to-brand-slate shadow-lg shadow-black/25">
              <span className="font-landing-display text-xl font-semibold tracking-tight text-brand-cloud">K</span>
            </div>
            <span className="font-landing-display text-2xl font-semibold tracking-tight text-brand-cloud">Kova</span>
          </div>
          <nav className="landing-rise flex items-center gap-2 sm:gap-3" style={{ animationDelay: '60ms' }} aria-label="Account">
            <button
              type="button"
              onClick={startGoogleAuth}
              disabled={busy}
              aria-label="Sign in with Google"
              className="rounded-lg border border-white/15 px-3 py-2 text-sm font-medium text-brand-cloud/90 transition hover:bg-white/[0.06] disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={startGoogleAuth}
              disabled={busy}
              aria-label="Sign up with Google"
              className="rounded-lg bg-brand-cloud px-3 py-2 text-sm font-semibold text-brand-navy shadow-md shadow-black/20 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
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
              Kova gives each client their own memory. It answers from your email and synced documents, so you
              aren&apos;t explaining the deal from scratch every time you open a chat.
            </p>
            {error && (
              <div
                className="landing-rise mt-6 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-left text-sm text-red-100"
                style={{ animationDelay: '200ms' }}
                role="alert"
              >
                {error}
              </div>
            )}
            <div
              className="landing-rise mt-10 flex flex-col gap-3 sm:flex-row sm:items-center"
              style={{ animationDelay: '220ms' }}
            >
              <button
                type="button"
                onClick={startGoogleAuth}
                disabled={busy}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/[0.03] px-6 py-3.5 text-sm font-semibold text-brand-cloud backdrop-blur-sm transition hover:border-white/30 hover:bg-white/[0.06] disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
              >
                {busy ? (
                  <>
                    <span className="inline-block h-4 w-4 shrink-0 rounded-full border-2 border-white/25 border-t-brand-cloud motion-reduce:animate-none animate-spin" />
                    Connecting…
                  </>
                ) : (
                  <>
                    <GoogleMark className="h-5 w-5 shrink-0 text-brand-cloud/90" />
                    Sign in with Google
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={startGoogleAuth}
                disabled={busy}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-cloud px-6 py-3.5 text-sm font-semibold text-brand-navy shadow-lg shadow-black/25 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
              >
                <GoogleMark className="h-5 w-5 shrink-0" />
                Sign up with Google
              </button>
            </div>
            <p className="landing-rise mt-4 max-w-md text-xs leading-relaxed text-brand-cloud/45" style={{ animationDelay: '280ms' }}>
              New or returning, it&apos;s the same Google sign-in. Email and document sync are optional, and only needed if
              you want Kova to pull things in for you.
            </p>
          </div>

          <aside
            className="landing-rise relative rounded-2xl border border-white/[0.08] bg-black/25 p-6 shadow-2xl shadow-black/40 backdrop-blur-md sm:p-8"
            style={{ animationDelay: '180ms' }}
          >
            <div className="absolute -right-6 -top-6 hidden h-28 w-28 rounded-full border border-white/[0.06] lg:block" aria-hidden />
            <p className="font-landing-display text-lg font-medium italic text-brand-cloud/85">For agents with too many tabs open</p>
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
            Simple pricing
          </h2>
          <p className="mt-3 max-w-2xl text-brand-cloud/55">
            Start free, no credit card required. AI is included — no API keys to manage.
          </p>
          <ul className="mt-10 grid gap-6 lg:grid-cols-3">
            <li className="flex flex-col rounded-2xl border border-white/[0.08] bg-white/[0.02] p-7">
              <h3 className="font-landing-display text-2xl font-semibold text-brand-cloud">Free</h3>
              <p className="mt-1 text-3xl font-semibold tracking-tight text-brand-cloud">$0</p>
              <p className="mt-1 text-xs text-brand-cloud/40">14-day trial, no card needed</p>
              <ul className="mt-6 flex-1 space-y-2 text-sm text-brand-cloud/55">
                <li>Limited AI usage</li>
                <li>Standard AI models</li>
                <li>1 active client workspace</li>
                <li>All features unlocked</li>
              </ul>
              <button
                type="button"
                onClick={startGoogleAuth}
                disabled={busy}
                className="mt-8 w-full rounded-xl border border-white/15 py-3 text-sm font-semibold text-brand-cloud transition hover:bg-white/[0.06] disabled:opacity-50"
              >
                Start for free
              </button>
            </li>
            <li className="relative flex flex-col rounded-2xl border border-brand-mint/35 bg-gradient-to-b from-brand-mint/10 to-transparent p-7 shadow-lg shadow-brand-mint/5 ring-1 ring-brand-mint/20">
              <span className="absolute right-5 top-5 rounded-full bg-brand-mint/20 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-brand-mint">
                Most popular
              </span>
              <h3 className="font-landing-display text-2xl font-semibold text-brand-cloud">Pro</h3>
              <p className="mt-1 text-3xl font-semibold tracking-tight text-brand-cloud">
                $20<span className="text-base font-normal text-brand-cloud/50">/mo</span>
              </p>
              <p className="mt-1 text-xs text-brand-cloud/40">Billed monthly, cancel anytime</p>
              <ul className="mt-6 flex-1 space-y-2 text-sm text-brand-cloud/70">
                <li>Everything in Free, plus:</li>
                <li>4× more AI usage</li>
                <li>Advanced AI models</li>
                <li>Unlimited clients</li>
              </ul>
              <button
                type="button"
                onClick={startGoogleAuth}
                disabled={busy}
                className="mt-8 w-full rounded-xl bg-brand-cloud py-3 text-sm font-semibold text-brand-navy shadow-md transition hover:bg-white disabled:opacity-50"
              >
                Get started
              </button>
            </li>
            <li className="flex flex-col rounded-2xl border border-white/[0.08] bg-white/[0.02] p-7">
              <h3 className="font-landing-display text-2xl font-semibold text-brand-cloud">Enterprise</h3>
              <p className="mt-1 text-lg text-brand-cloud/60">Brokerage-wide</p>
              <ul className="mt-6 flex-1 space-y-2 text-sm text-brand-cloud/55">
                <li>Volume pricing, security review, and onboarding for your firm</li>
                <li>Custom token limits and terms</li>
                <li>Dedicated rollout support</li>
              </ul>
              {enterpriseMailto ? (
                <a
                  href={enterpriseMailto}
                  className="mt-8 inline-flex w-full items-center justify-center rounded-xl border border-white/15 py-3 text-sm font-semibold text-brand-cloud transition hover:bg-white/[0.06]"
                >
                  Contact sales
                </a>
              ) : (
                <p className="mt-8 rounded-xl border border-dashed border-white/15 py-3 text-center text-xs text-brand-cloud/45">
                  Set <code className="text-brand-mint/90">VITE_SALES_EMAIL</code> for the contact button.
                </p>
              )}
            </li>
          </ul>
        </section>
      </main>

      <footer className="relative border-t border-white/[0.06] px-5 py-10 sm:px-8">
        <div className="mx-auto max-w-6xl text-center text-xs leading-relaxed text-brand-cloud/40">
          <p>
            Email and document sync are optional and only bring in what you choose. Kova is not affiliated with Google,
            Anthropic, OpenAI, or Google DeepMind.
          </p>
          <p className="mt-3 font-landing-display text-sm text-brand-cloud/50">Kova</p>
        </div>
      </footer>
    </div>
  )
}
