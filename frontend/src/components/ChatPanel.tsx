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
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

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
      <div className="px-6 py-4 border-b border-gray-800 bg-gray-900">
        <h2 className="font-semibold text-white">{projectName}</h2>
        <p className="text-xs text-gray-500">REMI AI Assistant</p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-14 h-14 rounded-full bg-blue-600 flex items-center justify-center text-2xl font-bold mb-4">
              R
            </div>
            <p className="text-gray-400 text-sm">
              Ask REMI anything about <span className="text-white font-medium">{projectName}</span>
            </p>
            <p className="text-gray-600 text-xs mt-1">
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
            <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold mr-2 shrink-0">
              R
            </div>
            <div className="bg-gray-800 rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-4 py-3 border-t border-gray-800 bg-gray-900">
        <div className="flex items-end gap-2 bg-gray-800 rounded-xl px-3 py-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            placeholder="Ask REMI about this client… (Enter to send, Shift+Enter for newline)"
            rows={1}
            className="flex-1 bg-transparent resize-none outline-none text-sm text-gray-100 placeholder-gray-500 py-1 max-h-[150px]"
          />
          {isStreaming ? (
            <button
              onClick={cancelStream}
              className="shrink-0 w-8 h-8 rounded-lg bg-red-600 hover:bg-red-500 flex items-center justify-center transition"
              title="Stop"
            >
              <span className="w-3 h-3 bg-white rounded-sm" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="shrink-0 w-8 h-8 rounded-lg bg-blue-600 hover:bg-blue-500 flex items-center justify-center transition disabled:opacity-40"
              title="Send"
            >
              <svg className="w-4 h-4 text-white rotate-90" fill="currentColor" viewBox="0 0 24 24">
                <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
