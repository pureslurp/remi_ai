import type { Project } from '../types'

export type ClientType = Project['client_type']

export interface ClientPanelCopy {
  transactionsSectionTitle: string
  transactionsSubtitle: string
  agentNotesPlaceholder: string
  newPropertyAddressPlaceholder: string
  newOfferPricePlaceholder: string
  emptyActiveTransactions: string
  propertyContextLabel: string
  transactionNotesPlaceholder: string
  multiOfferSameListingHint: string
  panelAccentClass: string
}

const buyer: ClientPanelCopy = {
  transactionsSectionTitle: 'Properties & offers',
  transactionsSubtitle:
    'Each row is a home they are considering or under contract on — add one per property or deal.',
  agentNotesPlaceholder:
    'Agent notes (pre-approval, budget, neighborhoods, must-haves, lender…)',
  newPropertyAddressPlaceholder: 'Property address they are pursuing',
  newOfferPricePlaceholder: 'Their offer price (e.g. 415000)',
  emptyActiveTransactions: 'No active deals yet. Add a property when they start looking or go under contract.',
  propertyContextLabel: 'Property',
  transactionNotesPlaceholder:
    'Offer history, counters, inspection, appraisal, lender conditions — anything specific to this purchase…',
  multiOfferSameListingHint: '', // not used for buyers
  panelAccentClass: 'border-l-[3px] border-l-blue-500/70',
}

const seller: ClientPanelCopy = {
  transactionsSectionTitle: 'Listing & offers',
  transactionsSubtitle:
    'Each row is an offer or contract on their listing — reuse the same address when comparing multiple buyers.',
  agentNotesPlaceholder:
    'Agent notes (list price, disclosure status, timeline, staging, preferred close…)',
  newPropertyAddressPlaceholder: 'Listing address (same for each competing offer)',
  newOfferPricePlaceholder: 'Buyer’s offer amount (e.g. 415000)',
  emptyActiveTransactions:
    'No active offers yet. Add a row per buyer or per contract on their home.',
  propertyContextLabel: 'Listing',
  transactionNotesPlaceholder:
    'Compare to other offers: contingencies, concessions, close date, buyer strength…',
  multiOfferSameListingHint: 'Multiple offers on the same listing — compare below.',
  panelAccentClass: 'border-l-[3px] border-l-emerald-500/70',
}

const buyerSeller: ClientPanelCopy = {
  transactionsSectionTitle: 'Buying & selling',
  transactionsSubtitle:
    'Track purchase deals and their sale in one list — use the address and notes to tell buying vs selling apart.',
  agentNotesPlaceholder:
    'Agent notes (bridge timing, contingent sale, both closings, lender on buy side…)',
  newPropertyAddressPlaceholder: 'Property address (purchase target or listing)',
  newOfferPricePlaceholder: 'Offer / list context price (e.g. 415000)',
  emptyActiveTransactions:
    'No active transactions. Add rows for homes they are buying and for offers on the home they are selling.',
  propertyContextLabel: 'Property',
  transactionNotesPlaceholder:
    'Deal-specific notes — whether this row is their purchase, their sale, or an offer they received…',
  multiOfferSameListingHint: 'Multiple rows on the same address — confirm whether each is buy-side or sell-side in notes.',
  panelAccentClass: 'border-l-[3px] border-l-purple-500/70',
}

const byType: Record<ClientType, ClientPanelCopy> = {
  buyer,
  seller,
  'buyer & seller': buyerSeller,
}

export function getClientPanelCopy(clientType: string): ClientPanelCopy {
  if (clientType === 'buyer' || clientType === 'seller' || clientType === 'buyer & seller') {
    return byType[clientType]
  }
  return buyer
}
