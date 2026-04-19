import { useState } from 'react'
import { useAppStore } from '../store/appStore'
import * as api from '../api/client'
import type { Project } from '../types'
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
    <div className="bg-gray-700/50 rounded-xl p-3 space-y-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-400">{label}</span>
        {onRemove && (
          <button onClick={onRemove} className="text-xs text-gray-500 hover:text-red-400 transition">
            Remove
          </button>
        )}
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 bg-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="First name"
          value={person.firstName}
          onChange={set('firstName')}
        />
        <input
          className="flex-1 bg-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Last name"
          value={person.lastName}
          onChange={set('lastName')}
        />
      </div>
      <input
        className="w-full bg-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
        placeholder="Email address"
        type="email"
        value={person.email}
        onChange={set('email')}
      />
      <input
        className="w-full bg-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
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
    // If spouse has same last name (or no last name entered), show "John & Mary Smith"
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

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 overflow-y-auto py-8">
      <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md shadow-xl mx-4">
        <h2 className="text-lg font-semibold mb-4">New Client</h2>
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
              className="w-full py-2 border border-dashed border-gray-600 hover:border-gray-400 rounded-xl text-xs text-gray-400 hover:text-gray-200 transition"
            >
              + Add Spouse / Partner
            </button>
          )}

          {preview && (
            <p className="text-xs text-gray-400 px-1">
              Name: <span className="text-white font-medium">{preview}</span>
            </p>
          )}

          <div>
            <p className="text-xs text-gray-400 mb-2">Transaction type</p>
            <div className="flex gap-2">
              {(['buyer', 'seller', 'buyer & seller'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setClientType(t)}
                  className={`flex-1 py-2 rounded-lg text-xs font-medium capitalize transition ${
                    clientType === t ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
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
            className="flex-1 py-2 rounded-lg bg-gray-700 text-sm hover:bg-gray-600 transition"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={loading || !buildName()}
            className="flex-1 py-2 rounded-lg bg-blue-600 text-sm font-medium hover:bg-blue-500 transition disabled:opacity-50"
          >
            {loading ? 'Creating…' : 'Create Client'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Sidebar() {
  const { projects, activeProjectId, setProjects, setActiveProject } = useAppStore()
  const [showModal, setShowModal] = useState(false)

  const handleCreated = (project: Project) => {
    setProjects([project, ...projects])
    setActiveProject(project.id)
    setShowModal(false)
  }

  return (
    <div className="flex flex-col h-full min-h-0 bg-gray-900 border-r border-gray-800">
      <div className="p-4 border-b border-gray-800 shrink-0">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-lg font-bold text-white">REMI AI</h1>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="w-full py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition"
        >
          + New Client
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto py-2">
        {projects.length === 0 && (
          <p className="text-gray-500 text-xs text-center px-4 py-8">
            No clients yet. Create your first client above.
          </p>
        )}
        {projects.map(p => (
          <button
            key={p.id}
            onClick={() => setActiveProject(p.id)}
            className={`w-full text-left px-4 py-3 transition hover:bg-gray-800 ${
              activeProjectId === p.id ? 'bg-gray-800 border-l-2 border-blue-500' : ''
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium truncate flex-1">{p.name}</span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  p.client_type === 'buyer'
                    ? 'bg-blue-900 text-blue-300'
                    : p.client_type === 'seller'
                    ? 'bg-emerald-900 text-emerald-300'
                    : 'bg-purple-900 text-purple-300'
                }`}
              >
                {p.client_type}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              {new Date(p.created_at).toLocaleDateString()}
            </p>
          </button>
        ))}
      </div>

      {showModal && (
        <NewClientModal onClose={() => setShowModal(false)} onCreated={handleCreated} />
      )}

      <UserProfile />
    </div>
  )
}
