# u-FIR Nexus: architecture, flow, plan

Principle: the smallest thing that demos the full evidence-first journey on one case.

## 1. Hackathon concept
- **Problem:** Excise case files are messy free text. Officers hunt through documents, miss repeat offenders, and retype diaries and chargesheets.
- **Our answer:** an intelligence layer over existing records. Officers change nothing about how they write.
- **Differentiator:** AI that shows its work: citations on every claim, candidate (not forced) identity matches, human-approved drafts, audit trail.
- **Judges see:** one coherent case journey (PRD 16.3), with synthetic data clearly labelled and honest limits stated (risk undefined, no invented metrics).

## 2. Architecture
```
React (Vite)  ──HTTP/JSON──►  FastAPI
                                │
        ┌───────────────────────┼────────────────────────┐
   auth + can_access()     services (plain modules)    audit.log()
                                │
   ingest → extract → resolve → brief / legal / draft / copilot
                                │
     SQLAlchemy → SQLite (demo) | Postgres (pilot)     files/ (original docs, read-only)
                                │
               LLM API: Claude or OpenAI (one module, env-selected)
```
- **Ingest:** upload text/PDF (OCR only if time permits) → save file + checksum → parse text per page → run extraction in a FastAPI background task. Status per doc: `received → extracted → indexed → needs_review | failed`.
- **Extract:** default is `rules` (`services/rules.py`: open-source regex, offline, deterministic; handles `Name, S/o Father`, vehicles, quantities, dates, sections, places). Set `EXTRACTOR=llm` for the optional LLM path, which returns JSON (persons, aliases, places, vehicles, items+qty, dates, legal sections) with `page` + quoted `span`. Validated by pydantic; invalid → retry once → `needs_review`. Verify that each span string actually appears in the page text; otherwise drop the fact or flag it.
- **Database:** SQLAlchemy models with portable types, selected by `DATABASE_URL` (`sqlite:///...` for demo, `postgresql://...` for pilot). Tables are created by `create_all` for the demo; add Alembic only when the Postgres pilot needs migrations.
- **Search** (`services/search.py`, the single dialect-aware module): one interface `search(query, scope)` with two backends. SQLite: FTS5 text search. Postgres: `tsvector` + GIN index, and `pg_trgm` for fuzzy names. Name normalisation (lowercase, strip honorifics, small transliteration map) and `rapidfuzz` scoring happen in Python on both, so entity matching behaves identically. Access scope is applied before ranking and snippets.
- **Resolve identities:** score = name similarity + shared father name/village/vehicle/phone. Below a threshold: no link. Above: `candidate` with reasons. Only a reviewer sets `confirmed`/`rejected`. Common name alone never links.
- **Relationships:** a plain `relationship` table (entity A, entity B, type, evidence fact ids, status). Graph view reads from it (cytoscape.js), plus a table view for accessibility.
- **Brief / timeline:** the brief is assembled by `services/brief.py` from extracted facts (template, no LLM), so every statement carries fact ids by construction and wording stays "recorded/named". It also reports conflicts (differing age/father/residence, registration date vs FIR date) and missing information. An optional LLM rewrite must keep the same citations. Timeline is built from dated facts.
- **Legal:** a local JSON catalogue of sections (from the organisers or a clearly marked demo list) with act name, text, and version. Retrieve candidates by keyword/embedding-free matching, then the LLM picks and justifies using case facts. Output is limited to catalogue IDs. Status `suggested → accepted/rejected/insufficient`.
- **Drafts:** template (markdown) + case facts → LLM fills sections, each tagged with source fact IDs. Status `draft → in_review → approved/returned`. Only the `supervisor` role can approve.
- **Copilot:** retrieve (access-filtered FTS) → answer with citations → "not found in available records" if retrieval is empty or weak.
- **Hotspots (P1):** group by district/station/place with counts; table + simple map where lat/lng exists; show how many records lack location.
- **Risk:** a static "not configured" panel. Nothing else.

