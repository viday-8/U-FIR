import { AlertTriangle, FilePlus2, Info, MessageSquare, Scale } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, type Stage, type Brief, type Case, type CaseMeta, type CaseNetwork, type DraftSummary, type Fact, type LegalResp, type Statement, type TimelineEvent, getRole } from './api'
import { EvidenceViewer, type Evidence } from './Evidence'
import CaseManagement from './CaseManagement'
import { useT } from './i18n'
import DocActions from './DocActions'
import FactsPanel from './FactsPanel'
import { useCrumb } from './Shell'
import TagEditor from './TagEditor'
import UploadPanel from './UploadPanel'
import { Badge, Empty, ErrorBox, fmtDate, Loading, Notice, PageHeader, useAsync } from './ui'

type Tab = 'brief' | 'manage' | 'legal' | 'facts' | 'documents' | 'drafts'
const canEdit = () => ['investigator', 'supervisor', 'admin'].includes(getRole())

export default function Cockpit({ id }: { id: number }) {
  const t = useT()
  const [tab, setTab] = useState<Tab>('brief')
  const [ev, setEv] = useState<Evidence | null>(null)
  const meta = useAsync(() => api<Case>(`/cases/${id}`), [id])
  const brief = useAsync(() => api<Brief>(`/cases/${id}/brief`), [id])
  const timeline = useAsync(() => api<TimelineEvent[]>(`/cases/${id}/timeline`), [id])
  const facts = useAsync(() => api<Fact[]>(`/cases/${id}/facts`), [id])
  const meta2 = useAsync(() => api<CaseMeta>(`/cases/${id}/meta`), [id])
  const net = useAsync(() => api<CaseNetwork>(`/cases/${id}/network`), [id])
  const stage = useAsync(() => api<Stage>(`/cases/${id}/stage`), [id])
  useEffect(() => { setEv(null); setTab('brief') }, [id])
  useCrumb(meta.data?.case_no)

  if (meta.error || brief.error) return <ErrorBox message={meta.error || brief.error} retry={() => { meta.reload(); brief.reload() }} />
  if (!meta.data || !brief.data) return <Loading what="Opening case" />
  const c = meta.data, b = brief.data
  const factMap = Object.fromEntries((facts.data ?? []).map(f => [f.id, f]))
  const docType = (docId: number) => b.records_reviewed.list.find(d => d.id === docId)?.type ?? 'Document'
  const openFact = (f: Fact) => setEv({ docId: f.document_id, page: f.page, span: f.span, label: docType(f.document_id) })
  const Cites = ({ ids }: { ids: number[] }) => (
    <span className="cites">
      {ids.slice(0, 4).map(i => factMap[i] && (
        <button key={i} className="chip" onClick={() => openFact(factMap[i])} aria-label={`${docType(factMap[i].document_id)} p${factMap[i].page}, open source`}>
          {docType(factMap[i].document_id)} p{factMap[i].page}
        </button>
      ))}
    </span>
  )
  const Stmt = ({ s }: { s: Statement }) => <li>{s.text} <Cites ids={s.fact_ids} /></li>
  const tabs: [Tab, string][] = [['brief', 'Brief & timeline'], ['manage', 'Case management'], ['legal', 'Legal'], ['facts', 'Facts'], ['documents', 'Documents'], ['drafts', 'Drafts']]

  const stepTab: Record<string, Tab> = { 'Seizure recorded': 'documents', 'Samples and lab': 'manage', Custody: 'manage', Chargesheet: 'drafts', Court: 'manage' }
  return (
    <>
      <div className="ribbon">{t('Case file · Official use only · Synthetic data')}</div>
      <PageHeader title={c.case_no} sub={`${c.district} · ${c.station} · registered ${c.registered_on}`}
        actions={<><a className="btn" href={`#/copilot?case=${c.id}`}><MessageSquare size={14} /> {t('Ask Copilot')}</a><Badge status={c.status} /><span className="muted small">{t('{n} document(s) reviewed', { n: b.records_reviewed.documents })}</span></>} />
      {stage.data && (
        <ol className="stepper" aria-label={t('Case progress')}>
          {stage.data.steps.map((st, i) => (
            <li key={st.name} className={st.state}>
              <button onClick={() => stepTab[st.name] && setTab(stepTab[st.name])} title={t(st.hint)} aria-current={st.state === 'current' ? 'step' : undefined}>
                <span className="dotstep">{st.state === 'done' ? '✓' : i + 1}</span><span className="steplabel">{t(st.name)}<small>{st.hint.startsWith('FIR registered ') ? `${t('FIR registered')} ${st.hint.slice(15)}` : t(st.hint)}</small></span>
              </button>
            </li>))}
        </ol>
      )}
      {meta2.data && (
        <div className="metastrip card pad" aria-label="Case metadata">
          <TagEditor caseId={id} meta={meta2.data} onChanged={meta2.reload} />
          <div>{meta2.data.flags.needs_review && <span className="badge warn">Needs review</span>}{meta2.data.flags.ocr && <span className="badge neutral">OCR text</span>}{meta2.data.flags.telugu && <span className="badge warn">Telugu</span>}</div>
          <dl className="metagrid">
            <div><dt>{t('Persons named')}</dt><dd>{meta2.data.accused.map(a => a.name).join(', ') || '—'}</dd></div>
            <div><dt>{t('Vehicles')}</dt><dd>{meta2.data.vehicles.join(', ') || '—'}</dd></div>
            <div><dt>{t('Items')}</dt><dd>{[...meta2.data.items, ...meta2.data.quantities.slice(0, 2)].join(', ') || '—'}</dd></div>
            <div><dt>{t('Places')}</dt><dd>{meta2.data.places.join(', ') || '—'}</dd></div>
            <div><dt>{t('Sections written')}</dt><dd>{meta2.data.sections.join(', ') || '—'}</dd></div>
            <div><dt>{t('Dates')}</dt><dd>{meta2.data.date_first ? `${meta2.data.date_first}${meta2.data.date_last && meta2.data.date_last !== meta2.data.date_first ? ` to ${meta2.data.date_last}` : ''}` : '—'}</dd></div>
          </dl>
          <div className="muted small">{t('Keywords:')} {meta2.data.keywords.map(k => <button key={k} className="chip" onClick={() => { location.hash = `/search?q=${encodeURIComponent(k)}` }}>{k}</button>)}</div>
        </div>
      )}
      <div role="tablist" className="tabs">
        {tabs.map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{t(l)}{k === 'documents' ? ` (${c.documents})` : ''}</button>)}
      </div>
      <div className={tab === 'manage' ? 'fullwidth' : 'split'}>
        <div className="main">
          {tab === 'brief' && (
            <>
              <section className="card" aria-label="Case brief">
                <div className="cardhead"><h2>{t('Case brief')}</h2><span className="muted small">Generated by {b.generated_by}</span></div>
                <div className="pad">
                  <Notice>{b.notice} Every line links to its source.</Notice>
                  {b.sections.map(s => <div key={s.title}><h3>{s.title}</h3><ul className="statements">{s.statements.map((st, i) => <Stmt key={i} s={st} />)}</ul></div>)}
                  {b.conflicts.length > 0 && <div className="flag warn"><h3><AlertTriangle size={14} /> Conflicts to review</h3><ul className="statements">{b.conflicts.map((s, i) => <Stmt key={i} s={s} />)}</ul></div>}
                  {b.missing.length > 0 && <div className="flag info"><h3><Info size={14} /> Missing information</h3><ul className="statements">{b.missing.map(m => <li key={m}>{m}</li>)}</ul></div>}
                </div>
              </section>
              {net.data && (
                <section className="card" aria-label="Related cases">
                  <div className="cardhead"><h2>{t('Related cases')}</h2><a className="link small" href={`#/network?focus=case:${id}`}>Open in network</a></div>
                  <div className="pad">
                    {net.data.related_cases.length === 0 ? <p className="muted small">No links to other cases you can access: this case's people and vehicles do not appear elsewhere in the records.</p> : (
                      <ul className="list">{net.data.related_cases.map(r => <li key={r.id}><a className="link strong" href={`#/cases/${r.id}`}>{r.case_no}</a>
                        <div className="small muted">{r.why.join(' · ')}</div></li>)}</ul>)}
                  </div>
                </section>
              )}
              <section className="card" aria-label="Timeline">
                <div className="cardhead"><h2>{t('Timeline')}</h2></div>
                <div className="pad">
                  {!timeline.data?.length ? <Empty>No dated events extracted.</Empty> : (
                    <ol className="timeline">
                      {timeline.data.map(t => (
                        <li key={t.fact_id}>
                          <button className="link" onClick={() => factMap[t.fact_id] && openFact(factMap[t.fact_id])}>
                            <strong>{t.date ?? t.date_text}</strong>{t.uncertain && ' (unclear date)'} · {t.doc_type} p{t.page}
                          </button>
                          <div className="muted small">…{t.context}…</div>
                        </li>
                      ))}
                    </ol>
                  )}
                </div>
              </section>
            </>
          )}
          {tab === 'manage' && <CaseManagement id={id} meta={meta2.data ?? undefined} />}
          {tab === 'legal' && <LegalPanel id={id} openPassage={p => setEv({ docId: p.document_id, page: p.page, span: p.span, label: docType(p.document_id) })} openFact={openFact} factMap={factMap} />}
          {tab === 'facts' && <FactsPanel caseId={id} brief={b} onOpen={openFact} onChanged={() => { brief.reload(); timeline.reload() }} />}
          {tab === 'documents' && (
            <>
              <section className="card tablewrap"><table>
                <thead><tr><th>Document</th><th>Status</th><th>Notes</th><th></th></tr></thead>
                <tbody>{b.records_reviewed.list.map(d => (
                  <tr key={d.id}><td>{d.type}</td><td><Badge status={d.status} /></td>
                    <td className="small">{d.ocr && <span className="badge warn">OCR text</span>} {d.language !== 'en' && <span className="badge warn">{d.language === 'te' ? 'Telugu' : 'Mixed language'}</span>}</td>
                    <td><button className="link" onClick={() => setEv({ docId: d.id, page: 1, span: '', label: d.type })}>View original</button>
                      <DocActions docId={d.id} status={d.status} onDone={() => { brief.reload(); meta.reload() }} /></td></tr>
                ))}</tbody></table></section>
              {canEdit() && <UploadPanel caseId={id} onDone={() => { meta.reload(); brief.reload(); facts.reload(); timeline.reload() }} />}
            </>
          )}
          {tab === 'drafts' && <DraftsPanel id={id} />}
        </div>
        {tab !== 'manage' && <EvidenceViewer ev={ev} />}
      </div>
    </>
  )
}

