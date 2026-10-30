import { AlertTriangle, ScanLine, Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, type Overview } from './api'
import { useT } from './i18n'
import { Badge, Empty, ErrorBox, Loading, PageHeader } from './ui'
import { Download } from 'lucide-react'

const empty = { q: '', offence: '', station: '', status: '', district: '', from_date: '', to_date: '', flag: '' }

export default function CasesList() {
  const t = useT()
  const [f, setF] = useState(empty)
  const [q, setQ] = useState('')  // debounced keyword
  const [data, setData] = useState<Overview | null>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { const t = setTimeout(() => setQ(f.q), 250); return () => clearTimeout(t) }, [f.q])
  const qs = new URLSearchParams(Object.entries({ ...f, q }).filter(([, v]) => v)).toString()
  useEffect(() => {
    let live = true
    setBusy(true); setErr('')
    api<Overview>('/cases/overview' + (qs ? `?${qs}` : '')).then(d => live && setData(d)).catch(e => live && setErr(e.message)).finally(() => live && setBusy(false))
    return () => { live = false }
  }, [qs])
  const filtered = Object.entries(f).some(([, v]) => v)
  const fx = data?.facets
  const sel = (key: keyof typeof empty, label: string, facet?: Record<string, number>) => (
    <label className="inline">{t(label)}<select value={f[key]} onChange={e => setF({ ...f, [key]: e.target.value })}>
      <option value="">{t('All')}</option>{Object.entries(facet ?? {}).map(([k, n]) => <option key={k} value={k}>{t(k)} ({n})</option>)}</select></label>
  )
  if (err) return <ErrorBox message={err} />
  return (
    <>
      <PageHeader title="Cases" sub="Search by number, name (any spelling), vehicle, place, item or section. Metadata is read from the documents themselves." />
      <div className="card pad filterbar" role="search">
        <label className="searchbox big"><Search size={15} /><span className="sr">{t('Search')}</span>
          <input placeholder={t('Try: AP 31 TX 4521 · Rameshbabu · ganja · Narsipatnam · 34(a)')} value={f.q} onChange={e => setF({ ...f, q: e.target.value })} /></label>
        <div className="toolbar">
          {sel('offence', 'Offence type', fx?.offence)}
          {fx && Object.keys(fx.district).length > 1 && sel('district', 'District', fx.district)}
          {sel('station', 'Station', fx?.station)}
          {sel('status', 'Status', fx?.status)}
          <label className="inline">{t('Registered from')}<input type="date" value={f.from_date} onChange={e => setF({ ...f, from_date: e.target.value })} /></label>
          <label className="inline">{t('to')}<input type="date" value={f.to_date} onChange={e => setF({ ...f, to_date: e.target.value })} /></label>
          <label className="inline">{t('Show')}<select value={f.flag} onChange={e => setF({ ...f, flag: e.target.value })}><option value="">{t('Everything')}</option><option value="needs_review">{t('Needs review')}</option><option value="ocr">{t('Scanned (OCR)')}</option></select></label>
          {filtered && <button className="btn sm" onClick={() => setF(empty)}><X size={12} /> {t('Clear')}</button>}
          <button className="btn sm" onClick={async () => { const csv = await api<string>('/cases/export.csv' + (qs ? `?${qs}` : '')); const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); Object.assign(document.createElement('a'), { href: url, download: 'cases.csv' }).click(); URL.revokeObjectURL(url) }}><Download size={12} /> {t('Export CSV')}</button>
          <span className="muted small">{busy ? t('Searching…') : t('{n} case(s)', { n: data?.total ?? 0 })}</span>
        </div>
      </div>
      {!data ? <Loading what="Loading cases" /> : data.items.length === 0 ? <div className="card"><Empty>No cases match. Try fewer words or clear a filter.</Empty></div> : (
        <div className="card tablewrap">
          <table>
            <thead><tr><th>{t('Case')}</th><th>{t('Offence & keywords')}</th><th>{t('People & vehicles')}</th><th>{t('Documents')}</th><th>{t('Registered')}</th></tr></thead>
            <tbody>{data.items.map(c => (
              <tr key={c.id}>
                <td><a className="link strong" href={`#/cases/${c.id}`}>{c.case_no}</a><div className="muted small">{c.station}</div>{c.matched.length > 0 && <div className="matched small">{t('Matched:')} {c.matched.join(' · ')}</div>}</td>
                <td>{c.meta.offence.map(o => <button key={o} className="chip" onClick={() => setF({ ...f, offence: o })}>{t(o)}</button>)}
                  <div className="muted small">{[...c.meta.items.slice(0, 2), ...c.meta.sections.slice(0, 1)].join(' · ')}</div></td>
                <td className="small">{c.meta.accused.slice(0, 2).map(a => a.name + (a.age ? ` (${a.age})` : '')).join(', ') || <span className="muted">{t('no person recorded')}</span>}
                  <div className="muted">{c.meta.vehicles.join(', ')}</div></td>
                <td className="small">{c.documents} · {Object.entries(c.meta.documents).map(([k, n]) => `${n} ${k}`).join(', ')}
                  <div>{c.meta.flags.needs_review && <span className="badge warn"><AlertTriangle size={11} /> Needs review</span>} {c.meta.flags.ocr && <span className="badge neutral"><ScanLine size={11} /> OCR</span>}</div></td>
                <td>{c.registered_on}<div><Badge status={c.status} /></div></td>
              </tr>))}</tbody>
          </table>
        </div>
      )}
    </>
  )
}
