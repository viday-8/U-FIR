import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { TE } from './te'

export type Lang = 'en' | 'te'
const read = (): Lang => { try { return localStorage.getItem('lang') === 'te' ? 'te' : 'en' } catch { return 'en' } }
let current: Lang = read()
export const locale = () => (current === 'te' ? 'te-IN' : 'en-IN')

/** English text is the key. Anything not in the dictionary stays in English, so the UI never shows a blank or a key. */
export function translate(lang: Lang, s: string, vars?: Record<string, string | number>): string {
  let out = lang === 'te' ? (TE[s] ?? s) : s
  if (vars) out = out.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`))
  return out
}

type Ctx = { lang: Lang; setLang: (l: Lang) => void; swapping: boolean }
const LangCtx = createContext<Ctx>({ lang: 'en', setLang: () => undefined, swapping: false })

/** Switching fades the page out, swaps every string at once, then fades back in (about 0.35s, no layout jump). */
export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setL] = useState<Lang>(current)
  const [swapping, setSwapping] = useState(false)
  const timer = useRef<number | undefined>(undefined)
  const setLang = useCallback((l: Lang) => {
    if (l === current) return
    window.clearTimeout(timer.current)
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
    setSwapping(!reduce)
    timer.current = window.setTimeout(() => {
      current = l
      try { localStorage.setItem('lang', l) } catch { /* storage unavailable */ }
      setL(l)
      window.setTimeout(() => setSwapping(false), 30)
    }, reduce ? 0 : 170)
  }, [])
  useEffect(() => { document.documentElement.lang = lang === 'te' ? 'te' : 'en' }, [lang])
  return <LangCtx.Provider value={{ lang, setLang, swapping }}>{children}</LangCtx.Provider>
}

export const useLang = () => useContext(LangCtx)
export function useT() {
  const { lang } = useContext(LangCtx)
  return useCallback((s: string, vars?: Record<string, string | number>) => translate(lang, s, vars), [lang])
}
