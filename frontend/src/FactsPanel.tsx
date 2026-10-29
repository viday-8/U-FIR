import { Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { api, type Brief, type Correction, type Fact, getRole } from './api'
import { Badge, Empty, ErrorBox, fmtDate, Loading, Notice, useAsync } from './ui'

const TYPES = ['person', 'place', 'vehicle', 'item', 'quantity', 'date', 'legal_section']

export default function FactsPanel({ caseId, brief, onOpen, onChanged }: { caseId: number; brief: Brief; onOpen: (f: Fact) => void; onChanged: () => void }) {
  const facts = useAsync(() => api<Fact[]>(`/cases/${caseId}/facts`), [caseId])
  const history = useAsync(() => api<Correction[]>(`/cases/${caseId}/corrections`), [caseId])
  const [editing, setEditing] = useState<number | null>(null)
  const [value, setValue] = useState('')
  const [reason, setReason] = useState('')
  const [msg, setMsg] = useState('')
  const [adding, setAdding] = useState(false)
  const [nf, setNf] = useState({ document_id: brief.records_reviewed.list[0]?.id ?? 0, page: 1, type: 'person', value: '', span: '' })
  const can = ['investigator', 'supervisor', 'admin'].includes(getRole())
  const refresh = () => { facts.reload(); history.reload(); onChanged() }
  const run = async (fn: () => Promise<unknown>) => { setMsg(''); try { await fn(); setEditing(null); setReason(''); setAdding(false); refresh() } catch (e) { setMsg((e as Error).message) } }

  if (facts.loading) return <Loading what="Loading facts" />
  if (facts.error) return <ErrorBox message={facts.error} retry={facts.reload} />
  return (
    <>
      <section className="card">
        <div className="cardhead"><h2>Extracted facts</h2>
          {can && <button className="btn" onClick={() => setAdding(!adding)}><Plus size={14} /> Add a missed fact</button>}</div>
        <div className="pad">
          <Notice>Fix anything the extractor got wrong. Every change keeps the old value, who changed it and why; the original document is never modified.</Notice>
          {msg && <ErrorBox message={msg} />}
          {adding && (
            <div className="card pad addform">
              <p className="muted small">Quote the exact words from the document. The system checks that the quote really appears on that page.</p>
              <div className="formrow">
                <label>Document<select value={nf.document_id} onChange={e => setNf({ ...nf, document_id: Number(e.target.value) })}>{brief.records_reviewed.list.map(d => <option key={d.id} value={d.id}>{d.type}</option>)}</select></label>
                <label>Page<input type="number" min={1} value={nf.page} onChange={e => setNf({ ...nf, page: Number(e.target.value) })} /></label>
                <label>Type<select value={nf.type} onChange={e => setNf({ ...nf, type: e.target.value })}>{TYPES.map(t => <option key={t}>{t}</option>)}</select></label>
              </div>
              <label>Value<input value={nf.value} onChange={e => setNf({ ...nf, value: e.target.value })} /></label>
              <label>Exact quote from the document<input value={nf.span} onChange={e => setNf({ ...nf, span: e.target.value })} /></label>
              <button className="btn primary" onClick={() => run(() => api(`/cases/${caseId}/facts`, { method: 'POST', body: JSON.stringify(nf) }))} disabled={!nf.value || !nf.span}>Add fact</button>
            </div>
          )}
          {!facts.data?.length ? <Empty>No facts extracted.</Empty> : (
            <table>
              <thead><tr><th>Type</th><th>Value</th><th>Source</th><th></th></tr></thead>
              <tbody>{facts.data.map(f => (
                <tr key={f.id}>
                  <td>{f.type}</td>
                  <td>{editing === f.id ? (
                    <div className="stack-v"><input aria-label="New value" value={value} onChange={e => setValue(e.target.value)} />
                      <input aria-label="Reason for change" placeholder="Reason (required)" value={reason} onChange={e => setReason(e.target.value)} />
                      <div className="actions"><button className="btn primary sm" onClick={() => run(() => api(`/facts/${f.id}`, { method: 'PATCH', body: JSON.stringify({ value, reason }) }))}>Save</button>
                        <button className="btn sm" onClick={() => setEditing(null)}>Cancel</button></div></div>
                  ) : <>{f.original} {f.corrected && <Badge status="accepted" label="Corrected" />}</>}</td>
                  <td><button className="link small" onClick={() => onOpen(f)}>{brief.records_reviewed.list.find(d => d.id === f.document_id)?.type} p{f.page}</button></td>
                  <td className="actions">{can && editing !== f.id && <>
                    <button className="btn sm" onClick={() => { setEditing(f.id); setValue(f.original); setReason('') }} aria-label={`Edit ${f.original}`}><Pencil size={12} /></button>
                    <button className="btn sm" aria-label={`Remove ${f.original}`} onClick={() => { const r = window.prompt('Reason for removing this fact (required):'); if (r) void run(() => api(`/facts/${f.id}/remove`, { method: 'POST', body: JSON.stringify({ reason: r }) })) }}><Trash2 size={12} /></button></>}</td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
      </section>
      <section className="card">
        <div className="cardhead"><h2>Correction history</h2></div>
        {!history.data?.length ? <Empty>No corrections yet.</Empty> : (
          <ul className="list">{history.data.map((c, i) => (
            <li key={i}><strong>{c.action}</strong> {c.type}: {c.old ? `“${c.old}”` : ''} {c.old && c.new ? '→' : ''} {c.new ? `“${c.new}”` : ''}
              <div className="muted small">{c.by} · {fmtDate(c.at)} · {c.reason}</div></li>))}</ul>
        )}
      </section>
    </>
  )
}
