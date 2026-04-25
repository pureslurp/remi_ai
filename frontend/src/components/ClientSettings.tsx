import { useState, useEffect, useMemo } from 'react'
import { useAppStore } from '../store/appStore'
import * as api from '../api/client'
import type { EmailThread, Project, Transaction } from '../types'
import { getClientPanelCopy } from '../lib/clientPanelCopy'
import TransactionPanel from './TransactionPanel'
import DocumentList from './DocumentList'
import SyncStatus from './SyncStatus'

type KeywordMode = 'include' | 'exclude'

/** Mirrors backend `_effective_rule`: local keywords override global; empty local list inherits global. */
function gmailAddressEffectiveFilters(project: Project, email: string): {
  keywords: string[]
  afterDate: string | null | undefined
  keywordMode: KeywordMode
} {
  const addrL = email.trim().toLowerCase()
  const raw = project.gmail_address_rules || {}
  const entry = Object.entries(raw).find(([k]) => k.trim().toLowerCase() === addrL)?.[1]
  const globalKw = (project.gmail_keywords || []).filter(Boolean)
  const globalMode: KeywordMode = project.gmail_keyword_mode === 'exclude' ? 'exclude' : 'include'
  if (entry && typeof entry === 'object') {
    const localKw = Array.isArray(entry.keywords) ? entry.keywords.filter(Boolean) : []
    const kw = localKw.length > 0 ? localKw : globalKw
    const mode: KeywordMode = entry.keyword_mode === 'exclude' ? 'exclude' : 'include'
    return { keywords: kw, afterDate: entry.after_date, keywordMode: mode }
  }
  return { keywords: globalKw, afterDate: undefined, keywordMode: globalMode }
}

/** Short line shown under each address chip (native `title` is slow / invisible when empty). */
function gmailAddressFilterSummary(project: Project, email: string): string {
  const { keywords, afterDate, keywordMode } = gmailAddressEffectiveFilters(project, email)
  const parts: string[] = []
  if (keywords.length > 0) {
    parts.push(
      keywordMode === 'exclude'
        ? `Do not include if subject contains: ${keywords.join(', ')}`
        : `Subject must contain one of: ${keywords.join(', ')}`
    )
  } else {
    parts.push('Any subject')
  }
  if (afterDate) {
    parts.push(`on or after ${String(afterDate).slice(0, 10)}`)
  }
  return parts.join(' · ')
}

function gmailAddressTitle(project: Project, email: string): string {
  return `${email} — ${gmailAddressFilterSummary(project, email)}`
}

/** One short label for a collapsed address row (not the full rule sentence). */
function gmailAddressShortBadge(project: Project, email: string): string {
  const { keywords, afterDate, keywordMode } = gmailAddressEffectiveFilters(project, email)
  if (!keywords.length && !afterDate) return 'All subjects'
  const bits: string[] = []
  if (keywords.length) {
    bits.push(keywordMode === 'exclude' ? 'Excludes phrases' : 'Requires phrase')
  }
  if (afterDate) bits.push('Has date cutoff')
  return bits.join(' · ')
}

function globalGmailSummaryLine(project: Project): string {
  const kw = (project.gmail_keywords || []).filter(Boolean)
  if (!kw.length) return 'No default phrase filters'
  const verb = project.gmail_keyword_mode === 'exclude' ? 'Skip if subject has' : 'Subject must include'
  const sample = kw.slice(0, 2).join(', ')
  return `${verb}: ${sample}${kw.length > 2 ? '…' : ''}`
}

