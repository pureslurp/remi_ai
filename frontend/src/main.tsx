import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { paintRecoFavicon, scheduleRecoFaviconRepaint } from './lib/recoFavicon'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

void paintRecoFavicon()
scheduleRecoFaviconRepaint()
