function timeAgo(dateStr?: string | null) {
  if (!dateStr) return 'Never'
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

interface Props {
  label: string
  lastSync?: string | null
  onSync: () => void
  syncing: boolean
  message?: string
}

export default function SyncStatus({ label, lastSync, onSync, syncing, message }: Props) {
  return (
    <div className="bg-gray-800/40 rounded-xl p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-300">{label}</span>
        <button
          onClick={onSync}
          disabled={syncing}
          className="text-xs text-blue-400 hover:text-blue-300 transition disabled:opacity-50"
        >
          {syncing ? 'Syncing…' : 'Sync Now'}
        </button>
      </div>
      <p className="text-xs text-gray-500">
        Last synced: {timeAgo(lastSync)}
      </p>
      {message && <p className="text-xs text-green-400 mt-1">{message}</p>}
    </div>
  )
}
