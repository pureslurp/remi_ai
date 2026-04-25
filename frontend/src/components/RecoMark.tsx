/**
 * reco-pilot “r.” tile — same markup as the landing header mark. Use everywhere this
 * glyph should match (landing, legal headers, favicon paint source of truth).
 */
type RecoMarkVariant = 'landing' | 'legal'

const WRAP: Record<RecoMarkVariant, string> = {
  landing:
    'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-gradient-to-br from-brand-navy to-brand-slate shadow-lg shadow-black/25 sm:h-11 sm:w-11 sm:rounded-xl',
  legal:
    'flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-gradient-to-br from-brand-navy to-brand-slate',
}

const LETTER: Record<RecoMarkVariant, string> = {
  landing: 'font-landing-display text-lg font-semibold tracking-tight text-brand-cloud sm:text-xl',
  legal: 'font-landing-display text-lg font-semibold tracking-tight text-brand-cloud',
}

type Props = {
  variant?: RecoMarkVariant
  className?: string
}

export function RecoMark({ variant = 'landing', className = '' }: Props) {
  const extra = className.trim()
  return (
    <div className={extra ? `${WRAP[variant]} ${extra}` : WRAP[variant]} aria-hidden>
      <span className={LETTER[variant]}>r.</span>
    </div>
  )
}
