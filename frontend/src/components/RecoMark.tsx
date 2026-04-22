/**
 * Reco “R” tile — same markup as the landing header mark. Use everywhere this
 * glyph should match (landing, legal headers, favicon paint source of truth).
 */
type RecoMarkVariant = 'landing' | 'legal'

const WRAP: Record<RecoMarkVariant, string> = {
  landing:
    'flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-gradient-to-br from-brand-navy to-brand-slate shadow-lg shadow-black/25',
  legal:
    'flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-gradient-to-br from-brand-navy to-brand-slate',
}

const LETTER: Record<RecoMarkVariant, string> = {
  landing: 'font-landing-display text-xl font-semibold tracking-tight text-brand-cloud',
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
      <span className={LETTER[variant]}>R</span>
    </div>
  )
}
