import { api, type ReviewItem } from './api'
import DocActions from './DocActions'
import { Badge, Empty, ErrorBox, Loading, PageHeader, useAsync } from './ui'

const TYPES: [string, string][] = [['', 'All'], ['identity', 'Identity matches'], ['legal', 'Legal suggestions'], ['draft', 'Drafts'], ['extraction', 'Extraction']]

export default function ReviewQueue({ type }: { type: string }) {
  const { data, error, loading, reload } = useAsync(() => api<ReviewItem[]>('/reviews' + (type ? `?type=${type}` : '')), [type])
  if (loading) return <Loading what="Loading review queue" />
  if (error) return <ErrorBox message={error} retry={reload} />
  return (
    <>
      <PageHeader title="Review Queue" sub="Everything that needs a human decision, in one place: uncertain extractions, possible identity matches, legal suggestions and drafts." />
      <div className="toolbar">{TYPES.map(([k, l]) => <a key={k} className={'pill' + (k === type ? ' on' : '')} href={k ? `#/reviews?type=${k}` : '#/reviews'}>{l}</a>)}
        <span className="muted small">{data?.length} item(s)</span></div>
      <div className="card tablewrap">
        {!data?.length ? <Empty>Nothing needs review.</Empty> : (
          <table>
            <thead><tr><th>Item</th><th>Type</th><th>Why it needs review</th><th>Status</th><th>Who can act</th><th></th></tr></thead>
            <tbody>{data.map((r, i) => (
              <tr key={i}><td className="strong">{r.label}</td><td>{r.type}</td><td>{r.reason}</td><td><Badge status={r.status} /></td><td className="muted small">{r.who}</td>
                <td><a className="link" href={r.href}>Open</a>{r.type === 'extraction' && r.document_id && <DocActions docId={r.document_id} status={r.status} onDone={reload} />}</td></tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </>
  )
}
