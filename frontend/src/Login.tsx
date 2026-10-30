import { ClipboardCheck, Fingerprint, Telescope } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { api, setSession } from './api'
import Crest from './Crest'
import { useT } from './i18n'
import { QuoteRotator } from './quotes'

const DEMO = [['inv_vizag', 'Investigator'], ['sup_vizag', 'Supervisor'], ['analyst_vizag', 'Analyst'], ['inv_guntur', 'Guntur'], ['inv_chittoor', 'Chittoor'], ['admin', 'Admin']]

export default function Login({ onDone }: { onDone: () => void }) {
  const t = useT()
  const [u, setU] = useState('')
  const [p, setP] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr('')
    try {
      const r = await api<{ token: string; role: string; district: string | null }>('/auth/login', { method: 'POST', body: JSON.stringify({ username: u, password: p }) })
      setSession(r.token, r.role, r.district ?? '', u); onDone()
    } catch (x) { setErr((x as Error).message.includes('Too many') ? (x as Error).message : t('Invalid username or password')) } finally { setBusy(false) }
  }
  return (
    <div className="loginsplit">
      <section className="loginhero" aria-label="About U-FIR ANVESHANA">
        <Crest size={360} className="watermark" />
        <span className="crest" style={{ width: 64, height: 64 }}><Crest size={64} /></span>
        <p className="mottoline">{t('Evidence · Integrity · Service')}</p>
        <p className="brandline"><strong>U-FIR ANVESHANA</strong> <span lang="te">(అన్వేషణ)</span> · {t('Investigation, exploration and discovery')}</p>
        <h1>{t('Every insight has evidence. Every decision is reviewed.')}</h1>
        <p>{t('An evidence-first case intelligence workspace for Prohibition & Excise officers. It reads existing records as they are written and shows its work.')}</p>
        <ul className="heropoints">
          <li><Telescope size={20} /><div><b>{t('Evidence on every line')}</b><span>{t('Each statement links to the exact passage in the original record.')}</span></div></li>
          <li><ClipboardCheck size={20} /><div><b>{t('The officer stays in control')}</b><span>{t('Matches, legal suggestions and drafts wait for a human decision.')}</span></div></li>
          <li><Fingerprint size={20} /><div><b>{t('Access by role and district')}</b><span>{t('You only ever see the records you are authorised to see.')}</span></div></li>
        </ul>
        <QuoteRotator />
      </section>
      <section className="loginpane">
        <form onSubmit={submit} className="card login" aria-labelledby="signin-h">
          <h2 id="signin-h">{t('Sign in')}</h2>
          <label>{t('Username')}<input value={u} onChange={e => setU(e.target.value)} autoComplete="username" autoFocus /></label>
          <label>{t('Password')}<input type="password" value={p} onChange={e => setP(e.target.value)} autoComplete="current-password" /></label>
          {err && <div className="errorbox" role="alert">{err}</div>}
          <button className="btn primary" type="submit" disabled={busy || !u || !p} style={{ justifyContent: 'center' }}>{busy ? t('Signing in…') : t('Sign in')}</button>
          <div>
            <p className="small muted" style={{ margin: '0 0 .3rem' }}>{t('Demo accounts (synthetic data). Password:')} <strong>demo123</strong>. {t('Choose one:')}</p>
            <div className="demoaccts">{DEMO.map(([name, label]) => <button type="button" key={name} className="chip" onClick={() => { setU(name); setP('demo123') }} aria-label={`${t(label)}, use demo account ${name}`}>{t(label)}</button>)}</div>
          </div>
          <p className="authnote">{t('Authorised users only. Consequential actions are recorded in an append-only audit ledger.')}</p>
        </form>
      </section>
    </div>
  )
}
