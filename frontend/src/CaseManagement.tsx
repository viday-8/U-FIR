import { Plus } from 'lucide-react'
import { useState } from 'react'
import { api, getRole, type Accused, type CaseMeta, type Checklist, type Milestone, type Property } from './api'
import { useT } from './i18n'
import { Badge, Empty, ErrorBox, Loading, Notice, useAsync } from './ui'

const editor = () => ['investigator', 'supervisor', 'admin'].includes(getRole())
const ACCUSED = [['named', 'Named'], ['arrested', 'Arrested'], ['remanded', 'In remand'], ['bailed', 'On bail'], ['absconding', 'Absconding']]
const PROPERTY = [['seized', 'Seized'], ['sample_sent', 'Sample sent'], ['lab_report_received', 'Lab report received'], ['produced_in_court', 'Produced in court'], ['released', 'Released'], ['destroyed', 'Destroyed']]
const KINDS = [['chargesheet_due', 'Chargesheet due'], ['remand_expiry', 'Remand expiry'], ['court_hearing', 'Court hearing'], ['lab_report_due', 'Lab report due'], ['other', 'Other']]

function useSend(after: () => void) {
  const [msg, setMsg] = useState('')
  const send = async (path: string, method: string, body?: object) => { setMsg(''); try { await api(path, { method, body: body ? JSON.stringify(body) : undefined }); after() } catch (e) { setMsg((e as Error).message) } }
  return { msg, send }
}

