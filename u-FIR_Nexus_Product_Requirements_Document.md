# u-FIR Nexus
## Product Requirements Document (PRD)

**Product type:** AI-enabled case intelligence and documentation platform  
**Challenge:** AI-Enabled Unified First Information Report (u-FIR)  
**Problem owner:** Andhra Pradesh Prohibition & Excise Department  
**Document version:** 1.0  
**Date:** 29 October 2026  
**Status:** Proposed product specification for hackathon prototype and 60-day pilot  
**Working product name:** **u-FIR Nexus — Unified Case Intelligence Workspace**

> **Source discipline:** “Official requirement” means the requirement is explicitly present in the supplied u-FIR hackathon problem statement. “Proposed enhancement” means a product recommendation intended to improve usefulness, differentiation, safety or demo quality. Organiser decisions are required where the brief leaves a matter undefined. This PRD does not imply access to real police records, operational deployment approval, or validated model performance.

---

## 1. Executive Summary

u-FIR Nexus is an evidence-first case intelligence workspace for authorised Prohibition & Excise officers. It transforms existing unstructured case records into searchable, structured information; gives officers a concise and traceable understanding of a case; suggests potentially relevant legal provisions; identifies candidate repeat-offender and network links; supports case diary and chargesheet drafting; visualises data-supported hotspots; and answers questions using records permitted for the user's role.

The product is designed around a key constraint in the official challenge: **officers must not need to change how they currently write records**. The platform works as an intelligence layer over legacy documents and preserves every source. AI-generated claims must link back to evidence, uncertain identity matches must remain reviewable, and legally consequential outputs must remain suggestions for an authorised human to review.

### Product thesis

Most prototypes can show a chatbot or a dashboard. u-FIR Nexus should demonstrate a complete, trustworthy workflow: **legacy record → extracted facts → evidence-backed case brief → explainable links → reviewed draft → audit trail**. The differentiator is not “AI everywhere”; it is **AI that can show its work**.

### Hackathon coverage

The PRD covers all five stated capabilities (structured/searchable records, fast case understanding, legal-section suggestions, repeat-offender/network detection and paperwork reduction), all five target outcomes (digitisation, automated diary/chargesheet drafting, links, hotspots and role-based chatbot), the existing-record constraint, variation in names and station formats, API/dashboard delivery, reviewable AI decisions, and the 3-district / 5–10-user / 60-day pilot. It also plans for the stated evaluation categories: usability/accessibility, impact, relevance, technical feasibility, innovation, data/integration and presentation quality.

### Critical dependency

The source brief sets a pilot threshold of **more than 90% accuracy in predicting risk**, but does not define the risk target, time horizon, ground truth or metric. The team must obtain written clarification before training, evaluating or claiming performance for this feature. The system must not label a person as a criminal or make automated enforcement decisions based on an undefined score.

---

## 2. Source of Truth and Scope Boundaries

### 2.1 Official challenge facts

| Item | Value in supplied problem statement |
|---|---|
| Challenge | AI-Enabled Unified First Information Report (u-FIR) |
| Problem owner | Andhra Pradesh Prohibition & Excise Department |
| Platform | AI Living Labs Foundation, Government of Andhra Pradesh; managed by EY |
| Hackathon ID | HCK_8E2E98DE568DB1A4 |
| Application deadline | 30 October 2026, 4:53 PM IST |
| Shortlist announcement | 3 November 2026, 4:53 PM IST |
| Presentation/demo | 13 November 2026, 4:53 PM IST |
| Winners announced | 16 November 2026, 4:53 PM IST |
| Shortlist threshold | Score of 70 |
| Pilot parameters | 3 selected Excise districts; about 5–10 department users; 60 days |
| Pilot success wording | More than 90% accuracy in predicting risk; “risk” is not defined |
| Output interface | API or dashboard |
| Source dataset | Five years of crime case records, including detected violations, decoy operation results and repeat-offender history |

Treat these dates and details as copied from the supplied source document. Confirm updates and application-specific requirements with the organisers.

### 2.2 Official capabilities mapped to product modules

| Source ID | Official capability | Product modules that satisfy it |
|---|---|---|
| C1 | Convert messy case files into searchable, usable data | Intake & Processing; Structured Facts; Unified Search; Data Quality Queue |
| C2 | Help officers understand a case quickly | Case Cockpit; Case Brief; Timeline; Evidence Viewer |
| C3 | Suggest relevant laws and legal sections | Legal Intelligence Workspace; Approved Legal Library; Review Queue |
| C4 | Detect repeat offenders and networks by connecting people, places, vehicles and other details | Identity Resolution; Relationship Explorer; Network Evidence Panel |
| C5 | Reduce paperwork | Document Studio; Templates; Draft Review & Approval |
| O1 | Convert case records to digital, structured data | Intake pipeline; extraction; searchable index |
| O2 | Generate case diaries and chargesheets automatically | Document Studio with human review |
| O3 | Automatically detect links between suspects and networks | Candidate matching; graph and link review |
| O4 | Identify crime hotspots | Geospatial Analytics and Hotspot Explorer |
| O5 | Provide a role-aware chatbot | u-FIR Copilot with role-filtered retrieval |

### 2.3 Must-preserve constraints

1. Process existing records without requiring authors to change their writing style or templates.
2. Preserve the original source documents and make extracted facts traceable to them.
3. Make results available through a dashboard and/or API.
4. Log AI-assisted decisions and make them reviewable.
5. Support spelling variation and station-to-station format variation.
6. Do not represent proposed technical design as confirmed department policy.

### 2.4 Explicit versus inferred scope

The official brief explicitly names the capabilities and outcomes above. Telugu/English and transliteration support, OCR for scans, particular legal acts, human-in-the-loop review, jurisdictional access controls, explainable scores, and measured precision/recall are sensible interpretations or enhancements to validate with organisers. They are included in this PRD as recommendations, not claimed to be verbatim official requirements.

---

## 3. Vision, Positioning and Differentiation

### 3.1 Vision

Give an authorised officer a reliable, traceable understanding of relevant case records in one workspace, while reducing repetitive paperwork and preserving human accountability.

### 3.2 Product promise

**“Every insight has evidence. Every AI action is reviewable. The officer stays in control.”**

### 3.3 Differentiators intended to make the product stand out

1. **Evidence-first AI:** a material statement in a summary, answer, legal suggestion or draft has a source citation or is explicitly marked as unsupported/unknown.
2. **One-minute Case Brief (aspirational UX concept, not a performance claim):** a compact overview of allegations recorded, key entities, known events, seized items, legal references, missing information and conflicts, with clickable evidence.
3. **Identity resolution without reckless merging:** the system proposes possible matches and explains reasons; ambiguous identities are kept separate until reviewed.
4. **Relationship Explorer with proof on every edge:** users can click a link to see the source records and whether it is extracted, inferred, verified or awaiting review.
5. **Draft-to-approval workflow:** generated case diary/chargesheet content is editable and marked as a draft until an authorised person reviews it.
6. **Role-aware Copilot:** answers are generated only from records the user may access, and unsupported questions produce a safe “not found in available records” response.
7. **Trust & Audit Ledger:** model version, evidence used, output, confidence/uncertainty, edits and review decisions are recorded according to approved policy.
8. **Language-aware search strategy:** preserve original script while supporting normalised names and possible transliteration variants, subject to dataset and language validation.
9. **Data quality as a feature:** make missing fields, conflicting dates, OCR uncertainty and duplicate records visible rather than hiding them behind polished charts.
10. **Pilot evidence built in:** show labelled test results, error examples and the agreed risk definition rather than relying on unsupported “AI accuracy” claims.

### 3.4 Product principles

- Evidence before eloquence.
- Search and retrieve before generating.
- Explain uncertainty; do not manufacture certainty.
- Human review for consequential decisions and official documents.
- Privacy and least privilege by default.
- Accessible, responsive design for long investigative sessions.
- Useful under imperfect data; never assume all fields are present.

---

