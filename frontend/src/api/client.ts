import type {
  Project,
  Property,
  Transaction,
  KeyDate,
  ChatMessage,
  Document,
  EmailThread,
  LlmOptionsResponse,
  AccountEntitlements,
} from '../types'

const rawBase = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') || ''
export const API_ROOT = rawBase ? `${rawBase}/api` : '/api'

function headersToRecord(init: HeadersInit | undefined): Record<string, string> {
  if (!init) return {}
  if (init instanceof Headers) {
    const o: Record<string, string> = {}
    init.forEach((v, k) => {
      o[k] = v
    })
    return o
  }
  if (Array.isArray(init)) return Object.fromEntries(init)
  return { ...init }
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const method = (opts?.method ?? 'GET').toUpperCase()
  const withJsonBody = !['GET', 'HEAD'].includes(method)
  const { headers: extraInit, ...restOpts } = opts ?? {}
  const merged: Record<string, string> = headersToRecord(extraInit)
  if (withJsonBody && !merged['Content-Type'] && !merged['content-type']) {
    merged['Content-Type'] = 'application/json'
  }
  const res = await fetch(API_ROOT + path, {
    ...restOpts,
    credentials: 'include',
    headers: merged,
    ...(path === '/auth/session' ? { cache: 'no-store' as RequestCache } : {}),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// Projects
export const listProjects = () => req<Project[]>('/projects')
export const createProject = (data: Partial<Project>) =>
  req<Project>('/projects', { method: 'POST', body: JSON.stringify(data) })
export const updateProject = (id: string, data: Partial<Project>) =>
  req<Project>(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteProject = (id: string) =>
  req<void>(`/projects/${id}`, { method: 'DELETE' })

// Properties
export const listProperties = (projectId: string) =>
  req<Property[]>(`/projects/${projectId}/properties`)
export const createProperty = (projectId: string, data: Partial<Property>) =>
  req<Property>(`/projects/${projectId}/properties`, { method: 'POST', body: JSON.stringify(data) })
export const updateProperty = (projectId: string, propId: string, data: Partial<Property>) =>
  req<Property>(`/projects/${projectId}/properties/${propId}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteProperty = (projectId: string, propId: string) =>
  req<void>(`/projects/${projectId}/properties/${propId}`, { method: 'DELETE' })

// Transactions
export const listTransactions = (projectId: string) =>
  req<Transaction[]>(`/projects/${projectId}/transactions`)
export const createTransaction = (projectId: string, data: Partial<Transaction>) =>
  req<Transaction>(`/projects/${projectId}/transactions`, { method: 'POST', body: JSON.stringify(data) })
export const updateTransaction = (projectId: string, txId: string, data: Partial<Transaction>) =>
  req<Transaction>(`/projects/${projectId}/transactions/${txId}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteTransaction = (projectId: string, txId: string) =>
  req<void>(`/projects/${projectId}/transactions/${txId}`, { method: 'DELETE' })

// Key Dates
export const addKeyDate = (projectId: string, txId: string, data: { label: string; due_date: string }) =>
  req<KeyDate>(`/projects/${projectId}/transactions/${txId}/dates`, { method: 'POST', body: JSON.stringify(data) })
export const updateKeyDate = (projectId: string, txId: string, dateId: string, data: Partial<KeyDate>) =>
  req<KeyDate>(`/projects/${projectId}/transactions/${txId}/dates/${dateId}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteKeyDate = (projectId: string, txId: string, dateId: string) =>
  req<void>(`/projects/${projectId}/transactions/${txId}/dates/${dateId}`, { method: 'DELETE' })

// Chat
export const getMessages = (projectId: string) =>
  req<ChatMessage[]>(`/projects/${projectId}/messages`)
export const clearMessages = (projectId: string) =>
  req<void>(`/projects/${projectId}/messages`, { method: 'DELETE' })
export const draftEmail = (projectId: string, data: { to: string; subject: string; body: string }) =>
  req<{ draft_url: string }>(`/projects/${projectId}/chat/draft-email`, { method: 'POST', body: JSON.stringify(data) })

// Documents
export const listDocuments = (projectId: string) =>
  req<Document[]>(`/projects/${projectId}/documents`)
export const uploadDocument = (projectId: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return fetch(`${API_ROOT}/projects/${projectId}/documents`, {
    method: 'POST',
    body: form,
    credentials: 'include',
  }).then((r) => r.json() as Promise<Document>)
}
export const deleteDocument = (projectId: string, docId: string) =>
  req<void>(`/projects/${projectId}/documents/${docId}`, { method: 'DELETE' })

// Gmail
export const listEmails = (projectId: string) =>
  req<EmailThread[]>(`/projects/${projectId}/emails`)
export const deleteEmailThread = (projectId: string, threadId: string) =>
  req<void>(`/projects/${projectId}/emails/${threadId}`, { method: 'DELETE' })
export const syncGmail = (projectId: string) =>
  req<{ synced: number; threads_checked?: number; message: string }>(
    `/projects/${projectId}/gmail/sync`,
    { method: 'POST' },
  )

// Drive
export const listDriveFiles = (projectId: string) =>
  req<Document[]>(`/projects/${projectId}/drive/files`)
export const syncDrive = (projectId: string) =>
  req<{ synced: number; skipped?: number; skip_reasons?: Record<string, number>; message: string }>(
    `/projects/${projectId}/drive/sync`,
    { method: 'POST' },
  )

// Auth — email
export const signup = (data: { email: string; password: string; name?: string }) =>
  req<{ authenticated: boolean; email: string; name?: string; google_connected: boolean }>('/auth/signup', { method: 'POST', body: JSON.stringify(data) })

export const login = (data: { email: string; password: string }) =>
  req<{ authenticated: boolean; email: string; name?: string; picture?: string; google_connected: boolean }>('/auth/login', { method: 'POST', body: JSON.stringify(data) })

export type SessionStatus = {
  authenticated: boolean
  account?: {
    email: string
    name?: string
    picture?: string
    auth_provider: string
    subscription_tier?: string
    stripe_customer_id?: string | null
  }
  google_connected?: boolean
}

export const getSessionStatus = () => req<SessionStatus>('/auth/session')
export const logout = () => req<void>('/auth/logout', { method: 'POST' })

// Auth — Google
export const getGoogleAuthUrl = () => req<{ url: string }>('/auth/google/url')
export const getGoogleLinkUrl = () => req<{ url: string }>('/auth/google/link')
export type GoogleStatus = {
  authenticated: boolean
  reason?: string
  email?: string
  name?: string
  picture?: string
}

export const getGoogleStatus = () => req<GoogleStatus>('/auth/google/status')
export const disconnectGoogle = () => req<void>('/auth/google/disconnect', { method: 'POST' })

// Account — AI system prompts (per transaction type)
export type SystemPromptsSettings = {
  default_buyer: string
  default_seller: string
  default_buyer_seller: string
  override_buyer: string | null
  override_seller: string | null
  override_buyer_seller: string | null
}

export type SystemPromptsUpdate = {
  override_buyer?: string | null
  override_seller?: string | null
  override_buyer_seller?: string | null
}

export const getSystemPrompts = () => req<SystemPromptsSettings>('/account/system-prompts')
export const updateSystemPrompts = (data: SystemPromptsUpdate) =>
  req<SystemPromptsSettings>('/account/system-prompts', { method: 'PUT', body: JSON.stringify(data) })

export const getLlmOptions = () => req<LlmOptionsResponse>('/llm/options')

export const getAccountEntitlements = () => req<AccountEntitlements>('/account/entitlements')

// Billing
export const createCheckoutSession = (plan: 'pro' | 'max' | 'ultra') =>
  req<{ url: string }>('/billing/create-checkout-session', {
    method: 'POST',
    body: JSON.stringify({ plan }),
  })

export const createPortalSession = () =>
  req<{ url: string }>('/billing/portal', { method: 'POST' })
