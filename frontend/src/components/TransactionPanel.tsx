import { useState, useEffect } from 'react'
import { useAppStore } from '../store/appStore'
import * as api from '../api/client'
import type { Transaction, KeyDate, Property, Project } from '../types'
import { getClientPanelCopy } from '../lib/clientPanelCopy'

function fmtMoney(v?: number) {
  if (!v) return 'N/A'
  return '$' + v.toLocaleString()
}

function fmtDate(d?: string) {
  if (!d) return 'N/A'
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function daysUntil(d?: string) {
  if (!d) return null
  return Math.round((new Date(d).getTime() - Date.now()) / 86400000)
}

const STATUS_COLORS: Record<string, string> = {
  active:     'bg-brand-mint/15 text-brand-mint border border-brand-mint/30',
  pending:    'bg-amber-300/10 text-amber-200 border border-amber-300/25',
  contingent: 'bg-orange-400/10 text-orange-200 border border-orange-400/25',
  closed:     'bg-brand-cloud/10 text-brand-cloud/90 border border-brand-cloud/20',
  dead:       'bg-white/[0.05] text-brand-cloud/50 border border-white/10',
}

function DateChip({ kd, projectId, txId }: { kd: KeyDate; projectId: string; txId: string }) {
  const { setTransactions, transactions } = useAppStore()
  const days = daysUntil(kd.due_date)
  const done = !!kd.completed_at
  const urgent = !done && days !== null && days >= 0 && days <= 3

  const toggleDone = async () => {
    const updated = await api.updateKeyDate(projectId, txId, kd.id, {
      completed_at: done ? undefined : new Date().toISOString(),
    })
    setTransactions(transactions.map(tx =>
      tx.id === txId
        ? { ...tx, key_dates: tx.key_dates.map(k => k.id === kd.id ? updated : k) }
        : tx
    ))
  }

  return (
    <div className={`flex items-center justify-between py-1.5 px-2 rounded-lg ${
      urgent ? 'bg-orange-400/10 border border-orange-400/30' : 'bg-white/[0.03] border border-white/5'
    }`}>
      <div className="flex items-center gap-2 min-w-0">
        <input type="checkbox" checked={done} onChange={toggleDone} className="shrink-0 accent-brand-mint" />
        <span className={`text-xs truncate ${done ? 'line-through text-brand-cloud/40' : 'text-brand-cloud/90'}`}>
          {kd.label}
        </span>
      </div>
      <span className={`text-xs shrink-0 ml-2 ${urgent ? 'text-orange-300 font-medium' : 'text-brand-cloud/55'}`}>
        {fmtDate(kd.due_date)}
        {days !== null && !done && (
          <span className="ml-1">
            ({days === 0 ? 'today' : days < 0 ? `${Math.abs(days)}d ago` : `${days}d`})
          </span>
        )}
      </span>
    </div>
  )
}

function AddKeyDateForm({ projectId, txId, onAdded }: {
  projectId: string; txId: string; onAdded: (kd: KeyDate) => void
}) {
  const [label, setLabel] = useState('')
  const [date, setDate] = useState('')

  const submit = async () => {
    if (!label || !date) return
    const kd = await api.addKeyDate(projectId, txId, { label, due_date: new Date(date).toISOString() })
    onAdded(kd)
    setLabel('')
    setDate('')
  }

  return (
    <div className="flex gap-1 mt-1">
      <input
        className="flex-1 bg-white/[0.04] border border-white/10 rounded px-2 py-1 text-xs text-brand-cloud placeholder-brand-cloud/35 outline-none focus:border-brand-mint/50"
        placeholder="Date label (e.g. Inspection deadline)"
        value={label}
        onChange={e => setLabel(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && submit()}
      />
      <input
        type="date"
        className="bg-white/[0.04] border border-white/10 rounded px-2 py-1 text-xs text-brand-cloud outline-none focus:border-brand-mint/50"
        value={date}
        onChange={e => setDate(e.target.value)}
      />
      <button onClick={submit} className="bg-brand-mint text-brand-navy hover:bg-brand-mint/90 px-2 py-1 rounded text-xs font-semibold transition">
        Add
      </button>
    </div>
  )
}

function TransactionCard({
  tx,
  prop,
  projectId,
  collapsed = false,
  propertyContextLabel,
  transactionNotesPlaceholder,
  variant = 'default',
}: {
  tx: Transaction
  prop?: Property
  projectId: string
  collapsed?: boolean
  propertyContextLabel: string
  transactionNotesPlaceholder: string
  variant?: 'default' | 'sellerOffer'
}) {
  const { setTransactions, transactions } = useAppStore()
  const [expanded, setExpanded] = useState(!collapsed)
  const [notes, setNotes] = useState(tx.notes ?? '')
  const [savingNotes, setSavingNotes] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const updateStatus = async (status: string) => {
    const updated = await api.updateTransaction(projectId, tx.id, { status })
    setTransactions(transactions.map(t => t.id === tx.id ? updated : t))
  }

  const saveNotes = async () => {
    if (notes === (tx.notes ?? '')) return
    setSavingNotes(true)
    const updated = await api.updateTransaction(projectId, tx.id, { notes })
    setTransactions(transactions.map(t => t.id === tx.id ? updated : t))
    setSavingNotes(false)
  }

  const handleKeyDateAdded = (kd: KeyDate) => {
    setTransactions(transactions.map(t =>
      t.id === tx.id ? { ...t, key_dates: [...t.key_dates, kd] } : t
    ))
  }

  const statusColor = STATUS_COLORS[tx.status] ?? 'bg-white/[0.05] text-brand-cloud/50 border border-white/10'

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl mb-3 overflow-hidden">
      {/* Header — always visible */}
      <button
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-white/[0.05] transition text-left"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex-1 min-w-0">
          {variant === 'sellerOffer' ? (
            <>
              <p className="text-[10px] uppercase tracking-wider text-brand-cloud/45 mb-0.5">Buyer offer</p>
              <p className="text-sm font-medium text-brand-cloud">{fmtMoney(tx.offer_price)}</p>
              <p className="text-xs text-brand-cloud/60 mt-0.5">
                Offer date {fmtDate(tx.offer_date)}
                {tx.close_date ? ` · Close ${fmtDate(tx.close_date)}` : ''}
              </p>
            </>
          ) : (
            <>
              <p className="text-[10px] uppercase tracking-wider text-brand-cloud/45 mb-0.5">{propertyContextLabel}</p>
              <p className="text-sm font-medium text-brand-cloud truncate">
                {prop?.address ?? 'No property linked'}
              </p>
              <p className="text-xs text-brand-cloud/60 mt-0.5">
                {fmtMoney(tx.offer_price)} · {fmtDate(tx.close_date ?? tx.offer_date)}
              </p>
            </>
          )}
        </div>
        <div className="flex items-center gap-2 ml-2 shrink-0">
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium capitalize ${statusColor}`}>
            {tx.status}
          </span>
          <span className="text-brand-cloud/40 text-xs">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-white/5 pt-2">
          <div className="grid grid-cols-2 gap-x-3 text-xs">
            <div>
              <span className="text-brand-cloud/50">Offer</span>
              <p className="text-brand-cloud font-medium">{fmtMoney(tx.offer_price)}</p>
            </div>
            <div>
              <span className="text-brand-cloud/50">Earnest</span>
              <p className="text-brand-cloud font-medium">{fmtMoney(tx.earnest_money)}</p>
            </div>
            <div className="mt-1">
              <span className="text-brand-cloud/50">Offer date</span>
              <p className="text-brand-cloud font-medium">{fmtDate(tx.offer_date)}</p>
            </div>
            <div className="mt-1">
              <span className="text-brand-cloud/50">Close date</span>
              <p className="text-brand-cloud font-medium">{fmtDate(tx.close_date)}</p>
            </div>
          </div>

          {/* Status */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-brand-cloud/55">Status:</span>
            <select
              value={tx.status}
              onChange={e => updateStatus(e.target.value)}
              className="bg-white/[0.04] border border-white/10 text-xs rounded px-1 py-0.5 outline-none text-brand-cloud/90"
            >
              {['active', 'pending', 'contingent', 'closed', 'dead'].map(s => (
                <option key={s} value={s} className="bg-brand-navy text-brand-cloud">{s}</option>
              ))}
            </select>
          </div>

          {/* Key dates */}
          {tx.key_dates.length > 0 && (
            <div className="space-y-1">
              <p className="text-[11px] text-brand-cloud/55 font-medium uppercase tracking-wider">Key Dates</p>
              {tx.key_dates.map(kd => (
                <DateChip key={kd.id} kd={kd} projectId={projectId} txId={tx.id} />
              ))}
            </div>
          )}
          <AddKeyDateForm projectId={projectId} txId={tx.id} onAdded={handleKeyDateAdded} />

          {/* Transaction notes */}
          <div>
            <p className="text-[11px] text-brand-cloud/55 font-medium uppercase tracking-wider mb-1">Transaction Notes</p>
            <textarea
              className="w-full bg-white/[0.04] border border-white/10 rounded-lg px-2 py-1.5 text-xs outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50 resize-none text-brand-cloud placeholder-brand-cloud/35"
              rows={3}
              placeholder={transactionNotesPlaceholder}
              value={notes}
              onChange={e => setNotes(e.target.value)}
              onBlur={saveNotes}
            />
            {savingNotes && <p className="text-xs text-brand-cloud/45">Saving…</p>}
          </div>

          {/* Delete */}
          {confirmDelete ? (
            <div className="flex items-center gap-2 pt-1">
              <p className="text-xs text-red-300 flex-1">Delete this transaction?</p>
              <button onClick={() => setConfirmDelete(false)} className="text-xs text-brand-cloud/55 hover:text-brand-cloud transition">Cancel</button>
              <button
                onClick={async () => {
                  await api.deleteTransaction(projectId, tx.id)
                  setTransactions(transactions.filter(t => t.id !== tx.id))
                }}
                className="text-xs text-red-300 hover:text-red-200 transition font-medium"
              >
                Delete
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="text-xs text-brand-cloud/40 hover:text-red-300 transition pt-1"
            >
              Delete transaction
            </button>
          )}
        </div>
      )}
    </div>
  )
}

interface Props {
  projectId: string
  clientType: Project['client_type']
  properties: Property[]
  transactions: Transaction[]
  /** For "buyer & seller" — only one property is the sale listing */
  salePropertyId?: string | null
  onProjectUpdated?: (p: Project) => void
}

function duplicateListingOfferHint(
  clientType: Project['client_type'],
  activeTxs: Transaction[],
  copy: ReturnType<typeof getClientPanelCopy>,
  salePropertyId?: string | null,
): string | null {
  if (clientType === 'buyer & seller' && !salePropertyId) {
    return null
  }
  const txForDup =
    clientType === 'buyer & seller' && salePropertyId
      ? activeTxs.filter(t => t.property_id === salePropertyId)
      : activeTxs
  const ids = txForDup.map(t => t.property_id).filter((id): id is string => Boolean(id))
  const counts = ids.reduce<Record<string, number>>((acc, id) => {
    acc[id] = (acc[id] ?? 0) + 1
    return acc
  }, {})
  const hasMultipleOffersSameProperty = Object.values(counts).some(n => n > 1)
  if (!hasMultipleOffersSameProperty || !copy.multiOfferSameListingHint) return null
  if (clientType === 'buyer & seller') return copy.multiOfferSameListingHint
  return null
}

/** Single home for sale: pick the listing row from project properties + transaction links. */
function resolveSellerListingProperty(
  projectId: string,
  properties: Property[],
  txsForProject: Transaction[],
): Property | undefined {
  const props = properties.filter(p => p.project_id === projectId)
  if (props.length === 0) {
    const pids = [...new Set(txsForProject.map(t => t.property_id).filter(Boolean) as string[])]
    if (pids.length === 1) return properties.find(p => p.id === pids[0])
    return undefined
  }
  if (props.length === 1) return props[0]
  const pidCounts: Record<string, number> = {}
  for (const t of txsForProject) {
    if (t.property_id) pidCounts[t.property_id] = (pidCounts[t.property_id] ?? 0) + 1
  }
  const ranked = Object.entries(pidCounts).sort((a, b) => b[1] - a[1])
  if (ranked[0]) {
    const match = props.find(p => p.id === ranked[0][0])
    if (match) return match
  }
  return props[0]
}

function SellerListingEditor({
  projectId,
  property,
}: {
  projectId: string
  property: Property
}) {
  const { setProperties, properties } = useAppStore()
  const [listPrice, setListPrice] = useState(
    property.list_price != null ? String(property.list_price) : '',
  )

  useEffect(() => {
    setListPrice(property.list_price != null ? String(property.list_price) : '')
  }, [property.id, property.list_price])

  const saveListPrice = async () => {
    const raw = listPrice.trim()
    const n = raw ? parseFloat(raw.replace(/[^0-9.]/g, '')) : undefined
    const prev = property.list_price ?? undefined
    if (n === prev || (n === undefined && prev === undefined)) return
    const updated = await api.updateProperty(projectId, property.id, {
      list_price: n,
    })
    setProperties(properties.map(p => (p.id === updated.id ? updated : p)))
  }

  return (
    <div className="space-y-2">
      <div>
        <p className="text-[10px] uppercase tracking-wide text-gray-500 mb-0.5">Address</p>
        <p className="text-sm font-medium text-white">{property.address}</p>
      </div>
      <div>
        <label className="text-[10px] uppercase tracking-wide text-gray-500 block mb-1">List price</label>
        <input
          className="w-full bg-gray-700/80 rounded-lg px-2 py-1.5 text-sm text-white outline-none focus:ring-1 focus:ring-emerald-500"
          inputMode="decimal"
          placeholder="e.g. 425000"
          value={listPrice}
          onChange={e => setListPrice(e.target.value)}
          onBlur={saveListPrice}
        />
      </div>
    </div>
  )
}

function BuyerSellerListingSetup({
  projectId,
  onListed,
}: {
  projectId: string
  onListed: (prop: Property) => void
}) {
  const { setProperties, properties } = useAppStore()
  const [addr, setAddr] = useState('')
  const [listPrice, setListPrice] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!addr.trim() || saving) return
    setSaving(true)
    try {
      const lp = listPrice.trim() ? parseFloat(listPrice.replace(/[^0-9.]/g, '')) : undefined
      const prop = await api.createProperty(projectId, {
        address: addr.trim(),
        list_price: lp,
      })
      setProperties([...properties, prop])
      setAddr('')
      setListPrice('')
      onListed(prop)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-400">Add the home they are selling — offers go underneath.</p>
      <input
        className="w-full bg-gray-700/80 rounded-lg px-2 py-1.5 text-sm outline-none focus:ring-1 focus:ring-emerald-500"
        placeholder="Listing street address"
        value={addr}
        onChange={e => setAddr(e.target.value)}
      />
      <input
        className="w-full bg-gray-700/80 rounded-lg px-2 py-1.5 text-sm outline-none focus:ring-1 focus:ring-emerald-500"
        inputMode="decimal"
        placeholder="List price (e.g. 425000)"
        value={listPrice}
        onChange={e => setListPrice(e.target.value)}
      />
      <button
        type="button"
        onClick={submit}
        disabled={!addr.trim() || saving}
        className="w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg text-xs font-medium transition"
      >
        {saving ? 'Saving…' : 'Save listing'}
      </button>
    </div>
  )
}

function SellerSetupListingForm({ projectId }: { projectId: string }) {
  const { setProperties, properties } = useAppStore()
  const [addr, setAddr] = useState('')
  const [listPrice, setListPrice] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!addr.trim() || saving) return
    setSaving(true)
    try {
      const lp = listPrice.trim() ? parseFloat(listPrice.replace(/[^0-9.]/g, '')) : undefined
      const prop = await api.createProperty(projectId, {
        address: addr.trim(),
        list_price: lp,
      })
      setProperties([...properties, prop])
      setAddr('')
      setListPrice('')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-400">Add the home they are selling — offers go underneath.</p>
      <input
        className="w-full bg-gray-700/80 rounded-lg px-2 py-1.5 text-sm outline-none focus:ring-1 focus:ring-emerald-500"
        placeholder="Listing street address"
        value={addr}
        onChange={e => setAddr(e.target.value)}
      />
      <input
        className="w-full bg-gray-700/80 rounded-lg px-2 py-1.5 text-sm outline-none focus:ring-1 focus:ring-emerald-500"
        inputMode="decimal"
        placeholder="List price (e.g. 425000)"
        value={listPrice}
        onChange={e => setListPrice(e.target.value)}
      />
      <button
        type="button"
        onClick={submit}
        disabled={!addr.trim() || saving}
        className="w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg text-xs font-medium transition"
      >
        {saving ? 'Saving…' : 'Save listing'}
      </button>
    </div>
  )
}

export default function TransactionPanel({
  projectId,
  clientType,
  properties,
  transactions,
  salePropertyId,
  onProjectUpdated,
}: Props) {
  const { setTransactions, setProperties } = useAppStore()
  const [addingTx, setAddingTx] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [newOffer, setNewOffer] = useState('')
  const [newClose, setNewClose] = useState('')
  const [newOfferDate, setNewOfferDate] = useState('')
  const [newPropAddr, setNewPropAddr] = useState('')
  const [bsSaleOfferOpen, setBsSaleOfferOpen] = useState(false)
  const [bsSaleNewOffer, setBsSaleNewOffer] = useState('')
  const [bsSaleNewOfferDate, setBsSaleNewOfferDate] = useState('')
  const [bsBuyOpen, setBsBuyOpen] = useState(false)
  const [bsBuyAddr, setBsBuyAddr] = useState('')
  const [bsBuyOffer, setBsBuyOffer] = useState('')
  const [bsBuyClose, setBsBuyClose] = useState('')
  const [showPastSaleOffers, setShowPastSaleOffers] = useState(false)
  const [showPastBuys, setShowPastBuys] = useState(false)

  const copy = getClientPanelCopy(clientType)
  const txsForProject = transactions.filter(t => t.project_id === projectId)
  const activeTxs = txsForProject.filter(t => !['closed', 'dead'].includes(t.status))
  const pastTxs = txsForProject.filter(t => ['closed', 'dead'].includes(t.status))
  const listingHint = duplicateListingOfferHint(clientType, activeTxs, copy, salePropertyId)
  const listingProp =
    clientType === 'seller' ? resolveSellerListingProperty(projectId, properties, txsForProject) : undefined

  const offerCardVariant = (tx: Transaction): 'default' | 'sellerOffer' =>
    clientType === 'seller' && listingProp && tx.property_id === listingProp.id ? 'sellerOffer' : 'default'

  const createSellerOffer = async () => {
    if (!listingProp) return
    const tx = await api.createTransaction(projectId, {
      property_id: listingProp.id,
      offer_price: newOffer ? parseFloat(newOffer.replace(/[^0-9.]/g, '')) : undefined,
      offer_date: newOfferDate ? new Date(newOfferDate).toISOString() : undefined,
      status: 'active',
    })
    setTransactions([...txsForProject, tx])
    setAddingTx(false)
    setNewOffer('')
    setNewOfferDate('')
  }

  const createTx = async () => {
    let propertyId: string | undefined
    if (newPropAddr.trim()) {
      const prop = await api.createProperty(projectId, { address: newPropAddr.trim() })
      setProperties([...properties, prop])
      propertyId = prop.id
    }
    const tx = await api.createTransaction(projectId, {
      property_id: propertyId,
      offer_price: newOffer ? parseFloat(newOffer.replace(/[^0-9.]/g, '')) : undefined,
      close_date: newClose ? new Date(newClose).toISOString() : undefined,
      status: 'active',
    })
    setTransactions([...txsForProject, tx])
    setAddingTx(false)
    setNewOffer('')
    setNewClose('')
    setNewPropAddr('')
  }

  if (clientType === 'seller') {
    return (
      <div>
        <p className="text-xs text-gray-500 mb-2">{copy.transactionsSubtitle}</p>

        <div className="bg-gray-800/60 rounded-xl p-3 mb-4 border border-gray-700/40">
          <p className="text-[10px] uppercase font-semibold tracking-wide text-emerald-400/90 mb-2">Listing</p>
          {listingProp ? (
            <SellerListingEditor projectId={projectId} property={listingProp} />
          ) : (
            <SellerSetupListingForm projectId={projectId} />
          )}
        </div>

        {listingProp && (
          <>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Buyer offers</p>
              <button
                type="button"
                onClick={() => {
                  setAddingTx(a => !a)
                  setNewOffer('')
                  setNewOfferDate('')
                }}
                className="text-xs text-emerald-400 hover:text-emerald-300 transition"
              >
                + Add offer
              </button>
            </div>

            {addingTx && (
              <div className="bg-gray-800 rounded-xl p-3 mb-3 space-y-2 border border-gray-700/40">
                <input
                  className="w-full bg-gray-700 rounded px-2 py-1.5 text-xs outline-none"
                  placeholder={copy.newOfferPricePlaceholder}
                  value={newOffer}
                  onChange={e => setNewOffer(e.target.value)}
                />
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-400 shrink-0">Offer date</label>
                  <input
                    type="date"
                    className="flex-1 bg-gray-700 rounded px-2 py-1 text-xs outline-none"
                    value={newOfferDate}
                    onChange={e => setNewOfferDate(e.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setAddingTx(false)
                      setNewOffer('')
                      setNewOfferDate('')
                    }}
                    className="flex-1 py-1.5 bg-gray-700 rounded text-xs hover:bg-gray-600 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={createSellerOffer}
                    className="flex-1 py-1.5 bg-emerald-600 rounded text-xs hover:bg-emerald-500 transition"
                  >
                    Add offer
                  </button>
                </div>
              </div>
            )}

            {activeTxs.length === 0 && !addingTx && (
              <p className="text-xs text-gray-500 mb-2">{copy.emptyActiveTransactions}</p>
            )}

            {activeTxs.map(tx => (
              <TransactionCard
                key={tx.id}
                variant={offerCardVariant(tx)}
                tx={tx}
                prop={properties.find(p => p.id === tx.property_id)}
                projectId={projectId}
                propertyContextLabel={copy.propertyContextLabel}
                transactionNotesPlaceholder={copy.transactionNotesPlaceholder}
              />
            ))}
          </>
        )}

        {!listingProp && activeTxs.length > 0 && (
          <div className="mb-3">
            <p className="text-xs text-amber-500/90 mb-2">
              These rows pre-date a saved listing. Add the listing above, then use “+ Add offer” so new
              offers attach to one address and list price.
            </p>
            {activeTxs.map(tx => (
              <TransactionCard
                key={tx.id}
                variant="default"
                tx={tx}
                prop={properties.find(p => p.id === tx.property_id)}
                projectId={projectId}
                propertyContextLabel={copy.propertyContextLabel}
                transactionNotesPlaceholder={copy.transactionNotesPlaceholder}
              />
            ))}
          </div>
        )}

        {pastTxs.length > 0 && (
          <div className="mt-3">
            <button
              type="button"
              onClick={() => setShowHistory(h => !h)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition mb-2"
            >
              <span>{showHistory ? '▼' : '▶'}</span>
              <span>Past offers ({pastTxs.length})</span>
            </button>
            {showHistory &&
              pastTxs.map(tx => (
                <TransactionCard
                  key={tx.id}
                  variant={offerCardVariant(tx)}
                  tx={tx}
                  prop={properties.find(p => p.id === tx.property_id)}
                  projectId={projectId}
                  collapsed={true}
                  propertyContextLabel={copy.propertyContextLabel}
                  transactionNotesPlaceholder={copy.transactionNotesPlaceholder}
                />
              ))}
          </div>
        )}
      </div>
    )
  }

  if (clientType === 'buyer & seller') {
    const sellerCopy = getClientPanelCopy('seller')
    const buyerCopy = getClientPanelCopy('buyer')
    const propsForProject = properties.filter(p => p.project_id === projectId)
    const saleProp = salePropertyId ? propsForProject.find(p => p.id === salePropertyId) : undefined

    const isSaleTx = (t: Transaction) => Boolean(salePropertyId && t.property_id === salePropertyId)
    const saleActiveTxs = activeTxs.filter(isSaleTx)
    const buyActiveTxs = activeTxs.filter(t => !isSaleTx(t))
    const salePastTxs = pastTxs.filter(isSaleTx)
    const buyPastTxs = pastTxs.filter(t => !isSaleTx(t))

    const bsOfferCardVariant = (tx: Transaction): 'default' | 'sellerOffer' =>
      saleProp && tx.property_id === saleProp.id ? 'sellerOffer' : 'default'

    const listingHintBs = duplicateListingOfferHint('buyer & seller', activeTxs, copy, salePropertyId)

    const persistSalePropertyId = async (id: string | null) => {
      if (!onProjectUpdated) return
      const u = await api.updateProject(projectId, { sale_property_id: id })
      onProjectUpdated(u)
    }

    const createBsSaleOffer = async () => {
      if (!saleProp) return
      const tx = await api.createTransaction(projectId, {
        property_id: saleProp.id,
        offer_price: bsSaleNewOffer ? parseFloat(bsSaleNewOffer.replace(/[^0-9.]/g, '')) : undefined,
        offer_date: bsSaleNewOfferDate ? new Date(bsSaleNewOfferDate).toISOString() : undefined,
        status: 'active',
      })
      setTransactions([...txsForProject, tx])
      setBsSaleOfferOpen(false)
      setBsSaleNewOffer('')
      setBsSaleNewOfferDate('')
    }

    const createBsBuyTx = async () => {
      let propertyId: string | undefined
      if (bsBuyAddr.trim()) {
        const prop = await api.createProperty(projectId, { address: bsBuyAddr.trim() })
        setProperties([...properties, prop])
        propertyId = prop.id
      }
      const tx = await api.createTransaction(projectId, {
        property_id: propertyId,
        offer_price: bsBuyOffer ? parseFloat(bsBuyOffer.replace(/[^0-9.]/g, '')) : undefined,
        close_date: bsBuyClose ? new Date(bsBuyClose).toISOString() : undefined,
        status: 'active',
      })
      setTransactions([...txsForProject, tx])
      setBsBuyOpen(false)
      setBsBuyOffer('')
      setBsBuyClose('')
      setBsBuyAddr('')
    }

    return (
      <div className="space-y-6">
        <p className="text-xs text-gray-500">{copy.transactionsSubtitle}</p>

        {/* —— Seller workspace: listing + offers on that listing —— */}
        <section>
          <div className="mb-2">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400/95">Selling</p>
            <p className="text-xs font-medium text-gray-300 mt-0.5">{sellerCopy.transactionsSectionTitle}</p>
            <p className="text-xs text-gray-500 mt-1">{sellerCopy.transactionsSubtitle}</p>
          </div>

          <div className="bg-gray-800/60 rounded-xl p-3 mb-4 border border-gray-700/40">
            <p className="text-[10px] uppercase font-semibold tracking-wide text-emerald-400/90 mb-2">Listing</p>
            {saleProp ? (
              <>
                <SellerListingEditor projectId={projectId} property={saleProp} />
                {onProjectUpdated ? (
                  <button
                    type="button"
                    className="mt-2 text-[10px] text-gray-500 hover:text-gray-300 transition"
                    onClick={() => void persistSalePropertyId(null)}
                  >
                    Choose a different sale address
                  </button>
                ) : null}
              </>
            ) : (
              <BuyerSellerListingSetup
                projectId={projectId}
                onListed={async prop => {
                  if (!onProjectUpdated) return
                  const u = await api.updateProject(projectId, { sale_property_id: prop.id })
                  onProjectUpdated(u)
                }}
              />
            )}
          </div>

        {saleProp ? (
          <>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Buyer offers</p>
              <button
                type="button"
                onClick={() => {
                  setBsSaleOfferOpen(a => !a)
                  setBsSaleNewOffer('')
                  setBsSaleNewOfferDate('')
                }}
                className="text-xs text-emerald-400 hover:text-emerald-300 transition"
              >
                + Add offer
              </button>
            </div>

            {listingHintBs ? (
              <p className="text-xs text-amber-500/90 mb-2">{listingHintBs}</p>
            ) : null}

            {bsSaleOfferOpen && (
              <div className="bg-gray-800 rounded-xl p-3 mb-3 space-y-2 border border-gray-700/40">
                <input
                  className="w-full bg-gray-700 rounded px-2 py-1.5 text-xs outline-none"
                  placeholder={sellerCopy.newOfferPricePlaceholder}
                  value={bsSaleNewOffer}
                  onChange={e => setBsSaleNewOffer(e.target.value)}
                />
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-400 shrink-0">Offer date</label>
                  <input
                    type="date"
                    className="flex-1 bg-gray-700 rounded px-2 py-1 text-xs outline-none"
                    value={bsSaleNewOfferDate}
                    onChange={e => setBsSaleNewOfferDate(e.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setBsSaleOfferOpen(false)
                      setBsSaleNewOffer('')
                      setBsSaleNewOfferDate('')
                    }}
                    className="flex-1 py-1.5 bg-gray-700 rounded text-xs hover:bg-gray-600 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => void createBsSaleOffer()}
                    className="flex-1 py-1.5 bg-emerald-600 rounded text-xs hover:bg-emerald-500 transition"
                  >
                    Add offer
                  </button>
                </div>
              </div>
            )}

            {saleActiveTxs.length === 0 && !bsSaleOfferOpen && (
              <p className="text-xs text-gray-500 mb-2">{sellerCopy.emptyActiveTransactions}</p>
            )}

            {saleActiveTxs.map(tx => (
              <TransactionCard
                key={tx.id}
                variant={bsOfferCardVariant(tx)}
                tx={tx}
                prop={properties.find(p => p.id === tx.property_id)}
                projectId={projectId}
                propertyContextLabel={sellerCopy.propertyContextLabel}
                transactionNotesPlaceholder={sellerCopy.transactionNotesPlaceholder}
              />
            ))}

            {salePastTxs.length > 0 && (
              <div className="mt-3 mb-6">
                <button
                  type="button"
                  onClick={() => setShowPastSaleOffers(h => !h)}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition mb-2"
                >
                  <span>{showPastSaleOffers ? '▼' : '▶'}</span>
                  <span>Past offers ({salePastTxs.length})</span>
                </button>
                {showPastSaleOffers &&
                  salePastTxs.map(tx => (
                    <TransactionCard
                      key={tx.id}
                      variant={bsOfferCardVariant(tx)}
                      tx={tx}
                      prop={properties.find(p => p.id === tx.property_id)}
                      projectId={projectId}
                      collapsed={true}
                      propertyContextLabel={sellerCopy.propertyContextLabel}
                      transactionNotesPlaceholder={sellerCopy.transactionNotesPlaceholder}
                    />
                  ))}
              </div>
            )}
          </>
        ) : null}
        </section>

        <section className={saleProp ? 'pt-4 border-t border-gray-700/30' : ''}>
          <div className="mb-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-blue-400/95">Buying</p>
            <p className="text-xs font-medium text-gray-300 mt-0.5">{buyerCopy.transactionsSectionTitle}</p>
            <p className="text-xs text-gray-500 mt-1">{buyerCopy.transactionsSubtitle}</p>
          </div>

          <div className="flex justify-end mb-2">
            <button
              type="button"
              onClick={() => {
                setBsBuyOpen(a => !a)
                setBsBuyAddr('')
                setBsBuyOffer('')
                setBsBuyClose('')
              }}
              className="text-xs text-blue-400 hover:text-blue-300 transition"
            >
              + Add
            </button>
          </div>

          {bsBuyOpen && (
            <div className="bg-gray-800 rounded-xl p-3 mb-3 space-y-2 border border-gray-700/40">
              <input
                className="w-full bg-gray-700 rounded px-2 py-1.5 text-xs outline-none"
                placeholder={buyerCopy.newPropertyAddressPlaceholder}
                value={bsBuyAddr}
                onChange={e => setBsBuyAddr(e.target.value)}
              />
              <input
                className="w-full bg-gray-700 rounded px-2 py-1.5 text-xs outline-none"
                placeholder={buyerCopy.newOfferPricePlaceholder}
                value={bsBuyOffer}
                onChange={e => setBsBuyOffer(e.target.value)}
              />
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-400 shrink-0">Close date:</label>
                <input
                  type="date"
                  className="flex-1 bg-gray-700 rounded px-2 py-1 text-xs outline-none"
                  value={bsBuyClose}
                  onChange={e => setBsBuyClose(e.target.value)}
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setBsBuyOpen(false)
                    setBsBuyAddr('')
                    setBsBuyOffer('')
                    setBsBuyClose('')
                  }}
                  className="flex-1 py-1.5 bg-gray-700 rounded text-xs hover:bg-gray-600 transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => void createBsBuyTx()}
                  className="flex-1 py-1.5 bg-blue-600 rounded text-xs hover:bg-blue-500 transition"
                >
                  Create
                </button>
              </div>
            </div>
          )}

          {buyActiveTxs.length === 0 && !bsBuyOpen && (
            <p className="text-xs text-gray-500 mb-2">{buyerCopy.emptyActiveTransactions}</p>
          )}

          {buyActiveTxs.map(tx => (
            <TransactionCard
              key={tx.id}
              variant="default"
              tx={tx}
              prop={properties.find(p => p.id === tx.property_id)}
              projectId={projectId}
              propertyContextLabel={buyerCopy.propertyContextLabel}
              transactionNotesPlaceholder={buyerCopy.transactionNotesPlaceholder}
            />
          ))}

          {buyPastTxs.length > 0 && (
            <div className="mt-3">
              <button
                type="button"
                onClick={() => setShowPastBuys(h => !h)}
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition mb-2"
              >
                <span>{showPastBuys ? '▼' : '▶'}</span>
                <span>Past properties ({buyPastTxs.length})</span>
              </button>
              {showPastBuys &&
                buyPastTxs.map(tx => (
                  <TransactionCard
                    key={tx.id}
                    variant="default"
                    tx={tx}
                    prop={properties.find(p => p.id === tx.property_id)}
                    projectId={projectId}
                    collapsed={true}
                    propertyContextLabel={buyerCopy.propertyContextLabel}
                    transactionNotesPlaceholder={buyerCopy.transactionNotesPlaceholder}
                  />
                ))}
            </div>
          )}
        </section>
      </div>
    )
  }

  return (
    <div>
      <p className="text-xs text-gray-500 mb-2">{copy.transactionsSubtitle}</p>
      {listingHint && (
        <p className="text-xs text-amber-500/90 mb-2">{listingHint}</p>
      )}
      <div className="flex justify-end mb-2">
        <button
          type="button"
          onClick={() => setAddingTx(!addingTx)}
          className="text-xs text-blue-400 hover:text-blue-300 transition"
        >
          + Add
        </button>
      </div>

      {addingTx && (
        <div className="bg-gray-800 rounded-xl p-3 mb-3 space-y-2">
          <input
            className="w-full bg-gray-700 rounded px-2 py-1.5 text-xs outline-none"
            placeholder={copy.newPropertyAddressPlaceholder}
            value={newPropAddr}
            onChange={e => setNewPropAddr(e.target.value)}
          />
          <input
            className="w-full bg-gray-700 rounded px-2 py-1.5 text-xs outline-none"
            placeholder={copy.newOfferPricePlaceholder}
            value={newOffer}
            onChange={e => setNewOffer(e.target.value)}
          />
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 shrink-0">Close date:</label>
            <input
              type="date"
              className="flex-1 bg-gray-700 rounded px-2 py-1 text-xs outline-none"
              value={newClose}
              onChange={e => setNewClose(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => setAddingTx(false)} className="flex-1 py-1.5 bg-gray-700 rounded text-xs hover:bg-gray-600 transition">Cancel</button>
            <button type="button" onClick={createTx} className="flex-1 py-1.5 bg-blue-600 rounded text-xs hover:bg-blue-500 transition">Create</button>
          </div>
        </div>
      )}

      {activeTxs.length === 0 && !addingTx && (
        <p className="text-xs text-gray-500 mb-2">{copy.emptyActiveTransactions}</p>
      )}

      {activeTxs.map(tx => (
        <TransactionCard
          key={tx.id}
          variant="default"
          tx={tx}
          prop={properties.find(p => p.id === tx.property_id)}
          projectId={projectId}
          propertyContextLabel={copy.propertyContextLabel}
          transactionNotesPlaceholder={copy.transactionNotesPlaceholder}
        />
      ))}

      {/* Past properties (closed / dead deals) */}
      {pastTxs.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowHistory(h => !h)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition mb-2"
          >
            <span>{showHistory ? '▼' : '▶'}</span>
            <span>Past properties ({pastTxs.length})</span>
          </button>
          {showHistory &&
            pastTxs.map(tx => (
              <TransactionCard
                key={tx.id}
                variant="default"
                tx={tx}
                prop={properties.find(p => p.id === tx.property_id)}
                projectId={projectId}
                collapsed={true}
                propertyContextLabel={copy.propertyContextLabel}
                transactionNotesPlaceholder={copy.transactionNotesPlaceholder}
              />
            ))}
        </div>
      )}
    </div>
  )
}
