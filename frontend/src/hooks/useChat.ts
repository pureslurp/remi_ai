import { useRef } from 'react'
import { API_ROOT } from '../api/client'
import { useAppStore } from '../store/appStore'
import type { ChatMessage } from '../types'

export function useChat(projectId: string | null) {
  const { setIsStreaming, setStreamingContent, addMessage, setMessages, messages } = useAppStore()
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = async (text: string) => {
    if (!projectId || !text.trim()) return

    // Optimistically add user message
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      project_id: projectId,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }
    addMessage(userMsg)
    setIsStreaming(true)
    setStreamingContent('')

    abortRef.current = new AbortController()
    let accumulated = ''

    try {
      const res = await fetch(`${API_ROOT}/projects/${projectId}/chat`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
        signal: abortRef.current.signal,
      })

      if (!res.ok) throw new Error(`${res.status}`)
      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const raw = decoder.decode(value, { stream: true })
        // Parse SSE lines: "data: <text>\n\n"
        const lines = raw.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const raw = line.slice(6).trim()
            if (raw === '[DONE]') break
            try {
              const chunk: string = JSON.parse(raw)
              if (chunk.startsWith('[ERROR] ')) {
                throw new Error(chunk.slice(8))
              }
              accumulated += chunk
              setStreamingContent(accumulated)
            } catch (parseErr) {
              if (parseErr instanceof Error && parseErr.message !== raw) throw parseErr
              // non-JSON line (e.g. keep-alive comment) — ignore
            }
          }
        }
      }

      // Commit final assistant message
      if (accumulated) {
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          project_id: projectId,
          role: 'assistant',
          content: accumulated,
          created_at: new Date().toISOString(),
        }
        addMessage(assistantMsg)
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        if (accumulated) {
          addMessage({
            id: crypto.randomUUID(),
            project_id: projectId,
            role: 'assistant',
            content: accumulated,
            created_at: new Date().toISOString(),
          })
        }
      } else {
        const msg = err instanceof Error ? err.message : String(err)
        addMessage({
          id: crypto.randomUUID(),
          project_id: projectId,
          role: 'assistant',
          content: `⚠️ Error: ${msg}`,
          created_at: new Date().toISOString(),
        })
      }
    } finally {
      setIsStreaming(false)
      setStreamingContent('')
    }
  }

  const cancelStream = () => {
    abortRef.current?.abort()
  }

  return { sendMessage, cancelStream }
}
