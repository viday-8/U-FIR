let token = ''
let role = ''
let district = ''
let username = ''
try { token = sessionStorage.getItem('token') ?? ''; role = sessionStorage.getItem('role') ?? ''; district = sessionStorage.getItem('district') ?? ''; username = sessionStorage.getItem('username') ?? '' } catch { /* storage unavailable */ }

export function setSession(t: string, r = '', d = '', u = '') {
  token = t; role = r; district = d; username = u
  try {
    if (t) { sessionStorage.setItem('token', t); sessionStorage.setItem('role', r); sessionStorage.setItem('district', d); sessionStorage.setItem('username', u) }
    else { sessionStorage.removeItem('token'); sessionStorage.removeItem('role'); sessionStorage.removeItem('district'); sessionStorage.removeItem('username') }
  } catch { /* ignore */ }
}
export const hasToken = () => !!token
export const getRole = () => role
export const getUsername = () => username || role
export const getDistrict = () => district || null

const QUIET = /^\/(auth|search|copilot|intake|ingest)/
function toastFor(path: string): string {
  if (/review|mark-reviewed|legal\/\d+\/review/.test(path)) return 'Decision recorded'
  if (/tags/.test(path)) return 'Tags saved'
  if (/milestones|chargesheet-deadline/.test(path)) return 'Deadline saved'
  if (/drafts/.test(path)) return 'Draft updated'
  if (/accused|property|checklist/.test(path)) return 'Saved'
  return 'Saved'
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch('/api/v1' + path, {
    ...init,
    headers: { ...(init?.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}), Authorization: `Bearer ${token}` },
  })
  if (res.status === 401 && token) { setSession(''); location.hash = ''; location.reload() }
  if (!res.ok) {
    let detail = ''
    try { detail = (await res.json()).detail } catch { /* no body */ }
    throw new Error(res.status === 404 ? 'Not found' : res.status === 403 ? (detail || 'You are not permitted to do this') : detail || `Request failed (${res.status})`)
  }
  if (init?.method && init.method !== 'GET' && !QUIET.test(path)) window.dispatchEvent(new CustomEvent('ufir:toast', { detail: toastFor(path) }))  // a quiet confirmation for every saved change
  return (res.headers.get('content-type') ?? '').includes('json') ? res.json() : (res.text() as unknown as T)
}

