import { create } from 'zustand'
import type { Project, Property, Transaction, ChatMessage, Document, EmailThread } from '../types'

export type GoogleUserProfile = {
  email?: string
  name?: string
  picture?: string
}

interface AppStore {
  projects: Project[]
  activeProjectId: string | null
  properties: Property[]
  transactions: Transaction[]
  messages: ChatMessage[]
  documents: Document[]
  emailThreads: EmailThread[]
  googleConnected: boolean
  googleUser: GoogleUserProfile | null
  authProvider: 'google' | 'email' | null
  streamingContent: string
  isStreaming: boolean

  setProjects: (projects: Project[]) => void
  setActiveProject: (id: string | null) => void
  setProperties: (props: Property[]) => void
  setTransactions: (txs: Transaction[]) => void
  setMessages: (msgs: ChatMessage[]) => void
  addMessage: (msg: ChatMessage) => void
  setDocuments: (docs: Document[]) => void
  setEmailThreads: (threads: EmailThread[]) => void
  setGoogleConnected: (v: boolean) => void
  setGoogleUser: (u: GoogleUserProfile | null) => void
  setAuthProvider: (v: 'google' | 'email' | null) => void
  setStreamingContent: (text: string) => void
  setIsStreaming: (v: boolean) => void
}

export const useAppStore = create<AppStore>((set) => ({
  projects: [],
  activeProjectId: null,
  properties: [],
  transactions: [],
  messages: [],
  documents: [],
  emailThreads: [],
  googleConnected: false,
  googleUser: null,
  authProvider: null,
  streamingContent: '',
  isStreaming: false,

  setProjects: (projects) => set({ projects }),
  setActiveProject: (id) => set({ activeProjectId: id, messages: [], properties: [], transactions: [], documents: [], emailThreads: [], streamingContent: '' }),
  setProperties: (properties) => set({ properties }),
  setTransactions: (transactions) => set({ transactions }),
  setMessages: (messages) => set({ messages }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setDocuments: (documents) => set({ documents }),
  setEmailThreads: (emailThreads) => set({ emailThreads }),
  setGoogleConnected: (googleConnected) => set({ googleConnected }),
  setGoogleUser: (googleUser) => set({ googleUser }),
  setAuthProvider: (authProvider) => set({ authProvider }),
  setStreamingContent: (streamingContent) => set({ streamingContent }),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
}))
