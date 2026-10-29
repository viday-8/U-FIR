import { FileText } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, type Doc } from './api'
import { Badge, ErrorBox, Loading, Notice } from './ui'

export type Evidence = { docId: number; page: number; span: string; label: string }

function Highlighted({ text, span }: { text: string; span: string }) {
  const i = span ? text.indexOf(span) : -1
  if (i < 0) return <>{text}</>
  return <>{text.slice(0, i)}<mark id="cited">{text.slice(i, i + span.length)}</mark>{text.slice(i + span.length)}</>
}

export function EvidenceViewer({ ev }: { ev: Evidence | null }) {
  const [doc, setDoc] = useState<Doc | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    if (!ev) return
    setErr(''); setDoc(null)
    api<Doc>(`/documents/${ev.docId}`).then(setDoc).catch(e => setErr(e.message))
  }, [ev?.docId])  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { document.getElementById('cited')?.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [doc, ev?.span])
  return (
    <aside aria-label="Source evidence" className="card evidence">
      <div className="cardhead"><h2><FileText size={16} /> Source evidence</h2></div>
      {!ev && <p className="muted pad">Select a citation, timeline event or source chip to see the exact passage in the original record.</p>}
      {err && <ErrorBox message={err} />}
      {ev && !doc && !err && <Loading what="Opening source" />}
      {ev && doc && (
        <div className="pad">
          <p className="muted small">{ev.label} · {doc.case_no} · page {ev.page} <Badge status={doc.status} /></p>
          {doc.reviewed_by && <Notice>Reviewed by {doc.reviewed_by}: {doc.review_note}</Notice>}
          {doc.has_ocr && <Notice tone="warn">Text on scanned pages was read by OCR and may contain errors. Check it against the original image before relying on it.</Notice>}
          {doc.language !== 'en' && <Notice tone="warn">This document is {doc.language === 'te' ? 'in Telugu' : 'partly in Telugu'}. Automatic extraction supports English only, so a person must review it.</Notice>}
          {doc.pages.map(p => (
            <section key={p.number} aria-label={`Page ${p.number}`}>
              <h3>Page {p.number}</h3>
              <pre className="source">{p.number === ev.page ? <Highlighted text={p.text} span={ev.span} /> : p.text}</pre>
            </section>
          ))}
          <p className="muted small">Original record is preserved unchanged (checksum-verified).</p>
        </div>
      )}
    </aside>
  )
}
