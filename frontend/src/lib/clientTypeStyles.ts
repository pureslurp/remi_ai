import type { Project } from '../types'

export type ClientType = Project['client_type']

/** Canonical client_type string for styling (unknown values → buyer). */
export function normalizeClientType(clientType: string): ClientType {
  if (clientType === 'buyer' || clientType === 'seller' || clientType === 'buyer & seller') {
    return clientType
  }
  return 'buyer'
}

/** Left sidebar pill — keep in sync with `clientTypePanelLeftAccentClass`. */
export function clientTypeSidebarPillClass(clientType: string): string {
  const t = normalizeClientType(clientType)
  if (t === 'buyer') {
    return 'bg-brand-mint/10 text-brand-mint/90 border border-brand-mint/20'
  }
  if (t === 'seller') {
    return 'bg-amber-300/10 text-amber-200/90 border border-amber-300/20'
  }
  return 'bg-brand-cloud/10 text-brand-cloud/80 border border-brand-cloud/20'
}

/** Vertical accent between chat and client panel — same hue family as sidebar pill. */
export function clientTypePanelLeftAccentClass(clientType: string): string {
  const t = normalizeClientType(clientType)
  if (t === 'buyer') {
    return 'border-l-[3px] border-l-brand-mint/55'
  }
  if (t === 'seller') {
    return 'border-l-[3px] border-l-amber-300/60'
  }
  return 'border-l-[3px] border-l-brand-cloud/45'
}
