import { RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { api, getRole } from './api'

/** Resolve a document that needs review: retry processing, or mark it reviewed with a note. */
export default function DocActions({ docId, status, onDone }: { docId: number; status: string; onDone: () => void }) {
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState('')
  const [msg, setMsg] = useState('')
  if (!['needs_review', 'failed'].includes(status) || !['investigator', 'supervisor', 'admin'].includes(getRole())) return null
  const run = async (path: string, body?: object) => {
    setMsg('')
    try { await api(`/documents/${docId}/${path}`, { method: 'POST', body: body ? JSON.stringify(body) : undefined }); setOpen(false); setNote(''); onDone() }
    catch (e) { setMsg((e as Error).message) }
  }
  return (
    <div className="docactions">
      <div className="actions">
        <button className="btn sm" onClick={() => run('retry')}><RefreshCw size={12} /> Retry</button>
        <button className="btn sm" onClick={() => setOpen(!open)} aria-expanded={open}>Mark reviewed</button>
      </div>
      {open && (
        <div className="stack-v">
          <label className="small">What did you check? (required)<input value={note} onChange={e => setNote(e.target.value)} placeholder="e.g. compared with the original scan" /></label>
          <button className="btn primary sm" disabled={!note.trim()} onClick={() => run('mark-reviewed', { note })}>Confirm reviewed</button>
        </div>
      )}
      {msg && <div className="errorbox" role="alert">{msg}</div>}
    </div>
  )
}
