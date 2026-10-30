import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useT } from './i18n'

export type Quote = { text: string; script?: string; source: string; note?: string }
/** Only quotations that can be sourced. The Peel line is labelled "attributed" because its exact authorship is debated. */
export const QUOTES: Quote[] = [
  { script: 'सत्यमेव जयते · సత్యమేవ జయతే', text: 'Truth alone triumphs.', source: 'Mundaka Upanishad (3.1.6)' },
  { text: '…JUSTICE, social, economic and political; LIBERTY of thought, expression, belief, faith and worship; EQUALITY of status and of opportunity…', source: 'Preamble to the Constitution of India' },
  { script: 'यतो धर्मस्ततो जयः', text: 'Where there is righteousness, there is victory.', source: 'Motto of the Supreme Court of India' },
  { text: 'The police are the public and the public are the police.', source: 'Sir Robert Peel’s principles of policing', note: 'attributed' },
  { text: 'Every insight has evidence. The officer decides; the system assists.', source: 'U-FIR ANVESHANA working principle' },
]

const dayIndex = () => Math.floor(Date.now() / 86400000) % QUOTES.length

export function QuoteBlock({ q, quiet }: { q: Quote; quiet?: boolean }) {
  const t = useT()
  return (
    <figure className={'quote' + (quiet ? ' quiet' : '')}>
      {q.script && <p className="qscript" lang="sa">{q.script}</p>}
      <blockquote><p>“{t(q.text)}”</p></blockquote>
      <figcaption>{t(q.source)}{q.note && <em> ({t(q.note)})</em>}</figcaption>
    </figure>
  )
}

/** Slow, pausable rotation for the sign-in page. Pauses on hover/focus and never moves for reduced-motion users. */
export function QuoteRotator() {
  const t = useT()
  const [i, setI] = useState(dayIndex())
  const [paused, setPaused] = useState(false)
  useEffect(() => {
    if (paused || matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const t = setInterval(() => setI(x => (x + 1) % QUOTES.length), 9000)
    return () => clearInterval(t)
  }, [paused])
  return (
    <div className="rotator" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <div key={i} className="fade"><QuoteBlock q={QUOTES[i]} /></div>
      <div className="qnav">
        <button aria-label={t('Previous quotation')} onClick={() => setI((i + QUOTES.length - 1) % QUOTES.length)}><ChevronLeft size={14} /></button>
        {QUOTES.map((_, k) => <button key={k} className={'qdot' + (k === i ? ' on' : '')} aria-label={`Quotation ${k + 1} of ${QUOTES.length}`} aria-current={k === i} onClick={() => setI(k)} />)}
        <button aria-label={t('Next quotation')} onClick={() => setI((i + 1) % QUOTES.length)}><ChevronRight size={14} /></button>
      </div>
    </div>
  )
}

/** One quotation per day, shown quietly on the dashboard. */
export function QuoteOfTheDay() {
  const t = useT()
  return <section className="qotd" aria-label={t('Thought for the day')}><span className="qlabel">{t('Thought for the day')}</span><QuoteBlock q={QUOTES[dayIndex()]} quiet /></section>
}
