import { create } from 'zustand'
import type { Project, Property, Transaction, ChatMessage, Document, EmailThread } from '../types'

interface AppStore {
  projects: Project[]
  activeProjectId: string | null
  properties: Property[]
  transactions: Transaction[]
  messages: ChatMessage[]
  documents: Document[]
  emailThreads: EmailThread[]
  googleConnected: boolean
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
  setStreamingContent: (streamingContent) => set({ streamingContent }),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
}))
