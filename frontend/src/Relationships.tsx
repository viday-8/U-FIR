import cytoscape from 'cytoscape'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type Candidate, type GEdge, type Graph, getRole } from './api'
import { EvidenceViewer, type Evidence } from './Evidence'
import { Badge, Empty, ErrorBox, Loading, Notice, PageHeader } from './ui'

function GraphView({ g, onEdge }: { g: Graph; onEdge: (e: GEdge) => void }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...g.nodes.map(n => ({ data: { id: n.id, label: n.label, kind: n.kind } })),
        ...g.edges.map(e => ({ data: { id: e.id, source: e.source, target: e.target, status: e.status, label: e.status === 'direct' ? '' : e.type } })),
      ],
      style: [
        { selector: 'node', style: { label: 'data(label)', 'font-size': 11, 'text-valign': 'bottom', 'text-margin-y': 4, 'text-wrap': 'wrap', 'text-max-width': '110px', color: '#334155', 'background-color': '#0b7285', width: 26, height: 26 } },
        { selector: 'node[kind="case"]', style: { shape: 'round-rectangle', 'background-color': '#0f2a4a', width: 30 } },
        { selector: 'node[kind="vehicle"]', style: { shape: 'diamond', 'background-color': '#b45309' } },
        { selector: 'edge', style: { width: 1.5, 'line-color': '#94a3b8', label: 'data(label)', 'font-size': 9, 'text-rotation': 'none', 'text-wrap': 'wrap', 'text-max-width': '90px', 'text-background-color': '#fff', 'text-background-opacity': 0.9, color: '#334155', 'curve-style': 'bezier' } },
        { selector: 'edge[status="candidate"]', style: { 'line-style': 'dashed', 'line-color': '#c2410c', width: 2.5 } },
        { selector: 'edge[status="confirmed"]', style: { 'line-color': '#15803d', width: 4 } },
      ],
      layout: { name: 'cose', animate: false, nodeRepulsion: () => 140000, idealEdgeLength: () => 120, nodeDimensionsIncludeLabels: true, numIter: 3000, gravity: 1.2, componentSpacing: 80, padding: 24, randomize: false },
    })
    cy.on('tap', 'edge', ev => { const e = g.edges.find(x => x.id === ev.target.id()); if (e) onEdge(e) })
    return () => cy.destroy()
  }, [g])  // eslint-disable-line react-hooks/exhaustive-deps
  return <div ref={ref} className="graph" role="img" aria-label="Relationship graph. An equivalent table follows." />
}

function Detail({ c, onEvidence, onDecided }: { c: Candidate; onEvidence: (e: Evidence) => void; onDecided: () => void }) {
  const [reason, setReason] = useState('')
  const [msg, setMsg] = useState('')
  useEffect(() => { setReason(''); setMsg('') }, [c.id])
  const canReview = ['investigator', 'supervisor', 'admin'].includes(getRole())
  const decide = async (decision: string) => {
    try { await api(`/candidates/${c.id}/review`, { method: 'POST', body: JSON.stringify({ decision, reason }) }); onDecided() }
    catch (e) { setMsg((e as Error).message) }
  }
  return (
    <section className="card" aria-label="Why linked?">
      <div className="cardhead"><h2>Why linked?</h2><Badge status={c.status} /></div>
      <div className="pad">
        <p><strong>{c.a.name}</strong> <span className="muted">({c.a.case_no})</span> ↔ <strong>{c.b.name}</strong> <span className="muted">({c.b.case_no})</span></p>
        <Notice>{c.strength === 'likely' ? 'Likely' : 'Possible'} match, score {c.score}/100. A candidate, not a finding of identity or guilt.</Notice>
        <h3>Signals</h3>
        <ul className="signals">{c.signals.map((s, i) => <li key={i} className={s.supports ? 'for' : 'against'}><strong>{s.supports ? '✓ For' : '✕ Against'}</strong> {s.text}</li>)}</ul>
        {c.missing.length > 0 && <><h3>Not available</h3><ul className="signals">{c.missing.map(m => <li key={m}>ℹ {m}</li>)}</ul></>}
        <h3>Source records</h3>
        <div>{c.evidence.filter(e => e.type !== 'date').map(e => (
          <button key={e.fact_id} className="chip" onClick={() => onEvidence({ docId: e.document_id, page: e.page, span: e.span, label: e.doc_type })}>{e.doc_type} p{e.page}: {e.original}</button>
        ))}</div>
        {c.decided_by && <p className="muted small">Decision by {c.decided_by}: {c.reason ?? 'no reason recorded'}</p>}
        {canReview ? (
          <>
            <h3>Review</h3>
            <label>Reason<textarea value={reason} onChange={e => setReason(e.target.value)} rows={2} /></label>
            <div className="actions">
              <button className="btn primary" onClick={() => decide('confirm')}>Confirm same person</button>
              <button className="btn" onClick={() => decide('reject')}>Not the same</button>
              <button className="btn" onClick={() => decide('defer')}>Defer</button>
            </div>
            {msg && <ErrorBox message={msg} />}
          </>
        ) : <p className="muted small">Your role can view but not decide matches.</p>}
      </div>
    </section>
  )
}