### Data tables (minimum)
`user(role,district)` · `case` · `document(case_id,path,checksum,status)` · `page(doc_id,n,text)` · `fact(case_id,type,original,normalised,doc_id,page,span,confidence,model)` · `entity` · `mention(entity_id,fact_id)` · `relationship` · `legal_ref` · `legal_suggestion` · `draft(version,status)` · `review(type,target,decision,by,reason,at)` · `audit(actor,action,resource,model,evidence_ids,outcome,at)`

### API (only what the UI needs)
`POST /auth/login` · `POST /ingest` · `GET /ingest/{id}` · `GET /cases` · `GET /cases/{id}` · `GET /cases/{id}/brief` · `GET /search` · `GET /entities/{id}/candidates` · `GET /relationships` · `POST /legal/suggest` · `POST /drafts` · `POST /drafts/{id}/review` · `POST /copilot` · `GET/POST /reviews` · `GET /audit` · `GET /hotspots`
FastAPI generates the OpenAPI docs, which covers the API documentation requirement for free.

### Repo layout
```
backend/  app/{main,auth,access,db,models,audit}.py  app/services/{ingest,extract,search,resolve,brief,legal,draft,copilot,hotspots}.py  tests/
frontend/ src/pages/{Command,Cases,CaseCockpit,Search,Relationships,Hotspots,Studio,Copilot,Reviews,Audit}.tsx  src/components/
data/     legal_catalogue.json   (synthetic cases + users live in backend/app/seed.py)
docs/
```

## 3. Application flow
1. **Login** as a demo role → role + district decide everything visible.
2. **Command Center:** processing status, needs-attention list, DEMO banner.
3. **Ingest** synthetic files → facts extracted with spans → bad or conflicting items go to the **Review Queue**.
4. **Search** (e.g. a spelling variant of a name) → results with highlighted snippets and "why matched".
5. **Case Cockpit:** cited brief + timeline + evidence viewer; click a sentence → source passage highlighted.
6. **Relationships:** candidate match shown with reasons → reviewer confirms/rejects → graph and linked cases update.
7. **Legal suggestions** with cited facts → accept/reject.
8. **Document Studio:** generate a diary/chargesheet draft → edit → request review → supervisor approves/returns.
9. **Copilot:** ask a question → cited answer or "not found".
10. **Audit Ledger:** show the trail for steps 5–9. **Risk panel:** "not configured".

## 4. Build order (each step demoable)
1. Seed data (2 districts, ~15 synthetic cases, 1 hero case with a spelling-variant repeat offender, and a prompt-injection doc) + DB + auth + `can_access`.
2. Ingest + extraction + FTS search.
3. Case Cockpit with brief, timeline, evidence viewer.
4. Identity resolution + relationship view + review actions.
5. Legal suggestions + Document Studio.
6. Copilot + audit ledger.
7. Command Center, hotspots (table first), risk placeholder, accessibility pass, README + demo script.
8. Postgres pass (after the demo works): add the Postgres search backend, run the full test suite against both DBs, add the compose file and README steps.
Cut from the bottom, not the middle, if time runs short.

## 5. Tests that matter (from PRD section 14, trimmed)
Pytest: restricted case → 404 via API/search/Copilot · missing field → null · two same-name people not linked · legal suggestion limited to catalogue IDs · unauthorised approve blocked · prompt-injection doc ignored · Copilot abstains when nothing is found · audit row written. Manual: keyboard-only walk through search → brief → evidence → draft.

## 6. Documentation to produce
- `README.md`: setup, run, demo accounts, env vars.
- `docs/ARCHITECTURE.md` (this file) + Decisions below.
- `docs/DEMO_SCRIPT.md`: 7–9 min narrative (PRD 16.3), one hero case.
- OpenAPI (auto) + `docs/LIMITATIONS.md`: open questions (risk undefined, languages, legal source, integration) and measured quality on the synthetic sample with sample size and method.

