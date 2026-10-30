import { CalendarClock, CheckCircle2, ChevronDown, Keyboard, Phone, X, ClipboardCheck, FileUp, FolderOpen, Gauge, Gavel, LayoutDashboard, LogOut, MapPin, Menu, MessageSquare, Monitor, Moon, Network, ScrollText, Search, Sun } from 'lucide-react'
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { api, type Dashboard, type Overview } from './api'
import Crest from './Crest'
import { useLang, useT } from './i18n'

/* ------------------------------ navigation model ------------------------------ */
export type NavItem = { href: string; match: string; label: string; desc: string; icon: ReactNode; roles?: string[] }
export type NavGroup = { key: string; label: string; icon: ReactNode; href?: string; match?: string; roles?: string[]; items?: NavItem[] }
const EDITORS = ['investigator', 'supervisor', 'admin']
const I = 16
export const GROUPS: NavGroup[] = [
  { key: 'home', label: 'Command Center', icon: <LayoutDashboard size={I} />, href: '#/dashboard', match: 'dashboard' },
  { key: 'cases', label: 'Cases', icon: <FolderOpen size={I} />, items: [
    { href: '#/cases', match: 'cases', label: 'Cases', desc: 'Browse and filter every case record', icon: <FolderOpen size={18} /> },
    { href: '#/intake', match: 'intake', label: 'Upload Case Files', desc: 'Add FIRs, panchanamas, diaries and scans', icon: <FileUp size={18} />, roles: EDITORS },
    { href: '#/search', match: 'search', label: 'Search', desc: 'Names, vehicles, places and document text', icon: <Search size={18} /> },
  ] },
  { key: 'intel', label: 'Intelligence', icon: <Network size={I} />, items: [
    { href: '#/network', match: 'network', label: 'Network', desc: 'Repeat offenders, shared vehicles, linked cases', icon: <Network size={18} /> },
    { href: '#/hotspots', match: 'hotspots', label: 'Hotspots', desc: 'Where recorded cases cluster', icon: <MapPin size={18} /> },
    { href: '#/copilot', match: 'copilot', label: 'Copilot', desc: 'Ask questions, get cited answers', icon: <MessageSquare size={18} /> },
  ] },
  { key: 'work', label: 'Workflow', icon: <ClipboardCheck size={I} />, items: [
    { href: '#/reviews', match: 'reviews', label: 'Review Queue', desc: 'Everything waiting for a human decision', icon: <ClipboardCheck size={18} /> },
    { href: '#/deadlines', match: 'deadlines', label: 'Deadlines', desc: 'Chargesheet limits, remand and hearing dates', icon: <CalendarClock size={18} /> },
    { href: '#/studio', match: 'studio', label: 'Document Studio', desc: 'Case diaries and chargesheet drafts', icon: <ScrollText size={18} /> },
  ] },
  { key: 'gov', label: 'Governance', icon: <Gauge size={I} />, roles: ['supervisor', 'admin'], items: [
    { href: '#/governance', match: 'governance', label: 'Quality & Governance', desc: 'Accuracy, risk status, users and settings', icon: <Gauge size={18} />, roles: ['supervisor', 'admin'] },
    { href: '#/audit', match: 'audit', label: 'Audit Ledger', desc: 'Append-only record of AI output and decisions', icon: <Gavel size={18} />, roles: ['supervisor', 'admin'] },
  ] },
]
export function visibleGroups(role: string) {
  return GROUPS.filter(g => !g.roles || g.roles.includes(role)).map(g => ({ ...g, items: g.items?.filter(i => !i.roles || i.roles.includes(role)) })).filter(g => g.href || g.items?.length)
}
export const ALL_ITEMS: (NavItem & { group: string })[] = GROUPS.flatMap(g => (g.href ? [{ href: g.href, match: g.match!, label: g.label, desc: 'Work queue, counts and what needs attention', icon: g.icon, group: g.label }] : (g.items ?? []).map(i => ({ ...i, group: g.label }))))

/* ------------------------------ breadcrumb label from the page ------------------------------ */
const CrumbCtx = createContext<(s: string) => void>(() => undefined)
export const CrumbProvider = CrumbCtx.Provider
export function useCrumb(label: string | undefined) {
  const set = useContext(CrumbCtx)
  useEffect(() => { if (label) { set(label); return () => set('') } }, [label, set])
}

