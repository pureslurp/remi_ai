/**
 * Paints the Chrome tab favicon from the same visual recipe as <RecoMark variant="landing" /> (r. glyph):
 * 44px header tile scaled to 32×32, Cormorant Garamond 600 after document fonts load.
 */
const OUT = 32
const TILE = 44
const SCALE = OUT / TILE
const RX = 12 * SCALE
const FONT_PX = 20 * SCALE

const NAVY = 'rgb(24, 24, 27)'
const SLATE = 'rgb(63, 63, 70)'
const CLOUD = 'rgb(244, 244, 245)'

function drawRecoMarkPng(): string | null {
  const canvas = document.createElement('canvas')
  const dpr = Math.min(2, typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1)
  const px = Math.round(OUT * dpr)
  canvas.width = px
  canvas.height = px
  const ctx = canvas.getContext('2d')
  if (!ctx || typeof ctx.roundRect !== 'function') return null

  ctx.scale(dpr, dpr)

  const x = 0.5
  const y = 0.5
  const w = OUT - 1
  const h = OUT - 1

  const grad = ctx.createLinearGradient(0, 0, OUT, OUT)
  grad.addColorStop(0, NAVY)
  grad.addColorStop(1, SLATE)

  ctx.save()
  ctx.shadowColor = 'rgba(0, 0, 0, 0.25)'
  ctx.shadowBlur = 8 * SCALE
  ctx.shadowOffsetY = 3 * SCALE
  ctx.fillStyle = grad
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, RX)
  ctx.fill()
  ctx.restore()

  ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, RX)
  ctx.stroke()

  ctx.fillStyle = CLOUD
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.font = `600 ${FONT_PX}px "Cormorant Garamond", Georgia, serif`
  ctx.fillText('r.', OUT / 2, OUT / 2 + 0.25)

  return canvas.toDataURL('image/png')
}

export async function paintRecoFavicon(): Promise<void> {
  const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]#app-favicon')
  if (!link) return

  try {
    await document.fonts.ready
    await document.fonts.load(`600 ${20}px "Cormorant Garamond"`)
  } catch {
    // Still draw with Georgia fallback
  }

  const href = drawRecoMarkPng()
  if (!href) return

  link.type = 'image/png'
  link.href = href
}

/** Fonts from Google CSS can resolve after `fonts.ready`; repaint once the page is fully loaded. */
export function scheduleRecoFaviconRepaint(): void {
  if (typeof window === 'undefined') return
  window.addEventListener(
    'load',
    () => {
      void paintRecoFavicon()
    },
    { once: true },
  )
}