## 7. Decisions (append as we go)
- Copilot is retrieval-first and works with no API key: access-scoped FTS retrieval -> verbatim cited quotes, structured lookups for vehicles and names, and a case-scoped "what is missing / conflicts" answer. Proper nouns in a question must appear in a case for it to answer (so "Where was Munaswamy found?" cannot be answered by unrelated records that say "found"). No evidence -> "Not found in the records available to you." Restricted or missing case scope returns the same 404. Optional LLM wording (`COPILOT_LLM=1`) only sees already-retrieved, delimited lines and is discarded unless it cites retrieved numbers. Audit rows hold document refs and the outcome, not the question text.
- Seed data: 12 synthetic cases across 3 districts modelled on common Excise offence patterns (border transport of ID liquor/NDPL, jaggery-wash manufacture, ganja transport, decoy operations), with varied station formats, date styles, aliases and spelling variants. All people, case numbers and vehicle numbers are fictional; no real accused persons or real records are used, per the PRD's synthetic-data rule. Real records can be loaded through the same ingest path once the department approves.
- Legal catalogue (`app/data/legal_catalogue.json`) is a small DEMO list, labelled unverified in the API and UI. Only the AP Excise Act 1968 s34(a) as a commonly charged provision, and the existence of s46 vehicle proceedings, were corroborated from public court orders; descriptions are paraphrases with no penalties. Matching is rule-based (item facts + activity words), cites verbatim passages, abstains (`insufficient`) when no activity is found, and re-runs never overwrite a human decision.
- Document Studio: drafts are template-assembled from facts and accepted legal suggestions. Required sections left as visible placeholders block submission. The chargesheet lists "persons named" and tells the officer to decide who is charged; it never labels anyone accused. Approval needs a supervisor/admin who is not the author; blocked attempts are audited. Export is allowed at any status but carries a DRAFT banner until approved.
- Frontend: hash-routed pages (dashboard, cases, cockpit, search, relationships, studio, audit), lucide-react icons, plain CSS design tokens with dark mode. Role from login hides unavailable actions; the server still enforces every rule.
- Identity resolution (`services/resolve.py`): one Entity per (case, normalised name); witnesses excluded. A Candidate needs name similarity >= 80 AND a person-level match (father/spouse or residence); vehicles are case-level so they only add weight. Score 0-100, shown >= 50, "likely" >= 75. Nothing is auto-confirmed; reviews need a reason, are scoped to cases the reviewer can see, are audited and survive recomputation. Pairwise comparison is O(n^2): fine for the demo, add blocking (by name prefix/phonetic key) before the pilot. Weights are hand-set, not learned; validate on labelled pairs before quoting precision.
- Relationship graph is built per request from scoped data (person, case, vehicle nodes). Edges are `direct` (recorded), `candidate` (dashed) or `confirmed`; each carries evidence fact ids. A table view mirrors the graph for accessibility.
- Brief is template-based first: deterministic, always cited, works offline. Prose quality is plainer than an LLM; acceptable for the demo.
- Frontend: Vite + React + TS, plain CSS, no UI/router/state libraries; `/api` proxied to the backend.
- Extraction defaults to rules, not an LLM: the records are semi-structured, rules cannot hallucinate, and every quote is verbatim. The LLM extractor stays opt-in for free-form text. **Limitation:** the rules were written against the synthetic seed, so seed accuracy is optimistic; measure on a held-out labelled set before quoting any number. Telugu and handwritten text are not covered.
- SQLite (FTS5) for the demo: zero setup. Postgres (tsvector, pg_trgm) is the pilot target. Same models via SQLAlchemy, search is the only divergent code. No Elastic, vector DB or Mongo.
- Postgres row-level security is deferred; access control lives in the app layer so both DBs behave the same. Revisit for the pilot.
- A `docker-compose.yml` with Postgres is added only at the pilot step, not for the demo.
- In-process background tasks instead of a queue.
- Graph stored as relational edges; no graph DB.
- Synthetic data only; the hosted LLM provider is acceptable because no real records are used.
- LLM: hosted Claude or OpenAI API, selected by `LLM_PROVIDER`; all calls go through `services/llm.py`. Everything else uses open-source libraries (FastAPI, SQLAlchemy, pypdf, rapidfuzz, cytoscape.js, React). The `openai` client can target a local Ollama via `OPENAI_BASE_URL`, so a self-hosted open model is a config change for the pilot.
- English first; Telugu/transliteration is limited to a small name-variant map, and the limitation is stated.
- No CCTNS integration; ingestion reads files.
