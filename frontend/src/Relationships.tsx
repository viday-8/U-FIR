import cytoscape, { type Core, type NodeSingular } from 'cytoscape'
import { Crosshair, Maximize2, RotateCcw, Search as SearchIcon } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, type Candidate, type Cluster, type GNode, type Graph, type Overview, getRole } from './api'
import { EvidenceViewer, type Evidence } from './Evidence'
import { Badge, ErrorBox, Loading, Notice, PageHeader } from './ui'

type Sel = { kind: 'node'; id: string } | { kind: 'edge'; id: string } | { kind: 'cluster'; id: string } | null
const LAYOUTS = { force: 'Force (default)', rings: 'Rings by connections', tree: 'Tree from cases' } as const
const canReview = () => ['investigator', 'supervisor', 'admin'].includes(getRole())

const css = (name: string, fallback: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback

/** Graph colours come from the page's design tokens, so the graph follows light/dark and the navy-and-gold palette. */
function makeStyle(): cytoscape.StylesheetJson {
  const ink = css('--ink', '#16202f'), surface = css('--surface', '#fff'), brand = css('--brand', '#1b4f8a'), navy = css('--navy-2', '#12395f'), gold = css('--gold', '#b58b2a'), line = css('--line-strong', '#c4cdd8')
  return [
    { selector: 'node', style: { label: 'data(label)', 'font-size': 11, 'text-valign': 'bottom', 'text-margin-y': 4, 'text-wrap': 'wrap', 'text-max-width': '120px', color: ink, 'text-outline-color': surface, 'text-outline-width': 2, width: 'data(size)', height: 'data(size)', 'background-color': brand, 'border-width': 0 } },
    { selector: 'node[kind="case"]', style: { shape: 'round-rectangle', 'background-color': navy, 'font-weight': 600 } },
    { selector: 'node[kind="vehicle"]', style: { shape: 'diamond', 'background-color': gold } },
    { selector: 'node[ring="cluster"]', style: { 'border-width': 4, 'border-color': '#e07b1a' } },
    { selector: 'node[ring="confirmed"]', style: { 'border-width': 4, 'border-color': '#2f9e63' } },
    { selector: 'edge', style: { width: 1.2, 'line-color': line, 'curve-style': 'bezier', 'font-size': 10, color: ink, 'text-background-color': surface, 'text-background-opacity': 0.92, 'text-background-padding': '2px', 'text-wrap': 'wrap', 'text-max-width': '100px' } },
    { selector: 'edge[status="candidate"]', style: { 'line-style': 'dashed', 'line-color': '#e07b1a', width: 3, label: 'data(label)' } },
    { selector: 'edge[status="confirmed"]', style: { 'line-color': '#2f9e63', width: 5, label: 'data(label)' } },
    { selector: '.hidden', style: { display: 'none' } },
    { selector: '.dim', style: { opacity: 0.12 } },
    { selector: '.focus', style: { 'overlay-color': brand, 'overlay-opacity': 0.25, 'overlay-padding': 8 } },
    { selector: ':selected', style: { 'overlay-color': brand, 'overlay-opacity': 0.3, 'overlay-padding': 8 } },
  ]
}

function layoutOptions(name: keyof typeof LAYOUTS, nodeCount = 0): cytoscape.LayoutOptions {
  if (name === 'rings') return { name: 'concentric', concentric: n => n.degree(), levelWidth: () => 2, minNodeSpacing: 40, animate: false, padding: 30 } as cytoscape.LayoutOptions
  if (name === 'tree') return { name: 'breadthfirst', directed: false, spacingFactor: 1.15, animate: false, padding: 30, roots: '[kind="case"]' } as cytoscape.LayoutOptions
  return { name: 'cose', animate: false, nodeRepulsion: () => 90000, idealEdgeLength: () => 110, nodeDimensionsIncludeLabels: true, numIter: nodeCount > 150 ? 600 : 2500, gravity: 0.9, componentSpacing: 40, padding: 30, randomize: false } as cytoscape.LayoutOptions
}

export default function Relationships({ focus }: { focus: string }) {
  const [g, setG] = useState<Graph | null>(null)
  const [cands, setCands] = useState<Candidate[]>([])
  const [sel, setSel] = useState<Sel>(null)
  const [ev, setEv] = useState<Evidence | null>(null)
  const [err, setErr] = useState('')
  const [show, setShow] = useState({ person: true, vehicle: true, case: true, candidate: true, confirmed: true })
  const [onlyLinked, setOnlyLinked] = useState(true)  // asked of the server, so large archives are never sent in full
  const [layout, setLayout] = useState<keyof typeof LAYOUTS>('force')
  const [focusSet, setFocusSet] = useState<string[] | null>(null)
  const [find, setFind] = useState('')
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null)
  const box = useRef<HTMLDivElement>(null)
  const cy = useRef<Core | null>(null)

  const [serverFocus, setServerFocus] = useState<string | null>(null)  // set when the server returns only a neighbourhood
  const [loading, setLoading] = useState(false)
  const [remote, setRemote] = useState<{ id: number; case_no: string; matched: string[] }[]>([])

  const load = useCallback(() => {
    const qs = new URLSearchParams({ linked_only: String(onlyLinked && !serverFocus), limit: '400' })
    if (serverFocus) { qs.set('focus', serverFocus); qs.set('depth', '2') }
    setLoading(true)
    Promise.all([api<Graph>(`/relationships?${qs}`), api<Candidate[]>('/candidates')])
      .then(([gr, c]) => { setG(gr); setCands(c) }).catch(e => setErr(e.message)).finally(() => setLoading(false))
  }, [onlyLinked, serverFocus])
  useEffect(load, [load])

  const nodeById = useMemo(() => Object.fromEntries((g?.nodes ?? []).map(n => [n.id, n])), [g])
  const candById = useMemo(() => Object.fromEntries(cands.map(c => [c.id, c])), [cands])
  const clusterById = useMemo(() => Object.fromEntries((g?.clusters ?? []).map(c => [c.id, c])), [g])

  // ---- build the cytoscape instance once per data load ----
  useEffect(() => {
    if (!g || !box.current) return
    const ring = (n: GNode) => { const c = n.cluster_id ? clusterById[n.cluster_id] : undefined; return c ? (c.status === 'confirmed' ? 'confirmed' : 'cluster') : '' }
    const inst = cytoscape({
      container: box.current, style: makeStyle(), wheelSensitivity: 0.25, minZoom: 0.1, maxZoom: 3,
      ...(g.nodes.length > 150 ? { textureOnViewport: true, hideEdgesOnViewport: true, motionBlur: false } : {}),  // keep panning smooth on big graphs
      elements: [
        ...g.nodes.map(n => ({ data: { id: n.id, label: n.label, kind: n.kind, ring: ring(n), size: (n.kind === 'case' ? 30 : 22) + Math.min(n.degree, 8) * 2.5 } })),
        ...g.edges.map(e => ({ data: { id: e.id, source: e.source, target: e.target, status: e.status, label: e.status === 'direct' ? '' : (e.score ? `${e.status === 'confirmed' ? '✓ same person' : '? possible'} ${e.score}` : e.type) } })),
      ],
    })
    cy.current = inst
    const restyle = new MutationObserver(() => inst.style(makeStyle()))  // follow the light/dark switch without rebuilding
    restyle.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    inst.on('tap', 'node', ev => { setSel({ kind: 'node', id: ev.target.id() }); setEv(null) })
    inst.on('tap', 'edge', ev => { if (ev.target.data('status') !== 'direct') { setSel({ kind: 'edge', id: ev.target.id() }); setEv(null) } })
    inst.on('tap', ev => { if (ev.target === inst) setSel(null) })
    inst.on('dbltap', 'node', ev => { const n = ev.target as NodeSingular; setFocusSet(n.closedNeighborhood().closedNeighborhood().nodes().map(x => x.id())) })
    inst.on('mouseover', 'node', ev => { const n = nodeById[ev.target.id()]; const p = ev.renderedPosition; if (n) setTip({ x: p.x, y: p.y, text: describe(n) }) })
    inst.on('mouseout', 'node', () => setTip(null))
    inst.on('pan zoom', () => setTip(null))
    return () => { restyle.disconnect(); inst.destroy(); cy.current = null }
  }, [g])  // eslint-disable-line react-hooks/exhaustive-deps

  // ---- filters: class toggles only, no rebuild ----
  const relayout = useCallback((fit = true) => {
    const c = cy.current; if (!c) return
    const vis = c.elements().not('.hidden')
    if (vis.nodes().length === 0) return
    vis.layout(layoutOptions(layout, vis.nodes().length)).run()
    if (fit) c.fit(vis, 40)
  }, [layout])

  useEffect(() => {
    const c = cy.current; if (!c || !g) return
    c.batch(() => {
      c.elements().removeClass('hidden')
      c.nodes().forEach(n => { if (!show[n.data('kind') as 'person' | 'vehicle' | 'case']) n.addClass('hidden') })
      c.edges().forEach(e => { const s = e.data('status'); if ((s === 'candidate' && !show.candidate) || (s === 'confirmed' && !show.confirmed)) e.addClass('hidden') })
      if (focusSet) c.nodes().forEach(n => { if (!focusSet.includes(n.id())) n.addClass('hidden') })

      c.edges().forEach(e => { if (e.source().hasClass('hidden') || e.target().hasClass('hidden')) e.addClass('hidden') })
    })
    relayout()
  }, [g, show, focusSet, layout, relayout])

  // ---- selection: dim everything outside the neighbourhood ----
  useEffect(() => {
    const c = cy.current; if (!c) return
    c.batch(() => {
      c.elements().removeClass('dim').unselect()
      if (!sel) return
      let keep = c.collection()
      if (sel.kind === 'node') { const n = c.getElementById(sel.id); keep = n.closedNeighborhood(); n.select() }
      if (sel.kind === 'edge') { const e = c.getElementById(sel.id); keep = e.connectedNodes().union(e.connectedNodes().neighborhood('node[kind="case"]')).union(e); e.select() }
      if (sel.kind === 'cluster') { const cl = clusterById[sel.id]; if (cl) keep = c.nodes().filter(n => cl.node_ids.includes(n.id())).closedNeighborhood() }
      c.elements().not(keep).addClass('dim')
      const shown = keep.not('.hidden')
      if (shown.nonempty()) c.animate({ fit: { eles: shown, padding: 80 } }, { duration: 300 })  // zoom to what was selected
    })
  }, [sel, clusterById])

  // ---- deep link: ?focus=case:12 | person:3 | vehicle:ap31tx4521 | cluster:cl:5 | link:7 ----
  const handled = useRef('')
  useEffect(() => {
    if (!focus || handled.current === focus) return
    handled.current = focus
    if (focus.startsWith('link:')) {
      api<Candidate[]>('/candidates').then(cs => { const c = cs.find(x => x.id === Number(focus.slice(5))); if (c) { setServerFocus(`person:${c.a.entity_id}`); setPendingSel({ kind: 'edge', id: `cand:${c.id}` }) } }).catch(() => undefined)
    } else if (focus.startsWith('cluster:')) { setPendingSel({ kind: 'cluster', id: focus.slice(8) }) }
    else { setServerFocus(focus); setPendingSel({ kind: 'node', id: focus }) }
  }, [focus])
  const [pendingSel, setPendingSel] = useState<Sel>(null)
  useEffect(() => {  // apply the requested selection once the (possibly reduced) graph has loaded
    if (!g || !pendingSel) return
    const ok = pendingSel.kind === 'node' ? nodeById[pendingSel.id] : pendingSel.kind === 'cluster' ? clusterById[pendingSel.id] : g.edges.some(e => e.id === pendingSel.id)
    if (ok) { setSel(pendingSel); setPendingSel(null) }
  }, [g, pendingSel, nodeById, clusterById])

  // search the whole archive (the graph on screen may be reduced): cases whose metadata matches the typed words
  useEffect(() => {
    if (find.trim().length < 2) { setRemote([]); return }
    const t = setTimeout(() => api<Overview>(`/cases/overview?q=${encodeURIComponent(find)}`).then(o => setRemote(o.items.slice(0, 5).map(i => ({ id: i.id, case_no: i.case_no, matched: i.matched })))).catch(() => setRemote([])), 250)
    return () => clearTimeout(t)
  }, [find])

  const centreOn = (id: string) => { setFocusSet(null); setSel({ kind: 'node', id }); setTimeout(() => { const n = cy.current?.getElementById(id); if (n?.nonempty()) cy.current?.animate({ center: { eles: n }, zoom: 1.4 }, { duration: 250 }) }, 60) }
  const matches = find.trim() ? (g?.nodes ?? []).filter(n => n.label.toLowerCase().includes(find.toLowerCase())).slice(0, 7) : []
  const reset = () => { setFocusSet(null); setServerFocus(null); setSel(null); setFind(''); setOnlyLinked(true); setShow({ person: true, vehicle: true, case: true, candidate: true, confirmed: true }) }

  if (err) return <ErrorBox message={err} retry={load} />
  if (!g) return <Loading what="Loading the investigation network" />
  const st = g.stats
  const selEdge = sel?.kind === 'edge' ? g.edges.find(e => e.id === sel.id) : undefined
  const selCand = selEdge?.candidate_id ? candById[selEdge.candidate_id] : undefined
  const toggle = (k: keyof typeof show, label: string) => <label className="check"><input type="checkbox" checked={show[k]} onChange={e => setShow({ ...show, [k]: e.target.checked })} /> {label}</label>

  return (
    <>
      <PageHeader title="Investigation Network" sub="Repeat offenders, shared vehicles and linked cases across the records you can access. Click anything to see its evidence."
        actions={<span className="muted small">{st.cases} cases · {st.people} people · {st.vehicles} vehicles · {st.links} possible links · {st.clusters} clusters</span>} />
      <Notice>{g.notice} Orange ring = person records that may be the same individual (unreviewed). Green ring = confirmed by a reviewer.</Notice>

      <div className="netbar card pad">
        <div className="findbox"><label className="searchbox"><SearchIcon size={15} /><span className="sr">Find a person, vehicle or case</span>
          <input placeholder="Find a person, vehicle or case…" value={find} onChange={e => setFind(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && matches[0]) { centreOn(matches[0].id); setFind('') } }} /></label>
          {(matches.length > 0 || remote.length > 0) && <ul className="suggest" role="listbox">
            {matches.map(n => <li key={n.id}><button type="button" onClick={() => { centreOn(n.id); setFind('') }}><span className="badge neutral">{n.kind}</span> {n.label}</button></li>)}
            {remote.filter(r => !matches.some(m => m.id === `case:${r.id}`)).map(r => <li key={'r' + r.id}><button type="button" onClick={() => { setServerFocus(`case:${r.id}`); setPendingSel({ kind: 'node', id: `case:${r.id}` }); setFind('') }}><span className="badge info">open network</span> {r.case_no} <span className="muted small">{r.matched[0]}</span></button></li>)}</ul>}</div>
        <div className="toolbar">
          <span className="small strong">Show</span>{toggle('person', 'People')}{toggle('vehicle', 'Vehicles')}{toggle('case', 'Cases')}
          <span className="small strong">Links</span>{toggle('candidate', 'Possible')}{toggle('confirmed', 'Confirmed')}
          <label className="check"><input type="checkbox" checked={onlyLinked} disabled={!!serverFocus} onChange={e => setOnlyLinked(e.target.checked)} /> Only linked networks</label>
          <label className="inline">Layout<select value={layout} onChange={e => setLayout(e.target.value as keyof typeof LAYOUTS)}>{Object.entries(LAYOUTS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
          <button className="btn sm" onClick={() => relayout()}><Maximize2 size={12} /> Fit</button>
          <button className="btn sm" onClick={reset}><RotateCcw size={12} /> Reset</button>
        </div>
        {serverFocus && <p className="focusbar"><Crosshair size={14} /> Showing the neighbourhood of <strong>{nodeById[serverFocus]?.label ?? serverFocus}</strong> from the full archive. <button className="link" onClick={() => setServerFocus(null)}>Show linked networks instead</button></p>}
        {g.scope.truncated && <p className="focusbar warnbar">Showing {g.scope.shown_nodes.toLocaleString()} of {g.scope.total_nodes.toLocaleString()} records (largest, most-linked networks first). Search above or open a case's network to see a specific one.</p>}
        {loading && <p className="muted small">Updating…</p>}
        {focusSet && <p className="focusbar"><Crosshair size={14} /> Showing the neighbourhood of the selected item. <button className="link" onClick={() => setFocusSet(null)}>Show everything again</button></p>}
      </div>

      <section aria-label="Repeat-offender clusters" className="clusterstrip">
        <h2 className="sr">Possible repeat offenders</h2>
        {g.clusters.length === 0 ? <p className="muted small">No linked person records yet. Upload more case files to find repeat names.</p> : g.clusters.map(c => (
          <button key={c.id} className={'clustercard' + (sel?.kind === 'cluster' && sel.id === c.id ? ' on' : '')} onClick={() => { setFocusSet(null); setSel({ kind: 'cluster', id: c.id }) }}>
            <strong>{c.label}</strong>
            <span className="small">{c.node_ids.length} records · {c.case_ids.length} cases{c.names.length > 1 && ` · also ${c.names.filter(n => n !== c.label).join(', ')}`}</span>
            <span className="small">score {c.min_score}–{c.max_score}{c.shared_vehicles.length > 0 && ` · ${c.shared_vehicles.join(', ')}`}</span>
            <Badge status={c.status === 'confirmed' ? 'confirmed' : 'unreviewed'} />
          </button>))}
      </section>

      <div className="canvaswrap card">
        <div ref={box} className="graph tall" role="img" aria-label="Interactive network of cases, people and vehicles. The same information is available in the tables below." />
        {tip && <div className="graphtip" style={{ left: tip.x + 14, top: tip.y + 14 }}>{tip.text}</div>}
        {sel && (
          <aside className="drawer" aria-label="Details">
            <button className="drawerclose" onClick={() => setSel(null)} aria-label="Close details">×</button>
            {sel.kind === 'node' && nodeById[sel.id] && <NodeDetail n={nodeById[sel.id]} g={g} nodeById={nodeById} clusterById={clusterById} onPick={centreOn} onCluster={id => setSel({ kind: 'cluster', id })} />}
            {sel.kind === 'cluster' && clusterById[sel.id] && <ClusterDetail c={clusterById[sel.id]} cands={cands} onEdge={cid => { const e = g.edges.find(x => x.candidate_id === cid); if (e) setSel({ kind: 'edge', id: e.id }) }} />}
            {selCand && <LinkDetail c={selCand} onEvidence={setEv} onDecided={load} />}
          </aside>
        )}
        <p className="muted small pad">Scroll to zoom · drag to pan · click to inspect · double-click to focus on a neighbourhood. {!sel && 'Select something to see what the records say about it.'}</p>
      </div>
      {ev && <EvidenceViewer ev={ev} />}

      <section className="card tablewrap" aria-label="Candidate matches table">
        <div className="cardhead"><h2>All possible matches (table view)</h2></div>
        {cands.length === 0 ? <p className="muted pad">No candidate matches in the records you can access.</p> : (
          <table><thead><tr><th>Record A</th><th>Record B</th><th>Strength</th><th>Status</th><th></th></tr></thead>
            <tbody>{cands.map(c => <tr key={c.id}><td>{c.a.name}<br /><span className="muted small">{c.a.case_no}</span></td><td>{c.b.name}<br /><span className="muted small">{c.b.case_no}</span></td>
              <td>{c.strength} ({c.score})</td><td><Badge status={c.status} /></td>
              <td><button className="link" onClick={() => { const e = g.edges.find(x => x.candidate_id === c.id); if (e) setSel({ kind: 'edge', id: e.id }) }}>Why linked?</button></td></tr>)}</tbody></table>
        )}
        <details className="pad"><summary>Every relationship as text ({g.edges.length})</summary>
          <table><thead><tr><th>From</th><th>Relationship</th><th>To</th><th>Basis</th></tr></thead>
            <tbody>{g.edges.map(e => <tr key={e.id}><td>{nodeById[e.source]?.label}</td><td>{e.type}</td><td>{nodeById[e.target]?.label}</td><td>{e.status === 'direct' ? 'Recorded' : e.status === 'confirmed' ? 'Confirmed' : 'Candidate'} · {e.evidence.length} source(s)</td></tr>)}</tbody></table>
        </details>
      </section>
    </>
  )
}

function describe(n: GNode): string {
  if (n.kind === 'person') return [n.label, n.age && `age ${n.age}`, n.father_or_spouse && `${n.relation ?? 'of'} ${n.father_or_spouse}`, n.resident && `R/o ${n.resident}`, n.case_no].filter(Boolean).join(' · ')
  if (n.kind === 'case') return [n.label, n.station, n.registered_on, ...(n.offence ?? [])].filter(Boolean).join(' · ')
  return `${n.label} · recorded in ${n.cases} case(s)`
}

function NodeDetail({ n, g, nodeById, clusterById, onPick, onCluster }: { n: GNode; g: Graph; nodeById: Record<string, GNode>; clusterById: Record<string, Cluster>; onPick: (id: string) => void; onCluster: (id: string) => void }) {
  const neighbours = g.edges.filter(e => e.status === 'direct' && (e.source === n.id || e.target === n.id)).map(e => nodeById[e.source === n.id ? e.target : e.source]).filter(Boolean)
  const cl = n.cluster_id ? clusterById[n.cluster_id] : undefined
  const pick = (x: GNode) => <button key={x.id} className="chip" onClick={() => onPick(x.id)}>{x.label}</button>
  return (
    <section className="card">
      <div className="cardhead"><h2>{n.kind === 'person' ? 'Person record' : n.kind === 'case' ? 'Case' : 'Vehicle'}</h2><span className="badge neutral">{n.degree} connection(s)</span></div>
      <div className="pad">
        <p className="strong">{n.label}</p>
        {n.kind === 'person' && <ul className="facts">
          {n.alias && <li>Also known as <strong>{n.alias}</strong></li>}{n.age && <li>Age <strong>{n.age}</strong></li>}
          {n.father_or_spouse && <li>{n.relation === 'W/o' ? 'Wife of' : n.relation === 'D/o' ? 'Daughter of' : 'Son of'} <strong>{n.father_or_spouse}</strong></li>}{n.resident && <li>Resident of <strong>{n.resident}</strong></li>}
          <li>Named in <a className="link" href={`#/cases/${n.case_id}`}>{n.case_no}</a></li></ul>}
        {n.kind === 'case' && <>
          <ul className="facts"><li>{n.station}, {n.district}</li><li>Registered {n.registered_on} · {n.documents} document(s)</li></ul>
          <div>{n.offence?.map(o => <span key={o} className="badge info">{o}</span>)}</div>
          <a className="btn sm" href={`#/cases/${n.case_id}`}>Open case</a></>}
        {n.kind === 'vehicle' && <p className="muted small">Recorded in {n.cases} case(s). Appearing in several cases links them, but a vehicle can be sold or lent, so it is a lead, not proof about any person.</p>}
        {cl && <div className="flag warn"><h3>Possible repeat offender</h3>
          <p className="small">{cl.names.join(' / ')} appear in {cl.case_nos.join(', ')}. <button className="link" onClick={() => onCluster(cl.id)}>See why these records are linked</button></p></div>}
        {neighbours.length > 0 && <><h3>{n.kind === 'case' ? 'Recorded in this case' : n.kind === 'vehicle' ? 'Seen in cases' : 'Case'}</h3><div>{neighbours.map(pick)}</div></>}
      </div>
    </section>
  )
}

function ClusterDetail({ c, cands, onEdge }: { c: Cluster; cands: Candidate[]; onEdge: (id: number) => void }) {
  const links = cands.filter(x => c.candidate_ids.includes(x.id))
  return (
    <section className="card">
      <div className="cardhead"><h2>Possible repeat offender</h2><Badge status={c.status === 'confirmed' ? 'confirmed' : 'unreviewed'} /></div>
      <div className="pad">
        <p className="strong">{c.names.join(' / ')}</p>
        <p className="small">{c.node_ids.length} person records across {c.case_ids.length} cases: {c.case_nos.join(', ')}.</p>
        {c.shared_vehicles.length > 0 && <p className="small">Shared vehicle: <strong>{c.shared_vehicles.join(', ')}</strong></p>}
        <Notice>These are separate records that look like the same person. Nothing is merged until a reviewer decides.</Notice>
        <h3>Links to review</h3>
        <ul className="list">{links.map(l => (
          <li key={l.id}><button className="link" onClick={() => onEdge(l.id)}>{l.a.name} ({l.a.case_no}) ↔ {l.b.name} ({l.b.case_no})</button>
            <div className="small muted">{l.strength} · score {l.score} · {l.status}</div></li>))}</ul>
      </div>
    </section>
  )
}

function LinkDetail({ c, onEvidence, onDecided }: { c: Candidate; onEvidence: (e: Evidence) => void; onDecided: () => void }) {
  const [reason, setReason] = useState('')
  const [msg, setMsg] = useState('')
  useEffect(() => { setReason(''); setMsg('') }, [c.id])
  const decide = async (decision: string) => {
    try { await api(`/candidates/${c.id}/review`, { method: 'POST', body: JSON.stringify({ decision, reason }) }); onDecided() } catch (e) { setMsg((e as Error).message) }
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
        <div>{c.evidence.filter(e => e.type !== 'date').map(e => <button key={e.fact_id} className="chip" onClick={() => onEvidence({ docId: e.document_id, page: e.page, span: e.span, label: e.doc_type })}>{e.doc_type} p{e.page}: {e.original}</button>)}</div>
        {c.decided_by && <p className="muted small">Decision by {c.decided_by}: {c.reason ?? 'no reason recorded'}</p>}
        {canReview() ? (
          <><h3>Review</h3><label>Reason<textarea value={reason} onChange={e => setReason(e.target.value)} rows={2} /></label>
            <div className="actions"><button className="btn primary" onClick={() => decide('confirm')}>Confirm same person</button><button className="btn" onClick={() => decide('reject')}>Not the same</button><button className="btn" onClick={() => decide('defer')}>Defer</button></div>
            {msg && <ErrorBox message={msg} />}</>
        ) : <p className="muted small">Your role can view but not decide matches.</p>}
      </div>
    </section>
  )
}
