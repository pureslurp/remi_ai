/** Per-browser session: server stores one Google token for the whole API, so we require this flag after OAuth in this tab. */
export const REMI_DEVICE_SESSION_KEY = 'remi_device_google_v1'

export function hasDeviceSession(): boolean {
  try {
    return sessionStorage.getItem(REMI_DEVICE_SESSION_KEY) === '1'
  } catch {
    return false
  }
}

export function setDeviceSession(): void {
  try {
    sessionStorage.setItem(REMI_DEVICE_SESSION_KEY, '1')
  } catch {
    /* private mode etc. */
  }
}

export function clearDeviceSession(): void {
  try {
    sessionStorage.removeItem(REMI_DEVICE_SESSION_KEY)
  } catch {
    /* ignore */
  }
}
