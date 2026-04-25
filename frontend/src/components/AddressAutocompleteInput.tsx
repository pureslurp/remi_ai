import { useState, useEffect, useRef } from 'react'
import * as api from '../api/client'
import { labelsFromAutocompleteBody, parseStructuredFromSuggestion } from '../lib/reapiAutocomplete'

const DEB_MS = 280
const MIN_Q = 3

type OnPick = (p: { address: string; city?: string; state?: string; zip_code?: string }) => void

type Props = {
  className?: string
  value: string
  onChange: (v: string) => void
  onCommitStructured?: OnPick
  disabled?: boolean
  placeholder?: string
  /** When false, no vendor autocomplete requests (server property-data off). */
  suggestionsEnabled?: boolean
}

/**
 * Typeahead for U.S. addresses; forwards to BFF (no key in the browser). Choose a line to set structured fields when the vendor returns them.
 */
export default function AddressAutocompleteInput({
  className = '',
  value,
  onChange,
  onCommitStructured,
  disabled,
  placeholder = 'Street address',
  suggestionsEnabled = true,
}: Props) {
  const [open, setOpen] = useState(false)
  const [suggestions, setSuggestions] = useState<{ label: string; raw: unknown }[]>([])
  const tRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wrap = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  useEffect(() => {
    if (tRef.current) clearTimeout(tRef.current)
    if (!suggestionsEnabled) {
      setSuggestions([])
      return
    }
    const q = value.trim()
    if (q.length < MIN_Q) {
      setSuggestions([])
      return
    }
    tRef.current = setTimeout(() => {
      void (async () => {
        try {
          const j = await api.getPropertyAutocomplete(q)
          const list = labelsFromAutocompleteBody(j)
          setSuggestions(list)
        } catch {
          setSuggestions([])
        }
      })()
    }, DEB_MS)
    return () => {
      if (tRef.current) clearTimeout(tRef.current)
    }
  }, [value, suggestionsEnabled])

  const pick = (i: number) => {
    const s = suggestions[i]
    if (!s) return
    const st = parseStructuredFromSuggestion(s.raw, s.label)
    onChange(st.address)
    onCommitStructured?.(st)
    setOpen(false)
    setSuggestions([])
  }

  return (
    <div ref={wrap} className="relative">
      <input
        className={className}
        value={value}
        disabled={disabled}
        autoComplete="off"
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => suggestionsEnabled && value.trim().length >= MIN_Q && setOpen(true)}
      />
      {suggestionsEnabled && open && suggestions.length > 0 && !disabled && (
        <ul
          className="absolute z-30 top-full left-0 right-0 mt-0.5 max-h-40 overflow-y-auto rounded-lg border border-white/12 bg-gray-800/95 py-0.5 shadow-lg"
          role="listbox"
        >
          {suggestions.map((s, i) => (
            <li key={i + s.label}>
              <button
                type="button"
                className="w-full text-left px-2 py-1.5 text-[11px] text-brand-cloud/90 hover:bg-white/10 truncate"
                onMouseDown={(ev) => ev.preventDefault()}
                onClick={() => pick(i)}
              >
                {s.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
