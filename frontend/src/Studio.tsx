import { Check, Download, Save, Send, Undo2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, type DraftFull, type DraftSummary, type Fact, getRole } from './api'
import { EvidenceViewer, type Evidence } from './Evidence'
import { Badge, Empty, ErrorBox, fmtDate, Loading, Notice, PageHeader, useAsync } from './ui'

const STATUSES = ['', 'draft', 'in_review', 'returned', 'approved']

export function StudioList({ status }: { status: string }) {
  const { data, error, loading, reload } = useAsync(() => api<DraftSummary[]>('/drafts' + (status ? `?status=${status}` : '')), [status])
  if (loading) return <Loading what="Loading drafts" />
  if (error) return <ErrorBox message={error} retry={reload} />
  return (
    <>
      <PageHeader title="Document Studio" sub="Case diaries and chargesheets assembled from case facts. Drafts become official only after supervisor approval." />
      <div className="toolbar">
        <span>Status:</span>
        {STATUSES.map(s => <a key={s} className={'pill' + (s === status ? ' on' : '')} href={s ? `#/studio?status=${s}` : '#/studio'}>{s ? s.replace('_', ' ') : 'all'}</a>)}
      </div>
      <div className="card tablewrap">
        {!data?.length ? <Empty>No drafts yet. Open a case and choose Drafts → Case diary or Chargesheet.</Empty> : (
          <table><thead><tr><th>Document</th><th>Case</th><th>Status</th><th>Version</th><th>Author</th><th>Updated</th></tr></thead>
            <tbody>{data.map(d => (
              <tr key={d.id}><td><a className="link strong" href={`#/studio/${d.id}`}>{d.title}</a></td><td>{d.case_no}</td>
                <td><Badge status={d.status} /></td><td>v{d.version}</td><td>{d.author}</td><td>{fmtDate(d.updated_at)}</td></tr>
            ))}</tbody></table>
        )}
      </div>
    </>
  )
}

