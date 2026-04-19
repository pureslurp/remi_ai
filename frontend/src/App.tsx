import { useEffect } from 'react'
import { useAppStore } from './store/appStore'
import * as api from './api/client'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import ClientSettings from './components/ClientSettings'
import { useProjectData } from './hooks/useProject'
import type { Project } from './types'

function GoogleBanner() {
  const { googleConnected, setGoogleConnected } = useAppStore()

  const connect = async () => {
    try {
      const data = await api.getGoogleAuthUrl()
      window.open(data.url, '_blank')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes('credentials.json')) {
        alert(
          'Google credentials not set up yet.\n\n' +
          'Follow the GCP setup steps in README.md to create credentials.json, ' +
          'then place it at ~/.remi/credentials.json.\n\n' +
          'See README.md for step-by-step instructions.'
        )
      } else {
        alert('Failed to get Google auth URL: ' + msg)
      }
    }
  }

  if (googleConnected) return null

  return (
    <div className="bg-yellow-900/40 border-b border-yellow-800/50 px-4 py-2 flex items-center justify-between">
      <p className="text-xs text-yellow-300">Connect Google to enable Gmail and Drive sync</p>
      <button
        onClick={connect}
        className="text-xs bg-yellow-600 hover:bg-yellow-500 px-3 py-1 rounded-lg transition"
      >
        Connect Google
      </button>
    </div>
  )
}

export default function App() {
  const { projects, activeProjectId, setProjects, setActiveProject, setGoogleConnected } = useAppStore()

  // Load projects on mount
  useEffect(() => {
    api.listProjects().then(ps => {
      setProjects(ps)
      if (ps.length > 0 && !activeProjectId) setActiveProject(ps[0].id)
    }).catch(() => {})

    api.getGoogleStatus().then(s => setGoogleConnected(s.authenticated)).catch(() => {})

    // Handle redirect from Google OAuth
    const params = new URLSearchParams(window.location.search)
    if (params.get('google_connected')) {
      setGoogleConnected(true)
      window.history.replaceState({}, '', '/')
    }
  }, [])

  // Load project-specific data when active project changes
  useProjectData(activeProjectId)

  const activeProject = projects.find(p => p.id === activeProjectId)

  const handleProjectUpdated = (updated: Project) => {
    setProjects(projects.map(p => p.id === updated.id ? updated : p))
  }

  return (
    <div className="flex flex-col h-screen">
      <GoogleBanner />
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar: 220px fixed */}
        <div className="w-[220px] shrink-0">
          <Sidebar />
        </div>

        {/* Main content */}
        {activeProject ? (
          <>
            {/* Chat: flexible center */}
            <div className="flex-1 flex flex-col overflow-hidden border-x border-gray-800">
              <ChatPanel projectId={activeProject.id} projectName={activeProject.name} />
            </div>

            {/* Right settings panel: 300px fixed */}
            <div className="w-[300px] shrink-0 bg-gray-900">
              <ClientSettings
                project={activeProject}
                onProjectUpdated={handleProjectUpdated}
              />
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-3xl font-bold mx-auto mb-4">
                R
              </div>
              <h2 className="text-lg font-semibold text-white mb-1">Welcome to REMI AI</h2>
              <p className="text-gray-400 text-sm">Create your first client to get started.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