/* ------------------------------ preferences (theme, text size) ------------------------------ */
type Theme = 'auto' | 'light' | 'dark'
type Size = 'sm' | 'md' | 'lg'
const read = (k: string, d: string) => { try { return localStorage.getItem(k) ?? d } catch { return d } }
const write = (k: string, v: string) => { try { localStorage.setItem(k, v) } catch { /* storage unavailable */ } }
export function usePrefs() {
  const [theme, setTheme] = useState<Theme>(() => read('theme', 'auto') as Theme)
  const [size, setSize] = useState<Size>(() => read('size', 'md') as Size)
  useEffect(() => { const r = document.documentElement; theme === 'auto' ? r.removeAttribute('data-theme') : (r.dataset.theme = theme); write('theme', theme) }, [theme])
  useEffect(() => { const r = document.documentElement; size === 'md' ? r.removeAttribute('data-size') : (r.dataset.size = size); write('size', size) }, [size])
  return { theme, setTheme, size, setSize }
}

export function LangSwitch() {
  const { lang, setLang } = useLang()
  return (
    <div className="langswitch" role="group" aria-label="Language / భాష" data-lang={lang}>
      <span className="langpill" aria-hidden />
      <button lang="en" aria-pressed={lang === 'en'} onClick={() => setLang('en')}>English</button>
      <button lang="te" aria-pressed={lang === 'te'} onClick={() => setLang('te')}>తెలుగు</button>
    </div>
  )
}

export function UtilityBar({ prefs, onHelp, authed }: { prefs: ReturnType<typeof usePrefs>; onHelp: () => void; authed: boolean }) {
  const t = useT()
  const next: Record<Theme, Theme> = { auto: 'light', light: 'dark', dark: 'auto' }
  const icon = prefs.theme === 'dark' ? <Moon size={13} /> : prefs.theme === 'light' ? <Sun size={13} /> : <Monitor size={13} />
  return (
    <div className="utility">
      <div className="container">
        <span className="demochip" role="status"><i /> {t('Demo environment · synthetic data · not connected to any live system')}</span>
        <div className="utilbtns">
          <a className="emergency" href="tel:112" title="National emergency number">{<Phone size={12} />} {t('Emergency 112')}</a>
          <LangSwitch />
          {authed && <button className="ubtn" onClick={onHelp} aria-label={t('Keyboard shortcuts')}><Keyboard size={13} /> {t('Shortcuts')}</button>}
          <span className="sep" aria-hidden />
          <button className="ubtn" aria-label="A−, decrease text size" aria-pressed={prefs.size === 'sm'} onClick={() => prefs.setSize('sm')}>A−</button>
          <button className="ubtn" aria-label="A, default text size" aria-pressed={prefs.size === 'md'} onClick={() => prefs.setSize('md')}>A</button>
          <button className="ubtn" aria-label="A+, increase text size" aria-pressed={prefs.size === 'lg'} onClick={() => prefs.setSize('lg')}>A+</button>
          <span className="sep" aria-hidden />
          <button className="ubtn" onClick={() => prefs.setTheme(next[prefs.theme])} aria-label={`${t(prefs.theme === 'auto' ? 'Auto' : prefs.theme === 'light' ? 'Light' : 'Dark')}: ${t('Colour theme')}`} title={`${t('Colour theme')}: ${prefs.theme} → ${next[prefs.theme]}`}>{icon} {t(prefs.theme === 'auto' ? 'Auto' : prefs.theme === 'light' ? 'Light' : 'Dark')}</button>
        </div>
      </div>
    </div>
  )
}

/* ------------------------------ masthead ------------------------------ */
export function Masthead({ username, role, district, onSignOut, searchRef }: { username: string; role: string; district: string | null; onSignOut: () => void; searchRef: React.RefObject<HTMLInputElement | null> }) {
  const t = useT()
  const [q, setQ] = useState('')
  const submit = (e: FormEvent) => { e.preventDefault(); if (q.trim()) { location.hash = `/search?q=${encodeURIComponent(q.trim())}`; setQ(''); searchRef.current?.blur() } }
  return (
    <header className="masthead">
      <div className="container">
        <a className="brand" href="#/dashboard">
          <span className="crest"><Crest size={46} /></span>
          <span className="brandtext"><strong>U-FIR ANVESHANA <span lang="te" className="tename">(అన్వేషణ)</span></strong><span>{t('Investigation · Exploration · Discovery')}</span></span>
        </a>
        <form className="gsearch" role="search" onSubmit={submit}>
          <Search size={16} className="ico" />
          <label className="sr" htmlFor="gsearch">{t('Search all records')}</label>
          <input id="gsearch" ref={searchRef} value={q} onChange={e => setQ(e.target.value)} placeholder={t('Search cases, names, vehicles…')} autoComplete="off" />
          <kbd aria-hidden>/</kbd>
        </form>
        <div className="userchip">
          <span className="avatar-s" aria-hidden>{username.slice(0, 1)}</span>
          <span className="who"><strong>{username}</strong><span><span className="pips" aria-hidden>{'★'.repeat({ investigator: 1, supervisor: 2, admin: 3 }[role] ?? 0)}</span>{t(role)}{district ? ` · ${t(district)}` : ` · ${t('all districts')}`}</span></span>
          <button className="btn sm" onClick={onSignOut}><LogOut size={13} /> {t('Sign out')}</button>
        </div>
      </div>
    </header>
  )
}

