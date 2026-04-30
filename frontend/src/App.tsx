import { useEffect, useState, useCallback, useRef } from 'react'
import { useAppStore } from './store/appStore'
import * as api from './api/client'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import ClientSettings from './components/ClientSettings'
import LandingPage from './components/LandingPage'
import HowToGuide from './components/HowToGuide'
import PrivacyPolicy from './components/PrivacyPolicy'
import TermsOfService from './components/TermsOfService'
import ResizableDivider from './components/ResizableDivider'
import { useProjectData } from './hooks/useProject'
import { useIsLgUp } from './hooks/useIsLgUp'
import type { Project } from './types'

const LS_SIDEBAR = 'reco.layout.sidebarWidth'
const LS_RIGHT = 'reco.layout.rightPanelWidth'
const LS_SIDEBAR_MODE = 'reco.layout.sidebarMode'

/** Min must fit header row: mark + "reco-pilot" (wordmark) + shell controls. */
const SIDEBAR = { min: 300, max: 440, def: 320 } as const
const SIDEBAR_RAIL = 52
const RIGHT_PANEL = { min: 260, max: 560, def: 420 } as const

type SidebarMode = 'expanded' | 'collapsed' | 'hidden'

function clamp(n: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, n))
}

function readStoredWidth(key: string, fallback: number, lo: number, hi: number) {
  try {
    const v = Number(localStorage.getItem(key))
    if (!Number.isFinite(v)) return fallback
    return clamp(v, lo, hi)
  } catch {
    return fallback
  }
}