function LegalPanel({ id, openPassage, openFact, factMap }: { id: number; openPassage: (p: { document_id: number; page: number; span: string }) => void; openFact: (f: Fact) => void; factMap: Record<number, Fact> }) {
  const { data, error, loading, reload } = useAsync(() => api<LegalResp>(`/cases/${id}/legal`), [id])
  const [reason, setReason] = useState<Record<number, string>>({})
  const [msg, setMsg] = useState('')
  const run = async () => { setMsg(''); try { await api(`/cases/${id}/legal/suggest`, { method: 'POST' }); reload() } catch (e) { setMsg((e as Error).message) } }
  const decide = async (sid: number, decision: string) => {
    setMsg('')
    try { await api(`/legal/${sid}/review`, { method: 'POST', body: JSON.stringify({ decision, reason: reason[sid] ?? '' }) }); reload() }
    catch (e) { setMsg((e as Error).message) }
  }
  if (loading) return <Loading what="Loading legal suggestions" />
  if (error) return <ErrorBox message={error} retry={reload} />
  return (
    <section className="card">
      <div className="cardhead"><h2><Scale size={16} /> Legal suggestions</h2>{canEdit() && <button className="btn" onClick={run}>{data?.suggestions.length ? 'Refresh suggestions' : 'Suggest provisions'}</button>}</div>
      <div className="pad">
        <Notice tone="warn">{data?.notice} Suggestions are advisory and need an officer's decision.</Notice>
        {msg && <ErrorBox message={msg} />}
        {!data?.suggestions.length ? <Empty>No suggestions yet. Run “Suggest provisions” to match the recorded facts against the catalogue.</Empty> : data.suggestions.map(s => (
          <article key={s.id} className="legal">
            <div className="row"><h3>{s.act}, Section {s.section}</h3><Badge status={s.status} /></div>
            <p><strong>{s.title}</strong></p>
            <p className="muted small">{s.summary}</p>
            <p><strong>Why suggested:</strong> {s.rationale}</p>
            {s.already_cited && <p className="small"><Info size={13} /> This section is already written in the case records.</p>}
            <div>
              {s.passages.map((p, i) => <button key={i} className="chip" onClick={() => openPassage(p)}>Passage p{p.page}</button>)}
              {s.fact_ids.slice(0, 6).map(fid => factMap[fid] && <button key={fid} className="chip" onClick={() => openFact(factMap[fid])}>{factMap[fid].type}: {factMap[fid].original}</button>)}
            </div>
            <p className="muted small">{s.label}</p>
            {s.decided_by && <p className="muted small">Decision by {s.decided_by}: {s.reason}</p>}
            {canEdit() && (s.status === 'suggested' || s.status === 'insufficient') && (
              <div className="reviewrow">
                <input aria-label="Reason" placeholder="Reason for your decision" value={reason[s.id] ?? ''} onChange={e => setReason({ ...reason, [s.id]: e.target.value })} />
                <button className="btn primary" onClick={() => decide(s.id, 'accept')}>Accept</button>
                <button className="btn" onClick={() => decide(s.id, 'reject')}>Reject</button>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}

function DraftsPanel({ id }: { id: number }) {
  const { data, error, loading, reload } = useAsync(() => api<DraftSummary[]>(`/cases/${id}/drafts`), [id])
  const [msg, setMsg] = useState('')
  const create = async (doc_type: string) => {
    setMsg('')
    try { const d = await api<DraftSummary>(`/cases/${id}/drafts`, { method: 'POST', body: JSON.stringify({ doc_type }) }); location.hash = `/studio/${d.id}` }
    catch (e) { setMsg((e as Error).message) }
  }
  if (loading) return <Loading what="Loading drafts" />
  if (error) return <ErrorBox message={error} retry={reload} />
  return (
    <section className="card">
      <div className="cardhead"><h2>Drafts</h2>
        {canEdit() && <div className="actions"><button className="btn" onClick={() => create('case_diary')}><FilePlus2 size={14} /> Case diary</button><button className="btn" onClick={() => create('chargesheet')}><FilePlus2 size={14} /> Chargesheet</button></div>}
      </div>
      <div className="pad">
        {msg && <ErrorBox message={msg} />}
        {!data?.length ? <Empty>No drafts for this case yet. Generated drafts are always marked as drafts until a supervisor approves them.</Empty> : (
          <table><thead><tr><th>Document</th><th>Status</th><th>Version</th><th>Author</th><th>Updated</th></tr></thead>
            <tbody>{data.map(d => <tr key={d.id}><td><a className="link strong" href={`#/studio/${d.id}`}>{d.title}</a></td><td><Badge status={d.status} /></td><td>v{d.version}</td><td>{d.author}</td><td>{fmtDate(d.updated_at)}</td></tr>)}</tbody></table>
        )}
      </div>
    </section>
  )
}
