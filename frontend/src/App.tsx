import { ClipboardCheck, FolderOpen, Gavel, Gauge, LayoutDashboard, LogOut, MapPin, MessageSquare, Network, ScrollText, Search, ShieldCheck } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { api, getRole, hasToken, setSession } from './api'
import Audit from './Audit'
import CasesList from './CasesList'
import Cockpit from './Cockpit'
import Copilot from './Copilot'
import Dashboard from './Dashboard'
import Governance from './Governance'
import Hotspots from './Hotspots'
import ReviewQueue from './ReviewQueue'
import Relationships from './Relationships'
import SearchPage from './SearchPage'
import { StudioEditor, StudioList } from './Studio'

function useHash() {
  const read = () => location.hash.slice(1) || '/dashboard'
  const [h, setH] = useState(read)
  useEffect(() => { const f = () => { setH(read()); window.scrollTo(0, 0) }; addEventListener('hashchange', f); return () => removeEventListener('hashchange', f) }, [])
  return h
}

function Login({ onDone }: { onDone: () => void }) {
  const [u, setU] = useState('inv_vizag')
  const [p, setP] = useState('demo123')
  const [err, setErr] = useState('')
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const r = await api<{ token: string; role: string }>('/auth/login', { method: 'POST', body: JSON.stringify({ username: u, password: p }) })
      setSession(r.token, r.role); onDone()
    } catch { setErr('Invalid username or password') }
  }
  return (
    <div className="loginwrap">
      <form onSubmit={submit} className="card login">
        <div className="brand big"><ShieldCheck size={26} /> u-FIR Nexus</div>
        <p className="muted">Unified case intelligence for Prohibition &amp; Excise officers.</p>
        <label>Username<input value={u} onChange={e => setU(e.target.value)} autoComplete="username" /></label>
        <label>Password<input type="password" value={p} onChange={e => setP(e.target.value)} autoComplete="current-password" /></label>
        {err && <div className="errorbox" role="alert">{err}</div>}
        <button className="btn primary" type="submit">Sign in</button>
        <details className="small"><summary>Demo accounts (synthetic data, password demo123)</summary>
          <p>inv_vizag · sup_vizag · analyst_vizag (Visakhapatnam)<br />inv_guntur · sup_guntur (Guntur)<br />inv_chittoor (Chittoor) · admin (all districts)</p></details>
      </form>
    </div>
  )
}

const NAV: { href: string; match: string; label: string; icon: ReactNode; roles?: string[] }[] = [
  { href: '#/dashboard', match: '/dashboard', label: 'Command Center', icon: <LayoutDashboard size={17} /> },
  { href: '#/cases', match: '/cases', label: 'Cases', icon: <FolderOpen size={17} /> },
  { href: '#/search', match: '/search', label: 'Search', icon: <Search size={17} /> },
  { href: '#/copilot', match: '/copilot', label: 'Copilot', icon: <MessageSquare size={17} /> },
  { href: '#/relationships', match: '/relationships', label: 'Relationships', icon: <Network size={17} /> },
  { href: '#/reviews', match: '/reviews', label: 'Review Queue', icon: <ClipboardCheck size={17} /> },
  { href: '#/hotspots', match: '/hotspots', label: 'Hotspots', icon: <MapPin size={17} /> },
  { href: '#/studio', match: '/studio', label: 'Document Studio', icon: <ScrollText size={17} /> },
  { href: '#/governance', match: '/governance', label: 'Quality & Governance', icon: <Gauge size={17} />, roles: ['supervisor', 'admin'] },
  { href: '#/audit', match: '/audit', label: 'Audit Ledger', icon: <Gavel size={17} />, roles: ['supervisor', 'admin'] },
]

export default function App() {
  const [authed, setAuthed] = useState(hasToken())
  const hash = useHash()
  const [path, query = ''] = hash.split('?')
  const params = new URLSearchParams(query)
  const parts = path.split('/').filter(Boolean)
  const role = getRole()

  let page: ReactNode
  if (parts[0] === 'cases' && parts[1]) page = <Cockpit id={Number(parts[1])} />
  else if (parts[0] === 'cases') page = <CasesList />
  else if (parts[0] === 'search') page = <SearchPage key={params.get('q') ?? ''} initial={params.get('q') ?? ''} />
  else if (parts[0] === 'copilot') page = <Copilot key={params.get('case') ?? ''} initialCase={params.get('case') ?? ''} />
  else if (parts[0] === 'relationships') page = <Relationships />
  else if (parts[0] === 'studio' && parts[1]) page = <StudioEditor id={Number(parts[1])} />
  else if (parts[0] === 'studio') page = <StudioList status={params.get('status') ?? ''} />
  else if (parts[0] === 'reviews') page = <ReviewQueue type={params.get('type') ?? ''} />
  else if (parts[0] === 'hotspots') page = <Hotspots />
  else if (parts[0] === 'governance') page = <Governance />
  else if (parts[0] === 'audit') page = <Audit />
  else page = <Dashboard />

  return (
    <>
      <button className="skip" onClick={() => document.getElementById('main')?.focus()}>Skip to main content</button>
      <div className="banner" role="status">DEMO · SYNTHETIC DATA · not connected to any live system</div>
      {!authed ? <Login onDone={() => { location.hash = '/dashboard'; setAuthed(true) }} /> : (
        <div className="shell">
          <nav className="nav" aria-label="Main">
            <div className="brand"><ShieldCheck size={20} /> u-FIR Nexus</div>
            <ul>
              {NAV.filter(n => !n.roles || n.roles.includes(role)).map(n => (
                <li key={n.href}><a href={n.href} aria-current={parts[0] === n.match.slice(1) ? 'page' : undefined}>{n.icon}{n.label}</a></li>
              ))}
            </ul>
            <div className="navfoot">
              <div className="small">Signed in as<br /><strong>{role}</strong></div>
              <button className="navbtn" onClick={() => { setSession(''); setAuthed(false); location.hash = '' }}><LogOut size={15} /> Sign out</button>
            </div>
          </nav>
          <main id="main" tabIndex={-1}>{page}</main>
        </div>
      )}
    </>
  )
}
