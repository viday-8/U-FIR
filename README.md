# u-FIR Nexus (hackathon prototype, synthetic data only)

Spec: `u-FIR_Nexus_Product_Requirements_Document.md` · Rules for contributors: `CLAUDE.md` · Design: `docs/ARCHITECTURE.md`

## Run (demo, SQLite)
```bash
./run_demo.sh          # builds the UI, seeds synthetic data, serves everything on http://localhost:8000
```
Or manually: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then `.venv/bin/python -m app.seed && .venv/bin/python -m app.process && .venv/bin/uvicorn app.main:app --port 8000`; for UI development run `cd frontend && npm install && npm run dev` (http://localhost:5173, proxies `/api`).
API docs (OpenAPI): http://localhost:8000/docs · Tests: `cd backend && .venv/bin/python -m pytest -q`

Docs: [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) · [docs/LIMITATIONS.md](docs/LIMITATIONS.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Demo accounts (password `demo123`)
`inv_vizag`, `sup_vizag`, `analyst_vizag` (Visakhapatnam) · `inv_guntur`, `sup_guntur` (Guntur) · `inv_chittoor` (Chittoor) · `admin` (all districts)

## Config (`.env.example`)
`DATABASE_URL` (SQLite default; Postgres later) · `EXTRACTOR=rules|llm` · `LLM_PROVIDER=anthropic|openai` + API key (only needed for LLM features)

## Status
All PRD P0 capabilities and the P1 items below are built and tested (67 backend tests; the demo journey, OCR upload, fact correction and admin were also driven end to end in a browser; 0 axe-core WCAG A/AA violations across 12 pages):
auth + district scoping, ingest, rule-based extraction, spelling-variant search, Case Cockpit (cited brief, timeline, evidence viewer), identity candidates + Relationship Explorer with review, legal suggestions (demo catalogue), Document Studio (versions, supervisor approval, export), role-aware Copilot, Review Queue, Hotspot Explorer, Command Center, Audit Ledger, Quality & Governance (held-out extraction scores, risk "not configured").
Also built: review resolution (mark reviewed with a note, retry) for flagged documents, dashboard filters, OCR for scanned PDFs/images, fact correction with history, search filters, admin user management, data-quality view, login rate limiting + security headers.
Not done: Postgres search backend (planned for the pilot), Telugu extraction (detected and flagged only), integrations. See SUBMISSION.md and docs/LIMITATIONS.md.
