/**
 * RealEstateAPI /v2/AutoComplete response shapes differ by account — normalize display lines.
 */
export function labelsFromAutocompleteBody(raw: unknown): { label: string; raw: unknown }[] {
  if (!raw || typeof raw !== 'object') return []
  const o = raw as Record<string, unknown>
  const status = o.statusCode ?? o.status
  if (status !== undefined && String(status) !== '200') {
    return []
  }
  const data = o.data ?? o.suggestions ?? o.autocomplete
  if (!Array.isArray(data) || data.length === 0) {
    if (data && typeof data === 'object' && !Array.isArray(data)) {
      return [{ label: JSON.stringify(data), raw: data }]
    }
    return []
  }
  return data
    .slice(0, 12)
    .map((item) => {
      if (item == null) {
        return { label: String(item), raw: item }
      }
      if (typeof item === 'string') {
        return { label: item, raw: item }
      }
      if (typeof item === 'object' && !Array.isArray(item)) {
        const r = item as Record<string, unknown>
        const title =
          (r.title as string) ||
          (r.label as string) ||
          (r.address as string) ||
          (r.street as string) ||
          (r.formatted as string) ||
          (r.text as string)
        if (title && String(title).trim()) {
          return { label: String(title).trim(), raw: item }
        }
        const a = r.address
        if (a && typeof a === 'object') {
          const d = a as Record<string, unknown>
          const line = (d.label as string) || (d.address as string) || (d.street as string)
          if (line) return { label: String(line).trim(), raw: item }
        }
        return { label: JSON.stringify(item).slice(0, 200), raw: item }
      }
      return { label: String(item), raw: item }
    })
    .filter((x) => x.label.length > 0)
}

/** Best-effort structured address fields for saving a Property (vendor-shaped). */
export function parseStructuredFromSuggestion(
  item: unknown,
  fallbackLine: string,
): { address: string; city?: string; state?: string; zip_code?: string } {
  if (!item || typeof item !== 'object' || Array.isArray(item)) {
    return { address: fallbackLine }
  }
  const r = item as Record<string, unknown>
  const a = r.address
  if (a && typeof a === 'object') {
    const d = a as Record<string, unknown>
    const line =
      (d.label as string) ||
      (d.street as string) ||
      (d.line1 as string) ||
      ((d as { house?: string }).house && d.street
        ? `${(d as { house: string }).house} ${(d as { street: string }).street}`
        : null)
    const city = (d.city as string) || (r.city as string)
    const state = (d.state as string) || (d.stateId as string) || (r.state as string) || (r.stateId as string)
    const z = d.zip as string
    if (line && String(line).trim()) {
      return {
        address: String(line).trim(),
        city: city ? String(city).trim() : undefined,
        state: state ? String(state).trim() : 'MI',
        zip_code: z ? String(z).trim() : undefined,
      }
    }
  }
  if (r.street) {
    return {
      address: [r.house, r.street, r.street2].filter(Boolean).map(String).join(' ').trim() || fallbackLine,
      city: (r.city as string) || undefined,
      state: (r.state as string) || 'MI',
      zip_code: (r.zip as string) || (r.postal as string) || undefined,
    }
  }
  return { address: fallbackLine }
}
