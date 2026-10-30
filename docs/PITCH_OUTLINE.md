# Pitch outline (10 slides · ~7 min) and 3-minute video script

Use the screenshots in `docs/screenshots/`. Say only what the product demonstrably does. Where we lack a number, say so: that is a strength with this jury (the brief itself leaves “risk” undefined).

## Slides
| # | Title | Content | Evidence |
|---|---|---|---|
| 1 | U-FIR ANVESHANA | One line: *every insight has evidence, every AI action is reviewable, the officer stays in control.* Team, challenge name, “prototype on synthetic data”. | |
| 2 | The problem | Free-text records in many station formats; manual search; repeat offenders hidden by spelling variants; diaries and chargesheets retyped. Officers must not change how they write. | brief |
| 3 | Our approach | Intelligence layer over existing records: record → facts → cited brief → explainable links → reviewed draft → audit. | flow diagram |
| 4 | Case Cockpit | Cited brief; click any line, the exact source sentence highlights; conflicts and missing information shown, not hidden. | screenshot 02 |
| 5 | Repeat offenders without false merges | Search “Rameshbabu” finds every spelling and shows why each case matched; the Investigation Network groups repeat names into clusters and, after an upload, shows exactly what the new documents connect to; candidate links show evidence for and against; two “Lakshmi Devi” records are provably not linked; a human confirms with a reason. | screenshots 04, 05, 12, 13 |
| 6 | Law and paperwork | Catalogue-limited legal suggestions that cite facts and abstain when unsure (demo catalogue, unverified, stated on screen); chargesheet and diary drafts with placeholders that block submission and supervisor-only approval. | screenshots 03, 07 |
| 7 | Role-aware Copilot | Answers only from records the user may access; cited quotes or “not found”; prompt injection in a document is treated as data. | screenshot 06 |
| 8 | Trust, security, accessibility | One access rule (role + district), same 404 for restricted and missing, audit ledger, rate limiting, CSP; 0 axe-core WCAG A/AA violations across 12 pages, light and dark. | screenshots 08, 11 |
| 9 | Honest quality | Held-out extraction test: precision ≈ 84%, recall ≈ 84% on 6 synthetic documents, with person recall 56% shown openly; OCR and Telugu always sent to human review; risk model “Not configured” until the department defines risk. | screenshot 10 |
| 10 | Pilot path and asks | 3 districts, 5–10 users, 60 days. Ready now: roles, review workflows, audit, API. Needed: risk definition, legal source, data sample, hosting policy, identity provider. Planned: Postgres, real-scan OCR validation, Telugu extraction, integration adapter. | LIMITATIONS.md |

## Judging criteria cheat-sheet
- **Innovation / AI:** evidence-first outputs, identity resolution with explicit uncertainty, retrieval-first Copilot with abstention.
- **Accuracy / reliability:** held-out test with misses published, citation on every statement, human review queue, audit.
- **Usability / accessibility:** one-click evidence, plain wording, keyboard and skip link, axe scan 0 violations (supporting evidence, not a full audit).
- **Scalability / deployment:** modular services, API with OpenAPI, SQLite demo → Postgres pilot, Docker files (not yet built), open-source stack.
- **Impact:** do not quote a time-saved number; we have not measured one. Say what is automated (search, brief, drafting scaffolds) and propose measuring it in the pilot against a baseline.
- **Privacy / security:** least privilege, same-404, no real data, audit holds references only.

## 3-minute video script
| Time | On screen | Voice-over |
|---|---|---|
| 0:00 | Command Center | “Excise officers work from free-text files. U-FIR ANVESHANA reads them as written and gives every insight its evidence.” |
| 0:25 | Case brief → click a line | “Every line links to the exact sentence in the original FIR. Conflicts and gaps are shown, not hidden.” |
| 0:55 | Search → Relationships | “One search finds every spelling. The system proposes a repeat-offender link, shows evidence for and against, and a person decides. Different people with the same name are never merged.” |
| 1:30 | Legal → Draft → approval | “Legal suggestions cite the facts and abstain when unsure. Drafts can’t be mistaken for official records until a supervisor approves.” |
| 2:05 | Copilot | “Ask in plain words. Answers come only from records you may access, with citations, or an honest ‘not found’.” |
| 2:30 | Governance | “We publish our own error rates, including the misses, and we do not invent a risk score the brief never defined.” |
| 2:50 | Title | “U-FIR ANVESHANA: evidence-first AI the officer controls.” |
