/** Google Picker — folder selection for drive.file scope. */

const GAPI_SCRIPT = 'https://apis.google.com/js/api.js'

type PickerDoc = {
  id: string
  name: string
  mimeType: string
  resourceKey?: string
}

type PickerResponse = {
  action: string
  docs?: PickerDoc[]
}

type GooglePickerApi = {
  Action: { PICKED: string; CANCEL: string }
  Feature: {
    SUPPORT_DRIVES: string
    SUPPORT_TEAM_DRIVES: string
    MULTISELECT_ENABLED: string
  }
  ViewId: { FOLDERS: string; DOCS: string }
  DocsView: new (viewId: string) => {
    setSelectFolderEnabled: (enabled: boolean) => unknown
  }
  PickerBuilder: new () => {
    addView: (view: unknown) => unknown
    setOAuthToken: (token: string) => unknown
    setDeveloperKey: (key: string) => unknown
    setAppId: (appId: string) => unknown
    setCallback: (cb: (data: PickerResponse) => void) => unknown
    enableFeature: (feature: string) => unknown
    build: () => { setVisible: (visible: boolean) => void }
  }
}

type GapiWindow = Window & {
  gapi?: {
    load: (name: string, opts: { callback: () => void }) => void
  }
  google?: {
    picker: GooglePickerApi
  }
}

let pickerLoadPromise: Promise<GooglePickerApi> | null = null

function loadScript(src: string): Promise<void> {
  const existing = document.querySelector(`script[src="${src}"]`)
  if (existing) {
    return Promise.resolve()
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`))
    document.head.appendChild(script)
  })
}

function ensurePickerApi(): Promise<GooglePickerApi> {
  if (pickerLoadPromise) return pickerLoadPromise
  pickerLoadPromise = (async () => {
    await loadScript(GAPI_SCRIPT)
    const win = window as GapiWindow
    await new Promise<void>((resolve, reject) => {
      if (!win.gapi?.load) {
        reject(new Error('Google API (gapi) failed to load'))
        return
      }
      win.gapi.load('picker', { callback: resolve })
    })
    const picker = win.google?.picker
    if (!picker) {
      throw new Error('Google Picker API failed to load')
    }
    return picker
  })()
  return pickerLoadPromise
}

export type DriveFolderPick = { id: string; name: string; resourceKey?: string }

export type DriveFilePick = { id: string; name: string; resourceKey?: string }

export type OpenDriveFolderPickerOptions = {
  accessToken: string
  developerKey: string
  appId: string
  onPicked: (folder: DriveFolderPick) => void
  onCancel?: () => void
  onError?: (message: string) => void
}

const FOLDER_MIME = 'application/vnd.google-apps.folder'

export async function openDriveFolderPicker(opts: OpenDriveFolderPickerOptions): Promise<void> {
  const { accessToken, developerKey, appId, onPicked, onCancel, onError } = opts
  if (!developerKey || !appId) {
    onError?.('Google Picker is not configured (missing API key or app ID).')
    return
  }

  try {
    const picker = await ensurePickerApi()
    const view = new picker.DocsView(picker.ViewId.FOLDERS)
    view.setSelectFolderEnabled(true)

    const builder = new picker.PickerBuilder()
    builder.addView(view)
    builder.setOAuthToken(accessToken)
    builder.setDeveloperKey(developerKey)
    builder.setAppId(appId)
    builder.enableFeature(picker.Feature.SUPPORT_DRIVES)
    builder.enableFeature(picker.Feature.SUPPORT_TEAM_DRIVES)
    builder.setCallback((data: PickerResponse) => {
      if (data.action === picker.Action.PICKED && data.docs?.[0]) {
        const doc = data.docs[0]
        if (doc.mimeType !== FOLDER_MIME) {
          onError?.('Please select a folder, not a file.')
          return
        }
        onPicked({
          id: doc.id,
          name: doc.name || 'Drive folder',
          resourceKey: doc.resourceKey,
        })
        return
      }
      if (data.action === picker.Action.CANCEL) {
        onCancel?.()
      }
    })

    builder.build().setVisible(true)
  } catch (err) {
    onError?.(err instanceof Error ? err.message : 'Could not open Google Picker')
  }
}

export type OpenDriveFilesPickerOptions = {
  accessToken: string
  developerKey: string
  appId: string
  parentFolderId?: string
  onPicked: (files: DriveFilePick[]) => void
  onCancel?: () => void
  onError?: (message: string) => void
}

export async function openDriveFilesPicker(opts: OpenDriveFilesPickerOptions): Promise<void> {
  const { accessToken, developerKey, appId, parentFolderId, onPicked, onCancel, onError } = opts
  if (!developerKey || !appId) {
    onError?.('Google Picker is not configured (missing API key or app ID).')
    return
  }

  try {
    const picker = await ensurePickerApi()
    const view = new picker.DocsView(picker.ViewId.DOCS)
    if (parentFolderId) {
      ;(view as { setParent?: (id: string) => unknown }).setParent?.(parentFolderId)
    }

    const builder = new picker.PickerBuilder()
    builder.addView(view)
    builder.setOAuthToken(accessToken)
    builder.setDeveloperKey(developerKey)
    builder.setAppId(appId)
    builder.enableFeature(picker.Feature.SUPPORT_DRIVES)
    builder.enableFeature(picker.Feature.SUPPORT_TEAM_DRIVES)
    builder.enableFeature(picker.Feature.MULTISELECT_ENABLED)
    builder.setCallback((data: PickerResponse) => {
      if (data.action === picker.Action.PICKED && data.docs?.length) {
        const files = data.docs
          .filter(d => d.mimeType !== FOLDER_MIME)
          .map(d => ({
            id: d.id,
            name: d.name || 'Drive file',
            resourceKey: d.resourceKey,
          }))
        if (!files.length) {
          onError?.('Select one or more files (not a folder).')
          return
        }
        onPicked(files)
        return
      }
      if (data.action === picker.Action.CANCEL) {
        onCancel?.()
      }
    })

    builder.build().setVisible(true)
  } catch (err) {
    onError?.(err instanceof Error ? err.message : 'Could not open Google Picker')
  }
}