export function StudioEditor({ id }: { id: number }) {
  const { data: d, error, loading, reload } = useAsync(() => api<DraftFull>(`/drafts/${id}`), [id])
  const facts = useAsync(() => (d ? api<Fact[]>(`/cases/${d.case_id}/facts`) : Promise.resolve([] as Fact[])), [d?.case_id])
  const [text, setText] = useState<Record<string, string>>({})
  const [ev, setEv] = useState<Evidence | null>(null)
  const [comment, setComment] = useState('')
  const [msg, setMsg] = useState<{ tone: 'ok' | 'bad'; text: string } | null>(null)
  const role = getRole()
  useEffect(() => { if (d) setText(Object.fromEntries(d.sections.map(s => [s.key, s.text]))) }, [d])
  if (loading && !d) return <Loading what="Opening draft" />
  if (error || !d) return <ErrorBox message={error || 'Not found'} retry={reload} />
  const factMap = Object.fromEntries((facts.data ?? []).map(f => [f.id, f]))
  const editable = (d.status === 'draft' || d.status === 'returned') && ['investigator', 'supervisor', 'admin'].includes(role)
  const dirty = d.sections.some(s => text[s.key] !== s.text)

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setMsg(null)
    try { await fn(); setMsg({ tone: 'ok', text: ok }); reload() } catch (e) { setMsg({ tone: 'bad', text: (e as Error).message }) }
  }
  const save = () => act(() => api(`/drafts/${id}`, { method: 'PUT', body: JSON.stringify({ sections: d.sections.map(s => ({ key: s.key, text: text[s.key] ?? s.text })) }) }), 'Draft saved as a new version.')
  const submit = () => act(() => api(`/drafts/${id}/submit`, { method: 'POST' }), 'Submitted for supervisor review.')
  const decide = (decision: string) => act(() => api(`/drafts/${id}/review`, { method: 'POST', body: JSON.stringify({ decision, comment }) }).then(() => setComment('')), decision === 'approve' ? 'Draft approved.' : 'Draft returned to the author.')
  const exportDoc = async () => {
    const body = await api<string>(`/drafts/${id}/export`)
    const url = URL.createObjectURL(new Blob([body], { type: 'text/markdown' }))
    Object.assign(document.createElement('a'), { href: url, download: `${d.title.replace(' ', '_')}_${d.id}_v${d.version}.md` }).click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <PageHeader title={d.title} sub={`Case ${d.sections[0]?.text.match(/Case No\.: (.*)/)?.[1] ?? ''} · version ${d.version} · author ${d.author}`}
        actions={<><Badge status={d.status} /><a className="link" href={`#/cases/${d.case_id}`}>Open case</a></>} />
      <Notice tone={d.status === 'approved' ? 'info' : 'warn'}><strong>{d.banner}</strong> {d.status !== 'approved' && 'Text marked “system” was assembled from extracted facts; text you edit is recorded as officer-entered.'}</Notice>
      {msg && <div className={msg.tone === 'ok' ? 'okbox' : 'errorbox'} role="status">{msg.text}</div>}
      <div className="split">
        <div className="main">
          {d.sections.map(s => (
            <section key={s.key} className="card section">
              <div className="cardhead">
                <h2>{s.title}{s.required && <span className="req" title="Required"> *</span>}</h2>
                <span className={'badge ' + (s.source === 'officer' ? 'info' : 'neutral')}>{s.source === 'officer' ? 'Officer-entered' : 'System-assembled'}</span>
              </div>
              <div className="pad">
                <textarea aria-label={s.title} value={text[s.key] ?? ''} readOnly={!editable} rows={Math.min(12, Math.max(3, (text[s.key] ?? '').split('\n').length + 1))}
                  className={(text[s.key] ?? '').includes('[Officer to enter') ? 'placeholder' : ''} onChange={e => setText({ ...text, [s.key]: e.target.value })} />
                {s.fact_ids.length > 0 && <div className="srcrow"><span className="muted small">Built from:</span>
                  {s.fact_ids.slice(0, 6).map(i => factMap[i] && <button key={i} className="chip" onClick={() => setEv({ docId: factMap[i].document_id, page: factMap[i].page, span: factMap[i].span, label: 'Source' })}>{factMap[i].type}: {factMap[i].original}</button>)}
                </div>}
              </div>
            </section>
          ))}
        </div>
        <div className="side">
          <section className="card">
            <div className="cardhead"><h2>Actions</h2></div>
            <div className="pad stack-v">
              {d.unfilled.length > 0 && <p className="small warnicon">Required before submitting: {d.unfilled.join(', ')}.</p>}
              {editable && <button className="btn" onClick={save} disabled={!dirty}><Save size={14} /> Save draft</button>}
              {editable && <button className="btn primary" onClick={submit} disabled={dirty || d.unfilled.length > 0} title={d.unfilled.length ? 'Complete the required sections first' : ''}><Send size={14} /> Request review</button>}
              {editable && dirty && <p className="muted small">Save your changes before requesting review.</p>}
              {d.status === 'in_review' && ['supervisor', 'admin'].includes(role) && (
                <>
                  <label>Reviewer comment<textarea rows={2} value={comment} onChange={e => setComment(e.target.value)} /></label>
                  <button className="btn primary" onClick={() => decide('approve')}><Check size={14} /> Approve</button>
                  <button className="btn" onClick={() => decide('return')}><Undo2 size={14} /> Return with comment</button>
                  <p className="muted small">You cannot approve a draft you authored.</p>
                </>
              )}
              <button className="btn" onClick={exportDoc}><Download size={14} /> Export (.md)</button>
            </div>
          </section>
          <section className="card">
            <div className="cardhead"><h2>History</h2></div>
            <ul className="list">
              {[...d.versions].reverse().map((v, i) => <li key={i} className="row"><span>v{v.version} · {v.note}</span><span className="muted small">{fmtDate(v.at)}</span></li>)}
              {d.comments.map((c, i) => <li key={'c' + i}><strong>{c.by}</strong> ({c.decision}): {c.text || 'no comment'}</li>)}
            </ul>
          </section>
          <EvidenceViewer ev={ev} />
        </div>
      </div>
    </>
  )
}
