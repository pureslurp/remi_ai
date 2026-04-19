import { useState } from 'react'
import { useAppStore } from '../store/appStore'
import * as api from '../api/client'
import type { Transaction, KeyDate, Property } from '../types'

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
  active:     'bg-blue-900/60 text-blue-300',
  pending:    'bg-yellow-900/60 text-yellow-300',
  contingent: 'bg-orange-900/60 text-orange-300',
  closed:     'bg-emerald-900/60 text-emerald-300',
  dead:       'bg-gray-700 text-gray-400',
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
      urgent ? 'bg-orange-900/40 border border-orange-700/50' : 'bg-gray-800/50'
    }`}>
      <div className="flex items-center gap-2 min-w-0">
        <input type="checkbox" checked={done} onChange={toggleDone} className="shrink-0 accent-blue-500" />
        <span className={`text-xs truncate ${done ? 'line-through text-gray-500' : 'text-gray-200'}`}>
          {kd.label}
        </span>
      </div>
      <span className={`text-xs shrink-0 ml-2 ${urgent ? 'text-orange-400 font-medium' : 'text-gray-400'}`}>
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
        className="flex-1 bg-gray-700 rounded px-2 py-1 text-xs outline-none"
        placeholder="Date label (e.g. Inspection deadline)"
        value={label}
        onChange={e => setLabel(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && submit()}
      />
      <input
        type="date"
        className="bg-gray-700 rounded px-2 py-1 text-xs outline-none"
        value={date}
        onChange={e => setDate(e.target.value)}
      />
      <button onClick={submit} className="bg-blue-600 hover:bg-blue-500 px-2 py-1 rounded text-xs transition">
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
}: {
  tx: Transaction
  prop?: Property
  projectId: string
  collapsed?: boolean
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

  const statusColor = STATUS_COLORS[tx.status] ?? 'bg-gray-700 text-gray-400'

  return (
    <div className="bg-gray-800/60 rounded-xl mb-3 overflow-hidden">
      {/* Header — always visible */}
      <button
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-gray-800/80 transition text-left"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white truncate">
            {prop?.address ?? 'No property linked'}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            {fmtMoney(tx.offer_price)} · {fmtDate(tx.close_date ?? tx.offer_date)}
          </p>
        </div>
        <div className="flex items-center gap-2 ml-2 shrink-0">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${statusColor}`}>
            {tx.status}
          </span>
          <span className="text-gray-500 text-xs">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-gray-700/50 pt-2">
          <div className="grid grid-cols-2 gap-x-3 text-xs">
            <div>
              <span className="text-gray-400">Offer</span>
              <p className="text-white font-medium">{fmtMoney(tx.offer_price)}</p>
            </div>
            <div>
              <span className="text-gray-400">Earnest</span>
              <p className="text-white font-medium">{fmtMoney(tx.earnest_money)}</p>
            </div>
            <div className="mt-1">
              <span className="text-gray-400">Offer date</span>
              <p className="text-white font-medium">{fmtDate(tx.offer_date)}</p>
            </div>
            <div className="mt-1">
              <span className="text-gray-400">Close date</span>
              <p className="text-white font-medium">{fmtDate(tx.close_date)}</p>
            </div>
          </div>

          {/* Status */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">Status:</span>
            <select
              value={tx.status}
              onChange={e => updateStatus(e.target.value)}
              className="bg-gray-700 text-xs rounded px-1 py-0.5 outline-none text-gray-200"
            >
              {['active', 'pending', 'contingent', 'closed', 'dead'].map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Key dates */}
          {tx.key_dates.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs text-gray-400 font-medium">Key Dates</p>
              {tx.key_dates.map(kd => (
                <DateChip key={kd.id} kd={kd} projectId={projectId} txId={tx.id} />
              ))}
            </div>
          )}
          <AddKeyDateForm projectId={projectId} txId={tx.id} onAdded={handleKeyDateAdded} />

          {/* Transaction notes */}
          <div>
            <p className="text-xs text-gray-400 font-medium mb-1">Transaction Notes</p>
            <textarea
              className="w-full bg-gray-700 rounded-lg px-2 py-1.5 text-xs outline-none focus:ring-1 focus:ring-blue-500 resize-none text-gray-100"
              rows={3}
              placeholder="Offer history, counter notes, inspection findings, any deal-specific details…"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              onBlur={saveNotes}
            />
            {savingNotes && <p className="text-xs text-gray-500">Saving…</p>}
          </div>

          {/* Delete */}
          {confirmDelete ? (
            <div className="flex items-center gap-2 pt-1">
              <p className="text-xs text-red-400 flex-1">Delete this transaction?</p>
              <button onClick={() => setConfirmDelete(false)} className="text-xs text-gray-400 hover:text-gray-200 transition">Cancel</button>
              <button
                onClick={async () => {
                  await api.deleteTransaction(projectId, tx.id)
                  setTransactions(transactions.filter(t => t.id !== tx.id))
                }}
                className="text-xs text-red-400 hover:text-red-300 transition font-medium"
              >
                Delete
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="text-xs text-gray-600 hover:text-red-400 transition pt-1"
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
  properties: Property[]
  transactions: Transaction[]
}

export default function TransactionPanel({ projectId, properties, transactions }: Props) {
  const { setTransactions, setProperties } = useAppStore()
  const [addingTx, setAddingTx] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [newOffer, setNewOffer] = useState('')
  const [newClose, setNewClose] = useState('')
  const [newPropAddr, setNewPropAddr] = useState('')

  const activeTxs = transactions.filter(t => !['closed', 'dead'].includes(t.status))
  const pastTxs = transactions.filter(t => ['closed', 'dead'].includes(t.status))

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
    setTransactions([...transactions, tx])
    setAddingTx(false)
    setNewOffer('')
    setNewClose('')
    setNewPropAddr('')
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Transactions</h3>
        <button
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
            placeholder="Property address"
            value={newPropAddr}
            onChange={e => setNewPropAddr(e.target.value)}
          />
          <input
            className="w-full bg-gray-700 rounded px-2 py-1.5 text-xs outline-none"
            placeholder="Offer price (e.g. 415000)"
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
            <button onClick={() => setAddingTx(false)} className="flex-1 py-1.5 bg-gray-700 rounded text-xs hover:bg-gray-600 transition">Cancel</button>
            <button onClick={createTx} className="flex-1 py-1.5 bg-blue-600 rounded text-xs hover:bg-blue-500 transition">Create</button>
          </div>
        </div>
      )}

      {activeTxs.length === 0 && !addingTx && (
        <p className="text-xs text-gray-500 mb-2">No active transactions.</p>
      )}

      {activeTxs.map(tx => (
        <TransactionCard
          key={tx.id}
          tx={tx}
          prop={properties.find(p => p.id === tx.property_id)}
          projectId={projectId}
        />
      ))}

      {/* Past transactions */}
      {pastTxs.length > 0 && (
        <div>
          <button
            onClick={() => setShowHistory(h => !h)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition mb-2"
          >
            <span>{showHistory ? '▼' : '▶'}</span>
            <span>Past transactions ({pastTxs.length})</span>
          </button>
          {showHistory && pastTxs.map(tx => (
            <TransactionCard
              key={tx.id}
              tx={tx}
              prop={properties.find(p => p.id === tx.property_id)}
              projectId={projectId}
              collapsed={true}
            />
          ))}
        </div>
      )}
    </div>
  )
}
