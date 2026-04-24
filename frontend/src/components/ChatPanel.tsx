import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { useAppStore } from '../store/appStore'
import { useChat } from '../hooks/useChat'
import * as api from '../api/client'
import ChatMessageBubble from './ChatMessage'
import type { AccountEntitlements, ChatMessage, Document, LlmOptionsResponse, Project } from '../types'

interface Props {
  project: Pick<Project, 'id' | 'name' | 'llm_provider' | 'llm_model'>
  onProjectUpdated: (p: Project) => void
}

function usageCaption(e: AccountEntitlements): { line: string } {
  if (e.is_admin) {
    return { line: 'Unlimited usage (admin)' }
  }
  if (e.subscription_tier === 'pro') {
    const cap = e.pro_included_tokens_per_month
    return {
      line: `${e.pro_tokens_remaining.toLocaleString()} / ${cap.toLocaleString()} billable units left this month`,
    }
  }
  const cap = e.trial_max_tokens
  return {
    line: `${e.trial_tokens_remaining.toLocaleString()} / ${cap.toLocaleString()} trial units left`,
  }
}

export default function ChatPanel({ project, onProjectUpdated }: Props) {
  const projectId = project.id
  const projectName = project.name
  const { messages, isStreaming, streamingContent, setMessages, documents } = useAppStore()
  const { sendMessage, cancelStream } = useChat(projectId)
  const [input, setInput] = useState('')
  const [llmOpts, setLlmOpts] = useState<LlmOptionsResponse | null>(null)
  const [llmLoading, setLlmLoading] = useState(true)
  const [llmSaving, setLlmSaving] = useState(false)
  const [entitlements, setEntitlements] = useState<AccountEntitlements | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const projectDocs = useMemo(
    () => documents.filter(d => d.project_id === projectId).sort((a, b) => a.filename.localeCompare(b.filename)),
    [documents, projectId],
  )
  const [attachedDocs, setAttachedDocs] = useState<{ id: string; filename: string }[]>([])
  const [mentionOpen, setMentionOpen] = useState(false)
  const [mentionQuery, setMentionQuery] = useState('')

  const mentionFiltered = useMemo(() => {
    const q = mentionQuery.trim().toLowerCase()
    if (!q) return projectDocs
    return projectDocs.filter(d => d.filename.toLowerCase().includes(q))
  }, [projectDocs, mentionQuery])

  const refreshEntitlements = useCallback(() => {
    void api.getAccountEntitlements().then(setEntitlements).catch(() => setEntitlements(null))
  }, [])

  useEffect(() => {
    let cancelled = false
    setLlmLoading(true)
    ;(async () => {
      try {
        const o = await api.getLlmOptions()
        if (!cancelled) setLlmOpts(o)
      } catch {
        if (!cancelled) setLlmOpts(null)
      } finally {
        if (!cancelled) setLlmLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [projectId, project.llm_provider, project.llm_model])

  useEffect(() => {
    refreshEntitlements()
  }, [projectId, refreshEntitlements])

  const usageCaptionText = entitlements ? usageCaption(entitlements) : null
  const canSendChat = entitlements == null || entitlements.can_send_chat
  const activeProviderId = (() => {
    if (!llmOpts?.providers?.length) {
      return project.llm_provider || llmOpts?.default_provider || ''
    }
    const pref = project.llm_provider || llmOpts.default_provider
    return llmOpts.providers.some(p => p.id === pref) ? pref : llmOpts.default_provider
  })()
  const activeProv = llmOpts?.providers.find(p => p.id === activeProviderId) || llmOpts?.providers[0]
  const modelIds = new Set((activeProv?.models ?? []).map(m => m.id))
  const activeModelId =
    project.llm_model && modelIds.has(project.llm_model)
      ? project.llm_model
      : activeProv?.models[0]?.id || ''
  const modelSelectDisabled =
    llmLoading || !llmOpts?.providers.length || isStreaming || llmSaving || !canSendChat

  const persistLlm = async (fields: Partial<Pick<Project, 'llm_provider' | 'llm_model'>>) => {
    setLlmSaving(true)
    try {
      const updated = await api.updateProject(projectId, fields)
      onProjectUpdated(updated)
    } catch {
      /* keep previous project; errors surface via network / server */
    } finally {
      setLlmSaving(false)
    }
  }

  useEffect(() => {
    // 'auto' = jump to bottom with no scroll animation (smooth looked jarring when switching clients).
    bottomRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' })
  }, [projectId, messages, streamingContent])

  const pickDocument = (doc: Document) => {
    setAttachedDocs(prev => (prev.some(p => p.id === doc.id) ? prev : [...prev, { id: doc.id, filename: doc.filename }]))
    const el = textareaRef.current
    if (el) {
      const v = el.value
      const cursor = el.selectionStart ?? v.length
      const before = v.slice(0, cursor)
      const after = v.slice(cursor)
      const at = before.lastIndexOf('@')
      if (at >= 0) {
        setInput(before.slice(0, at) + after)
        requestAnimationFrame(() => {
          const pos = at
          el.setSelectionRange(pos, pos)
        })
      }
    }
    setMentionOpen(false)
    setMentionQuery('')
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isStreaming || !canSendChat) return
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    const atts = attachedDocs.map(d => ({ type: 'document' as const, id: d.id }))
    setAttachedDocs([])
    await sendMessage(text, atts.length ? { attachments: atts } : undefined)
    refreshEntitlements()
  }

  const startNewSession = async () => {
    if (isStreaming || !canSendChat) return
    if (messages.length === 0) return
    if (!window.confirm('Start a new session? This clears the chat for this client (no undo).')) return
    try {
      await api.clearMessages(projectId)
      setMessages([])
    } catch {
      /* error toast could go here */
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Escape' && mentionOpen) {
      e.preventDefault()
      setMentionOpen(false)
      return
    }
    if (e.key === 'Enter' && !e.shiftKey && mentionOpen && mentionFiltered.length > 0) {
      e.preventDefault()
      pickDocument(mentionFiltered[0])
      return
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const v = e.target.value
    setInput(v)
    const el = e.target
    const cursor = el.selectionStart ?? v.length
    const before = v.slice(0, cursor)
    const match = before.match(/(?:^|\s)@([^\s@]*)$/)
    if (match) {
      setMentionOpen(true)
      setMentionQuery(match[1] ?? '')
    } else {
      setMentionOpen(false)
    }
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 150) + 'px'
  }

  const streamingMsg: ChatMessage | null = isStreaming && streamingContent
    ? { id: '__streaming__', project_id: projectId, role: 'assistant', content: streamingContent, created_at: '' }
    : null

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/5 bg-black/20">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="font-semibold text-brand-cloud tracking-tight">{projectName}</h2>
            <p className="text-[11px] uppercase tracking-[0.15em] text-brand-cloud/40 mt-0.5">Reco Pilot</p>
          </div>
          {messages.length > 0 && (
            <button
              type="button"
              onClick={() => void startNewSession()}
              disabled={isStreaming || !canSendChat}
              className="shrink-0 text-[10px] px-2 py-1 rounded-md border border-white/15 text-brand-cloud/55 hover:text-brand-cloud/80 hover:border-white/25 transition disabled:opacity-40"
              title="Clear chat and start a new session"
            >
              New session
            </button>
          )}
        </div>
        {entitlements && !entitlements.can_send_chat && (
          <p className="mt-2 text-[11px] text-amber-200/90 leading-relaxed">
            You’ve reached your token allowance for now. Upgrade to Pro or add usage to keep chatting.
            {entitlements.upgrade_url ? (
              <>
                {' '}
                <a
                  href={entitlements.upgrade_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-brand-mint underline-offset-2 hover:underline"
                >
                  Open billing
                </a>
              </>
            ) : null}
          </p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-navy to-brand-slate border border-white/10 flex items-center justify-center text-2xl font-semibold text-brand-cloud tracking-tight mb-4">
              R
            </div>
            <p className="text-brand-cloud/70 text-sm">
              Ask Reco anything about <span className="text-brand-cloud font-medium">{projectName}</span>
            </p>
            <p className="text-brand-cloud/40 text-xs mt-1">
              Offers, negotiations, purchase agreements, market analysis…
            </p>
          </div>
        )}
        {messages.map(msg => (
          <ChatMessageBubble key={msg.id} message={msg} isAdmin={!!entitlements?.is_admin} />
        ))}
        {streamingMsg && (
          <ChatMessageBubble message={streamingMsg} isAdmin={!!entitlements?.is_admin} />
        )}
        {isStreaming && !streamingContent && (
          <div className="flex justify-start mb-4">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-navy to-brand-slate border border-white/10 flex items-center justify-center text-xs font-semibold text-brand-cloud mr-2 shrink-0">
              R
            </div>
            <div className="bg-white/[0.03] backdrop-blur-sm border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 bg-brand-mint/70 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <div className="w-1.5 h-1.5 bg-brand-mint/70 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <div className="w-1.5 h-1.5 bg-brand-mint/70 rounded-full animate-bounce" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-4 pt-3 pb-2 border-t border-white/5 bg-black/20">
        <p className="text-[10px] text-brand-cloud/35 mb-1.5 px-0.5">
          Type <span className="text-brand-cloud/50">@</span> to attach a document for this message.
        </p>
        {attachedDocs.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {attachedDocs.map(d => (
              <span
                key={d.id}
                className="inline-flex items-center gap-1 max-w-full rounded-md border border-brand-mint/25 bg-brand-mint/10 px-2 py-0.5 text-[11px] text-brand-cloud/90"
              >
                <span className="truncate">{d.filename}</span>
                <button
                  type="button"
                  className="shrink-0 text-brand-cloud/50 hover:text-brand-cloud"
                  disabled={isStreaming}
                  onClick={() => setAttachedDocs(prev => prev.filter(x => x.id !== d.id))}
                  aria-label={`Remove ${d.filename}`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="relative">
          {mentionOpen && (
            <ul
              className="absolute bottom-full left-0 right-0 z-20 mb-1 max-h-40 overflow-y-auto rounded-lg border border-white/15 bg-brand-navy/95 py-1 shadow-lg backdrop-blur-sm"
              role="listbox"
            >
              {projectDocs.length === 0 ? (
                <li className="px-2 py-1.5 text-[11px] text-brand-cloud/45">No documents for this client yet</li>
              ) : mentionFiltered.length === 0 ? (
                <li className="px-2 py-1.5 text-[11px] text-brand-cloud/45">No matching documents</li>
              ) : (
                mentionFiltered.slice(0, 12).map(d => (
                  <li key={d.id}>
                    <button
                      type="button"
                      className="w-full truncate px-2 py-1.5 text-left text-[11px] text-brand-cloud/90 hover:bg-white/10"
                      onMouseDown={ev => ev.preventDefault()}
                      onClick={() => pickDocument(d)}
                    >
                      {d.filename}
                    </button>
                  </li>
                ))
              )}
            </ul>
          )}
        <div className="flex items-end gap-2 bg-white/[0.04] backdrop-blur-sm border border-white/10 rounded-xl px-3 py-2 focus-within:border-brand-mint/40 transition">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={isStreaming || !canSendChat}
            placeholder="Ask Reco about this client… (Enter to send, Shift+Enter for newline)"
            rows={1}
            className="flex-1 bg-transparent resize-none outline-none text-sm text-brand-cloud placeholder-brand-cloud/35 py-1 max-h-[150px] disabled:opacity-50"
          />
          {isStreaming ? (
            <button
              onClick={cancelStream}
              className="shrink-0 w-8 h-8 rounded-lg bg-red-500/80 hover:bg-red-500 flex items-center justify-center transition"
              title="Stop"
            >
              <span className="w-3 h-3 bg-white rounded-sm" />
            </button>
          ) : (
            <button
              onClick={() => void handleSend()}
              disabled={!input.trim() || !canSendChat}
              className="shrink-0 w-8 h-8 rounded-lg bg-brand-mint hover:bg-brand-mint/90 flex items-center justify-center transition disabled:opacity-40 disabled:bg-white/10"
              title="Send"
            >
              <svg className="w-4 h-4 text-brand-navy rotate-90" fill="currentColor" viewBox="0 0 24 24">
                <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
              </svg>
            </button>
          )}
        </div>
        </div>
        <div className="mt-1.5 mb-1 px-1 flex flex-col gap-1.5">
          <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between sm:gap-3 min-w-0">
            {!llmLoading && llmOpts && llmOpts.providers.length > 0 ? (
              <div className="flex flex-wrap items-center gap-1.5 min-w-0">
                <label className="sr-only" htmlFor={`chat-llm-provider-${projectId}`}>
                  Provider
                </label>
                <select
                  id={`chat-llm-provider-${projectId}`}
                  disabled={modelSelectDisabled}
                  value={activeProviderId}
                  onChange={e => {
                    const pid = e.target.value
                    const p = llmOpts.providers.find(x => x.id === pid)
                    const mid = p?.models[0]?.id
                    if (p && mid) void persistLlm({ llm_provider: pid, llm_model: mid })
                  }}
                  className="max-w-[min(100%,11rem)] h-7 rounded-md bg-white/[0.04] border border-white/10 px-2 text-[11px] text-brand-cloud/75 outline-none focus:border-brand-mint/35 focus:ring-1 focus:ring-brand-mint/25 disabled:opacity-45"
                >
                  {llmOpts.providers.map(p => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
                <label className="sr-only" htmlFor={`chat-llm-model-${projectId}`}>
                  Model
                </label>
                <select
                  id={`chat-llm-model-${projectId}`}
                  disabled={modelSelectDisabled}
                  value={activeModelId}
                  onChange={e => {
                    void persistLlm({
                      llm_provider: activeProviderId,
                      llm_model: e.target.value,
                    })
                  }}
                  className="min-w-0 flex-1 sm:max-w-[min(100%,16rem)] h-7 rounded-md bg-white/[0.04] border border-white/10 px-2 text-[11px] text-brand-cloud/75 outline-none focus:border-brand-mint/35 focus:ring-1 focus:ring-brand-mint/25 disabled:opacity-45"
                >
                  {(activeProv?.models ?? []).map(m => (
                    <option key={m.id} value={m.id}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>
            ) : llmLoading ? (
              <p className="text-[10px] text-brand-cloud/25">Loading models…</p>
            ) : (
              <p className="text-[10px] text-brand-cloud/25">No assistant models configured on the server.</p>
            )}

            {usageCaptionText && (
              <p className="flex flex-wrap items-baseline justify-end gap-x-2 gap-y-0.5 text-[10px] leading-relaxed text-brand-cloud/28 sm:text-right sm:min-w-0 sm:max-w-[55%]">
                <span className="min-w-0">{usageCaptionText.line}</span>
                {entitlements?.upgrade_url ? (
                  <a
                    href={entitlements.upgrade_url}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 text-brand-cloud/45 hover:text-brand-cloud/65 transition-colors underline-offset-[3px] hover:underline"
                  >
                    Upgrade
                  </a>
                ) : null}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
