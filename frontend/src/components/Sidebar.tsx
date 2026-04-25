import { useState } from 'react'
import { createPortal } from 'react-dom'
import { useAppStore } from '../store/appStore'
import * as api from '../api/client'
import type { Project } from '../types'
import { clientTypeSidebarPillClass } from '../lib/clientTypeStyles'
import UserProfile from './UserProfile'

interface PersonFields {
  firstName: string
  lastName: string
  email: string
  phone: string
}

const emptyPerson = (): PersonFields => ({ firstName: '', lastName: '', email: '', phone: '' })

function PersonForm({
  label,
  person,
  onChange,
  onRemove,
}: {
  label: string
  person: PersonFields
  onChange: (p: PersonFields) => void
  onRemove?: () => void
}) {
  const set = (key: keyof PersonFields) => (e: React.ChangeEvent<HTMLInputElement>) =>
    onChange({ ...person, [key]: e.target.value })

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 space-y-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[11px] font-medium uppercase tracking-wider text-brand-cloud/50">{label}</span>
        {onRemove && (
          <button onClick={onRemove} className="text-xs text-brand-cloud/40 hover:text-red-300 transition">
            Remove
          </button>
        )}
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-sm text-brand-cloud placeholder-brand-cloud/40 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
          placeholder="First name"
          value={person.firstName}
          onChange={set('firstName')}
        />
        <input
          className="flex-1 bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-sm text-brand-cloud placeholder-brand-cloud/40 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
          placeholder="Last name"
          value={person.lastName}
          onChange={set('lastName')}
        />
      </div>
      <input
        className="w-full bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-sm text-brand-cloud placeholder-brand-cloud/40 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
        placeholder="Email address"
        type="email"
        value={person.email}
        onChange={set('email')}
      />
      <input
        className="w-full bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-sm text-brand-cloud placeholder-brand-cloud/40 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
        placeholder="Phone (optional)"
        value={person.phone}
        onChange={set('phone')}
      />
    </div>
  )
}