function AccusedCard({ id, meta, onChange }: { id: number; meta?: CaseMeta; onChange: () => void }) {
  const t = useT()
  const list = useAsync(() => api<Accused[]>(`/cases/${id}/accused`), [id])
  const { msg, send } = useSend(() => { list.reload(); onChange() })
  const [nf, setNf] = useState({ name: '', father_or_spouse: '', age: '' })
  const can = editor()
  const known = new Set((list.data ?? []).map(a => a.name.toLowerCase()))
  const suggestions = (meta?.accused ?? []).filter(a => !known.has(a.name.toLowerCase()))
  if (list.loading) return <Loading what="Loading accused" />
  return (
    <section className="card">
      <div className="cardhead"><h2>{t('Accused and custody')}</h2><span className="muted small">Who is an accused is an officer's decision</span></div>
      <div className="pad">
        {msg && <ErrorBox message={msg} />}
        {can && suggestions.length > 0 && <p className="small">Named in the records: {suggestions.map(a => <button key={a.name} className="chip" onClick={() => send(`/cases/${id}/accused`, 'POST', { name: a.name, father_or_spouse: a.father_or_spouse ?? null, age: a.age ?? null })}>+ {a.name}</button>)}</p>}
        {!list.data?.length ? <Empty>No accused recorded yet. Add the people the officer decides are accused.</Empty> : (
          <div className="tablewrap"><table>
            <thead><tr><th>Name</th><th>Status</th><th>Arrested on</th><th>Remand till</th><th>Bail on</th><th>Deadline</th></tr></thead>
            <tbody>{list.data.map(a => (
              <tr key={a.id}>
                <td><strong>{a.name}</strong><div className="muted small">{[a.father_or_spouse && `S/o ${a.father_or_spouse}`, a.age && `age ${a.age}`].filter(Boolean).join(' · ')}</div></td>
                <td><select aria-label={`Status of ${a.name}`} value={a.status} disabled={!can} onChange={e => send(`/accused/${a.id}`, 'PATCH', { status: e.target.value })}>{ACCUSED.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></td>
                {(['arrested_on', 'remand_till', 'bail_on'] as const).map(f => <td key={f}><input type="date" aria-label={`${f.replace('_', ' ')} for ${a.name}`} value={a[f] ?? ''} disabled={!can} onChange={e => send(`/accused/${a.id}`, 'PATCH', { [f]: e.target.value || null })} /></td>)}
                <td>{can && a.arrested_on && <><button className="btn sm" onClick={() => send(`/accused/${a.id}/chargesheet-deadline`, 'POST', { days: 60 })}>+60 days</button><button className="btn sm" onClick={() => send(`/accused/${a.id}/chargesheet-deadline`, 'POST', { days: 90 })}>+90 days</button></>}</td>
              </tr>))}</tbody></table></div>
        )}
        {can && <div className="formrow addform">
          <label>{t('Name')}<input value={nf.name} onChange={e => setNf({ ...nf, name: e.target.value })} /></label>
          <label>Father/spouse<input value={nf.father_or_spouse} onChange={e => setNf({ ...nf, father_or_spouse: e.target.value })} /></label>
          <label>{t('Age')}<input value={nf.age} onChange={e => setNf({ ...nf, age: e.target.value })} /></label>
          <button className="btn" disabled={!nf.name.trim()} onClick={() => { void send(`/cases/${id}/accused`, 'POST', { name: nf.name, father_or_spouse: nf.father_or_spouse || null, age: nf.age || null }); setNf({ name: '', father_or_spouse: '', age: '' }) }}><Plus size={14} /> {t('Add')}</button>
        </div>}
        <p className="muted small">“+60/+90 days” sets a chargesheet deadline from the arrest date. The officer chooses the limit; confirm it with the prosecutor.</p>
      </div>
    </section>
  )
}

function PropertyCard({ id, onChange }: { id: number; onChange: () => void }) {
  const t = useT()
  const list = useAsync(() => api<Property[]>(`/cases/${id}/property`), [id])
  const { msg, send } = useSend(() => { list.reload(); onChange() })
  const [nf, setNf] = useState({ kind: 'liquor', description: '', quantity: '' })
  const can = editor()
  if (list.loading) return <Loading what="Loading seizure register" />
  return (
    <section className="card">
      <div className="cardhead"><h2>{t('Seizure register (malkhana)')}</h2>{can && <button className="btn sm" onClick={() => send(`/cases/${id}/property/from-records`, 'POST')}>Fill from the records</button>}</div>
      <div className="pad">
        {msg && <ErrorBox message={msg} />}
        {!list.data?.length ? <Empty>Nothing registered. “Fill from the records” adds the vehicles and items found in the documents.</Empty> : (
          <div className="tablewrap"><table>
            <thead><tr><th>Item</th><th>Custody</th><th>Status</th><th>Sample sent</th><th>Lab report</th></tr></thead>
            <tbody>{list.data.map(p => (
              <tr key={p.id}>
                <td><strong>{p.description}</strong><div className="muted small">{p.kind}{p.quantity ? ` · ${p.quantity}` : ''}</div></td>
                <td><input aria-label={`Custody of ${p.description}`} defaultValue={p.custody} disabled={!can} onBlur={e => e.target.value !== p.custody && send(`/property/${p.id}`, 'PATCH', { custody: e.target.value })} /></td>
                <td><select aria-label={`Status of ${p.description}`} value={p.status} disabled={!can} onChange={e => send(`/property/${p.id}`, 'PATCH', { status: e.target.value })}>{PROPERTY.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></td>
                <td><input type="date" aria-label={`Sample sent date for ${p.description}`} value={p.sample_sent_on ?? ''} disabled={!can} onChange={e => send(`/property/${p.id}`, 'PATCH', { sample_sent_on: e.target.value || null })} /></td>
                <td><input type="date" aria-label={`Lab report date for ${p.description}`} value={p.lab_report_on ?? ''} disabled={!can} onChange={e => send(`/property/${p.id}`, 'PATCH', { lab_report_on: e.target.value || null })} /></td>
              </tr>))}</tbody></table></div>
        )}
        {can && <div className="formrow addform">
          <label>Type<select value={nf.kind} onChange={e => setNf({ ...nf, kind: e.target.value })}><option value="liquor">Liquor</option><option value="ganja">Ganja</option><option value="vehicle">Vehicle</option><option value="other">Other</option></select></label>
          <label>{t('Description')}<input value={nf.description} onChange={e => setNf({ ...nf, description: e.target.value })} /></label>
          <label>{t('Quantity')}<input value={nf.quantity} onChange={e => setNf({ ...nf, quantity: e.target.value })} /></label>
          <button className="btn" disabled={!nf.description.trim()} onClick={() => { void send(`/cases/${id}/property`, 'POST', { ...nf, quantity: nf.quantity || null }); setNf({ kind: 'liquor', description: '', quantity: '' }) }}><Plus size={14} /> {t('Add')}</button>
        </div>}
      </div>
    </section>
  )
}

function DeadlinesCard({ id, onChange }: { id: number; onChange: () => void }) {
  const t = useT()
  const list = useAsync(() => api<Milestone[]>(`/cases/${id}/milestones`), [id])
  const { msg, send } = useSend(() => { list.reload(); onChange() })
  const [nf, setNf] = useState({ kind: 'court_hearing', title: '', due_on: '' })
  const can = editor()
  if (list.loading) return <Loading what="Loading deadlines" />
  return (
    <section className="card">
      <div className="cardhead"><h2>{t('Deadlines and dates')}</h2></div>
      <div className="pad">
        {msg && <ErrorBox message={msg} />}
        {!list.data?.length ? <Empty>No dates tracked. Add chargesheet limits, remand expiry, hearings and lab reports so none is missed.</Empty> : (
          <ul className="list">{list.data.map(m => (
            <li key={m.id} className="row"><span><strong>{m.due_on}</strong> · {m.title} <span className="muted small">({KINDS.find(k => k[0] === m.kind)?.[1]})</span></span>
              <span className="actions"><Badge status={m.state} label={m.state === 'overdue' ? `Overdue by ${-m.days} day(s)` : m.state === 'soon' ? `In ${m.days} day(s)` : undefined} />
                {can && <button className="btn sm" onClick={() => send(`/milestones/${m.id}`, 'PATCH', { done: !m.done })}>{m.done ? t('Reopen') : t('Mark done')}</button>}</span></li>))}</ul>
        )}
        {can && <div className="formrow addform">
          <label>Type<select value={nf.kind} onChange={e => setNf({ ...nf, kind: e.target.value })}>{KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
          <label>What<input value={nf.title} onChange={e => setNf({ ...nf, title: e.target.value })} /></label>
          <label>Due on<input type="date" value={nf.due_on} onChange={e => setNf({ ...nf, due_on: e.target.value })} /></label>
          <button className="btn" disabled={!nf.title.trim() || !nf.due_on} onClick={() => { void send(`/cases/${id}/milestones`, 'POST', nf); setNf({ ...nf, title: '', due_on: '' }) }}><Plus size={14} /> {t('Add')}</button>
        </div>}
      </div>
    </section>
  )
}

function ChecklistCard({ id }: { id: number }) {
  const t = useT()
  const c = useAsync(() => api<Checklist>(`/cases/${id}/checklist`), [id])
  const { msg, send } = useSend(c.reload)
  if (c.loading || !c.data) return <Loading what="Loading checklist" />
  const done = c.data.items.filter(i => i.done).length
  return (
    <section className="card">
      <div className="cardhead"><h2>{t('Compliance checklist')}</h2><span className="muted small">{done} of {c.data.items.length} done</span></div>
      <div className="pad">
        <Notice>{c.data.notice}</Notice>
        {msg && <ErrorBox message={msg} />}
        <ul className="list">{c.data.items.map(i => (
          <li key={i.key} className="row"><span>{i.done ? '✓' : '○'} {i.label}{i.by && <span className="muted small"> · ticked by {i.by}</span>}</span>
            {i.manual && editor() ? <button className="btn sm" onClick={() => send(`/cases/${id}/checklist/avrec`, 'POST', { done: !i.done })}>{i.done ? 'Untick' : 'Tick'}</button>
              : <span className="muted small">{i.manual ? 'ticked by an officer' : 'from the records'}</span>}</li>))}</ul>
      </div>
    </section>
  )
}

export default function CaseManagement({ id, meta }: { id: number; meta?: CaseMeta }) {
  const [v, setV] = useState(0)  // any change in one card refreshes the cards that depend on it (deadlines, checklist)
  const bump = () => setV(x => x + 1)
  return <><AccusedCard id={id} meta={meta} onChange={bump} /><DeadlinesCard key={'d' + v} id={id} onChange={bump} /><PropertyCard id={id} onChange={bump} /><ChecklistCard key={'c' + v} id={id} /></>
}
