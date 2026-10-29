import { Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { api, type Case } from './api'
import { Badge, Empty, ErrorBox, Loading, PageHeader, useAsync } from './ui'

export default function CasesList() {
  const { data, error, loading, reload } = useAsync(() => api<Case[]>('/cases'), [])
  const [q, setQ] = useState('')
  const [station, setStation] = useState('')
  const stations = useMemo(() => [...new Set((data ?? []).map(c => c.station))].sort(), [data])
  const rows = (data ?? []).filter(c =>
    (!station || c.station === station) && (!q || `${c.case_no} ${c.station} ${c.district}`.toLowerCase().includes(q.toLowerCase())))
  if (loading) return <Loading what="Loading cases" />
  if (error) return <ErrorBox message={error} retry={reload} />
  return (
    <>
      <PageHeader title="Cases" sub="Cases you are authorised to access. Open a case for the brief, timeline, legal suggestions and drafts." />
      <div className="toolbar">
        <label className="searchbox"><Search size={15} /><span className="sr">Filter cases</span>
          <input placeholder="Filter by case number, station…" value={q} onChange={e => setQ(e.target.value)} /></label>
        <label><span className="sr">Station</span>
          <select value={station} onChange={e => setStation(e.target.value)}>
            <option value="">All stations</option>{stations.map(s => <option key={s}>{s}</option>)}
          </select></label>
        <span className="muted small">{rows.length} of {data?.length} case(s)</span>
      </div>
      <div className="card tablewrap">
        {rows.length === 0 ? <Empty>No cases match these filters.</Empty> : (
          <table>
            <thead><tr><th>Case number</th><th>District</th><th>Station</th><th>Registered</th><th>Documents</th><th>Status</th></tr></thead>
            <tbody>
              {rows.map(c => (
                <tr key={c.id}>
                  <td><a className="link strong" href={`#/cases/${c.id}`}>{c.case_no}</a></td>
                  <td>{c.district}</td><td>{c.station}</td><td>{c.registered_on}</td><td>{c.documents}</td>
                  <td><Badge status={c.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}
