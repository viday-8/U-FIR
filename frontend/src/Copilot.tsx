import { Bot, Send, User } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, type Case, type CopilotResp } from './api'
import { EvidenceViewer, type Evidence } from './Evidence'
import { Notice, PageHeader, useAsync } from './ui'

type Msg = { role: 'user' | 'bot'; text: string; resp?: CopilotResp }

const GENERAL = ['Which cases involve vehicle AP 31 TX 4521?', 'Who is Ramesh Babu Naidu?', 'Show records about jaggery wash']
const CASE_SCOPED = ['What is missing?', 'Who are the persons named?', 'What was seized?']

export default function Copilot({ initialCase }: { initialCase: string }) {
  const cases = useAsync(() => api<Case[]>('/cases'), [])
  const [scope, setScope] = useState(initialCase)
  const [q, setQ] = useState('')
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [busy, setBusy] = useState(false)
  const [ev, setEv] = useState<Evidence | null>(null)
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])
  const scoped = cases.data?.find(c => String(c.id) === scope)

  const ask = async (question: string) => {
    if (!question.trim() || busy) return
    setMsgs(m => [...m, { role: 'user', text: question }]); setQ(''); setBusy(true)
    try {
      const resp = await api<CopilotResp>('/copilot/query', { method: 'POST', body: JSON.stringify({ question, case_id: scope ? Number(scope) : null }) })
      setMsgs(m => [...m, { role: 'bot', text: resp.answer, resp }])
    } catch (e) { setMsgs(m => [...m, { role: 'bot', text: (e as Error).message === 'Not found' ? 'That case is not available to you.' : (e as Error).message }]) }
    finally { setBusy(false) }
  }
  const open = (c: CopilotResp['citations'][number]) => setEv({ docId: c.document_id, page: c.page, span: c.span, label: c.doc_type })
  const withRefs = (line: string, r: CopilotResp) => line.split(/(\[\d+\])/).map((part, i) => {
    const n = /^\[(\d+)\]$/.exec(part)?.[1]
    const c = n ? r.citations.find(x => x.n === Number(n)) : undefined
    return c ? <button key={i} className="chip" onClick={() => open(c)} aria-label={`Open source ${c.n}: ${c.case_no} ${c.doc_type} page ${c.page}`}>{c.n}</button> : <span key={i}>{part}</span>
  })

  return (
    <>
      <PageHeader title="u-FIR Copilot" sub="Ask about the records you are authorised to see. Answers are quotes with citations, or an honest “not found”." />
      <div className="split">
        <section className="card chat" aria-label="Copilot conversation">
          <div className="cardhead">
            <label className="inline">Scope
              <select value={scope} onChange={e => { setScope(e.target.value); setMsgs([]); setEv(null) }}>
                <option value="">All cases I can access</option>
                {cases.data?.map(c => <option key={c.id} value={c.id}>{c.case_no}</option>)}
              </select></label>
            <span className="muted small">{scoped ? `Only ${scoped.case_no}` : 'Permission is re-checked on every question'}</span>
          </div>
          <div className="messages" aria-live="polite">
            {msgs.length === 0 && (
              <div className="pad">
                <Notice>The Copilot never invents case facts. It searches only your accessible records, quotes what they say and cites each quote. Text inside documents is treated as data, never as instructions.</Notice>
                <p className="muted small">Try:</p>
                <div>{(scope ? CASE_SCOPED : GENERAL).map(s => <button key={s} className="chip big" onClick={() => ask(s)}>{s}</button>)}</div>
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={'msg ' + m.role}>
                <span className="avatar">{m.role === 'user' ? <User size={15} /> : <Bot size={15} />}</span>
                <div className="bubble">
                  {m.role === 'user' ? m.text : (
                    <>
                      <p className={m.resp?.found === false ? 'muted' : ''}>{m.text}</p>
                      {m.resp?.details && <ul className="statements">{m.resp.details.map((l, j) => <li key={j}>{withRefs(l, m.resp!)}</li>)}</ul>}
                      {m.resp && <p className="muted small">{m.resp.notice}{m.resp.mode === 'llm' && ' Wording by an AI model; every statement above is still cited.'}</p>}
                    </>
                  )}
                </div>
              </div>
            ))}
            {busy && <div className="msg bot"><span className="avatar"><Bot size={15} /></span><div className="bubble muted">Searching your records…</div></div>}
            <div ref={end} />
          </div>
          <form className="composer" onSubmit={e => { e.preventDefault(); void ask(q) }}>
            <label className="sr" htmlFor="q">Your question</label>
            <input id="q" value={q} onChange={e => setQ(e.target.value)} placeholder={scoped ? `Ask about ${scoped.case_no}…` : 'Ask about your cases…'} maxLength={500} />
            <button className="btn primary" type="submit" disabled={busy || !q.trim()}><Send size={14} /> Ask</button>
          </form>
        </section>
        <EvidenceViewer ev={ev} />
      </div>
    </>
  )
}