## 4. Goals, Non-Goals and Success Criteria

### 4.1 Product goals

- Digitise and structure existing case records for search and analysis.
- Reduce time required to understand a case and prepare routine documents.
- Make candidate cross-case relationships discoverable and reviewable.
- Offer legal-section assistance grounded in an approved legal library.
- Enable role-aware natural-language questions over authorised records.
- Improve insight into geographic and temporal patterns where source data supports it.
- Provide traceability, privacy controls and evidence of quality suitable for a government pilot.

### 4.2 Non-goals / prohibited assumptions for the prototype

- Do not autonomously accuse, designate, arrest, prosecute, or make a final legal determination about a person.
- Do not automatically merge uncertain identities or present candidate network links as proven facts.
- Do not generate final official documents without authorised review and approval.
- Do not claim >90% risk accuracy until “risk” and the evaluation methodology are agreed and independently reproducible.
- Do not assume a live CCTNS or other departmental integration is available; build an adapter boundary and use approved sample data for the demo if needed.
- Do not upload real sensitive records to unapproved third-party services.
- Do not claim OCR/handwriting, Telugu or transliteration quality until tested on representative samples.

### 4.3 Success criteria

**Hackathon prototype:** end-to-end working flow across ingestion, extraction, search, case brief, evidence-backed legal suggestions, candidate entity links, drafting, Copilot and audit trail using approved or synthetic sample records.

**Pilot:** agreed user and data scope; usable experience for 5–10 users in 3 selected districts over 60 days; measured quality against agreed test sets; secure access and audit behaviour; and a defensible evaluation of the defined risk target.

**Operational success measures to agree with the department:** record processing coverage, field-level extraction precision/recall, search relevance, source citation coverage, legal suggestion review quality, false entity-merge rate, user time saved, draft edit/acceptance rate, role-access violations, usability and uptime.

---

## 5. Users, Personas and Jobs to Be Done

> The roles below are proposed personas. Actual department roles, rank names, responsibilities and jurisdiction permissions must be confirmed before deployment.

### 5.1 Investigating Officer

**Needs:** understand a case quickly, retrieve prior records, track events, inspect potential entity links, receive legal-reference assistance and draft documents.  
**Primary job:** “Help me understand what the records say and prepare a reviewable draft without making me search every document manually.”

### 5.2 Supervising Officer

**Needs:** review case progress, inspect supporting evidence, compare related cases, approve or return drafts and review AI suggestions.  
**Primary job:** “Help me review decisions and documents with traceable sources and clear outstanding issues.”

### 5.3 District Analyst / Authorised Intelligence User

**Needs:** examine aggregated trends, compare time periods and locations, inspect candidate networks and understand data quality.  
**Primary job:** “Help me see patterns across the records without exposing details beyond my authorisation.”

### 5.4 Department Administrator

**Needs:** manage users, roles, data sources, templates, legal-library versions, retention rules and integrations.  
**Primary job:** “Help me govern who can access what, and know that the system is operating as configured.”

### 5.5 Auditor / Quality Reviewer

**Needs:** reconstruct outputs, view evidence used, inspect model versions and review histories.  
**Primary job:** “Help me verify how a particular AI-assisted output was generated and handled.”

### 5.6 Accessibility and language needs

The UI should support keyboard use, readable contrast, clear labels, scalable text, screen-reader semantics and low-friction evidence inspection. Language requirements must be validated with the department; support architecture should not assume all source data is in one language.

---

## 6. Information Architecture and Navigation

### 6.1 Main navigation

1. **Command Center** — operational overview, assigned work, processing health and recent activity.
2. **Cases** — case list, filters, saved searches and Case Cockpit.
3. **Unified Search** — global search across cases, people, places, vehicles, items and legal references.
4. **Relationship Explorer** — entity resolution, link graph and repeat-offender review queue.
5. **Hotspot Explorer** — temporal/geospatial analysis where location data permits.
6. **Document Studio** — case diary and chargesheet drafting, templates and review status.
7. **u-FIR Copilot** — role-aware question answering over authorised records.
8. **Review Queue** — extraction corrections, identity-match decisions, legal suggestion review and document approvals.
9. **Trust & Audit Ledger** — searchable log of AI-assisted actions and review history.
10. **Administration** — users, roles, legal library, templates, data sources, model versions and system health; access restricted.

### 6.2 Persistent application shell

- Left navigation rail with icons and text labels; collapsible but never icon-only at narrow widths unless labels remain accessible.
- Top header with product mark, environment label (e.g., Demo/Sandbox), global search, notifications, help and signed-in role.
- Main content canvas with page title, a short context sentence, primary action and breadcrumb where appropriate.
- Context panel on case pages for related entities, source document count, review status and last-updated timestamp.
- Clear data sensitivity label and jurisdiction context where required by policy.
- Avoid implying live production connection when using demo or synthetic data.

---

## 7. Detailed Functional Requirements

Priority definitions: **P0** = essential for a compelling hackathon end-to-end demo; **P1** = core capability expected for pilot completeness; **P2** = useful enhancement or dependent on dataset/organiser approval. Priorities do not reduce coverage of official capabilities; they identify implementation sequencing.

### 7.1 Command Center / Operations Dashboard

**Purpose:** give users a clear, actionable view of work and system health—not just decorative KPI cards.

**Requirements**
- **DASH-01 (P0):** Show counts for available cases, documents processed, items needing review, drafts pending review and recent AI actions. Demo values must be labelled if synthetic.
- **DASH-02 (P0):** Show a processing pipeline with stages: received, parsing/OCR, extraction, indexing, review required, completed, failed.
- **DASH-03 (P1):** Display time-series trends for cases by date, district and case category only where data is present and access is authorised.
- **DASH-04 (P1):** Display a “Needs Attention” queue with reasons such as conflicting dates, low extraction confidence, unresolved identity match or draft awaiting approval.
- **DASH-05 (P1):** Provide quick actions: search cases, open a recent case, resume draft, review candidate links and open Copilot.
- **DASH-06 (P1):** Show the most recent data refresh and processing health.
- **DASH-07 (P1):** Filter all cards/charts by available district, period, status and other approved dimensions; charts must link to the underlying records.

**Acceptance criteria**
- Every metric has a clear definition and data period.
- Clicking a metric opens the corresponding filtered list.
- Empty and partial data states explain what is unavailable.
- Demo/synthetic data is visibly labelled; no fake live metrics.

### 7.2 Record Intake and Processing

**Purpose:** ingest legacy records without forcing changes to existing writing practices.

**Requirements**
- **ING-01 (P0):** Provide a controlled file/import mechanism for permitted document formats and a status per file.
- **ING-02 (P0):** Store a source identifier, checksum, upload/import time, document type if known, case association if known, source location and processing status.
- **ING-03 (P0):** Preserve original files as immutable source artifacts according to approved retention policy.
- **ING-04 (P1):** Detect duplicate uploads using checksum or equivalent safe deduplication; do not silently delete source records.
- **ING-05 (P1):** Detect text-based versus scanned documents and invoke OCR only when required.
- **ING-06 (P1):** Support retry for recoverable failures and display actionable error messages.
- **ING-07 (P1):** Handle partial processing; one malformed file must not block the whole batch.
- **ING-08 (P1):** Associate extracted documents with a case using stable identifiers or a review workflow when matching is uncertain.
- **ING-09 (P2):** Provide adapter interfaces for future approved department-system integrations.

**Acceptance criteria**
- Every input ends in a visible status: completed, completed with warnings, needs review, or failed.
- Original source can be opened by an authorised user.
- Processing failures are logged and retryable; no silent loss of records.
- No unapproved external service receives real records.

### 7.3 OCR, Language and Document Normalisation