export type Case = { id: number; case_no: string; district: string; station: string; status: string; registered_on: string; documents: number }
export type Statement = { text: string; fact_ids: number[] }
export type Brief = {
  case_no: string; station: string; district: string; registered_on: string; notice: string; generated_by: string
  records_reviewed: { documents: number; list: { id: number; type: string; status: string; language: string; ocr: boolean }[] }
  sections: { title: string; statements: Statement[] }[]
  conflicts: Statement[]; missing: string[]
}
export type Fact = { id: number; type: string; original: string; document_id: number; page: number; span: string; corrected?: boolean; model?: string }
export type TimelineEvent = { date: string | null; date_text: string; uncertain: boolean; document_id: number; doc_type: string; page: number; fact_id: number; context: string }
export type Doc = { id: number; case_no: string; doc_type: string; status: string; language: string; reviewed_by?: string | null; review_note?: string | null; has_ocr: boolean; pages: { number: number; text: string; ocr: boolean }[] }
export type Signal = { kind: string; supports: boolean; text: string }
export type EvidenceFact = { fact_id: number; case_id: number; document_id: number; page: number; doc_type: string; type: string; original: string; span: string }
export type Side = { entity_id: number; name: string; case_id: number; case_no: string; attributes: Record<string, string> }
export type Candidate = {
  id: number; status: 'unreviewed' | 'confirmed' | 'rejected' | 'deferred'; score: number; strength: 'likely' | 'possible'
  a: Side; b: Side; signals: Signal[]; missing: string[]; evidence: EvidenceFact[]; decided_by: string | null; reason: string | null
}
export type GNode = {
  id: string; kind: 'person' | 'case' | 'vehicle'; label: string; degree: number; cluster_id?: string; case_id?: number; case_no?: string
  station?: string; district?: string; registered_on?: string; offence?: string[]; documents?: number
  age?: string | null; father_or_spouse?: string | null; relation?: string | null; resident?: string | null; alias?: string | null; cases?: number
}
export type GEdge = { id: string; candidate_id?: number; source: string; target: string; type: string; status: 'direct' | 'candidate' | 'confirmed'; evidence: number[]; explanation: string; score?: number; strength?: string }
export type Cluster = { id: string; label: string; names: string[]; node_ids: string[]; case_ids: number[]; case_nos: string[]; shared_vehicles: string[]; min_score: number; max_score: number; status: 'confirmed' | 'needs_review'; candidate_ids: number[] }
export type Graph = { scope: { total_nodes: number; shown_nodes: number; linked_only: boolean; focus: string | null; truncated: boolean }; nodes: GNode[]; edges: GEdge[]; clusters: Cluster[]; stats: { cases: number; people: number; vehicles: number; links: number; clusters: number }; notice: string }
export type Legal = {
  id: number; ref_id: string; act: string; section: string; title: string; summary: string
  status: 'suggested' | 'insufficient' | 'accepted' | 'rejected'; rationale: string; fact_ids: number[]
  passages: { document_id: number; page: number; span: string }[]; already_cited: boolean; verified: boolean
  decided_by: string | null; reason: string | null; label: string
}
export type LegalResp = { notice: string; suggestions: Legal[] }
export type Section = { key: string; title: string; text: string; fact_ids: number[]; required: boolean; source: 'system' | 'officer' }
export type DraftSummary = { id: number; case_id: number; case_no?: string; doc_type: string; title: string; status: 'draft' | 'in_review' | 'approved' | 'returned'; version: number; author: string; reviewer: string | null; updated_at: string }
export type DraftFull = DraftSummary & {
  sections: Section[]; unfilled: string[]; banner: string
  comments: { by: string; decision: string; text: string; at: string }[]
  versions: { version: number; author: string; note: string; at: string }[]
}
export type Stage = { steps: { name: string; state: 'done' | 'current' | 'todo'; hint: string }[]; note: string }
export type Dashboard = {
  user: { username: string; role: string; district: string | null }
  filters: { district: string | null; station: string | null; from_month: string | null; to_month: string | null }
  options: { districts: string[]; stations: string[]; months: string[] }
  counts: { cases: number; documents: number; facts: number; identity_to_review: number; legal_to_review: number; drafts_in_review: number }
  deadlines: { overdue: number; soon: number; items: Milestone[] }
  pipeline: Record<string, number>; cases_by_station: Record<string, number>; cases_by_month: Record<string, number>
  attention: { kind: string; label: string; case_id?: number; candidate_id?: number; draft_id?: number }[]
  recent_activity: { at: string; actor: string; action: string; resource: string; outcome: string | null }[]
}
export type SearchResult = {
  query: string
  case_hits: { id: number; case_no: string; station: string; district: string; registered_on: string; matched: string[]; offence: string[]; accused: string[]; vehicles: string[] }[]
  text_hits: { case_id: number; case_no: string; document_id: number; page: number; snippet: string; why: string }[]
  name_matches: { case_id: number; case_no: string; name: string; document_id: number; page: number; span: string; score: number; why: string }[]
}
export type AuditRow = { at: string; actor: string; action: string; resource: string; model: string | null; outcome: string | null }

export type Citation = { n: number; case_id: number; case_no: string; document_id: number; doc_type: string; page: number; span: string }
export type CopilotResp = { found: boolean; answer: string; details?: string[]; mode: string; citations: Citation[]; notice: string }

