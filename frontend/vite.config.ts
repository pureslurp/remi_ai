import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const siteOrigin = (env.VITE_PUBLIC_SITE_URL || '').replace(/\/$/, '')

  return {
  plugins: [
    react(),
    {
      name: 'absolute-open-graph-urls',
      transformIndexHtml(html) {
        if (!siteOrigin) return html
        const image = `${siteOrigin}/og-image.png`
        return html.replaceAll('content="/og-image.png"', `content="${image}"`)
      },
    },
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
}})
