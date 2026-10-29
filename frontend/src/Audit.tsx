import { useState } from 'react'
import { api, type AuditRow } from './api'
import { Empty, ErrorBox, fmtDate, Loading, Notice, PageHeader, useAsync } from './ui'

export default function Audit() {
  const { data, error, loading, reload } = useAsync(() => api<AuditRow[]>('/audit'), [])
  const [q, setQ] = useState('')
  if (loading) return <Loading what="Loading audit ledger" />
  if (error) return <ErrorBox message={error} retry={reload} />
  const rows = (data ?? []).filter(r => !q || `${r.actor} ${r.action} ${r.resource} ${r.outcome} ${r.model}`.toLowerCase().includes(q.toLowerCase()))
  return (
    <>
      <PageHeader title="Trust & Audit Ledger" sub="Append-only record of AI-assisted outputs and human review decisions." />
      <Notice>The ledger stores references and outcomes, not document text, so it does not become a second copy of sensitive records.</Notice>
      <div className="toolbar"><label><span className="sr">Filter audit entries</span><input placeholder="Filter by user, action, case…" value={q} onChange={e => setQ(e.target.value)} /></label><span className="muted small">{rows.length} entr{rows.length === 1 ? 'y' : 'ies'}</span></div>
      <div className="card tablewrap">
        {rows.length === 0 ? <Empty>No entries.</Empty> : (
          <table><thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Resource</th><th>Model / version</th><th>Outcome</th></tr></thead>
            <tbody>{rows.map((r, i) => <tr key={i}><td>{fmtDate(r.at)}</td><td>{r.actor}</td><td>{r.action.replace(/_/g, ' ')}</td><td>{r.resource}</td><td>{r.model ?? '—'}</td><td>{r.outcome ?? '—'}</td></tr>)}</tbody></table>
        )}
      </div>
    </>
  )
}
