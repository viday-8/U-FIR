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