- **DOC-01 (P1):** Extract selectable text directly when available; use OCR for scanned/image content.
- **DOC-02 (P1):** Preserve page boundaries and source coordinates/spans to support citations.
- **DOC-03 (P1):** Detect or record language/script where feasible and expose uncertainty.
- **DOC-04 (P1):** Preserve source spellings and script; store normalised forms separately for search.
- **DOC-05 (P1):** Flag low OCR quality, illegible areas and incomplete extraction rather than filling gaps through inference.
- **DOC-06 (P2):** Support transliterated and common spelling variants once validated against representative data.
- **DOC-07 (P2):** Provide a review screen for correcting OCR/extracted text, with changes tracked separately from the original.

**Acceptance criteria**
- Any OCR-derived content is distinguishable from original typed text.
- Citations identify document and page/span whenever available.
- Corrections do not overwrite the original artifact.
- Supported languages and formats are documented based on actual tests.

### 7.4 Structured Facts and Searchable Data

- **EXT-01 (P0):** Extract supported facts including persons/aliases, places, vehicles, seized items, quantities, dates, document references and legal sections where present.
- **EXT-02 (P0):** Each fact includes source document, source span/page, extraction timestamp, method/model version and confidence/uncertainty where available.
- **EXT-03 (P0):** Validate structured outputs against a schema; unknown or missing fields must remain null/unknown instead of being fabricated.
- **EXT-04 (P1):** Normalise dates, units, identifiers and common variants while preserving the original value.
- **EXT-05 (P1):** Detect conflicting facts across documents and expose them as conflicts for review.
- **EXT-06 (P1):** Provide a correction workflow; maintain who changed a value, the prior value, reason and time.
- **EXT-07 (P1):** Index full text and extracted fields for filtered search.
- **EXT-08 (P1):** Support bulk processing and reprocessing under controlled model/version changes.
- **EXT-09 (P2):** Include data-quality dashboards by field, station/source and document type if data permits.

**Acceptance criteria**
- Users can open a fact and inspect its evidence.
- Original and normalised values remain separately visible.
- Missing/conflicting data is not silently resolved.
- Field-level extraction quality can be measured on a labelled sample.

### 7.5 Unified Search

- **SEARCH-01 (P0):** Search case IDs, document text, persons/aliases, places, vehicles, seized items, dates and legal references where indexed.
- **SEARCH-02 (P0):** Provide filters for authorised district/station, date range, case status, document type and other valid indexed fields.
- **SEARCH-03 (P1):** Support spelling variants and normalised forms without removing the original display value.
- **SEARCH-04 (P1):** Support exact search and relevance-based text search; semantic search may be added if it improves measured relevance.
- **SEARCH-05 (P1):** Show a result snippet with highlighted matched text and direct navigation to the source passage.
- **SEARCH-06 (P1):** Provide saved searches or recent search history subject to access/privacy policy.
- **SEARCH-07 (P1):** Respect role permissions in search results, snippets, counts, autocomplete and API responses.
- **SEARCH-08 (P2):** Support Telugu/English/mixed-language query forms if validated with the dataset.

**Acceptance criteria**
- No restricted record leaks through results, snippets, counts or suggestions.
- Every result explains why it matched and links to the record/source.
- Empty results give useful query/filter suggestions without widening access.

### 7.6 Case Cockpit: Case Brief, Timeline and Evidence Viewer

**Purpose:** the primary case workspace and the visual centrepiece of the demo.

**Requirements**
- **CASE-01 (P0):** Provide a case header with case identifier, status, jurisdiction, key dates and available document count.
- **CASE-02 (P0):** Generate a structured Case Brief: recorded allegation/summary, key entities, event chronology, relevant documents, recorded seizures/items, legal references, unresolved conflicts and missing information.
- **CASE-03 (P0):** Cite material summary statements to specific source documents and passages.
- **CASE-04 (P0):** Show source documents next to extracted facts/summary in a split view or side drawer.
- **CASE-05 (P1):** Provide a chronological timeline across FIR, diary, progress report, chargesheet and court documents where available.
- **CASE-06 (P1):** Clearly mark inferred events, unclear dates, conflicting accounts and gaps in source coverage.
- **CASE-07 (P1):** Show related people, places, vehicles and prior cases with review status.
- **CASE-08 (P1):** Allow users to provide feedback on a summary or flag unsupported content.
- **CASE-09 (P1):** Show a “records reviewed” indicator based on sources included in the current brief, not a blanket claim that all records are complete.

**Acceptance criteria**
- Every material generated claim is cited or explicitly marked unsupported/unknown.
- Users can navigate from summary sentence → source passage.
- A summary never states an allegation as an established finding unless the source and approved workflow support that wording.

### 7.7 Legal Intelligence Workspace

**Purpose:** assist officers with potentially relevant laws while keeping human decision-making and legal currency explicit.

**Requirements**
- **LEGAL-01 (P0):** Accept case facts or selected extracted facts and retrieve potentially relevant provisions from an approved legal reference library.
- **LEGAL-02 (P0):** For each suggestion, show provision/section, act name, rationale, cited facts, source of legal text, effective/version date when available, and review status.
- **LEGAL-03 (P0):** Label output as an AI-assisted suggestion—not a final legal decision.
- **LEGAL-04 (P1):** Allow an authorised reviewer to accept, reject, edit or mark “insufficient facts”; capture the decision and rationale.
- **LEGAL-05 (P1):** Support conflicting/ambiguous fact scenarios and abstain where evidence is insufficient.
- **LEGAL-06 (P1):** Version legal content and record which version supported a suggestion.
- **LEGAL-07 (P2):** Add a legal-library administration workflow for approved materials and review dates.

**Acceptance criteria**
- Every suggestion has a source reference to the approved legal library and to case facts.
- The system does not invent section numbers or cite an unapproved source as authoritative.
- Reviewer decisions are logged and can be audited.
- Relevant Acts and sections are confirmed with organisers/department legal experts before final scope is claimed.

### 7.8 Identity Resolution and Repeat-Offender Discovery

**Requirements**
- **IDR-01 (P0):** Detect possible repeated mentions across cases using available name forms, aliases and other lawful/approved identifiers.
- **IDR-02 (P0):** Show candidate links with explanation signals, source mentions and confidence/uncertainty.
- **IDR-03 (P0):** Distinguish “same entity confirmed”, “possible match”, “not the same entity” and “unreviewed” states.
- **IDR-04 (P1):** Let authorised reviewers confirm, reject or defer a match; preserve the decision history.
- **IDR-05 (P1):** Use more than name similarity where reliable identifiers are available; common names alone must not force a merge.
- **IDR-06 (P1):** Support alias and spelling-variant management while preserving each source form.
- **IDR-07 (P1):** Recalculate dependent graphs/search results when a reviewed match changes, with an audit record.
- **IDR-08 (P2):** Add duplicate-record and potential duplicate-case review.

**Acceptance criteria**
- No ambiguous candidate is silently represented as a confirmed person identity.
- Every candidate match includes inspectable supporting evidence and disconfirming/missing signals where available.
- False-merge cases are included in evaluation.

### 7.9 Relationship Explorer / Network Intelligence

**Requirements**
- **NET-01 (P0):** Visualise evidence-backed connections between persons/entities, places, vehicles, cases and other approved entity types.
- **NET-02 (P0):** Show edge type, source evidence, date, confidence/uncertainty, and verification status on selection.
- **NET-03 (P1):** Filter graph by time period, entity type, case, district/jurisdiction and link status, subject to permissions.
- **NET-04 (P1):** Distinguish direct facts from inferred candidate relationships using visual labels, not colour alone.
- **NET-05 (P1):** Offer a linked case list and a “why is this connected?” evidence drawer.
- **NET-06 (P1):** Allow reviewer feedback on links and record accepted/rejected status.
- **NET-07 (P2):** Provide graph analysis such as repeated co-occurrence or shared-asset patterns only when supported by data and validated to avoid misleading inference.

**Acceptance criteria**
- Every visible relationship can be traced to records.
- The UI never implies that association alone proves guilt or criminal activity.
- Graphs handle large networks through filtering, progressive loading and clear legends.

### 7.10 Hotspot Explorer / Geospatial Analytics

