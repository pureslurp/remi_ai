/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  /** Mailto target for Enterprise "Contact sales" on the landing page. */
  readonly VITE_SALES_EMAIL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