export type Hotspots = {
  kind: string; heatmap: { months: string[]; rows: { station: string; counts: number[]; total: number }[] }
  places: { name: string; cases: number; case_ids: number[]; case_nos: string[] }[]
  stations: { name: string; cases: number; case_ids: number[] }[]; months: Record<string, number>
  coverage: { cases_with_place: number; cases_total: number; note: string }; method: string; caveat: string
}
export type ReviewItem = { type: 'extraction' | 'identity' | 'legal' | 'draft'; status: string; label: string; reason: string; case_id: number; document_id?: number; href: string; who: string }
export type Governance = {
  mode: string
  system: { extractor: string; llm_provider: string; llm_model: string; copilot_llm: boolean; database: string; legal_catalogue: { version: string; verified: boolean } }
  risk: { configured: boolean; status: string; reason: string }
  evaluation: {
    extractor: string; documents: number; gold_facts: number; overall: { precision: number; recall: number }
    by_type: { type: string; tp: number; fp: number; fn: number; precision: number | null; recall: number | null }[]
    missed: { doc: string; type: string; expected: string }[]; spurious: { doc: string; type: string; extracted: string }[]; limits: string[]
  }
  users: { username: string; role: string; district: string; active: boolean }[] | null
  data_quality: { documents: number; needs_review: number; failed: number; ocr_documents: number; languages: Record<string, number>; facts_by_type: Record<string, number>; facts_corrected_by_officers: number; correction_events: number }
}
export type Correction = { fact_id: number; action: string; type: string; old: string | null; new: string | null; by: string; reason: string; at: string }
export type IntakeResult = {
  filename: string; size: number; ok: boolean; error?: string; doc_type?: string | null; case_ref?: string | null; registered_on?: string | null
  matches?: { id: number; case_no: string; station: string }[]; matched_case_id?: number | null
  duplicate_of?: { document_id: number; case_id: number; case_no: string } | null; ocr?: boolean; language?: string
}
export type CaseMeta = {
  offence: string[]; offence_detail: { tag: string; reasons: string[]; source: 'auto' | 'officer' }[]; offence_source: 'auto' | 'officer'; accused: { name: string; alias?: string; age?: string; resident?: string; father_or_spouse?: string }[]; witnesses: string[]
  vehicles: string[]; items: string[]; quantities: string[]; places: string[]; sections: string[]; documents: Record<string, number>
  date_first: string | null; date_last: string | null; flags: { needs_review: boolean; ocr: boolean; telugu: boolean }; keywords: string[]
}
export type CaseRow = Case & { meta: CaseMeta; matched: string[] }
export type Overview = { items: CaseRow[]; facets: { offence: Record<string, number>; station: Record<string, number>; district: Record<string, number>; status: Record<string, number> }; total: number }
export type Suggestion = { kind: string; text: string }
export type CaseNetwork = {
  case_id: number
  people: { entity_id: number; name: string; age: string | null; father_or_spouse: string | null; resident: string | null
    links: { candidate_id: number; status: string; score: number; strength: string; other: { entity_id: number; name: string; case_id: number; case_no: string }; top_signals: string[] }[] }[]
  shared_vehicles: { vehicle: string; cases: { id: number; case_no: string }[] }[]
  related_cases: { id: number; case_no: string; why: string[] }[]
  summary: { people: number; possible_matches: number; shared_vehicles: number; related_cases: number }
}
export type Accused = { id: number; case_id: number; name: string; father_or_spouse: string | null; age: string | null; status: 'named' | 'arrested' | 'remanded' | 'bailed' | 'absconding'; arrested_on: string | null; remand_till: string | null; bail_on: string | null }
export type Property = { id: number; case_id: number; kind: 'liquor' | 'ganja' | 'vehicle' | 'other'; description: string; quantity: string | null; custody: string; status: string; sample_sent_on: string | null; lab_report_on: string | null }
export type Milestone = { id: number; case_id: number; case_no: string; kind: string; title: string; due_on: string; done: boolean; state: 'overdue' | 'soon' | 'later' | 'done'; days: number }
export type Deadlines = { today: string; items: Milestone[]; counts: { overdue: number; soon: number } }
export type Checklist = { items: { key: string; label: string; done: boolean; manual: boolean; by: string | null }[]; notice: string }