**Requirements**
- **GEO-01 (P1):** Aggregate cases by location and time period if the source provides sufficiently reliable location information.
- **GEO-02 (P1):** Provide map and non-map alternatives such as ranked tables and time-series views.
- **GEO-03 (P1):** Filters include time period and available jurisdiction/category fields.
- **GEO-04 (P1):** Explain aggregation method and display data coverage/quality caveats.
- **GEO-05 (P1):** Allow users to open contributing authorised case records from an aggregate point/area.
- **GEO-06 (P2):** Use density or clustering methods only when appropriate to data density and validated with users.

**Acceptance criteria**
- Hotspots are presented as patterns in recorded data, not as proof of future crime or individual culpability.
- Incomplete/missing geocoding is visible.
- Map colours have a legend and a non-colour-only alternative is provided.

### 7.11 Document Studio: Case Diary and Chargesheet Drafting

**Requirements**
- **DOCS-01 (P0):** Generate editable drafts for case diaries and chargesheets from selected case facts and approved templates.
- **DOCS-02 (P0):** Show which source facts/documents contributed to generated sections.
- **DOCS-03 (P0):** Mark generated content as draft/AI-assisted until authorised approval.
- **DOCS-04 (P1):** Support section-by-section editing, regeneration of selected sections and source fact insertion.
- **DOCS-05 (P1):** Highlight unfilled required fields, unsupported statements, contradictions and stale facts.
- **DOCS-06 (P1):** Maintain versions, author/reviewer identity, review comments and approval/rejection status.
- **DOCS-07 (P1):** Export in an approved format after review, subject to the actual document template and policy.
- **DOCS-08 (P2):** Support template administration and approved language formats.

**Acceptance criteria**
- The generated document cannot be mistaken for an approved official record.
- Each material statement can be traced back to source information or identified as officer-entered.
- Edits and approval history are retained according to policy.

### 7.12 u-FIR Copilot: Role-Aware Case Assistant

**Requirements**
- **COP-01 (P0):** Provide natural-language questions over records the signed-in user is authorised to access.
- **COP-02 (P0):** Retrieve evidence before answering and cite case ID/document type/page or span when available.
- **COP-03 (P0):** Return “not found in available records” when sufficient evidence is absent; ask clarifying questions where useful.
- **COP-04 (P1):** Support follow-up questions that preserve case context while rechecking permission on every retrieval.
- **COP-05 (P1):** Let users open each citation and inspect the source passage.
- **COP-06 (P1):** Include safeguards against instructions embedded in retrieved documents; source content is data, not trusted system instructions.
- **COP-07 (P1):** Log queries/responses as permitted by retention and privacy rules; avoid unnecessary sensitive data in telemetry.
- **COP-08 (P2):** Support voice input/output only if requested by users, accessible, secure and validated; it is not required for the MVP.

**Acceptance criteria**
- Answers are evidence-grounded and citations point to accessible records.
- Retrieval enforces role/jurisdiction permissions before generation.
- The system refuses to invent case facts and clearly signals missing evidence.

### 7.13 Risk Prediction and Alerts

**Requirements**
- **RISK-01 (P0 for design; evaluation gated):** Maintain an explicit configuration of the agreed risk target, horizon, label source, intended use and metric before training/evaluation.
- **RISK-02 (P1):** If the organisers define a valid risk target and provide suitable labelled data, evaluate a baseline and candidate models using held-out data.
- **RISK-03 (P1):** Display score explanation, contributing evidence/features, data freshness, uncertainty and limitations; do not expose unsupported causal explanations.
- **RISK-04 (P1):** Restrict score use to approved, documented workflows; no autonomous enforcement decision.
- **RISK-05 (P1):** Record model version, threshold, output, user access and subsequent review action.
- **RISK-06 (P2):** Alerting based on validated aggregate trends may be added after alert fatigue, escalation path and false-positive handling are agreed.

**Acceptance criteria**
- The dashboard clearly states the prediction target and evaluation window.
- “More than 90% accuracy” is never claimed without agreed labels, test methodology and reproducible results.
- Unknown or unvalidated risk outputs are hidden or explicitly labelled unavailable—not fabricated.

### 7.14 Review Queue and Human Feedback

- **REV-01 (P0):** Unified queue for low-confidence extraction, conflicting facts, candidate identity matches, legal suggestions and document approvals.
- **REV-02 (P0):** Show item, reason for review, source evidence, assigned reviewer and current status.
- **REV-03 (P1):** Support accept/reject/edit/defer/escalate actions appropriate to item type.
- **REV-04 (P1):** Record reviewer, timestamp, reason/comment and old/new values where applicable.
- **REV-05 (P1):** Feed corrections into evaluation datasets only through an approved data governance process; do not silently retrain from all user changes.

### 7.15 Trust & Audit Ledger

- **AUD-01 (P0):** Log AI-assisted output, user, timestamp, action, case/document references, model/version and source evidence references, subject to approved policy.
- **AUD-02 (P0):** Record whether the result was accepted, edited, rejected or left unreviewed where applicable.
- **AUD-03 (P1):** Make audit entries searchable by case, user, action, date and model version for authorised reviewers.
- **AUD-04 (P1):** Protect logs against ordinary-user modification and apply retention/access policies.
- **AUD-05 (P1):** Provide an output replay/inspection view where feasible without exposing prompts or personal data beyond permissions.

**Acceptance criteria**
- A reviewer can reconstruct a selected AI-assisted decision from audit metadata and evidence references.
- Audit logs do not become a second uncontrolled store of sensitive data.

### 7.16 Administration, Configuration and System Health

- **ADM-01 (P1):** Manage users, roles and permissions; enforce least privilege.
- **ADM-02 (P1):** Manage approved document templates, legal reference versions and data source configuration.
- **ADM-03 (P1):** Expose ingestion failures, queue depth, processing latency and service health to authorised administrators.
- **ADM-04 (P1):** Support model/version metadata and controlled release/rollback.
- **ADM-05 (P2):** Provide configurable retention settings, access review reports and data export/deletion workflows if permitted by policy.

---

## 8. UI/UX Direction: Impressive, Trustworthy and Operational

### 8.1 Visual concept

Design the interface as a premium government intelligence workspace: calm, precise, modern and information-rich. Avoid a generic AI chatbot page or a dashboard filled with decorative gradients. Visual sophistication should come from hierarchy, typography, clear evidence, useful interaction and consistent information density.

**Suggested design direction**
- **Primary:** deep ink/navy for navigation and high-importance surfaces.
- **Canvas:** warm white or very light neutral for long-reading areas.
- **Accent:** restrained teal/cyan for interactive focus and verified/system states.
- **Semantic colours:** success, warning and error only for meaningful statuses; never use colour as the only signal.
- **Typography:** highly legible sans serif; compact but readable table text; strong distinction between page title, section title, metadata and evidence.
- **Shape:** restrained rounded corners, consistent spacing, thin dividers and subtle elevation only where it clarifies layering.
- **Motion:** brief transitions for opening evidence panels and graph focus; reduced-motion support; no flashy animations.

### 8.2 Signature page: Case Cockpit

The Case Cockpit should be the standout screen.

**Layout**
- Top case identity strip: case ID, jurisdiction, date/status, assigned officer (if permitted), document count and review state.
- Main column: Case Brief, event timeline, extracted facts and document sections.
- Evidence side panel: original text/PDF viewer with highlighted cited passages.
- Right/context rail: related entities, candidate links, legal suggestions and “Needs Review” flags.
- Persistent actions: Ask Copilot about this case; Create Draft; View Relationships; Open Audit.

**Signature interactions**
- Clicking a summary statement opens the exact cited passage.
- Hover/focus on an entity highlights mentions across the current case.
- A timeline event opens its source document.
- A conflicting date creates a reviewable issue, not a silent overwrite.
- A related-person link opens a “why linked?” panel and candidate/verified label.

### 8.3 Signature page: Relationship Explorer

