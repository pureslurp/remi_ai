import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '../store/appStore'
import { useChat } from '../hooks/useChat'
import ChatMessageBubble from './ChatMessage'
import type { ChatMessage } from '../types'

interface Props {
  projectId: string
  projectName: string
}

export default function ChatPanel({ projectId, projectName }: Props) {
  const { messages, isStreaming, streamingContent } = useAppStore()
  const { sendMessage, cancelStream } = useChat(projectId)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    // 'auto' = jump to bottom with no scroll animation (smooth looked jarring when switching clients).
    bottomRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' })
  }, [projectId, messages, streamingContent])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isStreaming) return
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    sendMessage(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'
  }

  const streamingMsg: ChatMessage | null = isStreaming && streamingContent
    ? { id: '__streaming__', project_id: projectId, role: 'assistant', content: streamingContent, created_at: '' }
    : null

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/5 bg-black/20">
        <h2 className="font-semibold text-brand-cloud tracking-tight">{projectName}</h2>
        <p className="text-[11px] uppercase tracking-[0.15em] text-brand-cloud/40 mt-0.5">Kova Assistant</p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-navy to-brand-slate border border-white/10 flex items-center justify-center text-2xl font-semibold text-brand-cloud tracking-tight mb-4">
              K
            </div>
            <p className="text-brand-cloud/70 text-sm">
              Ask Kova anything about <span className="text-brand-cloud font-medium">{projectName}</span>
            </p>
            <p className="text-brand-cloud/40 text-xs mt-1">
              Offers, negotiations, purchase agreements, market analysis…
            </p>
          </div>
        )}
        {messages.map(msg => (
          <ChatMessageBubble key={msg.id} message={msg} />
        ))}
        {streamingMsg && <ChatMessageBubble message={streamingMsg} />}
        {isStreaming && !streamingContent && (
          <div className="flex justify-start mb-4">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-navy to-brand-slate border border-white/10 flex items-center justify-center text-xs font-semibold text-brand-cloud mr-2 shrink-0">
              K
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

      <div className="px-4 py-3 border-t border-white/5 bg-black/20">
        <div className="flex items-end gap-2 bg-white/[0.04] backdrop-blur-sm border border-white/10 rounded-xl px-3 py-2 focus-within:border-brand-mint/40 transition">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            placeholder="Ask Kova about this client… (Enter to send, Shift+Enter for newline)"
            rows={1}
            className="flex-1 bg-transparent resize-none outline-none text-sm text-brand-cloud placeholder-brand-cloud/35 py-1 max-h-[150px]"
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
              onClick={handleSend}
              disabled={!input.trim()}
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
    </div>
  )
}
