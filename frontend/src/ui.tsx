import { AlertTriangle, CheckCircle2, CircleDashed, Clock, FileEdit, HelpCircle, Info, Loader2, XCircle } from 'lucide-react'
import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { locale, useLang, useT } from './i18n'

const TONES: Record<string, { tone: string; icon: ReactNode; label: string }> = {
  indexed: { tone: 'ok', icon: <CheckCircle2 size={13} />, label: 'Processed' },
  received: { tone: 'info', icon: <Loader2 size={13} />, label: 'Received' },
  needs_review: { tone: 'warn', icon: <AlertTriangle size={13} />, label: 'Needs review' },
  failed: { tone: 'bad', icon: <XCircle size={13} />, label: 'Failed' },
  reviewed: { tone: 'ok', icon: <CheckCircle2 size={13} />, label: 'Reviewed' },
  unreviewed: { tone: 'warn', icon: <HelpCircle size={13} />, label: 'Unreviewed' },
  confirmed: { tone: 'ok', icon: <CheckCircle2 size={13} />, label: 'Confirmed' },
  rejected: { tone: 'bad', icon: <XCircle size={13} />, label: 'Rejected' },
  deferred: { tone: 'neutral', icon: <Clock size={13} />, label: 'Deferred' },
  suggested: { tone: 'info', icon: <Info size={13} />, label: 'Suggested' },
  insufficient: { tone: 'neutral', icon: <CircleDashed size={13} />, label: 'Insufficient facts' },
  accepted: { tone: 'ok', icon: <CheckCircle2 size={13} />, label: 'Accepted' },
  draft: { tone: 'neutral', icon: <FileEdit size={13} />, label: 'Draft' },
  in_review: { tone: 'info', icon: <Clock size={13} />, label: 'In review' },
  approved: { tone: 'ok', icon: <CheckCircle2 size={13} />, label: 'Approved' },
  returned: { tone: 'warn', icon: <AlertTriangle size={13} />, label: 'Returned' },
  open: { tone: 'info', icon: <CircleDashed size={13} />, label: 'Open' },
  overdue: { tone: 'bad', icon: <AlertTriangle size={13} />, label: 'Overdue' },
  soon: { tone: 'warn', icon: <Clock size={13} />, label: 'Due soon' },
  later: { tone: 'neutral', icon: <Clock size={13} />, label: 'Later' },
  done: { tone: 'ok', icon: <CheckCircle2 size={13} />, label: 'Done' },
  named: { tone: 'neutral', icon: null, label: 'Named' },
  arrested: { tone: 'info', icon: null, label: 'Arrested' },
  remanded: { tone: 'info', icon: null, label: 'In remand' },
  bailed: { tone: 'neutral', icon: null, label: 'On bail' },
  absconding: { tone: 'warn', icon: null, label: 'Absconding' },
}

export function Badge({ status, label }: { status: string; label?: string }) {
  const tr = useT()
  const t = TONES[status] ?? { tone: 'neutral', icon: null, label: status }
  return <span className={`badge ${t.tone}`}>{t.icon}{label ?? tr(t.label)}</span>
}

export function Notice({ tone = 'info', children }: { tone?: 'info' | 'warn'; children: ReactNode }) {
  const t = useT()
  return <div className={`notice ${tone}`} role="note">{tone === 'warn' ? <AlertTriangle size={16} /> : <Info size={16} />}<div>{typeof children === 'string' ? t(children) : children}</div></div>
}

export function PageHeader({ title, sub, actions }: { title: string; sub?: string; actions?: ReactNode }) {
  const t = useT()
  return (
    <div className="pagehead">
      <div><h1>{t(title)}</h1>{sub && <p className="muted">{t(sub)}</p>}</div>
      {actions && <div className="actions">{actions}</div>}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  const t = useT()
  return <div className="empty">{typeof children === 'string' ? t(children) : children}</div>
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [n, setN] = useState(0)
  useEffect(() => {
    let live = true
    setLoading(true); setError('')
    fn().then(d => live && setData(d)).catch(e => live && setError(e.message)).finally(() => live && setLoading(false))
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, n])
  const reload = useCallback(() => setN(x => x + 1), [])
  return { data, error, loading, reload }
}

export function Loading({ what = 'Loading' }: { what?: string }) {
  const { lang } = useLang()
  const t = useT()
  return <div className="loading" aria-live="polite"><span>{lang === 'te' ? t('Loading') : what}…</span></div>
}

export function ErrorBox({ message, retry }: { message: string; retry?: () => void }) {
  const t = useT()
  return <div className="errorbox" role="alert"><AlertTriangle size={16} /> {message}{retry && <button className="btn sm" onClick={retry}>{t('Retry')}</button>}</div>
}

export const fmtDate = (s?: string | null) => (s ? new Date(s).toLocaleString(locale(), { dateStyle: 'medium', timeStyle: 'short' }) : '')
