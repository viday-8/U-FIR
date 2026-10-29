import { useState } from 'react'
import { api, type Hotspots as H } from './api'
import { Empty, ErrorBox, Loading, Notice, PageHeader, useAsync } from './ui'

export default function Hotspots() {
  const [kind, setKind] = useState<'location' | 'residence'>('location')
  const { data: d, error, loading, reload } = useAsync(() => api<H>(`/analytics/hotspots?kind=${kind}`), [kind])
  if (error) return <ErrorBox message={error} retry={reload} />
  const max = Math.max(1, ...(d?.places.map(p => p.cases) ?? [1]))
  return (
    <>
      <PageHeader title="Hotspot Explorer" sub="Where the recorded cases cluster, by place named in the FIR and by station." />
      {d && <Notice tone="warn"><strong>{d.caveat}</strong> {d.method}</Notice>}
      <div className="toolbar">
        <span>Show:</span>
        <button className={'pill' + (kind === 'location' ? ' on' : '')} onClick={() => setKind('location')}>Places named as location</button>
        <button className={'pill' + (kind === 'residence' ? ' on' : '')} onClick={() => setKind('residence')}>Accused residence</button>
        {d && <span className="muted small">Coverage: {d.coverage.cases_with_place} of {d.coverage.cases_total} cases name a place of this kind</span>}
      </div>
      {loading || !d ? <Loading what="Loading hotspots" /> : (
        <div className="two">
          <section className="card tablewrap">
            <div className="cardhead"><h2>Ranked places</h2></div>
            {d.places.length === 0 ? <Empty>No places recorded for your cases.</Empty> : (
              <table><thead><tr><th>Place</th><th>Cases</th><th></th><th>Case numbers</th></tr></thead>
                <tbody>{d.places.map(p => (
                  <tr key={p.name}><td className="strong">{p.name}</td><td>{p.cases}</td>
                    <td style={{ width: '30%' }}><span className="hbar" style={{ width: `${(p.cases / max) * 100}%` }} aria-hidden /></td>
                    <td>{p.case_ids.map((id, i) => <a key={id} className="link small" href={`#/cases/${id}`}>{p.case_nos[i]}{i < p.case_ids.length - 1 ? ', ' : ''}</a>)}</td></tr>
                ))}</tbody></table>
            )}
          </section>
          <div>
            <section className="card tablewrap">
              <div className="cardhead"><h2>By station</h2></div>
              <table><thead><tr><th>Station</th><th>Cases</th></tr></thead>
                <tbody>{d.stations.map(s => <tr key={s.name}><td>{s.name}</td><td>{s.cases}</td></tr>)}</tbody></table>
            </section>
            <section className="card tablewrap">
              <div className="cardhead"><h2>By month registered</h2></div>
              <table><thead><tr><th>Month</th><th>Cases</th></tr></thead>
                <tbody>{Object.entries(d.months).map(([m, n]) => <tr key={m}><td>{m}</td><td>{n}</td></tr>)}</tbody></table>
            </section>
          </div>
        </div>
      )}
    </>
  )
}
