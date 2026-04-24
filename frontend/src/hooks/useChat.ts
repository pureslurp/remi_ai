import { useRef } from 'react'
import { API_ROOT, getMessages } from '../api/client'
import { useAppStore } from '../store/appStore'
import type { ChatMessage } from '../types'

type QuotaDetail = {
  message?: string
  instruction?: string
  upgrade_url?: string | null
}

function quotaAssistantMarkdown(detail: QuotaDetail): string {
  const title = '### Plan limit reached\n\n'
  const body = [detail.message, detail.instruction].filter(Boolean).join('\n\n')
  const link =
    detail.upgrade_url != null && detail.upgrade_url !== ''
      ? `\n\n[Upgrade or manage billing](${detail.upgrade_url})`
      : ''
  return title + body + link
}

export type ChatSendOptions = {
  attachments?: { type: 'document'; id: string }[]
}

export function useChat(projectId: string | null) {
  const { setIsStreaming, setStreamingContent, addMessage, setMessages } = useAppStore()
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = async (text: string, opts?: ChatSendOptions): Promise<boolean> => {
    if (!projectId || !text.trim()) return false

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
        body: JSON.stringify({
          message: text,
          attachments: opts?.attachments ?? [],
        }),
        signal: abortRef.current.signal,
      })

      if (res.status === 402) {
        let detail: QuotaDetail = {}
        try {
          const j = (await res.json()) as { detail?: unknown }
          const d = j.detail
          if (d && typeof d === 'object' && !Array.isArray(d)) {
            detail = d as QuotaDetail
          }
        } catch {
          /* ignore */
        }
        addMessage({
          id: crypto.randomUUID(),
          project_id: projectId,
          role: 'assistant',
          content: quotaAssistantMarkdown(detail),
          created_at: new Date().toISOString(),
        })
        return false
      }

      if (import.meta.env.DEV) {
        const tok = res.headers.get('X-Context-Tokens')
        if (tok) {
          try {
            const parsed = JSON.parse(tok) as Record<string, number>
            console.info('[chat] X-Context-Tokens (est. input breakdown)', parsed)
          } catch {
            console.info('[chat] X-Context-Tokens', tok)
          }
        }
      }

      if (!res.ok) {
        let msg = `Request failed (${res.status})`
        try {
          const j = (await res.json()) as { detail?: unknown }
          const d = j.detail
          if (typeof d === 'string') msg = d
          else if (d && typeof d === 'object' && 'message' in d) {
            const m = (d as { message?: string }).message
            const url = (d as { upgrade_url?: string | null }).upgrade_url
            msg = m || msg
            if (url) msg = `${msg} ${url}`
          }
        } catch {
          /* ignore */
        }
        throw new Error(msg)
      }
      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const raw = decoder.decode(value, { stream: true })
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
            }
          }
        }
      }

      if (accumulated) {
        // Optimistic assistant bubble; then replace with server state (ids + referenced_items)
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          project_id: projectId,
          role: 'assistant',
          content: accumulated,
          created_at: new Date().toISOString(),
        }
        addMessage(assistantMsg)
        try {
          const serverMsgs = await getMessages(projectId)
          setMessages(serverMsgs)
        } catch {
          /* keep optimistic */
        }
      }
      return true
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
        return false
      }
      const msg = err instanceof Error ? err.message : String(err)
      addMessage({
        id: crypto.randomUUID(),
        project_id: projectId,
        role: 'assistant',
        content: `⚠️ Error: ${msg}`,
        created_at: new Date().toISOString(),
      })
      return false
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
