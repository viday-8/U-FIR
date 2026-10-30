import { FileUp } from 'lucide-react'
import { useRef, useState } from 'react'
import { api, getRole, type Case, type CaseMeta, type CaseNetwork, type IntakeResult } from './api'
import { Badge, Empty, ErrorBox, Loading, Notice, PageHeader, useAsync } from './ui'

type Row = IntakeResult & { file: File; include: boolean; docType: string; target: string }  // target: case id or 'new'
type Done = { name: string; status: string; error?: string; caseId?: number }
const DOC_TYPES: [string, string][] = [['fir', 'FIR'], ['seizure', 'Seizure panchanama'], ['diary', 'Case diary'], ['progress', 'Progress report'], ['remand', 'Remand report']]

function LeadReview({ id, onDone }: { id: number; onDone: () => void }) {
  const [reason, setReason] = useState('')
  const [msg, setMsg] = useState('')
  const decide = async (decision: string) => { setMsg(''); try { await api(`/candidates/${id}/review`, { method: 'POST', body: JSON.stringify({ decision, reason }) }); onDone() } catch (e) { setMsg((e as Error).message) } }
  return (
    <div className="reviewrow">
      <input aria-label="Reason for your decision" placeholder="Reason (required to confirm or reject)" value={reason} onChange={e => setReason(e.target.value)} />
      <button className="btn sm primary" onClick={() => decide('confirm')}>Same person</button>
      <button className="btn sm" onClick={() => decide('reject')}>Not the same</button>
      <button className="btn sm" onClick={() => decide('defer')}>Decide later</button>
      <a className="link small" href={`#/network?focus=link:${id}`}>Why linked?</a>
      {msg && <span className="errtext small" role="alert">{msg}</span>}
    </div>
  )
}

function Impact({ caseId, caseNo }: { caseId: number; caseNo: string }) {
  const meta = useAsync(() => api<CaseMeta>(`/cases/${caseId}/meta`), [caseId])
  const net = useAsync(() => api<CaseNetwork>(`/cases/${caseId}/network`), [caseId])
  const canReview = ['investigator', 'supervisor', 'admin'].includes(getRole())
  if (meta.loading || net.loading) return <Loading what={`Analysing ${caseNo}`} />
  const m = meta.data, n = net.data
  if (!m || !n) return null
  return (
    <section className="card" aria-label={`Impact of upload on ${caseNo}`}>
      <div className="cardhead"><h2>What this upload added to {caseNo}</h2><a className="btn sm" href={`#/network?focus=case:${caseId}`}>View in network</a></div>
      <div className="pad">
        <div>{m.offence.map(o => <span key={o} className="badge info">{o}</span>)}</div>
        <ul className="facts">
          <li><strong>{n.summary.people}</strong> person record(s): {m.accused.map(a => a.name).join(', ') || 'none found'}</li>
          <li><strong>{m.vehicles.length}</strong> vehicle(s): {m.vehicles.join(', ') || 'none found'} · items: {m.items.join(', ') || 'none found'} · places: {m.places.join(', ') || 'none found'}</li>
        </ul>
        {n.summary.possible_matches + n.summary.shared_vehicles === 0
          ? <Notice>No links to other cases were found. The people and vehicles in these documents are new to the records you can access.</Notice>
          : <Notice tone="warn"><strong>New connections found.</strong> {n.summary.possible_matches} possible person match(es) and {n.summary.shared_vehicles} shared vehicle(s) link this case to {n.summary.related_cases} other case(s). These are leads, not findings: decide each one below, with a reason, or leave it for the Review Queue.</Notice>}
        <ul className="list">
          {n.people.flatMap(p => p.links.map(l => (
            <li key={l.candidate_id}><strong>{p.name}</strong> ↔ {l.other.name} <span className="muted small">({l.other.case_no}) · {l.strength} match, score {l.score}</span>
              <div className="small muted">{l.top_signals.join(' · ')}</div>
              {l.status === 'unreviewed' || l.status === 'deferred' ? (canReview ? <LeadReview id={l.candidate_id} onDone={net.reload} /> : <a className="link small" href={`#/network?focus=link:${l.candidate_id}`}>Why linked?</a>) : <span className="badge ok">{l.status === 'confirmed' ? 'Confirmed same person' : l.status}</span>}</li>)))}
          {n.shared_vehicles.map(v => <li key={v.vehicle}>Vehicle <strong>{v.vehicle}</strong> also appears in {v.cases.map(c => c.case_no).join(', ')}</li>)}
        </ul>
        <p className="small muted">Undecided leads stay in the <a href="#/reviews?type=identity">Review Queue</a>; the <a href={`#/network?focus=case:${caseId}`}>network</a> shows them in context.</p>
      </div>
    </section>
  )
}

