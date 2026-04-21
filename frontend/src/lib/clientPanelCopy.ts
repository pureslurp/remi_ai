import type { ClientType } from './clientTypeStyles'
import { clientTypePanelLeftAccentClass, normalizeClientType } from './clientTypeStyles'

export type { ClientType }

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

type CopyCore = Omit<ClientPanelCopy, 'panelAccentClass'>

const buyer: CopyCore = {
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
}

const seller: CopyCore = {
  transactionsSectionTitle: 'Listing & buyer offers',
  transactionsSubtitle:
    'Their home is one listing (address and list price below). Add a row for each buyer’s offer — amount and offer date.',
  agentNotesPlaceholder:
    'Agent notes (disclosure status, timeline, staging, preferred close…)',
  newPropertyAddressPlaceholder: 'Listing street address',
  newOfferPricePlaceholder: 'Buyer’s offer amount (e.g. 415000)',
  emptyActiveTransactions:
    'No offers on file yet. Use “+ Add offer” after the listing is set up.',
  propertyContextLabel: 'Listing',
  transactionNotesPlaceholder:
    'Buyer name (if known), contingencies vs other offers, concessions, close date…',
  multiOfferSameListingHint: '',
}

const buyerSeller: CopyCore = {
  transactionsSectionTitle: 'Buying & selling',
  transactionsSubtitle:
    'Same layout as Seller-only + Buyer-only: one listing with buyer offers on it, plus a row per home they may buy.',
  agentNotesPlaceholder:
    'Agent notes (bridge timing, contingent sale, both closings, lender on buy side…)',
  newPropertyAddressPlaceholder: 'Address of a home they may buy',
  newOfferPricePlaceholder: 'Their offer price (e.g. 415000)',
  emptyActiveTransactions:
    'No active purchase deals yet. Add a property when they start looking or go under contract.',
  propertyContextLabel: 'Property',
  transactionNotesPlaceholder:
    'Offer stage, inspection, appraisal, lender — anything specific to this purchase…',
  multiOfferSameListingHint:
    'Multiple buyer offers on the same sale — use notes to tell each buyer apart.',
}

const byType: Record<ClientType, CopyCore> = {
  buyer,
  seller,
  'buyer & seller': buyerSeller,
}

export function getClientPanelCopy(clientType: string): ClientPanelCopy {
  const key = normalizeClientType(clientType)
  return {
    ...byType[key],
    panelAccentClass: clientTypePanelLeftAccentClass(key),
  }
}
