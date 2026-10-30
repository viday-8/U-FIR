import { Pencil } from 'lucide-react'
import { useState } from 'react'
import { api, type CaseMeta, getRole } from './api'
import { useT } from './i18n'
import { useAsync } from './ui'

/** Offence-type tags with the evidence behind each one, and an officer override (kept with who and why). */
export default function TagEditor({ caseId, meta, onChanged }: { caseId: number; meta: CaseMeta; onChanged: () => void }) {
  const t = useT()
  const types = useAsync(() => api<string[]>('/offence-types'), [])
  const [editing, setEditing] = useState(false)
  const [pick, setPick] = useState<string[]>(meta.offence)
  const [reason, setReason] = useState('')
  const [msg, setMsg] = useState('')
  const can = ['investigator', 'supervisor', 'admin'].includes(getRole())
  const run = async (fn: () => Promise<unknown>) => { setMsg(''); try { await fn(); setEditing(false); setReason(''); onChanged() } catch (e) { setMsg((e as Error).message) } }
  const toggle = (t: string) => setPick(p => (p.includes(t) ? p.filter(x => x !== t) : p.length < 3 ? [...p, t] : p))

  return (
    <div>
      {meta.offence_detail.map(d => (
        <span key={d.tag} className={'badge ' + (d.source === 'officer' ? 'ok' : 'info')} title={`Why: ${d.reasons.join('; ')}`}>{t(d.tag)}{d.source === 'officer' && ' ✓'}</span>
      ))}
      {meta.offence_detail.length === 0 && <span className="muted small">{t('No offence type detected')}</span>}
      <span className="muted small"> {t(meta.offence_source === 'officer' ? 'Set by an officer · hover a tag for the evidence' : 'Detected automatically · hover a tag for the evidence')}</span>
      {can && !editing && <button className="btn sm" onClick={() => { setPick(meta.offence); setEditing(true) }}><Pencil size={12} /> {t('Correct tags')}</button>}
      {meta.offence_detail.length > 0 && <details className="small"><summary>{t('Why these tags?')}</summary>
        <ul className="statements">{meta.offence_detail.map(d => <li key={d.tag}><strong>{d.tag}</strong>: {d.reasons.join('; ')}</li>)}</ul></details>}
      {editing && (
        <div className="card pad addform" aria-label="Correct offence tags">
          <p className="small muted">Choose up to three. This is a label for browsing and filtering, not a legal classification.</p>
          <div className="formrow">{(types.data ?? []).map(t => <label key={t} className="check"><input type="checkbox" checked={pick.includes(t)} onChange={() => toggle(t)} /> {t}</label>)}</div>
          <label>Reason for the change (required)<input value={reason} onChange={e => setReason(e.target.value)} /></label>
          <div className="actions">
            <button className="btn primary sm" disabled={!pick.length || !reason.trim()} onClick={() => run(() => api(`/cases/${caseId}/tags`, { method: 'PUT', body: JSON.stringify({ offence: pick, reason }) }))}>Save tags</button>
            {meta.offence_source === 'officer' && <button className="btn sm" onClick={() => run(() => api(`/cases/${caseId}/tags`, { method: 'DELETE' }))}>Go back to automatic</button>}
            <button className="btn sm" onClick={() => setEditing(false)}>Cancel</button>
          </div>
          {msg && <div className="errorbox" role="alert">{msg}</div>}
        </div>
      )}
    </div>
  )
}
