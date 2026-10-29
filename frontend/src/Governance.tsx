import { ShieldAlert } from 'lucide-react'
import { useState } from 'react'
import { api, type Governance as G } from './api'
import { Badge, ErrorBox, Loading, Notice, PageHeader, useAsync } from './ui'

export default function Governance() {
  const { data: g, error, loading, reload } = useAsync(() => api<G>('/governance'), [])
  const [nu, setNu] = useState({ username: '', password: '', role: 'investigator', district: 'Visakhapatnam' })
  const [msg, setMsg] = useState('')
  if (loading) return <Loading what="Loading governance" />
  if (error || !g) return <ErrorBox message={error || 'Unavailable'} retry={reload} />
  const ev = g.evaluation
  const act = async (fn: () => Promise<unknown>) => { setMsg(''); try { await fn(); reload() } catch (e) { setMsg((e as Error).message) } }
  const dq = g.data_quality
  const pct = (n: number | null) => (n === null ? '—' : `${Math.round(n * 100)}%`)
  return (
    <>
      <PageHeader title="Quality & Governance" sub="What the system is configured to do, how well it performs on a held-out test, and what is deliberately switched off." />
      <section className="card">
        <div className="cardhead"><h2><ShieldAlert size={16} /> Risk prediction</h2><span className="badge neutral">{g.risk.status}</span></div>
        <div className="pad"><p>{g.risk.reason}</p><p className="muted small">The interface and evaluation framework are ready; nothing is shown as a score until a target is agreed. No accuracy claim is made.</p></div>
      </section>
      <section className="card">
        <div className="cardhead"><h2>Extraction quality (held-out test)</h2><span className="muted small">{ev.extractor} · {ev.documents} documents · {ev.gold_facts} labelled facts</span></div>
        <div className="pad">
          <Notice tone="warn">Overall precision {pct(ev.overall.precision)}, recall {pct(ev.overall.recall)} on a small synthetic set. {ev.limits.join(' ')}</Notice>
          <table>
            <thead><tr><th>Fact type</th><th>Correct</th><th>Wrong</th><th>Missed</th><th>Precision</th><th>Recall</th></tr></thead>
            <tbody>{ev.by_type.map(r => <tr key={r.type}><td>{r.type}</td><td>{r.tp}</td><td>{r.fp}</td><td>{r.fn}</td><td>{pct(r.precision)}</td><td>{pct(r.recall)}</td></tr>)}</tbody>
          </table>
          <div className="two">
            <div><h3>Missed</h3><ul className="statements">{ev.missed.map((m, i) => <li key={i}><strong>{m.type}</strong> “{m.expected}” <span className="muted small">({m.doc})</span></li>)}</ul></div>
            <div><h3>Wrongly extracted</h3><ul className="statements">{ev.spurious.map((m, i) => <li key={i}><strong>{m.type}</strong> “{m.extracted}” <span className="muted small">({m.doc})</span></li>)}</ul></div>
          </div>
          <p className="muted small">Low-confidence and unverifiable extractions are sent to the Review Queue instead of being trusted.</p>
        </div>
      </section>
      <section className="card">
        <div className="cardhead"><h2>Data quality</h2></div>
        <div className="kpis">
          <div className="kpi"><span className="kpival">{dq.documents}</span><span className="kpilabel">Documents</span></div>
          <div className="kpi"><span className="kpival">{dq.needs_review}</span><span className="kpilabel">Need review</span></div>
          <div className="kpi"><span className="kpival">{dq.ocr_documents}</span><span className="kpilabel">OCR-read documents</span></div>
          <div className="kpi"><span className="kpival">{dq.facts_corrected_by_officers}</span><span className="kpilabel">Facts corrected by officers</span></div>
          <div className="kpi"><span className="kpival">{Object.values(dq.facts_by_type).reduce((a, b) => a + b, 0)}</span><span className="kpilabel">Facts extracted</span></div>
        </div>
        <p className="pad muted small">Languages: {Object.entries(dq.languages).map(([k, v]) => `${k}: ${v}`).join(' · ')} · Facts by type: {Object.entries(dq.facts_by_type).map(([k, v]) => `${k} ${v}`).join(', ')}</p>
      </section>
      <div className="two">
        <section className="card">
          <div className="cardhead"><h2>System configuration</h2></div>
          <ul className="list">
            <li className="row"><span>Mode</span><strong>{g.mode}</strong></li>
            <li className="row"><span>Fact extractor</span><strong>{g.system.extractor}</strong></li>
            <li className="row"><span>LLM provider / model</span><strong>{g.system.llm_provider} / {g.system.llm_model}</strong></li>
            <li className="row"><span>Copilot LLM wording</span><strong>{g.system.copilot_llm ? 'On' : 'Off (retrieval only)'}</strong></li>
            <li className="row"><span>Database</span><strong>{g.system.database}</strong></li>
            <li className="row"><span>Legal catalogue</span><span><strong>{g.system.legal_catalogue.version}</strong> <Badge status={g.system.legal_catalogue.verified ? 'approved' : 'needs_review'} label={g.system.legal_catalogue.verified ? 'Verified' : 'Unverified demo'} /></span></li>
          </ul>
        </section>
        {g.users && (
          <section className="card tablewrap">
            <div className="cardhead"><h2>Users and access</h2></div>
            <table><thead><tr><th>User</th><th>Role</th><th>District scope</th><th></th></tr></thead>
              <tbody>{g.users.map(u => <tr key={u.username}><td>{u.username}{!u.active && <span className="badge bad"> disabled</span>}</td><td>{u.role}</td><td>{u.district}</td>
                <td><button className="link small" onClick={() => act(() => api(`/admin/users/${u.username}/active`, { method: 'POST', body: JSON.stringify({ active: !u.active }) }))}>{u.active ? 'Disable' : 'Enable'}</button></td></tr>)}</tbody></table>
            <div className="pad stack-v">
              <h3>Add a user</h3>
              <div className="formrow">
                <label>Username<input value={nu.username} onChange={e => setNu({ ...nu, username: e.target.value })} /></label>
                <label>Password (8+ characters)<input type="password" value={nu.password} onChange={e => setNu({ ...nu, password: e.target.value })} /></label>
              </div>
              <div className="formrow">
                <label>Role<select value={nu.role} onChange={e => setNu({ ...nu, role: e.target.value })}><option>investigator</option><option>supervisor</option><option>analyst</option><option>admin</option></select></label>
                <label>District<select value={nu.district} onChange={e => setNu({ ...nu, district: e.target.value })}><option>Visakhapatnam</option><option>Guntur</option><option>Chittoor</option></select></label>
              </div>
              <button className="btn primary" onClick={() => act(() => api('/admin/users', { method: 'POST', body: JSON.stringify({ ...nu, district: nu.role === 'admin' ? null : nu.district }) }).then(() => setNu({ ...nu, username: '', password: '' })))}>Create user</button>
              {msg && <div className="errorbox" role="alert">{msg}</div>}
            </div>
          </section>
        )}
      </div>
    </>
  )
}