function NewClientModal({ onClose, onCreated }: { onClose: () => void; onCreated: (p: Project) => void }) {
  const [primary, setPrimary] = useState<PersonFields>(emptyPerson())
  const [spouse, setSpouse] = useState<PersonFields | null>(null)
  const [clientType, setClientType] = useState<'buyer' | 'seller' | 'buyer & seller'>('buyer')
  const [loading, setLoading] = useState(false)

  const buildName = () => {
    const first = primary.firstName.trim()
    const last = primary.lastName.trim()
    const spouseFirst = spouse?.firstName.trim() ?? ''
    const spouseLast = spouse?.lastName.trim() ?? ''
    if (!first) return ''
    const primaryName = last ? `${first} ${last}` : first
    if (!spouseFirst) return primaryName
    if (!spouseLast || spouseLast.toLowerCase() === last.toLowerCase()) {
      return `${first} & ${spouseFirst}${last ? ' ' + last : ''}`
    }
    return `${primaryName} & ${spouseFirst} ${spouseLast}`
  }

  const submit = async () => {
    const name = buildName()
    if (!name) return
    setLoading(true)
    const emails = [primary.email, spouse?.email ?? ''].filter(Boolean)
    try {
      const project = await api.createProject({
        name,
        client_type: clientType,
        email_addresses: emails,
        phone: primary.phone || undefined,
      })
      onCreated(project)
    } finally {
      setLoading(false)
    }
  }

  const preview = buildName()

  const modal = (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 overflow-y-auto py-8">
      <div className="bg-gradient-to-br from-brand-navy to-brand-slate/90 border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl mx-4">
        <h2 className="text-lg font-semibold mb-4 text-brand-cloud tracking-tight">New Client</h2>
        <div className="space-y-3">
          <PersonForm label="Primary Client" person={primary} onChange={setPrimary} />

          {spouse !== null ? (
            <PersonForm
              label="Spouse / Partner"
              person={spouse}
              onChange={setSpouse}
              onRemove={() => setSpouse(null)}
            />
          ) : (
            <button
              onClick={() => setSpouse(emptyPerson())}
              className="w-full py-2 border border-dashed border-white/15 hover:border-brand-mint/50 rounded-xl text-xs text-brand-cloud/60 hover:text-brand-cloud transition"
            >
              + Add Spouse / Partner
            </button>
          )}

          {preview && (
            <p className="text-xs text-brand-cloud/60 px-1">
              Name: <span className="text-brand-cloud font-medium">{preview}</span>
            </p>
          )}

          <div>
            <p className="text-[11px] uppercase tracking-wider text-brand-cloud/50 mb-2">Transaction type</p>
            <div className="flex gap-2">
              {(['buyer', 'seller', 'buyer & seller'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setClientType(t)}
                  className={`flex-1 py-2 rounded-lg text-xs font-medium capitalize transition border ${
                    clientType === t
                      ? 'bg-brand-mint/15 border-brand-mint/60 text-brand-cloud'
                      : 'bg-white/[0.03] border-white/10 text-brand-cloud/70 hover:bg-white/[0.06]'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-2 mt-5">
          <button
            onClick={onClose}
            className="flex-1 py-2 rounded-lg bg-white/[0.05] border border-white/10 text-sm text-brand-cloud hover:bg-white/[0.08] transition"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={loading || !buildName()}
            className="flex-1 py-2 rounded-lg bg-brand-mint text-brand-navy text-sm font-semibold hover:bg-brand-mint/90 transition disabled:opacity-50"
          >
            {loading ? 'Creating…' : 'Create Client'}
          </button>
        </div>
      </div>
    </div>
  )

  return typeof document !== 'undefined' ? createPortal(modal, document.body) : modal
}

function clientInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function IconChevronLeft({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 18l-6-6 6-6" />
    </svg>
  )
}

function IconChevronRight({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 18l6-6-6-6" />
    </svg>
  )
}

function IconPanelOff({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
    </svg>
  )
}

function IconTrash({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14zM10 11v6M14 11v6"
      />
    </svg>
  )
}

export type SidebarShell = 'expanded' | 'collapsed'

type SidebarProps = {
  shell?: SidebarShell
  onExpandShell?: () => void
  onCollapseToRail?: () => void
  onHideShell?: () => void
}

export default function Sidebar({
  shell = 'expanded',
  onExpandShell,
  onCollapseToRail,
  onHideShell,
}: SidebarProps) {
  const { projects, activeProjectId, setProjects, setActiveProject } = useAppStore()
  const [showModal, setShowModal] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleDeleteClient = async (p: Project) => {
    if (
      !window.confirm(
        `Delete “${p.name}” permanently? This removes chat history, documents, synced email in reco-pilot, and all other data for this client.`,
      )
    ) {
      return
    }
    setDeletingId(p.id)
    try {
      await api.deleteProject(p.id)
      const next = projects.filter(x => x.id !== p.id)
      setProjects(next)
      if (activeProjectId === p.id) {
        setActiveProject(next[0]?.id ?? null)
      }
    } catch (e) {
      console.error(e)
      window.alert('Could not delete this client. Please try again.')
    } finally {
      setDeletingId(null)
    }
  }

  const handleCreated = (project: Project) => {
    setProjects([project, ...projects])
    setActiveProject(project.id)
    setShowModal(false)
  }

  const modal = showModal ? (
    <NewClientModal onClose={() => setShowModal(false)} onCreated={handleCreated} />
  ) : null

  if (shell === 'collapsed') {
    return (
      <div className="flex flex-col h-full min-h-0 bg-black/25 backdrop-blur-sm border-r border-white/5 items-center py-2 gap-2">
        <button
          type="button"
          onClick={onExpandShell}
          title="Expand sidebar"
          className="p-1.5 rounded-lg text-brand-cloud/60 hover:text-brand-cloud hover:bg-white/[0.06] transition"
        >
          <IconChevronRight className="w-5 h-5" />
        </button>
        <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-navy to-brand-slate border border-white/10 flex items-center justify-center shrink-0">
          <span className="text-brand-cloud text-xs font-semibold tracking-tight">r.</span>
        </div>
        <button
          type="button"
          onClick={() => setShowModal(true)}
          title="New client"
          className="w-9 h-9 rounded-lg text-lg font-medium leading-none text-brand-cloud bg-white/[0.06] border border-white/10 hover:bg-white/[0.1] hover:border-brand-mint/40 transition"
        >
          +
        </button>

        <div className="flex-1 min-h-0 overflow-y-auto w-full flex flex-col items-center gap-1.5 py-1 px-1">
          {projects.length === 0 && (
            <p className="text-brand-cloud/35 text-[10px] text-center px-1 leading-snug">No clients</p>
          )}
          {projects.map(p => {
            const isActive = activeProjectId === p.id
            const busy = deletingId === p.id
            return (
              <div key={p.id} className="group relative h-10 w-10 shrink-0">
                <button
                  type="button"
                  title={p.name}
                  disabled={busy}
                  onClick={() => setActiveProject(p.id)}
                  className={`absolute inset-0 flex items-center justify-center rounded-xl text-[11px] font-semibold tracking-tight transition border ${
                    isActive
                      ? 'bg-brand-mint/20 border-brand-mint text-brand-cloud ring-1 ring-brand-mint/50'
                      : 'bg-white/[0.04] border-white/10 text-brand-cloud/85 hover:bg-white/[0.08]'
                  } ${busy ? 'opacity-40' : ''}`}
                >
                  {clientInitials(p.name)}
                </button>
                <button
                  type="button"
                  title="Delete client"
                  disabled={busy}
                  onClick={e => {
                    e.stopPropagation()
                    void handleDeleteClient(p)
                  }}
                  className="absolute bottom-0 right-0 z-10 flex h-[18px] w-[18px] items-center justify-center rounded-md border border-white/15 bg-brand-navy/95 text-brand-cloud/65 opacity-0 shadow-sm transition hover:border-red-400/50 hover:bg-red-950/90 hover:text-red-200 group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-mint/45 disabled:pointer-events-none"
                >
                  <IconTrash className="h-2.5 w-2.5" />
                </button>
              </div>
            )
          })}
        </div>

        {onHideShell && (
          <button
            type="button"
            onClick={onHideShell}
            title="Hide sidebar completely"
            className="p-1.5 rounded-lg text-brand-cloud/35 hover:text-brand-cloud/70 hover:bg-white/[0.05] transition"
          >
            <IconPanelOff className="w-4 h-4" />
          </button>
        )}

        <UserProfile compact />

        {modal}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full min-h-0 bg-black/25 backdrop-blur-sm border-r border-white/5">
      <div className="p-4 border-b border-white/5 shrink-0">
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-navy to-brand-slate border border-white/10 flex items-center justify-center shrink-0">
              <span className="text-brand-cloud text-xs font-semibold tracking-tight">r.</span>
            </div>
            <h1 className="font-wordmark-app text-xl font-semibold text-brand-cloud tracking-[0.06em] truncate">reco-pilot</h1>
          </div>
          <div className="flex shrink-0 gap-0.5">
            {onCollapseToRail && (
              <button
                type="button"
                onClick={onCollapseToRail}
                title="Minimize to slim strip"
                className="p-1.5 rounded-lg text-brand-cloud/45 hover:text-brand-cloud hover:bg-white/[0.06] transition"
              >
                <IconChevronLeft className="w-4 h-4" />
              </button>
            )}
            {onHideShell && (
              <button
                type="button"
                onClick={onHideShell}
                title="Hide sidebar completely"
                className="p-1.5 rounded-lg text-brand-cloud/45 hover:text-brand-cloud hover:bg-white/[0.06] transition"
              >
                <IconPanelOff className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="w-full py-2 rounded-lg text-sm font-medium text-brand-cloud bg-white/[0.05] border border-white/10 hover:bg-white/[0.1] hover:border-brand-mint/40 transition"
        >
          + New Client
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto py-2">
        {projects.length === 0 && (
          <p className="text-brand-cloud/40 text-xs text-center px-4 py-8 leading-relaxed">
            No clients yet. Create your first client above.
          </p>
        )}
        {projects.map(p => {
          const isActive = activeProjectId === p.id
          const busy = deletingId === p.id
          return (
            <div
              key={p.id}
              className={`group flex w-full items-stretch border-l-2 transition ${
                isActive ? 'bg-white/[0.04] border-brand-mint' : 'border-transparent hover:bg-white/[0.02]'
              }`}
            >
              <button
                type="button"
                disabled={busy}
                onClick={() => setActiveProject(p.id)}
                className="min-w-0 flex-1 px-4 py-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-mint/35 disabled:opacity-40"
              >
                <div className="min-w-0">
                  <p
                    className={`text-sm truncate ${isActive ? 'text-brand-cloud font-medium' : 'text-brand-cloud/85'}`}
                    title={p.name}
                  >
                    {p.name}
                  </p>
                  <div className="mt-1 flex min-w-0 items-center justify-between gap-2">
                    <p className="shrink-0 text-[11px] text-brand-cloud/40">
                      {new Date(p.created_at).toLocaleDateString()}
                    </p>
                    <span
                      className={`min-w-0 max-w-[11rem] shrink truncate text-[10px] px-2 py-0.5 rounded-full font-medium uppercase tracking-wide ${clientTypeSidebarPillClass(
                        p.client_type,
                      )}`}
                      title={p.client_type}
                    >
                      {p.client_type}
                    </span>
                  </div>
                </div>
              </button>
              <button
                type="button"
                title="Delete client"
                disabled={busy}
                onClick={e => {
                  e.stopPropagation()
                  void handleDeleteClient(p)
                }}
                className="shrink-0 px-2.5 text-brand-cloud/35 transition hover:bg-red-950/40 hover:text-red-300 group-hover:text-brand-cloud/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-mint/35 disabled:pointer-events-none"
              >
                <IconTrash className="mx-auto h-4 w-4" />
              </button>
            </div>
          )
        })}
      </div>

      {modal}

      <UserProfile />
    </div>
  )
}
