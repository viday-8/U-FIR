import { useState } from 'react'
import { api, type Deadlines as D } from './api'
import { useT } from './i18n'
import { Badge, Empty, ErrorBox, Loading, PageHeader, useAsync } from './ui'

export default function Deadlines() {
  const t = useT()
  const [all, setAll] = useState(false)
  const { data, error, loading, reload } = useAsync(() => api<D>(`/deadlines?include_done=${all}`), [all])
  if (error) return <ErrorBox message={error} retry={reload} />
  return (
    <>
      <PageHeader title="Deadlines" sub="Chargesheet limits, remand expiry, hearings and lab reports across your cases, most urgent first."
        actions={data && <span className="muted small">{data.counts.overdue} overdue · {data.counts.soon} due within 14 days</span>} />
      <div className="toolbar"><label className="check"><input type="checkbox" checked={all} onChange={e => setAll(e.target.checked)} /> {t('Include completed')}</label></div>
      {loading && !data ? <Loading what="Loading deadlines" /> : (
        <div className="card tablewrap">
          {!data?.items.length ? <Empty>Nothing is pending. Dates are added from a case's “Case management” tab.</Empty> : (
            <table><thead><tr><th>{t('Due')}</th><th>{t('What')}</th><th>{t('Case')}</th><th>{t('Status')}</th></tr></thead>
              <tbody>{data.items.map(m => (
                <tr key={m.id}><td className="strong">{m.due_on}</td><td>{m.title}</td><td><a className="link" href={`#/cases/${m.case_id}`}>{m.case_no}</a></td>
                  <td><Badge status={m.state} label={m.state === 'overdue' ? `Overdue by ${-m.days} day(s)` : m.state === 'soon' ? `In ${m.days} day(s)` : undefined} /></td></tr>))}</tbody></table>
          )}
        </div>
      )}
    </>
  )
}
