import { useCallback, useRef } from 'react'

type Props = {
  /** Horizontal delta in px since last event (positive = mouse moved right). */
  onDrag: (deltaX: number) => void
  onDragEnd?: () => void
}

export default function ResizableDivider({ onDrag, onDragEnd }: Props) {
  const rootRef = useRef<HTMLDivElement>(null)
  const lastX = useRef<number | null>(null)

  const cleanup = useCallback(
    (e: React.PointerEvent) => {
      if (lastX.current === null) return
      try {
        rootRef.current?.releasePointerCapture(e.pointerId)
      } catch {
        /* ignore */
      }
      lastX.current = null
      onDragEnd?.()
    },
    [onDragEnd],
  )

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault()
    rootRef.current?.setPointerCapture(e.pointerId)
    lastX.current = e.clientX
  }, [])

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (lastX.current === null) return
      const dx = e.clientX - lastX.current
      lastX.current = e.clientX
      if (dx !== 0) onDrag(dx)
    },
    [onDrag],
  )

  return (
    <div
      ref={rootRef}
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize panel"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={cleanup}
      onPointerCancel={cleanup}
      className="w-2 shrink-0 flex justify-center cursor-col-resize group z-20 select-none touch-none -mx-px"
    >
      <div className="w-px h-full min-h-[48px] my-auto bg-white/[0.06] group-hover:bg-brand-mint/45 group-active:bg-brand-mint/70 rounded-full transition-colors" />
    </div>
  )
}
