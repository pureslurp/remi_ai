import { useState, useEffect } from 'react'
import { useAppStore } from '../store/appStore'
import * as api from '../api/client'
import type { Project } from '../types'
import { getClientPanelCopy } from '../lib/clientPanelCopy'
import TransactionPanel from './TransactionPanel'
import DocumentList from './DocumentList'
import SyncStatus from './SyncStatus'

/** Tooltip so saved filters stay discoverable without expanding the UI */
function gmailAddressTitle(project: Project, email: string): string {
  const raw = project.gmail_address_rules || {}
  const entry = Object.entries(raw).find(([k]) => k.toLowerCase() === email.toLowerCase())?.[1]
  const bits: string[] = []
  if (entry?.keywords?.length) bits.push(`subject: ${entry.keywords.join(', ')}`)
  if (entry?.after_date) bits.push(`after ${String(entry.after_date).slice(0, 10)}`)
  if (!bits.length && (project.gmail_keywords || []).length) {
    bits.push(`inherits global keywords: ${(project.gmail_keywords || []).join(', ')}`)
  }
  return bits.length ? `${email} (${bits.join(' · ')})` : email
}

function Section({ title, defaultOpen = true, children }: {
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <section>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between mb-2 group"
      >
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.15em] text-brand-cloud/55 group-hover:text-brand-cloud transition">
          {title}
        </h3>
        <span className="text-brand-cloud/35 group-hover:text-brand-cloud/65 transition text-xs">{open ? '▲' : '▼'}</span>
      </button>
      {open && children}
    </section>
  )
}

interface Props {
  project: Project
  onProjectUpdated: (p: Project) => void
}

