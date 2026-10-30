# Known limitations and open questions

Written for judges and the pilot team. Nothing here is hidden in the UI; most of it is shown on the Quality & Governance page.

## What this prototype is
A working end-to-end prototype on **synthetic** records modelled on common Excise offence patterns. No real record, accused person or live system is involved. It is not an official record system, and generated drafts are never official until a supervisor approves them.

## Measured quality (see the Quality & Governance page)
- Rule-based fact extraction on a **held-out set of 6 hand-labelled documents (37 facts)**: overall precision ≈ 84%, recall ≈ 84%. Vehicles, dates, quantities and items were perfect on this small set; **person recall was 56% and place precision 56%**. Known misses: initials with honorifics ("Sri B. Ramu", "Ch. Rajamma"), a person named only in a remand list, section strings with a trailing year, and "Vill." read as a place.
- The set is small, labelled by one person, synthetic and not double-annotated. Do not extrapolate. We have not measured OCR, Telugu, handwriting, search relevance, identity-match precision/recall or legal-suggestion quality on real data.
- Identity-match weights are hand-set, not learned. They are intentionally conservative (a name match alone, or a name plus a case-level vehicle, never links two people).

## Deliberately not done
- **Risk prediction: not configured.** The brief says “more than 90% accuracy in predicting risk” but defines neither risk, horizon, labels nor metric. We show “Not configured / not evaluated” and claim no accuracy figure.
- **Legal catalogue is a demo.** Four provisions, short paraphrases, no penalties, marked unverified in API and UI. Only AP Excise Act s34(a) and the existence of s46 vehicle proceedings were corroborated from public court orders. The department's legal team must supply and approve the authoritative provisions.
- **Offence type** tags are rule-based labels for browsing and filtering, not a legal classification. Each tag now shows the evidence that produced it (item, section or word, matched as whole words, including local terms such as *navasagaram* and *belt shop*), and an officer can correct the tags with a required reason; the correction, who made it and why are kept, audited, and drive the filters. The vocabulary was written from the seed cases and public typologies, so it will need tuning on real wording; up to three tags per case.
- **Scale (measured, not assumed).** Identity matching used to compare every pair of people. It now uses blocking (name sound × father/spouse or residence key), incremental refresh (only pairs touching a changed case) and a graph cache that any audited change invalidates. Tests prove the indexed result equals the exhaustive result on generated data and that incremental equals full. On a synthetic archive on one laptop (SQLite): 1,000 cases / 1,748 people: full refresh 0.5 s, one new case 0.09 s, graph 0.3 s. 5,000 cases / 8,725 people: full refresh 10.3 s (3.3% of 38 million possible pairs scored), one new case 1.3 s, graph 1.9 s. Limits: the synthetic archive uses a small name pool; tens of thousands of cases and Postgres were not tested; blocking relies on a link needing a father/spouse or residence match (true of the current scoring rule, so records with neither could not link anyway); the cache is per process, so a multi-instance deployment needs a shared cache.
- **Large networks.** The server returns at most 400 nodes by default (up to 1,500), only linked networks unless asked, or just one item's neighbourhood; the screen says “showing N of M”, the find box searches the whole archive, and rendering is lighter above 150 nodes. Browser rendering speed at 400+ nodes was not benchmarked; very dense networks still need the filters.
- **Upload leads** are still leads, not findings. They can now be decided in place with a reason (or left for the Review Queue); nothing is confirmed automatically.
- **Intake** reads document type and case number from headings such as “FIRST INFORMATION REPORT” and “Cr.No.: 041/2025”. Files that do not use these conventions are not auto-matched; the officer picks the case. Word support reads paragraphs and tables, not text boxes, headers or images.
- **OCR** uses open-source RapidOCR for scanned PDFs and images; it was tested only on clean synthetic scans, not on real, skewed, stamped or handwritten pages. OCR text is always marked and the document is sent to review. **Telugu** is detected and flagged for human review, but automatic extraction supports English only; name matching tolerates common transliteration variants (Sathya/Satya, Reddy/Reddi) via a small phonetic key that has not been validated on real names.
- No CCTNS or other system integration. No map (no coordinates in the text). No voice. No automated enforcement action of any kind.
- `Dockerfile` and `docker-compose.yml` are provided for deployment but were not built here (no Docker available).
- Auth is demo-grade (seeded users, JWT, login rate limit, admin-managed accounts). Production needs the department's identity provider, MFA and session policy; set `ENV=production` and a strong `JWT_SECRET`.
- Postgres is the intended pilot database (see README); SQLite is used for the demo.

## Design choices that limit harm
Allegations are shown as “recorded/named”, never as findings. Candidate links stay unconfirmed until a reviewer decides, with reasons, and are scoped to cases the reviewer can see. A restricted record looks identical to a missing one. Document text is treated as data (a prompt-injection line is seeded in a diary to prove it). Audit rows store references and outcomes, not document text.

## Open questions for the organisers
1. What exactly is “risk”, the horizon, the labels and the accuracy metric?
2. Format, languages and scan quality of the five years of records; can a sample and data dictionary be shared?
3. Which Acts and sections are in scope, and what is the authoritative, current legal source?
4. Roles, districts and assignment boundaries for access control.
5. Is CCTNS integration expected, or only a future option?
6. Hosting, data residency, retention, model-provider and audit policies.
7. Official templates and approval flow for case diaries and chargesheets.
8. May masked real records be used for demonstration?

## Case management (what it is and is not)
Plain record-keeping: accused status and custody dates, a seizure register with sample/lab status, tracked deadlines, and a checklist. **It is not a legal tool.** The 60/90-day chargesheet limit is chosen by the officer and the title says to confirm it with the prosecutor; the checklist's BNSS reference (s.105 audio-video recording) is unverified and must be confirmed by the department's legal cell. Dates are shown against the server's date. There are no SMS/WhatsApp reminders, no hand-over between officers, and no court outcome tracking.

## Roadmap: expected by officers, deliberately not built
Telugu forms and printouts; mobile and offline capture in low-connectivity areas; a real map with geocoded locations and jurisdiction boundaries; CCTNS/ICJS and transport-registration integration; digital signatures with QR verification; informer/tip-off log; habitual-offender register; inter-state alerts; monthly returns in the department's format; BNSS/BNS-aligned templates and legal catalogue (needs the legal cell's input).

## Branding
The badge, colour scheme and quotations are original or properly sourced. The interface uses the flag's *colours* only; it does not draw the national flag, the Ashoka Chakra, the State Emblem of India or any police emblem, because their use is legally restricted and a lookalike could be mistaken for an official mark. If the department authorises its own emblem, replace `frontend/src/Crest.tsx` and `frontend/public/favicon.svg`. The "attributed" Peel line is a traditional attribution whose exact authorship is debated.

## Language (Telugu)
The interface is available in English and Telugu. Translations were drafted by an AI assistant for this prototype: **they need review by a native Telugu speaker and the department's official terminology** (for example *అభియోగపత్రం* for chargesheet and *దర్యాప్తు* for investigation). Not translated: case content (extracted facts, quoted passages, document text, draft text), the legal catalogue, notices written by the server (some are English), and the more detailed forms and tables on secondary pages, which fall back to English instead of breaking. Extraction, search and the Copilot work on English text; Telugu documents are still flagged for human review (see Telugu extraction above). Dates and month names follow the chosen language; digits stay Latin.