export default function Relationships() {
  const [g, setG] = useState<Graph | null>(null)
  const [cands, setCands] = useState<Candidate[]>([])
  const [sel, setSel] = useState<Candidate | null>(null)
  const [ev, setEv] = useState<Evidence | null>(null)
  const [err, setErr] = useState('')
  const load = useCallback(() => {
    Promise.all([api<Graph>('/relationships'), api<Candidate[]>('/candidates')])
      .then(([gr, c]) => { setG(gr); setCands(c); setSel(s => c.find(x => x.id === s?.id) ?? null) })
      .catch(e => setErr(e.message))
  }, [])
  useEffect(load, [load])
  if (err) return <ErrorBox message={err} retry={load} />
  if (!g) return <Loading what="Loading relationships" />
  const name = (id: string) => g.nodes.find(n => n.id === id)?.label ?? id
  return (
    <>
      <PageHeader title="Relationship Explorer" sub="Possible repeat offenders and shared vehicles across the cases you can access. Every link shows its evidence." />
      <section className="card" aria-label="Relationship graph">
        <div className="pad">
          <Notice>{g.notice}</Notice>
          <p className="muted small legend">● person · ▬ case · ◆ vehicle · thin line = recorded in the case · dashed = possible match, unreviewed · thick = confirmed same person. Select a dashed or thick line. Scroll to zoom, drag to pan.</p>
          <GraphView g={g} onEdge={e => setSel(cands.find(c => c.id === e.candidate_id) ?? null)} />
        </div>
      </section>
      <div className="split">
        <div className="main">
          <section className="card tablewrap" aria-label="Candidate matches">
            <div className="cardhead"><h2>Candidate matches</h2></div>
            {cands.length === 0 ? <Empty>No candidate matches in the records you can access.</Empty> : (
              <table>
                <thead><tr><th>Record A</th><th>Record B</th><th>Strength</th><th>Status</th><th></th></tr></thead>
                <tbody>{cands.map(c => (
                  <tr key={c.id}>
                    <td>{c.a.name}<br /><span className="muted small">{c.a.case_no}</span></td>
                    <td>{c.b.name}<br /><span className="muted small">{c.b.case_no}</span></td>
                    <td>{c.strength} ({c.score})</td><td><Badge status={c.status} /></td>
                    <td><button className="link" onClick={() => setSel(c)}>Why linked?</button></td>
                  </tr>))}</tbody>
              </table>
            )}
            <details className="pad"><summary>All relationships as a table ({g.edges.length})</summary>
              <table>
                <thead><tr><th>From</th><th>Relationship</th><th>To</th><th>Basis</th></tr></thead>
                <tbody>{g.edges.map(e => <tr key={e.id}><td>{name(e.source)}</td><td>{e.type}</td><td>{name(e.target)}</td><td>{e.status === 'direct' ? 'Recorded' : e.status === 'confirmed' ? 'Confirmed' : 'Candidate'} · {e.evidence.length} source(s)</td></tr>)}</tbody>
              </table>
            </details>
          </section>
        </div>
        <div className="side">
          {sel ? <Detail c={sel} onEvidence={setEv} onDecided={load} /> : <section className="card"><p className="muted pad">Select a candidate to see why the records were linked and to review it.</p></section>}
          <EvidenceViewer ev={ev} />
        </div>
      </div>
    </>
  )
}