export default function ClientSettings({ project, onProjectUpdated }: Props) {
  const { properties, transactions, documents, emailThreads, setDocuments, setEmailThreads, googleConnected } = useAppStore()

  const [name, setName] = useState(project.name)
  const [phone, setPhone] = useState(project.phone || '')
  const [notes, setNotes] = useState(project.notes || '')
  const [emailInput, setEmailInput] = useState('')
  const [newEmailKeywords, setNewEmailKeywords] = useState('')
  const [newEmailAfterDate, setNewEmailAfterDate] = useState('')
  const [driveUrl, setDriveUrl] = useState(project.drive_folder_id || '')
  const [gmailSyncing, setGmailSyncing] = useState(false)
  const [driveSyncing, setDriveSyncing] = useState(false)
  const [gmailMsg, setGmailMsg] = useState('')
  const [driveMsg, setDriveMsg] = useState('')
  const [clearConfirm, setClearConfirm] = useState(false)

  useEffect(() => {
    setName(project.name)
    setPhone(project.phone || '')
    setNotes(project.notes || '')
    setDriveUrl(project.drive_folder_id || '')
  }, [project.id])

  const save = async (fields: Partial<Project>) => {
    const updated = await api.updateProject(project.id, fields)
    onProjectUpdated(updated)
  }

  const addEmail = async () => {
    const email = emailInput.trim().toLowerCase()
    if (!email || project.email_addresses.includes(email)) return

    const kwRaw = newEmailKeywords.trim()
    const keywords = kwRaw ? kwRaw.split(',').map(k => k.trim()).filter(Boolean) : []
    const afterDate = newEmailAfterDate.trim() || null

    const raw = { ...(project.gmail_address_rules || {}) }
    if (keywords.length > 0 || afterDate) {
      raw[email] = { keywords, after_date: afterDate }
    }

    const updated = await api.updateProject(project.id, {
      email_addresses: [...project.email_addresses, email],
      gmail_address_rules: raw,
    })
    onProjectUpdated(updated)
    setEmailInput('')
    setNewEmailKeywords('')
    setNewEmailAfterDate('')
  }

  const removeEmail = async (email: string) => {
    const raw = { ...(project.gmail_address_rules || {}) }
    const key = Object.keys(raw).find(k => k.toLowerCase() === email.toLowerCase())
    if (key) delete raw[key]
    const updated = await api.updateProject(project.id, {
      email_addresses: project.email_addresses.filter(e => e !== email),
      gmail_address_rules: raw,
    })
    onProjectUpdated(updated)
  }

  const saveDriveUrl = async () => {
    const updated = await api.updateProject(project.id, { drive_folder_id: driveUrl.trim() || null as unknown as string })
    onProjectUpdated(updated)
  }

  const syncGmail = async () => {
    setGmailSyncing(true)
    setGmailMsg('')
    try {
      const result = await api.syncGmail(project.id)
      setGmailMsg(result.message)
      const threads = await api.listEmails(project.id)
      setEmailThreads(threads)
      const updated = await api.updateProject(project.id, {})
      onProjectUpdated(updated)
    } catch (err: unknown) {
      setGmailMsg(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setGmailSyncing(false)
    }
  }

  const syncDrive = async () => {
    setDriveSyncing(true)
    setDriveMsg('')
    try {
      const result = await api.syncDrive(project.id)
      setDriveMsg(result.message)
      const docs = await api.listDocuments(project.id)
      setDocuments(docs)
    } catch (err: unknown) {
      setDriveMsg(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setDriveSyncing(false)
    }
  }

  const clearChat = async () => {
    await api.clearMessages(project.id)
    useAppStore.getState().setMessages([])
    setClearConfirm(false)
  }

  const gmailThreadsForProject = emailThreads.filter(t => t.project_id === project.id)
  const panelCopy = getClientPanelCopy(project.client_type)

  return (
    <div className={`overflow-y-auto h-full ${panelCopy.panelAccentClass}`}>
      <div className="p-4 space-y-5">

        {/* Profile */}
        <Section title="Client">
          <div className="space-y-2">
            <input
              className="w-full bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-sm text-brand-cloud placeholder-brand-cloud/35 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
              value={name}
              onChange={e => setName(e.target.value)}
              onBlur={() => name !== project.name && save({ name })}
              placeholder="Client name"
            />
            <div className="flex items-center gap-2 px-3 py-2 bg-white/[0.03] border border-white/10 rounded-lg">
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium uppercase tracking-wide border ${
                project.client_type === 'buyer'
                  ? 'bg-brand-mint/10 text-brand-mint/90 border-brand-mint/20'
                  : project.client_type === 'seller'
                  ? 'bg-amber-300/10 text-amber-200/90 border-amber-300/20'
                  : 'bg-brand-cloud/10 text-brand-cloud/80 border-brand-cloud/20'
              }`}>
                {project.client_type}
              </span>
            </div>
            <input
              className="w-full bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-sm text-brand-cloud placeholder-brand-cloud/35 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              onBlur={() => phone !== (project.phone || '') && save({ phone })}
              placeholder="Phone"
            />
            <textarea
              className="w-full bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-sm text-brand-cloud placeholder-brand-cloud/35 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50 resize-none"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              onBlur={() => notes !== (project.notes || '') && save({ notes })}
              placeholder={panelCopy.agentNotesPlaceholder}
              rows={3}
            />
          </div>
        </Section>

        {/* Transaction */}
        <Section title={panelCopy.transactionsSectionTitle}>
          <TransactionPanel
            projectId={project.id}
            clientType={project.client_type}
            properties={properties}
            transactions={transactions}
            salePropertyId={project.client_type === 'buyer & seller' ? project.sale_property_id : undefined}
            onProjectUpdated={onProjectUpdated}
          />
        </Section>

        {/* Documents */}
        <Section title={`Documents (${documents.filter(d => d.project_id === project.id).length})`} defaultOpen={false}>
          <DocumentList projectId={project.id} documents={documents.filter(d => d.project_id === project.id)} />
        </Section>

        {/* Gmail */}
        <Section title="Gmail Sync" defaultOpen={false}>
          <p className="text-xs text-brand-cloud/50 mb-2 leading-relaxed">
            Threads match when the client’s email appears in From or To. Optional filters below apply only when you add an address — hover a chip to see saved rules.
          </p>
          {(project.gmail_keywords || []).length > 0 && (
            <p className="text-xs text-amber-300/90 mb-2">
              Global keywords still apply to addresses added without filters: {(project.gmail_keywords || []).join(', ')}
            </p>
          )}
          <div className="flex flex-wrap gap-1 mb-3">
            {project.email_addresses.map(email => (
              <span
                key={email}
                title={gmailAddressTitle(project, email)}
                className="flex items-center gap-1 bg-white/[0.04] border border-white/10 text-xs px-2 py-1 rounded-full text-brand-cloud/85 max-w-full"
              >
                <span className="truncate">{email}</span>
                <button type="button" onClick={() => removeEmail(email)} className="text-brand-cloud/45 hover:text-red-300 transition shrink-0">×</button>
              </span>
            ))}
          </div>
          <div className="space-y-2 mb-3 rounded-xl border border-white/10 bg-white/[0.02] p-3">
            <div className="flex gap-2">
              <input
                className="flex-1 bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-xs text-brand-cloud placeholder-brand-cloud/35 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
                value={emailInput}
                onChange={e => setEmailInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addEmail()}
                placeholder="Email address…"
              />
              <button type="button" onClick={addEmail} className="bg-white/[0.06] border border-white/10 hover:bg-white/[0.1] px-3 py-2 rounded-lg text-xs text-brand-cloud transition shrink-0">
                Add
              </button>
            </div>
            <p className="text-[11px] text-brand-cloud/45">Optional — only for this address</p>
            <input
              className="w-full bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-xs text-brand-cloud placeholder-brand-cloud/35 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
              value={newEmailKeywords}
              onChange={e => setNewEmailKeywords(e.target.value)}
              placeholder="Subject must contain (comma-separated)…"
            />
            <label className="flex items-center gap-2 text-[11px] text-brand-cloud/55">
              <span className="shrink-0">On or after</span>
              <input
                type="date"
                className="flex-1 min-w-0 bg-white/[0.04] border border-white/10 rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50 text-brand-cloud/85"
                value={newEmailAfterDate}
                onChange={e => setNewEmailAfterDate(e.target.value)}
              />
            </label>
          </div>
          {!googleConnected && (
            <p className="text-xs text-amber-300 mb-2">Connect Google in settings to enable sync.</p>
          )}
          <SyncStatus
            label="Gmail"
            lastSync={project.last_gmail_sync}
            onSync={syncGmail}
            syncing={gmailSyncing}
            message={gmailMsg}
          />
          <p className="text-[11px] text-brand-cloud/45 mt-2 leading-relaxed">
            Message bodies stay in this Gmail section (and in chat context). Documents lists files only —
            mostly Drive plus PDF or Word attachments from mail.
          </p>
          {gmailThreadsForProject.length > 0 && (
            <div className="mt-3 space-y-2 border-t border-white/10 pt-3">
              <p className="text-[11px] font-medium uppercase tracking-wider text-brand-cloud/55">
                Synced threads ({gmailThreadsForProject.length})
              </p>
              <ul className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {gmailThreadsForProject.map(thread => (
                    <li
                      key={thread.id}
                      className="rounded-lg border border-white/10 bg-white/[0.03] px-2 py-2 text-xs"
                    >
                      <p className="font-medium text-brand-cloud/90 truncate" title={thread.subject || ''}>
                        {thread.subject || '(no subject)'}
                      </p>
                      <p className="text-[11px] text-brand-cloud/45 mt-0.5">
                        {(thread.messages?.length ?? 0)} message(s)
                        {thread.last_message_date
                          ? ` · last ${new Date(thread.last_message_date).toLocaleString()}`
                          : ''}
                      </p>
                      {(thread.messages?.length ?? 0) > 0 && (
                        <ul className="mt-2 space-y-1 border-t border-white/5 pt-2 text-[11px] text-brand-cloud/60">
                          {thread.messages!.slice(-5).map(m => (
                            <li key={m.id} className="pl-1 border-l border-white/10">
                              <span className="text-brand-cloud/45">
                                {m.date ? new Date(m.date).toLocaleDateString() : ''}
                                {m.from_addr ? ` · ${m.from_addr.slice(0, 48)}` : ''}
                              </span>
                              {m.snippet && (
                                <p className="text-brand-cloud/60 mt-0.5 line-clamp-2">{m.snippet}</p>
                              )}
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
              </ul>
            </div>
          )}
        </Section>

        {/* Drive */}
        <Section title="Google Drive Sync" defaultOpen={false}>
          <div className="flex gap-2 mb-3">
            <input
              className="flex-1 bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-xs text-brand-cloud placeholder-brand-cloud/35 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
              value={driveUrl}
              onChange={e => setDriveUrl(e.target.value)}
              onBlur={saveDriveUrl}
              placeholder="Paste Drive folder URL or ID"
            />
          </div>
          <SyncStatus
            label="Drive"
            lastSync={project.last_drive_sync}
            onSync={syncDrive}
            syncing={driveSyncing}
            message={driveMsg}
          />
        </Section>

        {/* Danger zone */}
        <section className="border-t border-white/5 pt-4">
          {clearConfirm ? (
            <div className="bg-red-500/10 border border-red-400/30 rounded-xl p-3">
              <p className="text-xs text-red-100 mb-2">Clear all chat history for this client?</p>
              <div className="flex gap-2">
                <button onClick={() => setClearConfirm(false)} className="flex-1 py-1.5 bg-white/[0.05] border border-white/10 rounded text-xs text-brand-cloud hover:bg-white/[0.08] transition">Cancel</button>
                <button onClick={clearChat} className="flex-1 py-1.5 bg-red-500/80 rounded text-xs text-white hover:bg-red-500 transition">Clear</button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setClearConfirm(true)}
              className="w-full py-2 text-xs text-brand-cloud/45 hover:text-red-300 transition"
            >
              Clear Chat History
            </button>
          )}
        </section>

      </div>
    </div>
  )
}
