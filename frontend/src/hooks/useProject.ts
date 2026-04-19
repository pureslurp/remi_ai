import { useEffect } from 'react'
import { useAppStore } from '../store/appStore'
import * as api from '../api/client'

export function useProjectData(projectId: string | null) {
  const {
    setMessages, setProperties, setTransactions,
    setDocuments, setEmailThreads,
  } = useAppStore()

  useEffect(() => {
    if (!projectId) return
    api.getMessages(projectId).then(setMessages).catch(() => {})
    api.listProperties(projectId).then(setProperties).catch(() => {})
    api.listTransactions(projectId).then(setTransactions).catch(() => {})
    api.listDocuments(projectId).then(setDocuments).catch(() => {})
    api.listEmails(projectId).then(setEmailThreads).catch(() => {})
  }, [projectId])
}
