import { useEffect, useState } from 'react'

/** Matches Tailwind `lg:` (1024px). */
const LG_MEDIA = '(min-width: 1024px)'

export function useIsLgUp(): boolean {
  const [isLgUp, setIsLgUp] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(LG_MEDIA).matches : true,
  )

  useEffect(() => {
    const mq = window.matchMedia(LG_MEDIA)
    const onChange = () => setIsLgUp(mq.matches)
    onChange()
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  return isLgUp
}