function Section({ title, defaultOpen = true, children }: {
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <section className="min-w-0">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="group mb-2 flex w-full min-w-0 items-center justify-between gap-2"
      >
        <h3 className="min-w-0 flex-1 truncate text-left text-[11px] font-semibold uppercase tracking-[0.15em] text-brand-cloud/55 transition group-hover:text-brand-cloud">
          {title}
        </h3>
        <span className="shrink-0 text-xs text-brand-cloud/35 transition group-hover:text-brand-cloud/65">{open ? '▲' : '▼'}</span>
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
  const { properties, transactions, documents, emailThreads, setDocuments, setEmailThreads, googleConnected, authProvider } =
    useAppStore()

  const [name, setName] = useState(project.name)
  const [phone, setPhone] = useState(project.phone || '')
  const [notes, setNotes] = useState(project.notes || '')
  const [emailInput, setEmailInput] = useState('')
  const [newEmailKeywords, setNewEmailKeywords] = useState('')
  const [newEmailKeywordMode, setNewEmailKeywordMode] = useState<KeywordMode>('include')
  const [newEmailAfterDate, setNewEmailAfterDate] = useState('')
  const [globalKwInput, setGlobalKwInput] = useState('')
  const [globalKeywordMode, setGlobalKeywordMode] = useState<KeywordMode>('include')
  const [gmailDefaultsOpen, setGmailDefaultsOpen] = useState(false)
  const [expandedClientEmail, setExpandedClientEmail] = useState<string | null>(null)
  const [driveUrl, setDriveUrl] = useState(project.drive_folder_id || '')
  const [gmailSyncing, setGmailSyncing] = useState(false)
  const [driveSyncing, setDriveSyncing] = useState(false)
  const [gmailMsg, setGmailMsg] = useState('')
  const [driveMsg, setDriveMsg] = useState('')
  const [clearConfirm, setClearConfirm] = useState(false)
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null)
  const [taggingThreadId, setTaggingThreadId] = useState<string | null>(null)

  useEffect(() => {
    setName(project.name)
    setPhone(project.phone || '')
    setNotes(project.notes || '')
    setDriveUrl(project.drive_folder_id || '')
    setGlobalKwInput((project.gmail_keywords || []).join(', '))
    setGlobalKeywordMode(project.gmail_keyword_mode === 'exclude' ? 'exclude' : 'include')
    setExpandedClientEmail(null)
  }, [project.id, project.gmail_keywords, project.gmail_keyword_mode])

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
    if (keywords.length > 0 || afterDate || newEmailKeywordMode !== 'include') {
      raw[email] = {
        keywords,
        after_date: afterDate,
        keyword_mode: newEmailKeywordMode,
      }
    }

    const updated = await api.updateProject(project.id, {
      email_addresses: [...project.email_addresses, email],
      gmail_address_rules: raw,
    })
    onProjectUpdated(updated)
    setEmailInput('')
    setNewEmailKeywords('')
    setNewEmailKeywordMode('include')
    setNewEmailAfterDate('')
  }

  const saveGlobalGmailFilters = async () => {
    const keywords = globalKwInput
      .split(',')
      .map(k => k.trim())
      .filter(Boolean)
    const updated = await api.updateProject(project.id, {
      gmail_keywords: keywords,
      gmail_keyword_mode: globalKeywordMode,
    })
    onProjectUpdated(updated)
  }

  const setAddressKeywordMode = async (email: string, mode: KeywordMode) => {
    const raw = { ...(project.gmail_address_rules || {}) }
    const key =
      Object.keys(raw).find(k => k.trim().toLowerCase() === email.trim().toLowerCase()) || email
    const prev = raw[key] && typeof raw[key] === 'object' ? { ...raw[key] } : {}
    raw[key] = { ...prev, keyword_mode: mode }
    const updated = await api.updateProject(project.id, { gmail_address_rules: raw })
    onProjectUpdated(updated)
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
  const projectTransactions = useMemo(
    () => transactions.filter(t => t.project_id === project.id),
    [transactions, project.id],
  )
  const panelCopy = getClientPanelCopy(project.client_type)

  const transactionLabel = (t: Transaction) => {
    const addr = t.property_id ? properties.find(p => p.id === t.property_id)?.address : undefined
    return (addr && String(addr).trim()) || t.status || t.id.slice(0, 8)
  }

  const tagThreadToTransaction = async (thread: EmailThread, transactionId: string | null) => {
    setTaggingThreadId(thread.id)
    try {
      const updated = await api.tagEmailThread(project.id, thread.id, { transaction_id: transactionId })
      setEmailThreads(emailThreads.map(th => (th.id === thread.id ? updated : th)))
    } catch (err: unknown) {
      setGmailMsg(err instanceof Error ? err.message : 'Could not update tag')
    } finally {
      setTaggingThreadId(null)
    }
  }

  const removeSyncedThread = async (thread: EmailThread) => {
    setDeletingThreadId(thread.id)
    try {
      await api.deleteEmailThread(project.id, thread.id)
      const msgIds = new Set((thread.messages || []).map(m => m.id))
      setEmailThreads(emailThreads.filter(t => t.id !== thread.id))
      if (msgIds.size > 0) {
        setDocuments(
          documents.filter(
            d =>
              !(
                d.project_id === project.id &&
                d.gmail_message_id &&
                msgIds.has(d.gmail_message_id)
              ),
          ),
        )
      }
    } catch (err: unknown) {
      setGmailMsg(err instanceof Error ? err.message : 'Could not remove thread')
    } finally {
      setDeletingThreadId(null)
    }
  }

  return (
    <div className={`h-full min-w-0 overflow-y-auto ${panelCopy.panelAccentClass}`}>
      <div className="min-w-0 space-y-5 p-4">

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
          {authProvider === 'email' ? (
            <p className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2.5 text-[11px] leading-relaxed text-brand-cloud/65">
              You&apos;re signed in with email and password. Chat and documents you upload manually work as usual.
              Gmail and Google Drive sync are not available on this account type.
            </p>
          ) : (
            <>
          <p className="text-xs text-brand-cloud/50 mb-3 leading-relaxed">
            A thread syncs when the client’s address appears in From, To, or Cc. Use subject phrases below to narrow or exclude mail when adding an address — or open an existing address for details.
          </p>

          <button
            type="button"
            onClick={() => setGmailDefaultsOpen(o => !o)}
            aria-expanded={gmailDefaultsOpen}
            className="mb-2 flex w-full items-center gap-2 rounded-lg border border-white/10 bg-white/[0.02] px-2.5 py-2 text-left transition hover:bg-white/[0.04] focus:outline-none focus:ring-1 focus:ring-brand-mint/40"
          >
            <span className="text-[10px] text-brand-cloud/40 w-4 shrink-0 select-none">{gmailDefaultsOpen ? '▼' : '▶'}</span>
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-medium uppercase tracking-wider text-brand-cloud/50">Workspace defaults</p>
              <p className="truncate text-[11px] text-brand-cloud/65">{globalGmailSummaryLine(project)}</p>
            </div>
          </button>
          {gmailDefaultsOpen && (
            <div className="mb-3 space-y-2 rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2.5">
              <p className="text-[10px] text-brand-cloud/45 leading-snug">
                Used for every address until you set phrases when adding that address. “Exclude” skips blasts (e.g. prospective-home sends).
              </p>
              <input
                className="w-full bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-xs text-brand-cloud placeholder-brand-cloud/35 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
                value={globalKwInput}
                onChange={e => setGlobalKwInput(e.target.value)}
                placeholder="Comma-separated phrases…"
              />
              <div className="flex flex-wrap items-center gap-2">
                <select
                  className="min-w-0 flex-1 bg-white/[0.04] border border-white/10 rounded-lg px-2 py-1.5 text-xs text-brand-cloud/90 outline-none focus:ring-1 focus:ring-brand-mint/50"
                  value={globalKeywordMode}
                  onChange={e => setGlobalKeywordMode(e.target.value as KeywordMode)}
                >
                  <option value="include">Include — keep if subject matches</option>
                  <option value="exclude">Exclude — skip if subject matches</option>
                </select>
                <button
                  type="button"
                  onClick={() => void saveGlobalGmailFilters()}
                  className="shrink-0 rounded-lg border border-white/10 bg-white/[0.08] px-3 py-1.5 text-xs text-brand-cloud transition hover:bg-white/[0.12]"
                >
                  Save
                </button>
              </div>
            </div>
          )}

          <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-brand-cloud/50">Client addresses</p>
          <ul className="mb-3 space-y-1">
            {project.email_addresses.map(email => {
              const open = expandedClientEmail === email
              return (
                <li
                  key={email}
                  className="overflow-hidden rounded-lg border border-white/10 bg-white/[0.02]"
                >
                  <div className="flex items-stretch gap-0">
                    <button
                      type="button"
                      aria-expanded={open}
                      title={gmailAddressTitle(project, email)}
                      onClick={() => setExpandedClientEmail(open ? null : email)}
                      className="flex min-w-0 flex-1 items-center gap-2 px-2 py-2 text-left transition hover:bg-white/[0.04] focus:outline-none focus:ring-1 focus:ring-inset focus:ring-brand-mint/30"
                    >
                      <span className="w-4 shrink-0 text-center text-[10px] text-brand-cloud/35 select-none">{open ? '▼' : '▶'}</span>
                      <span className="truncate text-xs text-brand-cloud/90">{email}</span>
                      <span className="ml-1 max-w-[42%] shrink-0 truncate text-right text-[10px] text-brand-cloud/40">
                        {gmailAddressShortBadge(project, email)}
                      </span>
                    </button>
                    <button
                      type="button"
                      onClick={() => void removeEmail(email)}
                      className="shrink-0 border-l border-white/10 px-2.5 text-brand-cloud/40 transition hover:bg-red-500/10 hover:text-red-300"
                      aria-label={`Remove ${email}`}
                    >
                      ×
                    </button>
                  </div>
                  {open && (
                    <div className="space-y-2 border-t border-white/5 bg-black/20 px-3 py-2.5">
                      <p className="text-[11px] leading-relaxed text-brand-cloud/55">{gmailAddressFilterSummary(project, email)}</p>
                      <div className="flex flex-col gap-1">
                        <label htmlFor={`kw-mode-${email}`} className="text-[10px] uppercase tracking-wide text-brand-cloud/45">
                          Subject phrases apply as
                        </label>
                        <select
                          id={`kw-mode-${email}`}
                          className="w-full rounded-md border border-white/10 bg-white/[0.04] px-2 py-1.5 text-xs text-brand-cloud/90 outline-none focus:ring-1 focus:ring-brand-mint/50"
                          value={gmailAddressEffectiveFilters(project, email).keywordMode}
                          onChange={e => void setAddressKeywordMode(email, e.target.value as KeywordMode)}
                        >
                          <option value="include">Include — keep when subject matches a phrase</option>
                          <option value="exclude">Exclude — skip when subject matches a phrase</option>
                        </select>
                      </div>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>

          <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-brand-cloud/50">Add address</p>
          <div className="mb-3 space-y-2 rounded-xl border border-white/10 bg-white/[0.02] p-3">
            <div className="flex gap-2">
              <input
                className="min-w-0 flex-1 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-brand-cloud placeholder-brand-cloud/35 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
                value={emailInput}
                onChange={e => setEmailInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addEmail()}
                placeholder="Email address…"
              />
              <button
                type="button"
                onClick={addEmail}
                className="shrink-0 rounded-lg border border-white/10 bg-white/[0.06] px-3 py-2 text-xs text-brand-cloud transition hover:bg-white/[0.1]"
              >
                Add
              </button>
            </div>
            <p className="text-[10px] text-brand-cloud/45">Optional filters for this address only</p>
            <input
              className="w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-brand-cloud placeholder-brand-cloud/35 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
              value={newEmailKeywords}
              onChange={e => setNewEmailKeywords(e.target.value)}
              placeholder="Subject phrases, comma-separated…"
            />
            <select
              className="w-full rounded-lg border border-white/10 bg-white/[0.04] px-2 py-1.5 text-xs text-brand-cloud/90 outline-none focus:ring-1 focus:ring-brand-mint/50"
              value={newEmailKeywordMode}
              onChange={e => setNewEmailKeywordMode(e.target.value as KeywordMode)}
            >
              <option value="include">Include — sync only if subject matches a phrase</option>
              <option value="exclude">Exclude — do not sync if subject matches a phrase</option>
            </select>
            <label className="flex items-center gap-2 text-[11px] text-brand-cloud/55">
              <span className="shrink-0">On or after</span>
              <input
                type="date"
                className="min-w-0 flex-1 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-brand-cloud/85 outline-none focus:ring-1 focus:ring-brand-mint/50 focus:border-brand-mint/50"
                value={newEmailAfterDate}
                onChange={e => setNewEmailAfterDate(e.target.value)}
              />
            </label>
          </div>
          {authProvider === 'google' && !googleConnected && (
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
                      <div className="flex items-start gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-brand-cloud/90 truncate" title={thread.subject || ''}>
                            {thread.subject || '(no subject)'}
                          </p>
                          <p className="mt-0.5 text-[11px] text-brand-cloud/45">
                            {(thread.messages?.length ?? 0)} message(s)
                            {thread.last_message_date
                              ? ` · last ${new Date(thread.last_message_date).toLocaleString()}`
                              : ''}
                          </p>
                          <label className="mt-2 block text-[10px] font-medium uppercase tracking-wider text-brand-cloud/40">
                            Tag to transaction
                            <select
                              className="mt-1 w-full rounded-md border border-white/10 bg-white/[0.04] px-2 py-1.5 text-[11px] text-brand-cloud/90 outline-none focus:ring-1 focus:ring-brand-mint/40"
                              value={thread.transaction_id ?? ''}
                              disabled={taggingThreadId === thread.id}
                              onChange={e => {
                                const v = e.target.value
                                void tagThreadToTransaction(thread, v === '' ? null : v)
                              }}
                            >
                              <option value="">Unassigned</option>
                              {projectTransactions.map(t => (
                                <option key={t.id} value={t.id}>
                                  {transactionLabel(t)}
                                </option>
                              ))}
                            </select>
                          </label>
                          {thread.tag_source === 'manual' && (
                            <p className="mt-1 text-[10px] text-brand-mint/70">Manual tag — resync won’t replace it</p>
                          )}
                        </div>
                        <button
                          type="button"
                          disabled={deletingThreadId === thread.id}
                          title="Remove from this client only (mail stays in Gmail)"
                          onClick={() => void removeSyncedThread(thread)}
                          className="shrink-0 rounded-md border border-white/10 px-2 py-1 text-[11px] text-brand-cloud/50 transition hover:border-red-400/40 hover:bg-red-500/10 hover:text-red-200 disabled:opacity-40"
                        >
                          {deletingThreadId === thread.id ? '…' : 'Remove'}
                        </button>
                      </div>
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
            </>
          )}
        </Section>

        {/* Drive */}
        <Section title="Google Drive Sync" defaultOpen={false}>
          {authProvider === 'email' && (
            <p className="mb-3 text-[11px] leading-relaxed text-brand-cloud/55">
              Drive folder sync isn&apos;t available on email-only accounts. Add files under{' '}
              <span className="text-brand-cloud/70">Documents</span> above instead.
            </p>
          )}
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
