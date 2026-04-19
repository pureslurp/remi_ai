import { useRef, useState } from 'react'
import { useAppStore } from '../store/appStore'
import * as api from '../api/client'
import type { Document } from '../types'

function sourceIcon(source: string) {
  if (source === 'drive') return '🗂'
  if (source === 'gmail') return '📧'
  return '📄'
}

function fmtSize(bytes?: number) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

interface Props {
  projectId: string
  documents: Document[]
}

export default function DocumentList({ projectId, documents }: Props) {
  const { setDocuments } = useAppStore()
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const doc = await api.uploadDocument(projectId, file)
      setDocuments([doc, ...documents])
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleDelete = async (doc: Document) => {
    if (!confirm(`Delete "${doc.filename}"?`)) return
    await api.deleteDocument(projectId, doc.id)
    setDocuments(documents.filter(d => d.id !== doc.id))
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (!file) return
    setUploading(true)
    try {
      const doc = await api.uploadDocument(projectId, file)
      setDocuments([doc, ...documents])
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <div
        onDrop={handleDrop}
        onDragOver={e => e.preventDefault()}
        className="border-2 border-dashed border-gray-700 hover:border-gray-500 rounded-xl p-3 mb-2 text-center transition cursor-pointer"
        onClick={() => fileRef.current?.click()}
      >
        <p className="text-xs text-gray-400">
          {uploading ? 'Uploading…' : 'Drop file or click to upload (PDF, DOCX, TXT)'}
        </p>
        <input ref={fileRef} type="file" className="hidden" accept=".pdf,.docx,.txt" onChange={handleUpload} />
      </div>

      <div className="space-y-1">
        {documents.map(doc => (
          <div key={doc.id} className="flex items-center gap-2 py-1.5 px-2 rounded-lg bg-gray-800/40 hover:bg-gray-800 group transition">
            <span className="text-sm shrink-0">{sourceIcon(doc.source)}</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs truncate text-gray-200">{doc.filename}</p>
              <p className="text-xs text-gray-500">
                {fmtSize(doc.size_bytes)}
                {doc.chunk_count > 0 && ` · ${doc.chunk_count} chunks`}
              </p>
            </div>
            <button
              onClick={() => handleDelete(doc)}
              className="text-gray-600 hover:text-red-400 transition opacity-0 group-hover:opacity-100 shrink-0"
            >
              ×
            </button>
          </div>
        ))}
        {documents.length === 0 && (
          <p className="text-xs text-gray-500">No documents yet.</p>
        )}
      </div>
    </div>
  )
}