/* ------------------------------ primary navigation ------------------------------ */
export function NavBar({ role, parts, hash, onPalette }: { role: string; parts: string[]; hash: string; onPalette: () => void }) {
  const t = useT()
  const groups = useMemo(() => visibleGroups(role), [role])
  const [open, setOpen] = useState<string | null>(null)
  const [mobile, setMobile] = useState(false)
  const bar = useRef<HTMLElement>(null)
  const timer = useRef<number | undefined>(undefined)
  useEffect(() => { setOpen(null); setMobile(false) }, [hash])
  useEffect(() => {
    const down = (e: MouseEvent) => { if (bar.current && !bar.current.contains(e.target as Node)) setOpen(null) }
    document.addEventListener('mousedown', down); return () => document.removeEventListener('mousedown', down)
  }, [])
  const activeGroup = (g: (typeof groups)[number]) => (g.href ? parts[0] === g.match : g.items?.some(i => parts[0] === i.match || (i.match === 'network' && parts[0] === 'relationships')))
  return (
    <nav className="navbar" aria-label="Main" ref={bar} onKeyDown={e => { if (e.key === 'Escape') setOpen(null) }}>
      <div className="container">
        <button className="menutoggle" aria-expanded={mobile} aria-controls="navlist" onClick={() => setMobile(!mobile)}><Menu size={16} /> {t('Menu')}</button>
        <ul id="navlist" className={'navlist' + (mobile ? ' open' : '')}>
          {groups.map(g => (
            <li key={g.key} className="navitem" onMouseEnter={() => { window.clearTimeout(timer.current); if (g.items && matchMedia('(hover:hover)').matches) setOpen(g.key) }} onMouseLeave={() => { timer.current = window.setTimeout(() => setOpen(null), 160) }}>
              {g.href ? (
                <a className="navlink" href={g.href} aria-current={parts[0] === g.match ? 'page' : undefined}>{g.icon}{t(g.label)}</a>
              ) : (
                <>
                  <button className={'navtrigger' + (activeGroup(g) ? ' active' : '')} aria-expanded={open === g.key} aria-haspopup="true" onClick={() => setOpen(open === g.key ? null : g.key)}>
                    {g.icon}{t(g.label)}<ChevronDown size={14} className="chev" />
                  </button>
                  {(open === g.key || mobile) && (
                    <ul className="menu" aria-label={t(g.label)}>
                      {g.items!.map(i => (
                        <li key={i.href}><a href={i.href} aria-current={parts[0] === i.match || (i.match === 'network' && parts[0] === 'relationships') ? 'page' : undefined}>{i.icon}<b>{t(i.label)}</b><span>{t(i.desc)}</span></a></li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </li>
          ))}
        </ul>
        <button className="ubtn" style={{ marginLeft: 'auto', color: '#dbe5f2' }} onClick={onPalette} title="Quick find: jump to any page or case (Control or Command + K)"><Search size={14} /> {t('Quick find')} <kbd style={{ font: '.68rem ui-monospace,monospace', border: '1px solid rgba(255,255,255,.3)', borderRadius: 4, padding: '0 .3rem' }}>⌘K</kbd></button>
      </div>
    </nav>
  )
}

/* ------------------------------ breadcrumbs ------------------------------ */
/** Today's briefing: what needs the officer's attention, refreshed after every saved change. */
export function Briefing() {
  const t = useT()
  const { lang } = useLang()
  const [d, setD] = useState<Dashboard | null>(null)
  const load = useCallback(() => { api<Dashboard>('/dashboard').then(setD).catch(() => undefined) }, [])
  useEffect(() => {
    load()
    const t = setInterval(load, 45000)
    let after: number | undefined
    const onSaved = () => { window.clearTimeout(after); after = window.setTimeout(load, 500) }
    addEventListener('ufir:toast', onSaved)
    return () => { clearInterval(t); removeEventListener('ufir:toast', onSaved); window.clearTimeout(after) }
  }, [load])
  const today = new Date().toLocaleDateString(lang === 'te' ? 'te-IN' : 'en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
  const overdue = d?.deadlines.overdue ?? 0
  const reviews = d ? d.counts.identity_to_review + d.counts.legal_to_review + d.counts.drafts_in_review + (d.pipeline.needs_review ?? 0) + (d.pipeline.failed ?? 0) : 0
  return (
    <div className="briefing" aria-label="Today's briefing">
      <span className="today">{today}</span>
      {d && overdue > 0 && <a className="bchip bad" href="#/deadlines">{t('{n} overdue deadline(s)', { n: overdue })}</a>}
      {d && d.deadlines.soon > 0 && <a className="bchip warn" href="#/deadlines">{t('{n} due within 14 days', { n: d.deadlines.soon })}</a>}
      {d && reviews > 0 && <a className="bchip warn" href="#/reviews">{t('{n} awaiting review', { n: reviews })}</a>}
      {d && overdue === 0 && reviews === 0 && d.deadlines.soon === 0 && <span className="bchip ok"><CheckCircle2 size={12} /> {t('All clear')}</span>}
    </div>
  )
}

export function Breadcrumbs({ parts, role, extra }: { parts: string[]; role: string; extra: string }) {
  const t = useT()
  const key = parts[0] === 'relationships' ? 'network' : parts[0] || 'dashboard'
  const item = ALL_ITEMS.find(i => i.match === key)
  const group = item?.group && item.group !== item.label ? item.group : null
  void role
  return (
    <div className="crumbbar">
      <div className="container">
        <ol className="crumbs" aria-label="Breadcrumb">
          <li><a href="#/dashboard">{t('Home')}</a></li>
          {group && <li>{t(group)}</li>}
          {item && item.label !== 'Command Center' && <li>{extra ? <a href={item.href}>{t(item.label)}</a> : <span aria-current="page">{t(item.label)}</span>}</li>}
          {extra && <li><span aria-current="page">{extra}</span></li>}
        </ol>
        <Briefing />
      </div>
    </div>
  )
}

export function Footer() {
  const t = useT()
  return (
    <footer className="footer">
      <div className="container">
        <div>
          <p className="motto"><span className="crest sm"><Crest size={22} /></span> {t('Evidence · Integrity · Service')}</p>
          <p><strong>U-FIR ANVESHANA</strong> (<span lang="te">అన్వేషణ</span>): {t('a hackathon prototype for the Andhra Pradesh Prohibition & Excise “AI-Enabled Unified FIR” challenge.')}</p>
          <p>{t('Synthetic data only. Not an official record system. AI-assisted output is advisory and needs an officer’s review; allegations in records are not findings.')}</p>
        </div>
        <div>
          <p>Accessibility target: WCAG 2.2 AA · keyboard: <kbd>/</kbd> search, <kbd>Ctrl/⌘ K</kbd> quick find</p>
          <p>{t('Consequential actions are recorded in an append-only audit ledger.')}</p>
        </div>
      </div>
    </footer>
  )
}

/* ------------------------------ command palette ------------------------------ */
export function CommandPalette({ open, onClose, role }: { open: boolean; onClose: () => void; role: string }) {
  const t = useT()
  const [q, setQ] = useState('')
  const [cases, setCases] = useState<{ id: number; case_no: string; hint: string }[]>([])
  const [idx, setIdx] = useState(0)
  const input = useRef<HTMLInputElement>(null)
  const returnTo = useRef<Element | null>(null)
  const pages = useMemo(() => visibleGroups(role).flatMap(g => (g.href ? [{ href: g.href, label: g.label, desc: 'Work queue, counts and what needs attention', group: 'Page' }] : g.items!.map(i => ({ href: i.href, label: i.label, desc: i.desc, group: g.label })))), [role])
  useEffect(() => {  // Esc closes the palette from anywhere, even before the input has focus
    if (!open) return
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    addEventListener('keydown', esc); return () => removeEventListener('keydown', esc)
  }, [open, onClose])
  useEffect(() => { if (open) { returnTo.current = document.activeElement; setQ(''); setIdx(0); setTimeout(() => input.current?.focus(), 20) } else (returnTo.current as HTMLElement | null)?.focus?.() }, [open])
  useEffect(() => {
    if (!open || q.trim().length < 2) { setCases([]); return }
    const t = setTimeout(() => api<Overview>(`/cases/overview?q=${encodeURIComponent(q)}`).then(o => setCases(o.items.slice(0, 5).map(c => ({ id: c.id, case_no: c.case_no, hint: c.matched[0] ?? c.meta.offence[0] ?? c.station })))).catch(() => setCases([])), 200)
    return () => clearTimeout(t)
  }, [q, open])
  const filtered = pages.filter(p => !q.trim() || `${p.label} ${p.desc} ${p.group} ${t(p.label)} ${t(p.desc)}`.toLowerCase().includes(q.toLowerCase()))
  const options: { key: string; label: string; hint: string; href: string }[] = [
    ...filtered.map(p => ({ key: p.href, label: t(p.label), hint: t(p.group), href: p.href })),
    ...cases.map(c => ({ key: 'c' + c.id, label: `Open case ${c.case_no}`, hint: c.hint, href: `#/cases/${c.id}` })),
    ...(q.trim().length >= 2 ? [{ key: 'search', label: `Search all records for “${q.trim()}”`, hint: 'Search', href: `#/search?q=${encodeURIComponent(q.trim())}` }] : []),
  ]
  const go = (href: string) => { onClose(); location.hash = href.slice(1) }
  if (!open) return null
  return (
    <div className="scrim" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="palette" role="dialog" aria-modal="true" aria-label="Quick find">
        <input ref={input} value={q} placeholder={t('Go to a page, or type a case number, name or vehicle…')} aria-label={t('Quick find')} role="combobox" aria-expanded aria-controls="palette-list" aria-activedescendant={options[idx] ? `opt-${idx}` : undefined}
          onChange={e => { setQ(e.target.value); setIdx(0) }}
          onKeyDown={e => {
            if (e.key === 'Escape') onClose()
            else if (e.key === 'ArrowDown') { e.preventDefault(); setIdx(i => Math.min(i + 1, options.length - 1)) }
            else if (e.key === 'ArrowUp') { e.preventDefault(); setIdx(i => Math.max(i - 1, 0)) }
            else if (e.key === 'Enter' && options[idx]) go(options[idx].href)
          }} />
        <ul id="palette-list" role="listbox">
          {options.length === 0 && <li className="empty">{t('Nothing matches. Press Enter to search all records.')}</li>}
          {options.map((o, i) => (
            <li key={o.key} role="presentation"><button id={`opt-${i}`} role="option" aria-selected={i === idx} onMouseEnter={() => setIdx(i)} onClick={() => go(o.href)}>{o.label}<small>{o.hint}</small></button></li>
          ))}
        </ul>
        <div className="palettehint"><span>{t('↑↓ to move')}</span><span>{t('Enter to open')}</span><span>{t('Esc to close')}</span></div>
      </div>
    </div>
  )
}

/* ------------------------------ toasts ------------------------------ */
export function Toaster() {
  const t = useT()
  const [items, setItems] = useState<{ id: number; text: string }[]>([])
  useEffect(() => {
    let n = 0
    const on = (e: Event) => {
      const id = ++n
      setItems(x => [...x.slice(-2), { id, text: (e as CustomEvent<string>).detail }])
      setTimeout(() => setItems(x => x.filter(i => i.id !== id)), 3200)
    }
    addEventListener('ufir:toast', on); return () => removeEventListener('ufir:toast', on)
  }, [])
  return (
    <div className="toasts" aria-live="polite" role="status">
      {items.map(i => <div key={i.id} className="toast"><CheckCircle2 size={16} /> {t(i.text)}<button aria-label="Dismiss" onClick={() => setItems(x => x.filter(t => t.id !== i.id))}><X size={12} /></button></div>)}
    </div>
  )
}

/* ------------------------------ keyboard shortcuts help ------------------------------ */
export function ShortcutsHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  const t = useT()
  const ref = useRef<HTMLButtonElement>(null)
  useEffect(() => { if (open) ref.current?.focus() }, [open])
  useEffect(() => {
    if (!open) return
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    addEventListener('keydown', esc); return () => removeEventListener('keydown', esc)
  }, [open, onClose])
  if (!open) return null
  const rows: [string, string][] = [['/', 'Jump to the search box'], ['Ctrl / ⌘ + K', 'Quick find: any page or case'], ['?', 'Show this help'], ['Esc', 'Close menus and dialogs'], ['Tab', 'Move between controls (focus is always visible)']]
  return (
    <div className="scrim" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }} onKeyDown={e => { if (e.key === 'Escape') onClose() }}>
      <div className="palette helpbox" role="dialog" aria-modal="true" aria-label={t('Keyboard shortcuts')}>
        <div className="cardhead"><h2><Keyboard size={16} /> {t('Keyboard shortcuts')}</h2><button ref={ref} className="btn sm" onClick={onClose}>{t('Close')}</button></div>
        <dl className="shortcuts">{rows.map(([k, d]) => <div key={k}><dt><kbd>{k}</kbd></dt><dd>{t(d)}</dd></div>)}</dl>
      </div>
    </div>
  )
}
