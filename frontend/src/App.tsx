import { useEffect, useState, useCallback } from 'react'
import { useAppStore } from './store/appStore'
import * as api from './api/client'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import ClientSettings from './components/ClientSettings'
import LoginScreen from './components/LoginScreen'
import { useProjectData } from './hooks/useProject'
import type { Project } from './types'
import { hasDeviceSession, setDeviceSession, clearDeviceSession } from './auth/session'

async function loadSessionProjects(
  setProjects: (p: Project[]) => void,
  setActiveProject: (id: string | null) => void,
) {
  const ps = await api.listProjects()
  setProjects(ps)
  const cur = useAppStore.getState().activeProjectId
  if (ps.length > 0) {
    const stillValid = cur && ps.some(p => p.id === cur)
    if (!stillValid) setActiveProject(ps[0].id)
  } else {
    setActiveProject(null)
  }
}

export default function App() {
  const {
    projects,
    activeProjectId,
    setProjects,
    setActiveProject,
    setGoogleConnected,
    setGoogleUser,
    googleConnected,
  } = useAppStore()

  const [authReady, setAuthReady] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)
  /** True only when the API has a valid Google token AND this browser completed OAuth (sessionStorage). */
  const [sessionUnlocked, setSessionUnlocked] = useState(false)

  const bootstrap = useCallback(async () => {
    setAuthError(null)
    const params = new URLSearchParams(window.location.search)
    if (params.get('google_connected')) {
      setDeviceSession()
      window.history.replaceState({}, '', '/')
    }

    try {
      const status = await api.getGoogleStatus()
      if (!status.authenticated) {
        clearDeviceSession()
      }

      setGoogleConnected(status.authenticated)
      if (status.authenticated) {
        setGoogleUser({
          email: status.email,
          name: status.name,
          picture: status.picture,
        })
      } else {
        setGoogleUser(null)
      }

      const unlocked = status.authenticated && hasDeviceSession()
      setSessionUnlocked(unlocked)

      if (unlocked) {
        await loadSessionProjects(setProjects, setActiveProject)
      } else {
        setProjects([])
        setActiveProject(null)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setAuthError(msg)
      setGoogleConnected(false)
      setGoogleUser(null)
      setSessionUnlocked(false)
      setProjects([])
      setActiveProject(null)
    } finally {
      setAuthReady(true)
    }
  }, [setProjects, setActiveProject, setGoogleConnected, setGoogleUser])

  useEffect(() => {
    bootstrap()
  }, [bootstrap])

  useProjectData(sessionUnlocked ? activeProjectId : null)

  const activeProject = projects.find(p => p.id === activeProjectId)

  const handleProjectUpdated = (updated: Project) => {
    setProjects(projects.map(p => (p.id === updated.id ? updated : p)))
  }

  if (!authReady) {
    return (
      <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center gap-4">
        <div className="h-9 w-9 border-2 border-gray-600 border-t-blue-500 rounded-full animate-spin" />
        <p className="text-sm text-gray-400">Checking your session…</p>
      </div>
    )
  }

  if (authError) {
    return (
      <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-6">
        <div className="max-w-md w-full rounded-xl border border-red-800/50 bg-red-950/40 p-6 text-center">
          <p className="text-sm text-red-200 mb-4">Could not reach the API: {authError}</p>
          <button
            type="button"
            onClick={() => {
              setAuthReady(false)
              bootstrap()
            }}
            className="px-4 py-2 rounded-lg bg-gray-800 text-sm text-white hover:bg-gray-700 transition"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!sessionUnlocked) {
    const needsDeviceLink = googleConnected && !hasDeviceSession()
    return <LoginScreen needsDeviceLink={needsDeviceLink} />
  }

  return (
    <div className="flex flex-col h-screen">
      <div className="flex flex-1 overflow-hidden">
        <div className="w-[220px] shrink-0">
          <Sidebar />
        </div>

        {activeProject ? (
          <>
            <div className="flex-1 flex flex-col overflow-hidden border-x border-gray-800">
              <ChatPanel projectId={activeProject.id} projectName={activeProject.name} />
            </div>

            <div className="w-[300px] shrink-0 bg-gray-900">
              <ClientSettings project={activeProject} onProjectUpdated={handleProjectUpdated} />
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-950">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-3xl font-bold mx-auto mb-4 text-white">
                R
              </div>
              <h2 className="text-lg font-semibold text-white mb-1">Welcome to REMI AI</h2>
              <p className="text-gray-400 text-sm">Create your first client in the sidebar to get started.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
