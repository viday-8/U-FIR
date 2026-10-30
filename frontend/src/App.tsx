import { useEffect, useRef, useState, type ReactNode } from 'react'
import { getDistrict, getRole, getUsername, hasToken, setSession } from './api'
import Audit from './Audit'
import CasesList from './CasesList'
import Cockpit from './Cockpit'
import Copilot from './Copilot'
import Dashboard from './Dashboard'
import Deadlines from './Deadlines'
import Governance from './Governance'
import Hotspots from './Hotspots'
import Intake from './Intake'
import Login from './Login'
import Relationships from './Relationships'
import ReviewQueue from './ReviewQueue'
import SearchPage from './SearchPage'
import { useLang, useT } from './i18n'
import { Breadcrumbs, CommandPalette, CrumbProvider, Footer, Masthead, NavBar, ShortcutsHelp, Toaster, UtilityBar, ALL_ITEMS, usePrefs } from './Shell'
import { StudioEditor, StudioList } from './Studio'

function useHash() {
  const read = () => location.hash.slice(1) || '/dashboard'
  const [h, setH] = useState(read)
  useEffect(() => { const f = () => { setH(read()); window.scrollTo(0, 0) }; addEventListener('hashchange', f); return () => removeEventListener('hashchange', f) }, [])
  return h
}

export default function App() {
  const [authed, setAuthed] = useState(hasToken())
  const hash = useHash()
  const prefs = usePrefs()
  const t = useT()
  const { swapping } = useLang()
  const [palette, setPalette] = useState(false)
  const [help, setHelp] = useState(false)
  const [crumb, setCrumb] = useState('')
  const search = useRef<HTMLInputElement>(null)
  const [path, query = ''] = hash.split('?')
  const params = new URLSearchParams(query)
  const parts = path.split('/').filter(Boolean)
  const role = getRole()

  // keyboard shortcuts: "/" focuses search, Ctrl/Cmd+K opens quick find
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName) || t.isContentEditable
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k' && authed) { e.preventDefault(); setPalette(p => !p) }
      else if (e.key === '/' && !typing && authed) { e.preventDefault(); search.current?.focus() }
      else if (e.key === '?' && !typing && authed) { e.preventDefault(); setHelp(h => !h) }
    }
    addEventListener('keydown', onKey); return () => removeEventListener('keydown', onKey)
  }, [authed])

  const key = parts[0] === 'relationships' ? 'network' : parts[0] || 'dashboard'
  const current = ALL_ITEMS.find(i => i.match === key)
  useEffect(() => { document.title = authed ? `${crumb || t(current?.label ?? 'Command Center')} · U-FIR ANVESHANA` : 'U-FIR ANVESHANA (అన్వేషణ)' }, [crumb, current, t, authed])

  const rule = ALL_ITEMS.find(n => n.roles && key === n.match)
  const allowed = !rule || rule.roles!.includes(role)
  let page: ReactNode
  if (parts[0] === 'cases' && parts[1]) page = <Cockpit id={Number(parts[1])} />
  else if (parts[0] === 'cases') page = <CasesList />
  else if (parts[0] === 'intake') page = <Intake district={getDistrict()} />
  else if (parts[0] === 'search') page = <SearchPage key={params.get('q') ?? ''} initial={params.get('q') ?? ''} />
  else if (parts[0] === 'copilot') page = <Copilot key={params.get('case') ?? ''} initialCase={params.get('case') ?? ''} />
  else if (parts[0] === 'network' || parts[0] === 'relationships') page = <Relationships key={params.get('focus') ?? ''} focus={params.get('focus') ?? ''} />
  else if (parts[0] === 'studio' && parts[1]) page = <StudioEditor id={Number(parts[1])} />
  else if (parts[0] === 'studio') page = <StudioList status={params.get('status') ?? ''} />
  else if (parts[0] === 'reviews') page = <ReviewQueue type={params.get('type') ?? ''} />
  else if (parts[0] === 'deadlines') page = <Deadlines />
  else if (parts[0] === 'hotspots') page = <Hotspots />
  else if (parts[0] === 'governance') page = <Governance />
  else if (parts[0] === 'audit') page = <Audit />
  else page = <Dashboard />
  if (!allowed) page = <div className="card pad" role="alert"><h1>Not available for your role</h1><p className="muted">This page is only for {rule!.roles!.join(' / ')} accounts. Use the menu to continue.</p><a className="btn" href="#/dashboard">Back to Command Center</a></div>

  const signOut = () => { setSession(''); setAuthed(false); location.hash = '' }

  return (
    <div className={'app' + (swapping ? ' swapping' : '')}>
      <button className="skip" onClick={() => document.getElementById('main')?.focus()}>{t('Skip to main content')}</button>
      <div className="tricolour" aria-hidden><i /><i /><i /></div>
      <UtilityBar prefs={prefs} onHelp={() => setHelp(true)} authed={authed} />
      {!authed ? <Login onDone={() => { location.hash = '/dashboard'; setAuthed(true) }} /> : (
        <>
          <Masthead username={getUsername()} role={role} district={getDistrict()} onSignOut={signOut} searchRef={search} />
          <NavBar role={role} parts={parts} hash={hash} onPalette={() => setPalette(true)} />
          <Breadcrumbs parts={parts} role={role} extra={crumb} />
          <CrumbProvider value={setCrumb}><main id="main" tabIndex={-1}>{page}</main></CrumbProvider>
          <CommandPalette open={palette} onClose={() => setPalette(false)} role={role} />
          <ShortcutsHelp open={help} onClose={() => setHelp(false)} />
          <Toaster />
        </>
      )}
      <Footer />
    </div>
  )
}