export default function Intake({ district }: { district: string | null }) {
  const cases = useAsync(() => api<Case[]>('/cases'), [])
  const input = useRef<HTMLInputElement>(null)
  const [rows, setRows] = useState<Row[]>([])
  const [reading, setReading] = useState(false)
  const [err, setErr] = useState('')
  const [done, setDone] = useState<Done[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [nc, setNc] = useState({ case_no: '', district: district ?? '', station: '', registered_on: '' })
  const needsNew = rows.some(r => r.include && r.ok && r.target === 'new')
  const districts = [...new Set((cases.data ?? []).map(c => c.district))]
  const stations = [...new Set((cases.data ?? []).map(c => c.station))]
  const patch = (i: number, p: Partial<Row>) => setRows(rs => rs.map((r, j) => (j === i ? { ...r, ...p } : r)))

  const read = async (files: FileList | null) => {
    if (!files?.length) return
    setErr(''); setDone(null); setReading(true)
    const list = [...files]
    try {
      const body = new FormData(); list.forEach(f => body.append('files', f))
      const res = await api<IntakeResult[]>('/intake/analyze', { method: 'POST', body })
      const next: Row[] = res.map((r, i) => ({ ...r, file: list[i], include: r.ok && !r.duplicate_of, docType: r.doc_type ?? 'fir', target: r.matched_case_id ? String(r.matched_case_id) : '' }))
      setRows(next)
      const first = res.find(r => r.ok && !r.matched_case_id)
      if (first) setNc(n => ({ ...n, registered_on: first.registered_on ?? n.registered_on, case_no: n.case_no || (first.case_ref ? `Cr.${first.case_ref}` : '') }))
    } catch (e) { setErr((e as Error).message) } finally { setReading(false) }
  }

  const upload = async () => {
    setBusy(true); setErr('')
    const out: Done[] = []; setDone(out)
    try {
      let newId: number | null = null
      if (needsNew) newId = (await api<Case>('/cases', { method: 'POST', body: JSON.stringify(nc) })).id
      for (const r of rows.filter(x => x.include && x.ok)) {
        const caseId = r.target === 'new' ? newId : Number(r.target)
        try {
          const body = new FormData(); body.append('case_id', String(caseId)); body.append('doc_type', r.docType); body.append('file', r.file)
          const res = await api<{ document_id: number; status: string }>('/ingest', { method: 'POST', body })
          let status = res.status
          for (let i = 0; i < 24 && status === 'received'; i++) { await new Promise(x => setTimeout(x, 500)); status = (await api<{ status: string }>(`/ingest/${res.document_id}`)).status }
          out.push({ name: r.filename, status, caseId: caseId ?? undefined })
        } catch (e) { out.push({ name: r.filename, status: 'failed', error: (e as Error).message }) }  // one bad file never blocks the rest
        setDone([...out])
      }
      setRows([]); cases.reload()
    } catch (e) { setErr((e as Error).message) } finally { setBusy(false); if (input.current) input.current.value = '' }
  }

  const ready = rows.some(r => r.include && r.ok && r.target) && (!needsNew || (nc.case_no.trim() && nc.district && nc.station.trim() && nc.registered_on))
  return (
    <>
      <PageHeader title="Upload case files" sub="Bring in FIRs, panchanamas, diaries and reports exactly as they are written today. The system reads them, suggests where each belongs, and you confirm." />
      <Notice>Accepted: text, Word (.docx), PDF and scanned images (read with OCR), up to 5 MB each and 20 files at a time. Scans and non-English documents are always sent to a person for review, and the original file is stored unchanged.</Notice>
      {err && <ErrorBox message={err} />}
      <section className="card">
        <div className="cardhead"><h2><FileUp size={16} /> 1. Choose files</h2></div>
        <div className="pad"><label>Case files<input ref={input} type="file" multiple accept=".txt,.pdf,.docx,.png,.jpg,.jpeg" onChange={e => void read(e.target.files)} /></label>
          {reading && <Loading what="Reading files" />}</div>
      </section>

      {rows.length > 0 && (
        <section className="card tablewrap">
          <div className="cardhead"><h2>2. Confirm what was read</h2><span className="muted small">Nothing is stored until you upload</span></div>
          <table>
            <thead><tr><th>Add</th><th>File</th><th>Document type</th><th>Belongs to case</th><th>Notes</th></tr></thead>
            <tbody>{rows.map((r, i) => (
              <tr key={i}>
                <td><input type="checkbox" aria-label={`Include ${r.filename}`} checked={r.include} disabled={!r.ok} onChange={e => patch(i, { include: e.target.checked })} /></td>
                <td className="strong">{r.filename}</td>
                {r.ok ? (<>
                  <td><select aria-label={`Document type for ${r.filename}`} value={r.docType} onChange={e => patch(i, { docType: e.target.value })}>{DOC_TYPES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
                    {!r.doc_type && <div className="muted small">Not detected: please check</div>}</td>
                  <td><select aria-label={`Case for ${r.filename}`} value={r.target} onChange={e => patch(i, { target: e.target.value })}>
                    <option value="">Choose a case…</option><option value="new">＋ Create a new case</option>
                    {cases.data?.map(c => <option key={c.id} value={c.id}>{c.case_no}</option>)}</select>
                    {r.case_ref && <div className="muted small">Case number in file: {r.case_ref}{r.matches?.length === 0 && ' (no matching case)'}{(r.matches?.length ?? 0) > 1 && ' (several matches: choose)'}</div>}</td>
                  <td className="small">{r.duplicate_of && <div className="badge warn">Already uploaded to {r.duplicate_of.case_no}</div>} {r.ocr && <span className="badge warn">Scan: OCR + review</span>} {r.language && r.language !== 'en' && <span className="badge warn">Telugu: review</span>}</td>
                </>) : <td colSpan={3} className="errtext">⚠ {r.error}</td>}
              </tr>))}</tbody>
          </table>
          {needsNew && (
            <div className="pad addform">
              <h3>New case details</h3>
              <div className="formrow">
                <label>Case number<input value={nc.case_no} onChange={e => setNc({ ...nc, case_no: e.target.value })} /></label>
                <label>District<select value={nc.district} disabled={!!district} onChange={e => setNc({ ...nc, district: e.target.value })}><option value="">Choose…</option>{districts.map(d => <option key={d}>{d}</option>)}{district && !districts.includes(district) && <option>{district}</option>}</select></label>
              </div>
              <div className="formrow">
                <label>Station<input list="stations" value={nc.station} onChange={e => setNc({ ...nc, station: e.target.value })} /><datalist id="stations">{stations.map(s => <option key={s} value={s} />)}</datalist></label>
                <label>Registered on<input type="date" value={nc.registered_on} onChange={e => setNc({ ...nc, registered_on: e.target.value })} /></label>
              </div>
            </div>
          )}
          <div className="pad"><button className="btn primary" disabled={!ready || busy} onClick={() => void upload()}>{busy ? 'Uploading…' : `Upload ${rows.filter(r => r.include && r.ok).length} file(s)`}</button></div>
        </section>
      )}

      {done && (
        <section className="card">
          <div className="cardhead"><h2>3. Results</h2></div>
          {done.length === 0 ? <Empty>Starting…</Empty> : (
            <ul className="list">{done.map((d, i) => (
              <li key={i} className="row"><span>{d.name}{d.error && <span className="muted small"> · {d.error}</span>}</span>
                <span className="actions"><Badge status={d.status} />{d.caseId && <a className="link small" href={`#/cases/${d.caseId}`}>Open case</a>}</span></li>))}</ul>
          )}
          {!busy && done.length > 0 && <p className="pad muted small">Processed documents are searchable now. Anything marked “Needs review” is waiting in the <a href="#/reviews?type=extraction">Review Queue</a>.</p>}
        </section>
      )}
      {!busy && done && [...new Map(done.filter(d => d.caseId).map(d => [d.caseId!, d])).keys()].map(cid => <Impact key={cid} caseId={cid} caseNo={cases.data?.find(c => c.id === cid)?.case_no ?? `case ${cid}`} />)}
    </>
  )
}
