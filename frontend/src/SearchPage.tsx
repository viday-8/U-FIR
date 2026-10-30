import { Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, type Overview, type SearchResult, type Suggestion } from './api'
import { EvidenceViewer, type Evidence } from './Evidence'
import { Empty, ErrorBox, Loading, PageHeader } from './ui'

function Snippet({ s }: { s: string }) {
  return <>{s.split(/(\[[^\]]+\])/).map((p, i) => (p.startsWith('[') && p.endsWith(']') ? <mark key={i}>{p.slice(1, -1)}</mark> : <span key={i}>{p}</span>))}</>
}

export default function SearchPage({ initial }: { initial: string }) {
  const [q, setQ] = useState(initial)
  const [res, setRes] = useState<SearchResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [ev, setEv] = useState<Evidence | null>(null)
  const [f, setF] = useState({ doc_type: '', station: '', offence: '', from_date: '', to_date: '' })
  const [sugg, setSugg] = useState<Suggestion[]>([])
  const [open, setOpen] = useState(false)
  const [facets, setFacets] = useState<Overview['facets'] | null>(null)
  const [recent, setRecent] = useState<string[]>(() => { try { return JSON.parse(localStorage.getItem('recentSearches') ?? '[]') } catch { return [] } })
  const first = useRef(true)

  useEffect(() => { api<Overview>('/cases/overview').then(o => setFacets(o.facets)).catch(() => undefined) }, [])
  useEffect(() => {
    if (q.trim().length < 2) { setSugg([]); return }
    const t = setTimeout(() => api<Suggestion[]>(`/search/suggest?q=${encodeURIComponent(q)}`).then(setSugg).catch(() => setSugg([])), 180)
    return () => clearTimeout(t)
  }, [q])

  const run = async (text = q, filters = f) => {
    if (!text.trim()) return
    setBusy(true); setErr(''); setOpen(false)
    try {
      const params = new URLSearchParams({ q: text }); Object.entries(filters).forEach(([k, v]) => v && params.set(k, v))
      setRes(await api<SearchResult>(`/search?${params}`)); setEv(null)
      const next = [text, ...recent.filter(r => r !== text)].slice(0, 5); setRecent(next)
      try { localStorage.setItem('recentSearches', JSON.stringify(next)) } catch { /* storage unavailable */ }
    } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }
  useEffect(() => { if (first.current) { first.current = false; if (initial) void run() } }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  const setFilter = (k: keyof typeof f, v: string) => { const n = { ...f, [k]: v }; setF(n); if (q.trim()) void run(q, n) }

  return (
    <>
      <PageHeader title="Search" sub="One box for names (any spelling), vehicles, places, items, sections, case numbers and words inside documents." />
      <form onSubmit={e => { e.preventDefault(); void run() }} className="searchbar" role="search">
        <div className="suggestwrap">
          <label className="searchbox big"><Search size={16} /><span className="sr">Search query</span>
            <input autoFocus role="combobox" aria-expanded={open && sugg.length > 0} aria-controls="suggest-list" autoComplete="off"
              placeholder="e.g. Rameshbabu, AP 31 TX 4521, jaggery wash, Kuppam, 34(a)" value={q}
              onChange={e => { setQ(e.target.value); setOpen(true) }} onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 150)} /></label>
          {open && sugg.length > 0 && (
            <ul id="suggest-list" className="suggest" role="listbox">{sugg.map((s, i) => (
              <li key={i} role="option" aria-selected="false"><button type="button" onMouseDown={() => { setQ(s.text); void run(s.text) }}><span className="badge neutral">{s.kind}</span> {s.text}</button></li>))}</ul>
          )}
        </div>
        <button className="btn primary" type="submit">Search</button>
      </form>
      <div className="toolbar">
        <label className="inline">Offence<select value={f.offence} onChange={e => setFilter('offence', e.target.value)}><option value="">Any</option>{Object.entries(facets?.offence ?? {}).map(([k, n]) => <option key={k} value={k}>{k} ({n})</option>)}</select></label>
        <label className="inline">Document<select value={f.doc_type} onChange={e => setFilter('doc_type', e.target.value)}>
          <option value="">Any</option><option value="fir">FIR</option><option value="seizure">Seizure panchanama</option><option value="diary">Case diary</option><option value="progress">Progress report</option><option value="remand">Remand report</option></select></label>
        <label className="inline">Station<select value={f.station} onChange={e => setFilter('station', e.target.value)}><option value="">Any</option>{Object.keys(facets?.station ?? {}).map(s => <option key={s}>{s}</option>)}</select></label>
        <label className="inline">From<input type="date" value={f.from_date} onChange={e => setFilter('from_date', e.target.value)} /></label>
        <label className="inline">To<input type="date" value={f.to_date} onChange={e => setFilter('to_date', e.target.value)} /></label>
        {recent.length > 0 && <span className="muted small">Recent: {recent.map(r => <button key={r} className="chip" onClick={() => { setQ(r); void run(r) }}>{r}</button>)}</span>}
      </div>
      {busy && <Loading what="Searching" />}
      {err && <ErrorBox message={err} />}
      {res && !busy && (
        <div className="split">
          <div className="main">
            <section className="card">
              <div className="cardhead"><h2>Matching cases</h2><span className="muted small">{res.case_hits.length} case(s) · matched on metadata</span></div>
              {res.case_hits.length === 0 ? <Empty>No case matches every word. Try fewer words, or check the text matches below.</Empty> : (
                <ul className="list">{res.case_hits.map(c => (
                  <li key={c.id}>
                    <a className="link strong" href={`#/cases/${c.id}`}>{c.case_no}</a> <span className="muted small">· {c.station} · {c.registered_on}</span>
                    <div>{c.offence.map(o => <span key={o} className="badge info">{o}</span>)} <span className="small">{c.accused.join(', ')} {c.vehicles.length > 0 && `· ${c.vehicles.join(', ')}`}</span></div>
                    <div className="matched small">Matched: {c.matched.join(' · ')}</div>
                  </li>))}</ul>
              )}
            </section>
            <section className="card">
              <div className="cardhead"><h2>Name matches</h2><span className="muted small">Original spelling is always shown</span></div>
              {res.name_matches.length === 0 ? <Empty>No similar names found.</Empty> : (
                <ul className="list">{res.name_matches.map(m => (
                  <li key={m.case_no + m.page + m.name + m.span}>
                    <button className="link strong" onClick={() => setEv({ docId: m.document_id, page: m.page, span: m.span, label: 'Source' })}>{m.name}</button>
                    <span className="muted small"> · {m.case_no} · {m.why}</span></li>))}</ul>
              )}
            </section>
            <section className="card">
              <div className="cardhead"><h2>Text inside documents</h2></div>
              {res.text_hits.length === 0 ? <Empty>No text matches. Try fewer words or another spelling.</Empty> : (
                <ul className="list">{res.text_hits.map((h, i) => (
                  <li key={i}>
                    <a className="link strong" href={`#/cases/${h.case_id}`}>{h.case_no}</a><span className="muted small"> · page {h.page}</span>
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
