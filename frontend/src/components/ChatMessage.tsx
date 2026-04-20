import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { normalizeChatMarkdown } from '../lib/normalizeChatMarkdown'
import type { ChatMessage as Msg } from '../types'

interface Props {
  message: Msg
}

export default function ChatMessageBubble({ message }: Props) {
  const isUser = message.role === 'user'
  const assistantMarkdown = useMemo(
    () => normalizeChatMarkdown(message.content),
    [message.content],
  )

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-navy to-brand-slate border border-white/10 flex items-center justify-center text-xs font-semibold text-brand-cloud mr-2 mt-1 shrink-0 tracking-tight">
          K
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
      </div>
    </div>
  )
}
