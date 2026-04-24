import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { normalizeChatMarkdown } from '../lib/normalizeChatMarkdown'
import type { ChatMessage as Msg, ChatReferencedItems } from '../types'

interface Props {
  message: Msg
  /** When true, show provider token counts from `referenced_items.admin_usage` (admins only). */
  isAdmin?: boolean
}

function ReferencedBlock({ r, isAdmin }: { r: ChatReferencedItems; isAdmin?: boolean }) {
  const hasDocs = r.documents && r.documents.length > 0
  const hasEmails = r.emails && r.emails.length > 0
  const fall = [r.doc_fallback, r.email_fallback].filter(Boolean)
  const u = isAdmin ? r.admin_usage : undefined
  const hasContextList = hasDocs || hasEmails || fall.length > 0
  if (!hasContextList && !u) return null

  const summaryLabel =
    hasContextList && u ? 'Context & tokens' : hasContextList ? 'Context used for this answer' : 'Tokens (admin)'

  return (
    <details className="group mt-3 pt-2 border-t border-white/10 text-[11px] text-brand-cloud/45">
      <summary
        className="list-none cursor-pointer select-none flex items-center gap-1.5 font-medium text-brand-cloud/55 hover:text-brand-cloud/75 transition-colors [&::-webkit-details-marker]:hidden"
      >
        <svg
          viewBox="0 0 12 12"
          aria-hidden="true"
          className="w-2.5 h-2.5 transition-transform duration-150 group-open:rotate-90 text-brand-cloud/40"
        >
          <path d="M4 2.5l3.5 3.5L4 9.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {summaryLabel}
      </summary>
      <div className="mt-2 pl-4">
        {hasContextList && (
          <>
            {hasDocs && (
              <p className="mb-0.5">
                <span className="text-brand-cloud/50">Documents: </span>
                {r.documents!.map(d => d.label).join(', ')}
              </p>
            )}
            {hasEmails && (
              <p>
                <span className="text-brand-cloud/50">Emails: </span>
                {r.emails!.map(e => e.label).join(' · ')}
              </p>
            )}
            {fall.length > 0 && (
              <p className="mt-1 text-brand-cloud/30">(Fallback: {fall.join(', ')})</p>
            )}
          </>
        )}
        {u && (
          <div className={hasContextList ? 'mt-2 pt-2 border-t border-white/[0.07]' : ''}>
            <p className="font-medium text-brand-cloud/55 mb-0.5">Tokens (admin)</p>
            <p className="text-brand-cloud/50">
              ~{u.input_tokens.toLocaleString()} in · ~{u.output_tokens.toLocaleString()} out ·{' '}
              <span className="text-brand-cloud/65 tabular-nums">
                {u.billable_units.toLocaleString()} billable units
              </span>
              <span className="text-brand-cloud/35"> — counts toward plan caps</span>
            </p>
          </div>
        )}
      </div>
    </details>
  )
}

export default function ChatMessageBubble({ message, isAdmin }: Props) {
  const isUser = message.role === 'user'
  const assistantMarkdown = useMemo(
    () => normalizeChatMarkdown(message.content),
    [message.content],
  )

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-navy to-brand-slate border border-white/10 flex items-center justify-center text-xs font-semibold text-brand-cloud mr-2 mt-1 shrink-0 tracking-tight">
          R
        </div>
      )}
      <div
        className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'max-w-[75%] bg-brand-mint text-brand-navy rounded-br-sm'
            : 'w-full bg-white/[0.03] backdrop-blur-sm border border-white/10 text-brand-cloud rounded-bl-sm'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap font-medium">{message.content}</p>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
              ul: ({ children }) => (
                <ul className="list-disc pl-5 mb-3 space-y-1 marker:text-brand-mint/60">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal pl-5 mb-3 space-y-1 marker:text-brand-mint/60">{children}</ol>
              ),
              li: ({ children }) => <li className="leading-relaxed">{children}</li>,
              strong: ({ children }) => (
                <strong className="font-semibold text-brand-cloud">{children}</strong>
              ),
              em: ({ children }) => <em className="italic text-brand-cloud/80">{children}</em>,
              h1: ({ children }) => (
                <h1 className="text-base font-bold text-brand-cloud mb-2 mt-3 first:mt-0 tracking-tight">{children}</h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-sm font-bold text-brand-cloud mb-2 mt-3 first:mt-0 tracking-tight">{children}</h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-sm font-semibold text-brand-cloud mb-1 mt-2 first:mt-0">{children}</h3>
              ),
              hr: () => <hr className="border-white/10 my-3" />,
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-brand-mint/60 pl-3 my-2 text-brand-cloud/80 italic">
                  {children}
                </blockquote>
              ),
              code: ({ children, className }) => {
                const isBlock = className?.includes('language-')
                return isBlock ? (
                  <pre className="bg-black/40 border border-white/10 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono">
                    <code>{children}</code>
                  </pre>
                ) : (
                  <code className="bg-black/30 border border-white/10 px-1.5 py-0.5 rounded text-xs font-mono text-brand-mint">
                    {children}
                  </code>
                )
              },
              table: ({ children }) => (
                <div className="overflow-x-auto my-3 rounded-lg border border-white/10">
                  <table className="min-w-full text-left text-sm border-collapse">{children}</table>
                </div>
              ),
              thead: ({ children }) => <thead className="bg-white/[0.06]">{children}</thead>,
              tbody: ({ children }) => <tbody className="divide-y divide-white/10">{children}</tbody>,
              tr: ({ children }) => <tr>{children}</tr>,
              th: ({ children }) => (
                <th className="px-3 py-2 font-semibold text-brand-cloud border-r border-white/10 last:border-r-0 align-top">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="px-3 py-2 text-brand-cloud/90 border-r border-white/5 last:border-r-0 align-top">
                  {children}
                </td>
              ),
            }}
          >
            {assistantMarkdown}
          </ReactMarkdown>
        )}
        {!isUser && message.referenced_items && (
          <ReferencedBlock r={message.referenced_items} isAdmin={isAdmin} />
        )}
      </div>
    </div>
  )
}
