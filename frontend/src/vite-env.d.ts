/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  /** Mailto target for Enterprise "Contact sales" on the landing page. */
  readonly VITE_SALES_EMAIL?: string
  /**
   * Public origin of the deployed frontend (no trailing slash). Build-time only:
   * `vite.config` rewrites og/twitter image URLs to absolute for link previews.
   */
  readonly VITE_PUBLIC_SITE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
