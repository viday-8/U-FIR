import { FileUp } from 'lucide-react'
import { useRef, useState } from 'react'
import { api } from './api'
import { Badge, Notice } from './ui'

type Item = { name: string; status: string; error?: string }

export default function UploadPanel({ caseId, onDone }: { caseId: number; onDone: () => void }) {
  const [docType, setDocType] = useState('fir')
  const [items, setItems] = useState<Item[]>([])
  const input = useRef<HTMLInputElement>(null)
  const set = (name: string, patch: Partial<Item>) => setItems(xs => xs.map(x => (x.name === name ? { ...x, ...patch } : x)))

  const upload = async (files: FileList | null) => {
    if (!files?.length) return
    const list = [...files]
    setItems(list.map(f => ({ name: f.name, status: 'received' })))
    for (const f of list) {  // one bad file never blocks the rest of the batch
      try {
        const body = new FormData(); body.append('case_id', String(caseId)); body.append('doc_type', docType); body.append('file', f)
        const r = await api<{ document_id: number; status: string }>('/ingest', { method: 'POST', body })
        let status = r.status
        for (let i = 0; i < 20 && status === 'received'; i++) {
          await new Promise(res => setTimeout(res, 500))
          status = (await api<{ status: string }>(`/ingest/${r.document_id}`)).status
        }
        set(f.name, { status })
      } catch (e) { set(f.name, { status: 'failed', error: (e as Error).message }) }
    }
    if (input.current) input.current.value = ''
    onDone()
  }
  return (
    <section className="card">
      <div className="cardhead"><h2><FileUp size={16} /> Add documents</h2></div>
      <div className="pad">
        <Notice>Upload text files, PDFs or scanned images (.txt, .pdf, .png, .jpg). Scanned pages are read with OCR and always sent for review; originals are stored unchanged.</Notice>
        <div className="formrow">
          <label>Document type<select value={docType} onChange={e => setDocType(e.target.value)}>
            <option value="fir">FIR</option><option value="seizure">Seizure panchanama</option><option value="diary">Case diary</option><option value="progress">Progress report</option><option value="remand">Remand report</option></select></label>
          <label>Files<input ref={input} type="file" multiple accept=".txt,.pdf,.png,.jpg,.jpeg" onChange={e => void upload(e.target.files)} /></label>
        </div>
        {items.length > 0 && <ul className="list">{items.map(i => <li key={i.name} className="row"><span>{i.name}{i.error && <span className="muted small"> · {i.error}</span>}</span><Badge status={i.status} /></li>)}</ul>}
      </div>
    </section>
  )
}
