import { AlertTriangle, FileCheck2, FolderOpen, Network, Scale, ScrollText } from 'lucide-react'
import { useState } from 'react'
import { api, getRole, type Dashboard as D } from './api'
import { Empty, ErrorBox, fmtDate, Loading, Notice, PageHeader, useAsync } from './ui'

const STAGES = [['received', 'Received'], ['indexed', 'Processed'], ['reviewed', 'Reviewed by a person'], ['needs_review', 'Needs review'], ['failed', 'Failed']] as const

export default function Dashboard() {
  const [f, setF] = useState({ district: '', station: '', from_month: '', to_month: '' })
  const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString()
  const { data: d, error, loading, reload } = useAsync(() => api<D>('/dashboard' + (qs ? `?${qs}` : '')), [qs])
  const [opts, setOpts] = useState<D['options'] | null>(null)
  if (d && !opts) setOpts(d.options)
  if (loading && !d) return <Loading what="Loading command center" />
  if (error || !d) return <ErrorBox message={error || 'Unavailable'} retry={reload} />
  const c = d.counts
  const kpis = [
    { icon: <FolderOpen size={18} />, label: 'Cases in scope', value: c.cases, href: '#/cases' },
    { icon: <ScrollText size={18} />, label: 'Documents processed', value: c.documents, href: '#/cases' },
    { icon: <Network size={18} />, label: 'Identity matches to review', value: c.identity_to_review, href: '#/reviews?type=identity', warn: c.identity_to_review > 0 },
    { icon: <Scale size={18} />, label: 'Legal suggestions to review', value: c.legal_to_review, href: '#/reviews?type=legal', warn: c.legal_to_review > 0 },
    { icon: <FileCheck2 size={18} />, label: 'Drafts awaiting approval', value: c.drafts_in_review, href: '#/reviews?type=draft', warn: c.drafts_in_review > 0 },
  ]
  const total = Object.values(d.pipeline).reduce((a, b) => a + b, 0) || 1
  const months = Object.entries(d.cases_by_month)
  const max = Math.max(1, ...months.map(([, n]) => n))
  const href = (a: D['attention'][number]) => a.kind === 'identity' ? '#/relationships' : a.kind === 'draft' ? `#/studio/${a.draft_id}` : `#/cases/${a.case_id}`
  return (
    <>
      <PageHeader title="Command Center" sub={`${d.user.district ?? 'All districts'} · signed in as ${d.user.role}. ${c.facts} facts extracted from ${c.documents} document(s).`}
        actions={['investigator', 'supervisor', 'admin'].includes(getRole()) ? <a className="btn primary" href="#/intake">Upload case files</a> : undefined} />
      {opts && (
        <div className="toolbar" role="group" aria-label="Filters">
          {opts.districts.length > 1 && <label className="inline">District<select value={f.district} onChange={e => setF({ ...f, district: e.target.value, station: '' })}><option value="">All</option>{opts.districts.map(x => <option key={x}>{x}</option>)}</select></label>}
          <label className="inline">Station<select value={f.station} onChange={e => setF({ ...f, station: e.target.value })}><option value="">All</option>{opts.stations.map(x => <option key={x}>{x}</option>)}</select></label>
          <label className="inline">From<select value={f.from_month} onChange={e => setF({ ...f, from_month: e.target.value })}><option value="">Start</option>{opts.months.map(x => <option key={x}>{x}</option>)}</select></label>
          <label className="inline">To<select value={f.to_month} onChange={e => setF({ ...f, to_month: e.target.value })}><option value="">Latest</option>{opts.months.map(x => <option key={x}>{x}</option>)}</select></label>
          {qs && <button className="btn sm" onClick={() => setF({ district: '', station: '', from_month: '', to_month: '' })}>Clear filters</button>}
          {loading && <span className="muted small">Updating…</span>}
        </div>
      )}
      <Notice>All figures are computed from the records you are authorised to see, on synthetic demo data. Each tile opens the matching list.</Notice>
      <div className="kpis">
        {kpis.map(k => (
          <a key={k.label} className={'kpi' + (k.warn ? ' warn' : '')} href={k.href}>
            <span className="kpiicon">{k.icon}</span><span className="kpival">{k.value}</span><span className="kpilabel">{k.label}</span>
          </a>
        ))}
      </div>
      <div className="two">
        <section className="card">
          <div className="cardhead"><h2>Needs attention</h2><a href="#/reviews" className="link">Open review queue</a></div>
          {d.attention.length === 0 ? <Empty>Nothing needs review right now.</Empty> : (
            <ul className="list">
              {d.attention.map((a, i) => (
                <li key={i}><a href={href(a)}><AlertTriangle size={14} className="warnicon" /> {a.label}</a></li>
              ))}
            </ul>
          )}
        </section>
        <section className="card">
          <div className="cardhead"><h2>Processing pipeline</h2></div>
          <div className="pad">
            <div className="stack" role="img" aria-label={STAGES.map(([k, l]) => `${l}: ${d.pipeline[k] ?? 0}`).join(', ')}>
              {STAGES.map(([k]) => (d.pipeline[k] ? <span key={k} className={`seg ${k}`} style={{ width: `${(d.pipeline[k] / total) * 100}%` }} /> : null))}
            </div>
            <ul className="legendlist">
              {STAGES.map(([k, l]) => <li key={k}><span className={`dot ${k}`} />{l}<strong>{d.pipeline[k] ?? 0}</strong></li>)}
            </ul>
            <p className="muted small">Files that fail or need review never block the rest of a batch.</p>
          </div>
        </section>
        <section className="card">
          <div className="cardhead"><h2>Cases registered by month</h2></div>
          <div className="pad">
            {months.length === 0 ? <Empty>No cases.</Empty> : (
              <div className="bars" role="img" aria-label={months.map(([m, n]) => `${m}: ${n}`).join(', ')}>
                {months.map(([m, n]) => <div key={m} className="barcol"><span className="barval">{n}</span><span className="bar" style={{ height: `${(n / max) * 110}px` }} /><span className="barlab">{m.slice(2)}</span></div>)}
              </div>
            )}
            <h3>By station</h3>
            <ul className="legendlist">{Object.entries(d.cases_by_station).map(([s, n]) => <li key={s}>{s}<strong>{n}</strong></li>)}</ul>
          </div>
        </section>
        <section className="card">
          <div className="cardhead"><h2>Recent AI-assisted activity</h2><a href="#/audit" className="link">Open audit ledger</a></div>
          {d.recent_activity.length === 0 ? <Empty>Activity is visible to supervisors and administrators.</Empty> : (
            <ul className="list">
              {d.recent_activity.map((r, i) => <li key={i} className="row"><span><strong>{r.action.replace(/_/g, ' ')}</strong> · {r.resource}</span><span className="muted small">{r.actor} · {fmtDate(r.at)}</span></li>)}
            </ul>
          )}
        </section>
      </div>
    </>
  )
}
