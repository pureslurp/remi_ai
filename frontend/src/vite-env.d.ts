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
  /** Google Picker — same OAuth Web client ID as backend GOOGLE_CLIENT_ID */
  readonly VITE_GOOGLE_CLIENT_ID?: string
  /** Google Cloud API key (HTTP referrer restricted) for Picker */
  readonly VITE_GOOGLE_API_KEY?: string
  /** GCP project number for Picker setAppId */
  readonly VITE_GOOGLE_APP_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
