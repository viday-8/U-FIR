import { AlertTriangle, CalendarClock, FileCheck2, FileUp, FolderOpen, MessageSquare, Network, RefreshCw, Scale, ScrollText, Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, getRole, type Dashboard as D } from './api'
import { locale, useT } from './i18n'
import { QuoteOfTheDay } from './quotes'
import { Badge, Empty, ErrorBox, fmtDate, Loading, Notice, PageHeader, useAsync } from './ui'

/** Number that counts up when it first appears or changes (instantly, if the user prefers reduced motion). */
function CountUp({ value }: { value: number }) {
  const [shown, setShown] = useState(0)
  const from = useRef(0)
  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches || value === from.current) { setShown(value); from.current = value; return }
    const start = performance.now(), a = from.current
    let raf = 0
    const tick = (t: number) => { const k = Math.min(1, (t - start) / 600); setShown(Math.round(a + (value - a) * (1 - Math.pow(1 - k, 3)))); if (k < 1) raf = requestAnimationFrame(tick); else from.current = value }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value])
  return <>{shown}</>
}

/** Server-built attention lines are English; translate their fixed phrases so the list reads naturally in Telugu. */
const trLine = (t: (s: string) => string, line: string) => line.replace(/^(Possible match:|OVERDUE:)/, m => t(m)).replace(/\((likely|possible),/, (_, w) => `(${t(w)},`).replace(' was due ', ` ${t('was due')} `)

const greeting = () => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening' }

const STAGES = [['received', 'Received'], ['indexed', 'Processed'], ['reviewed', 'Reviewed by a person'], ['needs_review', 'Needs review'], ['failed', 'Failed']] as const

export default function Dashboard() {
  const t = useT()
  const [f, setF] = useState({ district: '', station: '', from_month: '', to_month: '' })
  const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString()
  const { data: d, error, loading, reload } = useAsync(() => api<D>('/dashboard' + (qs ? `?${qs}` : '')), [qs])
  const [opts, setOpts] = useState<D['options'] | null>(null)
  const [updated, setUpdated] = useState(new Date())
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
  const href = (a: D['attention'][number]) => a.kind === 'deadline' ? `#/cases/${a.case_id}` : a.kind === 'identity' ? '#/network' : a.kind === 'draft' ? `#/studio/${a.draft_id}` : `#/cases/${a.case_id}`
  return (
    <>
      <PageHeader title="Command Center" sub={t('{greeting}, {role}. {district} · {facts} facts extracted from {docs} document(s).', { greeting: t(greeting()), role: t(d.user.role), district: d.user.district ? t(d.user.district) : t('all districts'), facts: c.facts, docs: c.documents })}
        actions={<><button className="btn" onClick={() => { reload(); setUpdated(new Date()) }}><RefreshCw size={14} /> {t('Refresh')}</button><span className="muted small">{t('Updated')} {updated.toLocaleTimeString(locale(), { hour: '2-digit', minute: '2-digit' })}</span>
          {['investigator', 'supervisor', 'admin'].includes(getRole()) && <a className="btn primary" href="#/intake">{t('Upload case files')}</a>}</>} />
      <QuoteOfTheDay />
      <nav className="quick" aria-label="Quick actions">
        {[...(['investigator', 'supervisor', 'admin'].includes(getRole()) ? [{ href: '#/intake', icon: <FileUp size={20} />, t: 'Upload case files', d: 'Add FIRs, panchanamas, scans' }] : []),
          { href: '#/search', icon: <Search size={20} />, t: 'Search records', d: 'Names, vehicles, places' },
          { href: '#/copilot', icon: <MessageSquare size={20} />, t: 'Ask the Copilot', d: 'Cited answers only' },
          { href: '#/network', icon: <Network size={20} />, t: 'Open the network', d: 'Repeat offenders and links' },
          { href: '#/deadlines', icon: <CalendarClock size={20} />, t: 'Deadlines', d: 'Remand, chargesheet, hearings' }].map(q => (
          <a key={q.t} className="qtile" href={q.href}>{q.icon}<span><strong>{t(q.t)}</strong><small>{t(q.d)}</small></span></a>))}
      </nav>
      {opts && (
        <div className="toolbar" role="group" aria-label="Filters">
          {opts.districts.length > 1 && <label className="inline">{t('District')}<select value={f.district} onChange={e => setF({ ...f, district: e.target.value, station: '' })}><option value="">{t('All')}</option>{opts.districts.map(x => <option key={x}>{x}</option>)}</select></label>}
          <label className="inline">{t('Station')}<select value={f.station} onChange={e => setF({ ...f, station: e.target.value })}><option value="">{t('All')}</option>{opts.stations.map(x => <option key={x}>{x}</option>)}</select></label>
          <label className="inline">{t('From')}<select value={f.from_month} onChange={e => setF({ ...f, from_month: e.target.value })}><option value="">{t('Start')}</option>{opts.months.map(x => <option key={x}>{x}</option>)}</select></label>
          <label className="inline">{t('To')}<select value={f.to_month} onChange={e => setF({ ...f, to_month: e.target.value })}><option value="">{t('Latest')}</option>{opts.months.map(x => <option key={x}>{x}</option>)}</select></label>
          {qs && <button className="btn sm" onClick={() => setF({ district: '', station: '', from_month: '', to_month: '' })}>{t('Clear filters')}</button>}
          {loading && <span className="muted small">{t('Updating…')}</span>}
        </div>
      )}
      <Notice>All figures are computed from the records you are authorised to see, on synthetic demo data. Each tile opens the matching list.</Notice>
      <div className="kpis">
        {kpis.map(k => (
          <a key={k.label} className={'kpi' + (k.warn ? ' warn' : '')} href={k.href}>
            <span className="kpiicon">{k.icon}</span><span className="kpival"><CountUp value={k.value} /></span><span className="kpilabel">{t(k.label)}</span>
          </a>
        ))}
      </div>
      <div className="two">
        <section className="card">
          <div className="cardhead"><h2>{t('Needs attention')}</h2><a href="#/reviews" className="link">{t('Open review queue')}</a></div>
          {d.attention.length === 0 ? <Empty>Nothing needs review right now.</Empty> : (
            <ul className="list">
              {d.attention.map((a, i) => (
                <li key={i}><a href={href(a)}><AlertTriangle size={14} className="warnicon" /> {trLine(t, a.label)}</a></li>
              ))}
            </ul>
          )}
        </section>
        <section className="card">
          <div className="cardhead"><h2>{t('Deadlines')}</h2><a href="#/deadlines" className="link">{t('All deadlines')}</a></div>
          {d.deadlines.items.length === 0 ? <Empty>No overdue dates and nothing due in the next 14 days.</Empty> : (
            <ul className="list">{d.deadlines.items.map(m => (
              <li key={m.id} className="row"><span><a className="link" href={`#/cases/${m.case_id}`}>{m.case_no}</a> · {m.title} <span className="muted small">{m.due_on}</span></span>
                <Badge status={m.state} label={m.state === 'overdue' ? `Overdue by ${-m.days} day(s)` : `In ${m.days} day(s)`} /></li>))}</ul>
          )}
        </section>
        <section className="card">
          <div className="cardhead"><h2>{t('Processing pipeline')}</h2></div>
          <div className="pad">
            <div className="stack" role="img" aria-label={STAGES.map(([k, l]) => `${t(l)}: ${d.pipeline[k] ?? 0}`).join(', ')}>
              {STAGES.map(([k]) => (d.pipeline[k] ? <span key={k} className={`seg ${k}`} style={{ width: `${(d.pipeline[k] / total) * 100}%` }} /> : null))}
            </div>
            <ul className="legendlist">
              {STAGES.map(([k, l]) => <li key={k}><span className={`dot ${k}`} />{t(l)}<strong>{d.pipeline[k] ?? 0}</strong></li>)}
            </ul>
            <p className="muted small">{t('Files that fail or need review never block the rest of a batch.')}</p>
          </div>
        </section>
        <section className="card">
          <div className="cardhead"><h2>{t('Cases registered by month')}</h2></div>
          <div className="pad">
            {months.length === 0 ? <Empty>No cases.</Empty> : (
              <div className="bars" role="img" aria-label={months.map(([m, n]) => `${m}: ${n}`).join(', ')}>
                {months.map(([m, n]) => <div key={m} className="barcol"><span className="barval">{n}</span><span className="bar" style={{ height: `${(n / max) * 110}px` }} /><span className="barlab">{m.slice(2)}</span></div>)}
              </div>
            )}
            <h3>{t('By station')}</h3>
            <ul className="legendlist">{Object.entries(d.cases_by_station).map(([s, n]) => <li key={s}>{s}<strong>{n}</strong></li>)}</ul>
          </div>
        </section>
        <section className="card">
          <div className="cardhead"><h2>{t('Recent AI-assisted activity')}</h2><a href="#/audit" className="link">{t('Open audit ledger')}</a></div>
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
