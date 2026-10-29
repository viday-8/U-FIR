import { Search } from 'lucide-react'
import { useState } from 'react'
import { api, type Case, type SearchResult } from './api'
import { EvidenceViewer, type Evidence } from './Evidence'
import { Empty, ErrorBox, Loading, PageHeader, useAsync } from './ui'

function Snippet({ s }: { s: string }) {
  return <>{s.split(/(\[[^\]]+\])/).map((p, i) => (p.startsWith('[') && p.endsWith(']') ? <mark key={i}>{p.slice(1, -1)}</mark> : <span key={i}>{p}</span>))}</>
}

export default function SearchPage({ initial }: { initial: string }) {
  const [q, setQ] = useState(initial)
  const [res, setRes] = useState<SearchResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [ev, setEv] = useState<Evidence | null>(null)
  const [docType, setDocType] = useState('')
  const [station, setStation] = useState('')
  const [recent, setRecent] = useState<string[]>(() => { try { return JSON.parse(localStorage.getItem('recentSearches') ?? '[]') } catch { return [] } })
  const cases = useAsync(() => api<Case[]>('/cases'), [])
  const stations = [...new Set((cases.data ?? []).map(c => c.station))].sort()
  const run = async (e?: React.FormEvent, text = q) => {
    e?.preventDefault()
    if (!text.trim()) return
    setBusy(true); setErr('')
    try {
      const params = new URLSearchParams({ q: text }); if (docType) params.set('doc_type', docType); if (station) params.set('station', station)
      setRes(await api<SearchResult>(`/search?${params}`)); setEv(null)
      const next = [text, ...recent.filter(r => r !== text)].slice(0, 5); setRecent(next)
      try { localStorage.setItem('recentSearches', JSON.stringify(next)) } catch { /* storage unavailable */ }
    } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }
  useState(() => { if (initial) void run() })
  return (
    <>
      <PageHeader title="Search" sub="Search across the case records you are authorised to see: text, names (with spelling variants), vehicles, places." />
      <form onSubmit={run} className="searchbar" role="search">
        <label className="searchbox big"><Search size={16} /><span className="sr">Search query</span>
          <input autoFocus placeholder="e.g. Ramesh Babu Naidu, AP 31 TX 4521, jaggery wash" value={q} onChange={e => setQ(e.target.value)} /></label>
        <button className="btn primary" type="submit">Search</button>
      </form>
      <div className="toolbar">
        <label className="inline">Document type<select value={docType} onChange={e => setDocType(e.target.value)}>
          <option value="">Any</option><option value="fir">FIR</option><option value="seizure">Seizure panchanama</option><option value="diary">Case diary</option><option value="progress">Progress report</option><option value="remand">Remand report</option></select></label>
        <label className="inline">Station<select value={station} onChange={e => setStation(e.target.value)}><option value="">Any</option>{stations.map(s => <option key={s}>{s}</option>)}</select></label>
        {recent.length > 0 && <span className="muted small">Recent: {recent.map(r => <button key={r} className="chip" onClick={() => { setQ(r); void run(undefined, r) }}>{r}</button>)}</span>}
      </div>
      {busy && <Loading what="Searching" />}
      {err && <ErrorBox message={err} />}
      {res && !busy && (
        <div className="split">
          <div className="main">
            <section className="card">
              <div className="cardhead"><h2>Name matches</h2><span className="muted small">Original spelling is always shown</span></div>
              {res.name_matches.length === 0 ? <Empty>No similar names found.</Empty> : (
                <ul className="list">{res.name_matches.map(m => (
                  <li key={m.case_no + m.page + m.name + m.span}>
                    <button className="link strong" onClick={() => setEv({ docId: m.document_id, page: m.page, span: m.span, label: 'Source' })}>{m.name}</button>
                    <span className="muted small"> · {m.case_no} · {m.why}</span>
                  </li>))}</ul>
              )}
            </section>
            <section className="card">
              <div className="cardhead"><h2>Text matches</h2></div>
              {res.text_hits.length === 0 ? <Empty>No text matches. Try fewer words or another spelling.</Empty> : (
                <ul className="list">{res.text_hits.map((h, i) => (
                  <li key={i}>
                    <a className="link strong" href={`#/cases/${h.case_id}`}>{h.case_no}</a><span className="muted small"> · page {h.page} · {h.why}</span>
                    <div className="snippet"><Snippet s={h.snippet} /> <button className="link small" onClick={() => setEv({ docId: h.document_id, page: h.page, span: /\[([^\]]+)\]/.exec(h.snippet)?.[1] ?? '', label: 'Source' })}>View in source</button></div>
                  </li>))}</ul>
              )}
            </section>
          </div>
          <EvidenceViewer ev={ev} />
        </div>
      )}
    </>
  )
}