- Graph canvas with meaningful node types and clear edge semantics.
- Search and filters in a compact left panel.
- Selected entity summary and evidence drawer on the right.
- Toggle between graph and accessible relationship table.
- Show direct fact, inferred relationship, confirmed match and pending review using label + icon + visual treatment.
- Prevent accidental visual clutter through progressive expansion, neighbourhood depth and time filters.
- Every edge must lead to evidence; “association” is never styled as proof of culpability.

### 8.4 Signature page: Command Center

The dashboard prioritises work, system state and traceable metrics:
- Processing funnel rather than vanity statistics.
- “Needs Attention” with actionable issue types.
- Workload/task cards that navigate to queues.
- Trend charts with visible period, count definition, filter and click-through.
- Data coverage and quality indicators alongside headline insight.
- Explicit demo/sandbox banner for non-production data.

### 8.5 Signature page: Document Studio

- Paper-like editable document canvas with stable toolbar and review status.
- Source evidence rail listing facts used for each selected paragraph/section.
- Inline flags for unsupported claims, missing required fields and conflicts.
- Version compare for draft changes.
- Clear “Save Draft”, “Request Review”, “Approve” actions depending on role.
- Approval action is not available to an unauthorised user.

### 8.6 Signature page: u-FIR Copilot

- Chat panel with visible selected case/context scope and role context.
- Citations as compact source chips that open evidence, not decorative footnotes.
- Separate fact response from “possible interpretation” where appropriate.
- “What is missing?” and “Show supporting records” quick actions.
- No unsupported confidence badges or unexplained percentages.
- Permission errors must not reveal whether a restricted record exists.

### 8.7 Design tokens and components

Create a consistent component library with:
- App shell, navigation, breadcrumbs, page headers and action bars.
- Status chips with text and icon; confidence/uncertainty indicators with explanation.
- Search field, filters, saved search, result row and highlighted snippet.
- Case header, entity card, timeline event, source citation, evidence drawer.
- Data tables with sorting, pagination, empty states and accessible header semantics.
- Graph legend, graph node/edge selection, and accessible relationship table.
- Document editor, paragraph source badge, review comment and version diff.
- Audit entry row, activity timeline, confirmation dialog and toasts.
- Loading skeletons, retry states, validation messages and offline/service status.

### 8.8 UX states every major page must support

- Initial loading, incremental loading and long-running processing.
- Empty state with next action.
- Partial/low-quality data state.
- Error state with safe error details and retry where appropriate.
- Permission denied state that does not disclose restricted data.
- AI uncertainty / insufficient evidence state.
- Stale data or source refresh state.
- Review required / accepted / rejected / superseded states.

### 8.9 Accessibility and responsive behaviour

Target WCAG 2.2 Level AA as a product goal, subject to validation. Ensure keyboard navigation, visible focus, logical heading order, labels, screen-reader names, error announcements, contrast, zoom/reflow and reduced motion. Provide an accessible table alternative for graphs and maps. On smaller screens, prioritise search, case facts, citations and review tasks; complex graph editing can be desktop-first but must remain usable through its table representation.

---

## 9. Key User Journeys

### Journey A: From legacy file to searchable case
1. Authorised user or approved ingestion job supplies source documents.
2. The system records source metadata, detects format and parses/OCRs as needed.
3. Extracted facts appear with source spans and uncertainty indicators.
4. Low-quality/conflicting fields enter the Review Queue.
5. Validated content is indexed for search and case summarisation.
6. User opens the case and can navigate to every cited fact.

**Success:** no change to officer writing practices; source preserved; searchable facts trace back to documents.

### Journey B: Understand a case quickly
1. User opens a case from search/dashboard.
2. Case Cockpit displays the Case Brief and timeline.
3. User clicks a claim to inspect its source passage.
4. User reviews missing or conflicting information.
5. User asks a follow-up question scoped to that case.

**Success:** fast orientation without unsupported claims, with evidence available in one action.

### Journey C: Review a possible repeat-offender link
1. User searches a name/alias or opens Relationship Explorer.
2. System lists possible matches and signals behind each candidate.
3. User reviews source mentions, identifiers and contradictory evidence.
4. Authorised user confirms, rejects or defers the match.
5. The graph and linked-case views update and record the review decision.

**Success:** possible links are surfaced while ambiguous identities remain separate pending review.

### Journey D: Create a case diary/chargesheet draft
1. User opens Document Studio from a case.
2. User chooses an approved document template and source scope.
3. System drafts supported sections and identifies missing fields/conflicts.
4. User edits content and checks source citations.
5. User requests review; authorised reviewer approves or returns the draft.
6. System logs versions, reviewer action and export event.

**Success:** document creation is accelerated without misrepresenting AI text as final/approved.

### Journey E: Ask Copilot a question
1. User asks a case or cross-case question.
2. Permission-aware retrieval selects only accessible records.
3. Copilot answers with source citations and limitation notes.
4. User opens citations or asks a follow-up.
5. Audit event is recorded according to policy.

**Success:** grounded, access-controlled answer or an honest “not found” response.

---

## 10. Data and Technical Architecture

### 10.1 Logical architecture

1. **Experience layer:** responsive web application; pages defined in the navigation section.
2. **Identity/API layer:** authentication, role and jurisdiction enforcement, request validation, rate limits and audit hooks.
3. **Ingestion pipeline:** file intake, format detection, parsing/OCR, queues/workers, retries and processing status.
4. **Extraction and normalisation:** schema-bound entity/fact extraction, validation, entity mention linking and conflict detection.
5. **Retrieval and AI services:** keyword/hybrid search, optional vector retrieval, summarisation, legal retrieval, entity resolution, Q&A and drafting.
6. **Data services:** relational store for case records and workflow state; object storage for source files; search index for full text and filters; optional graph or graph tables for relationships; optional vector index if justified by measured value.
7. **Analytics layer:** time/location aggregates, data quality and risk evaluation if authorised and defined.
8. **Governance layer:** audit events, model versions, evaluation datasets/results, legal library versions and policy configuration.

### 10.2 Technology neutrality

This PRD specifies behaviours and interfaces, not mandatory vendors. The implementation should use the project's existing stack where practical. Proposed reference patterns include a web frontend, backend API, relational database, object storage, full-text search and asynchronous workers. Select LLMs, embedding models, OCR providers and deployment infrastructure based on data controls, language coverage, latency, cost, reproducibility and approved hosting. No third-party provider is assumed approved for sensitive records.

### 10.3 Data entities (proposed)

| Entity | Key fields | Purpose |
|---|---|---|
| Case | case_id, jurisdiction, station, date, status, source references | Canonical case metadata |
| Document | document_id, case_id, type, source_uri, checksum, language, ingest status | Original document and provenance |
| ExtractedFact | fact_id, case_id, field_type, original_value, normalised_value, source span, confidence, model version | Traceable structured fact |
| Entity | entity_id, type, canonical label, identifier references, resolution status | Person/place/vehicle/item representation |
| EntityMention | mention_id, entity_id/candidate_id, document_id, surface form, source span | Specific occurrence of an entity mention |
| CaseEvent | event_id, case_id, event date/range, event type, source document, uncertainty | Timeline event |
| LegalReference | reference_id, act, section, text/version, effective date, approved source | Versioned legal catalogue |
| LegalSuggestion | suggestion_id, case_id, reference_id, rationale, supporting facts, review state, model version | Explainable legal suggestion |
| Relationship | relationship_id, source/target entities, type, source evidence, confidence, review state | Evidence-backed graph edge |
| Draft | draft_id, case_id, document type, content/version, author, reviewer, status | Draft lifecycle |
| ReviewTask | task_id, type, priority, assigned role/user, source reference, decision history | Human review workflow |
| AuditEvent | actor, action, timestamp, resource, model/version, evidence refs, outcome | Reviewable system history |
| UserRole | user/role assignments, scope/jurisdiction, permissions, validity | Access control |
| ModelEvaluation | model version, dataset/version, metric, slice, result, date | Evaluation evidence |