function readStoredSidebarMode(): SidebarMode {
  try {
    const v = localStorage.getItem(LS_SIDEBAR_MODE)
    if (v === 'collapsed' || v === 'hidden' || v === 'expanded') return v
  } catch {
    /* ignore */
  }
  return 'expanded'
}

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
  if (window.location.pathname === '/privacy') return <PrivacyPolicy />
  if (window.location.pathname === '/terms') return <TermsOfService />

  const { projects, activeProjectId, setProjects, setActiveProject, setGoogleConnected, setGoogleUser, setAuthProvider } =
    useAppStore()

  const [authReady, setAuthReady] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)
  const [sessionUnlocked, setSessionUnlocked] = useState(false)

  const bootstrap = useCallback(async () => {
    setAuthError(null)
    const params = new URLSearchParams(window.location.search)
    if (
      params.get('google_connected') ||
      params.get('google_linked') ||
      params.get('checkout_success') ||
      params.get('checkout_canceled') ||
      params.get('signed_out')
    ) {
      window.history.replaceState({}, '', '/')
    }

    try {
      const session = await api.getSessionStatus()
      const unlocked = session.authenticated === true
      setSessionUnlocked(unlocked)
      setGoogleConnected(session.google_connected ?? false)
      setAuthProvider(session.account?.auth_provider as 'google' | 'email' | null ?? null)

      if (unlocked && session.account) {
        setGoogleUser({
          email: session.account.email,
          name: session.account.name,
          picture: session.account.picture,
        })
      } else {
        setGoogleUser(null)
        setAuthProvider(null)
      }

      if (unlocked) {
        // If user signed up with Google while a paid plan was pending, redirect to Stripe now
        const pendingPlan = sessionStorage.getItem('pendingPlan')
        if (pendingPlan && session.account?.subscription_tier === 'free') {
          sessionStorage.removeItem('pendingPlan')
          try {
            const { url } = await api.createCheckoutSession(pendingPlan as 'pro' | 'max' | 'ultra')
            window.location.href = url
            return
          } catch {
            // If checkout fails, continue into the app on free plan
          }
        }
        try {
          await loadSessionProjects(setProjects, setActiveProject)
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : String(e)
          if (msg.includes('401')) {
            setGoogleConnected(false)
            setSessionUnlocked(false)
            setGoogleUser(null)
            setAuthProvider(null)
            setProjects([])
            setActiveProject(null)
          } else {
            throw e
          }
        }
      } else {
        setProjects([])
        setActiveProject(null)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setAuthError(msg)
      setGoogleConnected(false)
      setGoogleUser(null)
      setAuthProvider(null)
      setSessionUnlocked(false)
      setProjects([])
      setActiveProject(null)
    } finally {
      setAuthReady(true)
    }
  }, [setProjects, setActiveProject, setGoogleConnected, setGoogleUser, setAuthProvider])

  useEffect(() => {
    bootstrap()
  }, [bootstrap])

  useProjectData(sessionUnlocked ? activeProjectId : null)

  const activeProject = projects.find(p => p.id === activeProjectId)

  const googleConnected = useAppStore(s => s.googleConnected)
  const authProvider = useAppStore(s => s.authProvider)
  const [googleBannerDismissed, setGoogleBannerDismissed] = useState(false)
  // Only prompt users who signed in with Google but have no OAuth tokens (rare / recovery).
  // Email/password accounts must not see this — linking Google would use a different identity.
  const showGoogleBanner =
    sessionUnlocked && authProvider === 'google' && !googleConnected && !googleBannerDismissed

  const handleConnectGoogle = async () => {
    try {
      const { url } = await api.getGoogleLinkUrl()
      window.location.href = url
    } catch {
      // Fallback to regular Google auth URL if link endpoint fails
      const { url } = await api.getGoogleAuthUrl()
      window.location.href = url
    }
  }

  const [sidebarMode, setSidebarMode] = useState<SidebarMode>(() => readStoredSidebarMode())
  const [sidebarWidth, setSidebarWidth] = useState(() =>
    readStoredWidth(LS_SIDEBAR, SIDEBAR.def, SIDEBAR.min, SIDEBAR.max),
  )
  const [rightPanelWidth, setRightPanelWidth] = useState(() =>
    readStoredWidth(LS_RIGHT, RIGHT_PANEL.def, RIGHT_PANEL.min, RIGHT_PANEL.max),
  )
  const sidebarRef = useRef(sidebarWidth)
  const rightRef = useRef(rightPanelWidth)
  sidebarRef.current = sidebarWidth
  rightRef.current = rightPanelWidth

  useEffect(() => {
    try {
      localStorage.setItem(LS_SIDEBAR_MODE, sidebarMode)
    } catch {
      /* private mode */
    }
  }, [sidebarMode])

  const persistLayout = useCallback(() => {
    try {
      localStorage.setItem(LS_SIDEBAR, String(sidebarRef.current))
      localStorage.setItem(LS_RIGHT, String(rightRef.current))
    } catch {
      /* private mode */
    }
  }, [])

  const onSidebarDrag = useCallback((delta: number) => {
    setSidebarWidth(w => {
      const n = clamp(w + delta, SIDEBAR.min, SIDEBAR.max)
      sidebarRef.current = n
      return n
    })
  }, [])

  const onRightPanelDrag = useCallback((delta: number) => {
    // Divider sits between chat (left) and this pane: dragging the handle right
    // moves the split right → wider chat, narrower right pane (opposite of sidebar).
    setRightPanelWidth(w => {
      const n = clamp(w - delta, RIGHT_PANEL.min, RIGHT_PANEL.max)
      rightRef.current = n
      return n
    })
  }, [])

  const handleProjectUpdated = (updated: Project) => {
    setProjects(projects.map(p => (p.id === updated.id ? updated : p)))
  }

  const isLgUp = useIsLgUp()
  const [mobileClientListOpen, setMobileClientListOpen] = useState(false)
  const [mobileClientDetailOpen, setMobileClientDetailOpen] = useState(false)

  useEffect(() => {
    if (isLgUp) {
      setMobileClientListOpen(false)
      setMobileClientDetailOpen(false)
    }
  }, [isLgUp])

  useEffect(() => {
    if (!mobileClientListOpen && !mobileClientDetailOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMobileClientDetailOpen(false)
        setMobileClientListOpen(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [mobileClientListOpen, mobileClientDetailOpen])

  const closeMobileClientList = useCallback(() => setMobileClientListOpen(false), [])
  const closeMobileClientDetail = useCallback(() => setMobileClientDetailOpen(false), [])

  if (!authReady) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <div className="h-9 w-9 border-2 border-white/15 border-t-brand-mint rounded-full animate-spin" />
        <p className="text-sm text-brand-cloud/60">Checking your session…</p>
      </div>
    )
  }

  if (authError) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-6">
        <div className="max-w-md w-full rounded-xl border border-red-400/30 bg-red-500/10 backdrop-blur-sm p-6 text-center">
          <p className="text-sm text-red-100 mb-4">Could not reach the API: {authError}</p>
          <button
            type="button"
            onClick={() => {
              setAuthReady(false)
              bootstrap()
            }}
            className="px-4 py-2 rounded-lg bg-white/10 border border-white/15 text-sm text-brand-cloud hover:bg-white/15 transition"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!sessionUnlocked) {
    return <LandingPage onEmailAuth={bootstrap} />
  }

  if (window.location.pathname === '/guide') {
    return <HowToGuide />
  }

  return (
    <div className="flex flex-col h-screen reco-fade-in">
      {showGoogleBanner && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3 border-b border-amber-400/20 bg-amber-500/[0.07] px-4 py-2.5 text-sm text-amber-100/90">
          <p>
            Connect your Google account to enable email sync and Drive document import.{' '}
            <button
              type="button"
              onClick={handleConnectGoogle}
              className="font-semibold text-brand-mint hover:text-brand-mint/80 transition underline underline-offset-2"
            >
              Connect Google
            </button>
          </p>
          <button
            type="button"
            onClick={() => setGoogleBannerDismissed(true)}
            className="shrink-0 rounded p-1 text-amber-100/50 hover:text-amber-100 transition"
            aria-label="Dismiss"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {isLgUp && sidebarMode === 'hidden' && (
        <button
          type="button"
          aria-label="Show clients sidebar"
          title="Show clients"
          onClick={() => setSidebarMode('expanded')}
          className="fixed left-0 top-1/2 z-50 -translate-y-1/2 flex items-center gap-0.5 rounded-r-lg border border-l-0 border-white/15 bg-black/55 backdrop-blur-md py-4 pl-1 pr-1.5 text-brand-cloud/75 hover:text-brand-cloud hover:bg-white/[0.08] transition shadow-lg"
        >
          <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 18l6-6-6-6" />
          </svg>
        </button>
      )}

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {isLgUp && sidebarMode !== 'hidden' && (
          <>
            <div
              className="shrink-0 min-h-0 min-w-0 flex flex-col"
              style={{ width: sidebarMode === 'collapsed' ? SIDEBAR_RAIL : sidebarWidth }}
            >
              <Sidebar
                shell={sidebarMode === 'collapsed' ? 'collapsed' : 'expanded'}
                onExpandShell={() => setSidebarMode('expanded')}
                onCollapseToRail={() => setSidebarMode('collapsed')}
                onHideShell={() => setSidebarMode('hidden')}
              />
            </div>

            {sidebarMode === 'expanded' && (
              <ResizableDivider onDrag={onSidebarDrag} onDragEnd={persistLayout} />
            )}
          </>
        )}

        {activeProject ? (
          <>
            <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden border-white/5 lg:border-x lg:min-w-[260px]">
              <ChatPanel
                project={activeProject}
                onProjectUpdated={handleProjectUpdated}
                mobileNav={
                  isLgUp
                    ? undefined
                    : {
                        onOpenClients: () => setMobileClientListOpen(true),
                        onOpenClientDetails: () => setMobileClientDetailOpen(true),
                      }
                }
              />
            </div>

            {isLgUp && (
              <>
                <ResizableDivider onDrag={onRightPanelDrag} onDragEnd={persistLayout} />

                <div
                  className="shrink-0 min-h-0 min-w-0 flex flex-col bg-black/20 backdrop-blur-sm border-l border-white/5"
                  style={{ width: rightPanelWidth }}
                >
                  <ClientSettings project={activeProject} onProjectUpdated={handleProjectUpdated} />
                </div>
              </>
            )}
          </>
        ) : (
          <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden lg:min-w-[240px]">
            <div className="flex-1 flex items-center justify-center overflow-auto p-6">
              <div className="text-center max-w-md">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-navy to-brand-slate border border-white/10 flex items-center justify-center text-2xl font-semibold mx-auto mb-5 text-brand-cloud tracking-tight font-landing-display">
                  r.
                </div>
                <h2 className="text-xl font-semibold text-brand-cloud mb-1 tracking-tight">
                  Welcome to{' '}
                  <span className="font-wordmark-app tracking-[0.06em]">reco-pilot</span>
                </h2>
                <p className="text-brand-cloud/60 text-sm">
                  {isLgUp
                    ? 'Create your first client in the sidebar to get started.'
                    : 'Create your first client from the client list.'}
                </p>
                {!isLgUp && (
                  <button
                    type="button"
                    onClick={() => setMobileClientListOpen(true)}
                    className="mt-5 w-full max-w-xs mx-auto py-2.5 rounded-lg text-sm font-medium text-brand-navy bg-brand-mint hover:bg-brand-mint/90 transition"
                  >
                    Open clients
                  </button>
                )}
                {isLgUp && sidebarMode === 'hidden' && (
                  <p className="text-brand-cloud/40 text-xs mt-3 max-w-sm mx-auto">
                    Sidebar is hidden — use the tab on the left screen edge to open clients and add one.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {!isLgUp && mobileClientListOpen && (
        <div className="fixed inset-0 z-[60] flex lg:hidden" role="dialog" aria-modal="true" aria-label="Clients">
          <button
            type="button"
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            aria-label="Close client list"
            onClick={closeMobileClientList}
          />
          <div className="relative flex h-full w-[min(20rem,92vw)] flex-col border-r border-white/10 bg-zinc-950/95 shadow-2xl">
            <div className="flex shrink-0 items-center justify-between gap-2 border-b border-white/10 px-3 py-2.5 pt-[max(0.625rem,env(safe-area-inset-top))]">
              <span className="text-sm font-semibold text-brand-cloud">Clients</span>
              <button
                type="button"
                onClick={closeMobileClientList}
                className="rounded-lg p-2 text-brand-cloud/60 hover:bg-white/[0.08] hover:text-brand-cloud transition"
                aria-label="Close"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-hidden">
              <Sidebar
                shell="expanded"
                omitShellControls
                onAfterSelectClient={closeMobileClientList}
              />
            </div>
          </div>
        </div>
      )}

      {!isLgUp && mobileClientDetailOpen && activeProject && (
        <div className="fixed inset-0 z-[60] flex justify-end lg:hidden" role="dialog" aria-modal="true" aria-label="Client workspace">
          <button
            type="button"
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            aria-label="Close client workspace"
            onClick={closeMobileClientDetail}
          />
          <div className="relative flex h-full w-[min(100vw,24rem)] flex-col border-l border-white/10 bg-zinc-950/95 shadow-2xl pb-[max(0.5rem,env(safe-area-inset-bottom))]">
            <div className="flex shrink-0 items-center justify-between gap-2 border-b border-white/10 px-3 py-2.5 pt-[max(0.625rem,env(safe-area-inset-top))]">
              <span className="min-w-0 truncate text-sm font-semibold text-brand-cloud" title={activeProject.name}>
                {activeProject.name}
              </span>
              <button
                type="button"
                onClick={closeMobileClientDetail}
                className="shrink-0 rounded-lg p-2 text-brand-cloud/60 hover:bg-white/[0.08] hover:text-brand-cloud transition"
                aria-label="Close"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
              <ClientSettings project={activeProject} onProjectUpdated={handleProjectUpdated} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