Schema details, retention and identifier design must be validated against actual data and policy. Use stable internal IDs; avoid treating a text name as a unique person identifier.

### 10.4 API requirements and illustrative contracts

The official brief requires results through an API or dashboard. A documented API is recommended even if the primary hackathon demo is the UI. Exact paths are illustrative and should be aligned with the codebase.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/health` | GET | Service health, without exposing sensitive configuration |
| `/api/v1/ingestion/jobs` | POST | Create an approved ingestion job |
| `/api/v1/ingestion/jobs/{jobId}` | GET | Processing status and safe errors |
| `/api/v1/cases` | GET | Permission-filtered case search/list |
| `/api/v1/cases/{caseId}` | GET | Case metadata and accessible document list |
| `/api/v1/cases/{caseId}/brief` | GET | Case Brief with source references and generation metadata |
| `/api/v1/cases/{caseId}/timeline` | GET | Events and evidence links |
| `/api/v1/search` | GET/POST | Structured and full-text search |
| `/api/v1/entities/{entityId}/candidates` | GET | Candidate identity matches with evidence |
| `/api/v1/relationships` | GET | Filtered relationship results/graph data |
| `/api/v1/legal/suggestions` | POST | Generate legal suggestions from approved case facts |
| `/api/v1/drafts` | POST | Create an editable draft from approved template and sources |
| `/api/v1/drafts/{draftId}/review` | POST | Review/approve/return a draft if authorised |
| `/api/v1/copilot/query` | POST | Ask a permission-aware question |
| `/api/v1/reviews` | GET/POST | Fetch or decide review tasks |
| `/api/v1/audit` | GET | Permission-filtered audit search |
| `/api/v1/analytics/hotspots` | GET | Aggregated hotspot data with filters |
| `/api/v1/evaluations` | GET | Approved evaluation summaries |

**API rules:** authenticated endpoints; role/jurisdiction checks at request and record level; request/response schema validation; pagination; safe error codes; idempotency for long-running submissions where needed; audit hooks for consequential actions; versioning; no sensitive data in URLs or routine logs; rate limiting; and documented examples using synthetic data.

### 10.5 Interoperability

- Preserve an adapter layer for future approved systems; do not assume a named integration is mandated.
- Support export of authorised structured data and evaluation summaries under policy.
- Document data formats, ID mapping and error handling.
- Separate internal canonical schema from source-specific import formats.

---

## 11. AI Quality, Evaluation and Guardrails

### 11.1 Evaluation before demo claims

Every metric presented to judges should include: definition, dataset/sample size, test method, baseline if applicable, results, limitations and whether the data is synthetic or real/approved. Never mix training/evaluation records in a way that inflates performance.

### 11.2 Metrics by capability

| Capability | Suggested evaluation |
|---|---|
| OCR/text extraction | Character/word error or field recovery by document type/language, when OCR applies |
| Structured facts | Precision, recall and F1 by field/entity type; completeness and conflict-detection quality |
| Search | Relevant-result rate/precision at K and task completion on a judged query set |
| Summary | Unsupported-claim rate, citation coverage, material omission rate and expert review |
| Legal suggestions | Expert-rated relevance, citation correctness, abstention quality and harmful/unsupported suggestion rate |
| Entity resolution | Precision/recall on reviewed match pairs; false-merge rate; review burden |
| Relationship graph | Evidence completeness, false-link rate and reviewer utility |
| Drafting | Unsupported-statement rate, source coverage, reviewer edit time and acceptance/edit rate |
| Copilot | Answer correctness, citation precision/coverage, abstention correctness and permission-boundary tests |
| Hotspots | Location completeness, aggregation correctness and user interpretation testing |
| Risk prediction | Agreed metrics only after target/labels/time horizon are defined; use a held-out set and relevant subgroup analyses |

### 11.3 Generative AI controls

- Retrieval before generation for record-grounded outputs.
- Source citations at claim/paragraph level where possible.
- Schema validation for extracted facts and generated structured output.
- Abstain when evidence is insufficient or conflicting.
- Treat retrieved documents as untrusted content to mitigate prompt injection.
- Redact/minimise data sent to model providers; use approved deployment and retention settings.
- Version prompts, models and legal sources; regression test changes before release.
- Keep model outputs distinct from officer-entered or verified facts.

### 11.4 Risk prediction: required decision gate

Before any risk model can be evaluated for official acceptance, obtain agreement on:
1. What is being predicted and for whom/what (case, event, location or other target).
2. Prediction horizon and the point in time at which features are available.
3. Exact ground-truth label and who validates it.
4. Metric and definition of “accuracy”; class balance and error costs.
5. Permitted actions and prohibited uses of the score.
6. Evaluation sample, time split, leakage controls and subgroup review.
7. Review, escalation, override and monitoring process.

If these are not clarified, ship the UI and evaluation framework in a clearly labelled “not configured/not evaluated” state; do not invent a risk score.

---

## 12. Non-Functional Requirements

| ID | Requirement | Target / acceptance approach |
|---|---|---|
| NFR-01 Security | Authenticate all protected functionality and authorise each data access | Automated tests for role and jurisdiction boundaries; no search/snippet leakage |
| NFR-02 Privacy | Minimise sensitive information in logs and external processing | Review data flows and provider settings before using real records |
| NFR-03 Auditability | Consequential AI outputs are reviewable | Reconstruct output, version and evidence in an audit test |
| NFR-04 Reliability | Long-running ingestion and AI operations survive individual failures | Status tracking, retry and dead-letter/error handling where applicable |
| NFR-05 Performance | Search and common case screens remain responsive under pilot load | Establish baseline and agree target after dataset/load discovery |
| NFR-06 Scalability | Ingestion and AI processing can scale separately from the UI | Queue/worker design and documented deployment path |
| NFR-07 Accessibility | Target WCAG 2.2 AA | Manual keyboard/screen-reader/contrast/reflow test; automated scans are supporting evidence only |
| NFR-08 Usability | Core tasks are learnable by intended users | Task-based usability testing with representative users where authorised |
| NFR-09 Maintainability | Modular services, schema/version migrations and documented setup | New environment setup and regression-test checklist |
| NFR-10 Observability | Errors, latency and job status are visible without exposing sensitive records | Structured, minimised operational logs and health dashboard |
| NFR-11 Reproducibility | Model/prompt/legal-library versions are tracked | Evaluation can be reproduced for a given version and dataset |
| NFR-12 Language support | Validate real script/language requirements and coverage | Test on representative records; publish supported/unsupported cases |
| NFR-13 Data integrity | Preserve source documents and correction history | Checksum/provenance and immutable-source tests |
| NFR-14 Interoperability | API/dataset import boundaries documented | OpenAPI or equivalent API documentation and sample payloads |

Where the problem statement gives no numeric target, the team should measure a baseline and agree pilot targets with the department rather than inventing figures.

---

## 13. Security, Privacy and Responsible Use

### 13.1 Access and data handling

- Implement role-based access control plus jurisdiction/assignment scope where required.
- Check access on all API calls, search results, snippets, citations, graph neighbours, exports, assistant retrieval and background jobs.
- Encrypt in transit and at rest where supported by the selected deployment environment.
- Keep secrets outside source code; use environment/secret-management controls appropriate to deployment.
- Apply approved retention and deletion policies to source records, derived data, prompt/response logs, backups and evaluation copies.
- Use synthetic or approved masked data for public demonstrations.
- Do not connect real records to unapproved SaaS, telemetry, analytics or model providers.

### 13.2 AI safety and accountability

- Show that an item is alleged, extracted, inferred, reviewed or verified; do not collapse these categories.
- No automatic guilt attribution, arrest recommendation or final legal judgement.
- Require human review for official document approval and ambiguous identity matches.
- Show evidence and uncertainty in a usable way.
- Allow corrections and audit the correction lifecycle.
- Test for prompt injection in source documents, leakage between roles and fabricated citations.
- Assess the impact of false positives and false negatives before enabling any risk-based operational workflow.

### 13.3 Incident readiness

Before pilot launch, define who can suspend AI features, report a suspected data exposure, review compromised credentials, roll back a model version, correct bad data and notify the department under its approved policy.

---

## 14. Testing Strategy and Acceptance Test Catalogue

### 14.1 Functional test cases

| Test ID | Scenario | Expected result |
|---|---|---|
| T-ING-01 | Import a valid typed document | Source saved, status displayed, text extracted and indexed |
| T-ING-02 | Import a scanned document where OCR is configured | OCR output marked; page/span provenance retained where available |
| T-ING-03 | Import a malformed file | File fails safely with reason; other batch files continue |
| T-EXT-01 | Extract a person, place, vehicle and quantity from a sample | Fields match reviewed ground truth or are flagged uncertain |
| T-EXT-02 | Field absent from source | System returns unknown/null, not a guessed value |
| T-EXT-03 | Documents disagree on a date | Conflict is visible and reviewable |
| T-SEA-01 | Search exact case ID | Correct authorised case appears |
| T-SEA-02 | Search a known spelling variant | Relevant candidate results appear while original form is preserved |
| T-SEC-01 | User opens a restricted case by direct URL/API | Access denied without revealing sensitive metadata |
| T-CASE-01 | Open generated Case Brief | Material claims have source citations and uncertainty is visible |
| T-LEGAL-01 | Request a section suggestion for ambiguous facts | System shows caveat/abstains; does not invent a provision |
| T-IDR-01 | Two different people share a common name | Candidate remains unconfirmed without adequate evidence |
| T-NET-01 | Open a network edge | Source evidence, edge semantics and status are inspectable |
| T-GEO-01 | Location data is missing | Missing coverage is indicated; no false precise location is plotted |
| T-DRAFT-01 | Generate a document draft | Editable, marked as draft, source-linked, not auto-approved |
| T-DRAFT-02 | Unauthorised user attempts approval | Approval blocked and security event/audit recorded as policy requires |
| T-COP-01 | Ask a question supported by authorised records | Answer includes valid citations to accessible sources |
| T-COP-02 | Ask an unanswerable question | Assistant states evidence is not found; does not hallucinate a fact |
| T-COP-03 | Retrieved document contains prompt-injection text | Text is treated as untrusted content; system instructions/permissions remain intact |
| T-AUD-01 | Review an AI-assisted output | Audit shows actor/time/action/version/evidence/review state within policy |
| T-RISK-01 | Risk target is not configured | UI shows unavailable/not evaluated; no fabricated risk output |
| T-ACC-01 | Navigate key flows by keyboard | Focus is visible and all core controls are operable |
| T-ACC-02 | Inspect graph/map using accessible alternative | Relationship table or equivalent readable alternative is available |

### 14.2 Model testing and human evaluation

- Build a representative, authorised annotation sample before judging model quality.
- Include hard negatives: similar names that refer to different people; conflicting records; missing fields; poor-quality scans; unsupported questions.
- Measure extraction/linking/legal suggestion quality separately.
- Use reviewers with appropriate expertise for legal content and consequential judgments.
- Record disagreement between annotators and define adjudication rules.
- Report the number and composition of tested examples and known blind spots.

### 14.3 Accessibility/usability testing

- Keyboard-only completion of search → case brief → source evidence → draft.
- Screen-reader checks for navigation, forms, tables, alerts and review status.
- Contrast and zoom/reflow checks.
- Verify status is conveyed through text/icons as well as colour.
- Test language clarity, long-document fatigue and error recovery with representative users if access is granted.

---

## 15. Roadmap and Pilot Delivery Plan

### 15.1 MVP for hackathon differentiation

**P0 — Must work end to end**
- Import synthetic/approved sample documents and display processing state.
- Structured extraction with source-linked facts.
- Unified Search with filters and spelling-variant handling where feasible.
- Case Cockpit with cited Case Brief, timeline and evidence viewer.
- Legal suggestions grounded in an approved/legal-reviewable catalogue, clearly marked advisory.
- Candidate entity resolution and evidence-backed relationship view.
- Editable case diary/chargesheet draft with review status.
- Role-aware Copilot with citations and abstention.
- Audit Ledger for AI-assisted outputs and reviewer decisions.
- Modern, accessible UI shell with clear demo/sandbox mode.

**P1 — Pilot-completeness features**
- Hotspot analytics using available reliable location data.
- Review Queue for extraction conflicts, identity matches, legal suggestions and drafts.
- Administration for roles, templates, legal content and job health.
- API documentation, data quality metrics, model/version metadata and security regression tests.
- Risk evaluation framework, gated until target definition and labels are agreed.

**P2 — Useful extensions where time/data permit**
- Voice input/output, only if secure and requested.
- Advanced network metrics and automated trend alerts after validation.
- Department-system integration adapter after technical and policy approval.
- Rich multilingual/transliteration support after dataset assessment.
- Evaluation comparison and model-change monitoring dashboards.

### 15.2 Indicative 60-day pilot plan

| Phase | Indicative days | Work | Exit evidence |
|---|---:|---|---|
| Discovery and access | 1–7 | Confirm risk target, roles, legal sources, hosting, formats and data rights | Approved scope, data inventory and access assumptions |
| Baseline and ingestion | 8–18 | Build import path, parsing/OCR and labelled quality sample | Ingestion report and baseline metrics |
| Core workflow | 19–32 | Search, facts, Case Brief, timeline and evidence viewer | End-to-end case workflow demo |
| Intelligence and drafting | 33–43 | Legal assistance, entity matching, network view, draft workflow, hotspot prototype | Reviewed cases and error analysis |
| Validation and security | 44–53 | User testing, access-control testing, model evaluation and corrections | Test report and remediation status |
| Pilot handover | 54–60 | Train 5–10 users across 3 selected districts; review outcomes | Pilot report and scale-up recommendations |

This is a proposed schedule consistent with the official duration, not an organiser-supplied project plan. Data access and approvals may change sequencing.

---

## 16. Hackathon Scoring Alignment

### 16.1 Admin screening

| Criterion | Weight | Product evidence |
|---|---:|---|
| Innovation and AI Advancement | 25% | Evidence-grounded RAG, explainable relationship discovery and assisted drafting as one workflow |
| Accuracy and Reliability | 20% | Labelled evaluation, source citations, abstention, failure analysis and version tracking |
| Usability and Accessibility | 15% | Case Cockpit, low-friction source inspection, keyboard/accessibility support |
| Scalability and Deployment | 15% | Modular pipeline, queues, API contract, deployment options and observability |
| Impact Potential | 15% | Measured time saved and task completion against baseline |
| Data Privacy and Security | 10% | Role/jurisdiction checks, audit, data minimisation and controlled hosting plan |

### 16.2 Jury round

| Criterion | Marks | Demo strategy |
|---|---:|---|
| User Experience and Accessibility | 20 | Lead with Case Cockpit and evidence click-through; show accessible alternatives |
| Impact and Outcome Potential | 20 | Quantify measured time/effort reduction without inflated claims |
| Relevance to Problem Statement | 15 | Trace each official capability/outcome to a working screen |
| Technical Feasibility and Scalability | 15 | Explain data pipeline, architecture, API and deployment path |
| Innovation and Novelty | 10 | Emphasise evidence-first AI, identity uncertainty and Trust & Audit Ledger |
| Data and Integration Capability | 10 | Show schema, provenance, permissions and integration boundary |
| Presentation and Demo Quality | 10 | Demonstrate one coherent case journey, not disconnected features |

### 16.3 Recommended 7–9 minute demo narrative

1. **Problem (45 sec):** show a legacy free-text document and the manual search burden.
2. **Ingestion (45 sec):** show record intake, extraction and data-quality status.
3. **Case Cockpit (90 sec):** reveal the Case Brief and click claims to source passages.
4. **Search + identity (60 sec):** find a spelling variant; inspect a candidate match without auto-merging.
5. **Network intelligence (60 sec):** show an evidence-backed relationship and its source records.
6. **Legal + draft (90 sec):** show a cited legal suggestion and generate an editable reviewed draft.
7. **Copilot (60 sec):** ask a grounded question and show citations or safe abstention.
8. **Trust + impact (60 sec):** open audit trail and measured evaluation evidence; state limitations and risk-target dependency.

Keep the screen transitions coherent and use the same case throughout the demo. Label synthetic data prominently. Never invent benchmark values to improve the pitch.

---

## 17. Risks, Dependencies and Mitigation

| Risk/dependency | Impact | Mitigation / decision needed |
|---|---|---|
| Risk target undefined | Cannot validly train/evaluate >90% risk accuracy | Obtain written target, horizon, labels, metric and permitted use |
| Dataset timing/format unknown | Limits product completeness and model choice | Request representative sample and data dictionary early |
| OCR/language variation | Extraction and search errors | Profile real documents; report quality by format/script; review low-quality outputs |
| Entity false merges | Misleading network interpretation | Conservative resolution, evidence display, reviewer decisions and false-merge tests |
| Legal source ambiguity | Incorrect or outdated suggestions | Obtain approved legal reference material and expert review process |
| Sensitive data restrictions | May block external model use or hosted demos | Use approved deployment and synthetic/masked demo data until access approved |
| Integration not specified | Overbuilding can delay MVP | Keep adapters modular; do not assume CCTNS integration is mandatory |
| Location incompleteness | Hotspot views may mislead | Show coverage and uncertainty; provide tables and avoid false precision |
| Risk-model data leakage/bias | Inflated results or harmful outputs | Time-aware held-out evaluation, subgroup review and limited permitted use |
| Overloaded UI | Officers cannot find key information | Task-based usability tests, progressive disclosure and contextual evidence panels |
| Model/provider changes | Reproducibility and quality regressions | Version models/prompts/legal sources; maintain regression suite and rollback |
| Undefined retention/audit policy | Privacy and compliance risk | Obtain policy decisions before pilot; minimise logs and restrict access |

---

## 18. Open Questions to Resolve with Organisers

1. What exactly does “risk” refer to, what is the prediction horizon, and how will the >90% target be calculated?
2. When and in what format will five years of data be shared? Can a sample and data dictionary be provided?
3. Which languages/scripts are present; are records typed, scanned, handwritten or mixed?
4. Which Acts and legal provisions are in scope, and what source is authoritative and current?
5. Which roles, districts and assignment boundaries determine access?
6. Is integration with CCTNS or another departmental system expected or merely a future option?
7. What hosting, data residency, model provider, retention, audit and incident policies apply?
8. What application/demo artefacts are required (pitch deck, video, prototype, repository, team details)?
9. Who provides adjudicated labels and approves legal recommendations during pilot evaluation?
10. What official document templates and approval flow should case diaries and chargesheets follow?
11. Can test records be synthetic/masked for public demos, and what data may be shown to judges?
12. What response-time, availability and accessibility targets should be agreed for the pilot?

---

## 19. Traceability Matrix: Official Requirements to PRD

| Official requirement / outcome | PRD coverage | Acceptance evidence |
|---|---|---|
| C1: unstructured files to searchable data | Intake, normalisation, extraction, unified search | Source-preserved record searchable by fields/text |
| C2: fast case understanding | Case Cockpit, Case Brief, timeline, source viewer | Cited summary and one-click evidence inspection |
| C3: suggest laws/sections | Legal Intelligence Workspace | Citation-backed suggestions and review decisions |
| C4: repeat offenders/networks | Identity Resolution and Relationship Explorer | Candidate matches, link evidence and human status |
| C5: reduce paperwork | Document Studio | Editable diary/chargesheet draft and review history |
| O1: all records structured | Ingestion/extraction/data quality | Processing coverage and field-level evaluation |
| O2: diary/chargesheet generation | Document Studio | Source-linked draft workflow |
| O3: network links | Relationship Explorer | Evidence-backed graph and reviewed relationships |
| O4: hotspots | Hotspot Explorer | Data-grounded map/table and caveats |
| O5: role-aware chatbot | u-FIR Copilot and permissions | Cited answers; cross-role tests pass |
| Existing records; no writing change | Intake over legacy file types | Process records as supplied; no mandatory authoring-template change |
| Spelling and station format variation | Normalisation, Search, Identity Resolution | Variant tests and preserved source forms |
| Reviewable AI decisions | Trust & Audit Ledger | Reconstruct output and review path |
| API or dashboard | UI plus documented API | Working dashboard/API contract |
| >90% risk-prediction target | Gated risk framework | Written definition plus reproducible held-out evaluation |
| 3 districts / 5–10 users / 60 days | Pilot plan | Pilot scope, training and end report |
| UX/accessibility and impact scoring | UI/UX, test plan, impact metrics | Usability evidence and measured workflow outcomes |
| Privacy/security | Security controls and test catalogue | Access-boundary and audit tests |

---

## 20. Definition of Done

The hackathon release is ready to demonstrate when all items below are true:

- [ ] The app clearly indicates whether it is running in demo/sandbox or approved pilot mode.
- [ ] Sample/approved source records can be ingested and the status of each is visible.
- [ ] Original documents are preserved and extracted facts retain evidence references.
- [ ] Unified Search returns relevant authorised records and supports key filters.
- [ ] Case Cockpit shows a Case Brief, timeline and source passages.
- [ ] Legal suggestions use an inspectable legal reference source and remain advisory.
- [ ] Identity matches are presented as candidates until appropriately reviewed.
- [ ] Relationship Explorer exposes evidence for each connection and has a table alternative.
- [ ] Document Studio creates editable, clearly marked drafts with review states.
- [ ] Copilot retrieves only authorised records and cites its answers or abstains.
- [ ] Hotspot analysis is available where source location data is sufficient; otherwise the limitation is explicit.
- [ ] Risk prediction is configured and evaluated only if the target is agreed; otherwise it is clearly not evaluated.
- [ ] AI-assisted outputs and human review actions are audit-traceable.
- [ ] Role/jurisdiction permission tests pass for UI, API, search, citations, exports and background tasks.
- [ ] Keyboard and accessibility checks cover core journeys.
- [ ] Demo uses approved/synthetic data and does not imply unapproved production integration.
- [ ] Evaluation claims include sample size, method, actual result and limitations.
- [ ] Open questions, risks and known limitations are documented for the judges and pilot team.

---

## 21. Glossary

| Term | Meaning in this PRD |
|---|---|
| Case Brief | Compact, source-cited overview of recorded case information |
| Entity resolution | Determining whether mentions across records may refer to the same real-world entity |
| Evidence-first AI | AI output accompanied by inspectable supporting source references and uncertainty |
| RAG | Retrieval-augmented generation: retrieving permitted source material before generating an answer |
| Human-in-the-loop | An authorised human reviews, corrects or approves consequential AI-assisted output |
| Candidate link | A possible relationship that is not yet confirmed by an authorised review process |
| Risk target | The precise outcome/label the model is intended to predict; must be defined by organisers |
| Source span | A page, paragraph, coordinate range or text segment in the original document supporting a fact |
| Synthetic data | Artificial test data that does not reproduce real sensitive case records |

---

## 22. Source and Assumption Register

### Official source used

**u-FIR Hackathon — Problem Statement (Source of Truth)**, supplied by the user. The document states that official challenge information was taken from the AI Living Labs Foundation challenge page:  
https://ailivinglabs.ap.gov.in/hackathon-arena/ai-enabled-unified-first-information-report-u-fir-a8eb

### Assumptions requiring validation

- Actual source document formats and language mix are not confirmed by the supplied brief.
- Actual officer roles and access boundaries are not specified.
- Specific legal provisions and authoritative legal source versions are not fully specified.
- Hosting and integration constraints are not specified.
- “Risk” and the >90% measurement are undefined in the brief.
- All detailed architecture, schemas, UI patterns, acceptance tests and prioritisation in this PRD are proposed designs for planning purposes.

**End of PRD.**
