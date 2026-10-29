# Demo script (7–9 minutes, one case, synthetic data)

Run `./run_demo.sh`, open http://localhost:8000. The banner always says DEMO · SYNTHETIC DATA. Use one story throughout: **Ramesh Babu Naidu**, a repeat offender across three Narsipatnam cases, with a spelling-variant record in Guntur.

| Time | Screen | Say / do | PRD |
|---|---|---|---|
| 0:00 | Slide / Cases | Problem: free-text Excise files; officers search by hand, miss repeat offenders, retype diaries. We add an intelligence layer over existing records; officers change nothing. | C1 |
| 0:30 | Upload Case Files | Drop a Word FIR, a panchanama and a diary: the system reads each, detects the type, matches the diary to its existing case, offers to create the new case (date pre-filled), rejects a bad file, and flags a duplicate. Upload → processed in seconds. | C1, O1 |
| 0:45 | Command Center (`sup_vizag`) | Pipeline of 13 processed documents, needs-attention list, honest counts. Every tile opens a filtered list. | O1 |
| 1:30 | Cases → EXC/NRP/041/2025 | The Case Brief. Click “Ramesh Babu Naidu … is named in the records” → the exact sentence highlights in the original FIR. Point out “named in the records”, never “guilty”. Show Missing/Conflicts. | C2 |
| 2:15 | Case → Documents | Upload a scanned panchanama image: OCR reads it, it is badged “OCR text” and goes to review. Facts tab: correct a fact; the old value, who and why are kept. Review Queue: mark the scan reviewed with a note (it leaves the queue and is audited). | C1, EXT-06 |
| 2:30 | Search | Type `Rameshbabu Naidu`: finds Ramesh Babu Naidu, original spellings kept, with why each matched. | C1 |
| 3:15 | Relationships | Dashed line = possible match, not auto-merged. Open “Why linked?”: father match, same village, same vehicle AP 31 TX 4521; age not recorded (shown as missing). Confirm with a reason. Note the two “Lakshmi Devi” records are NOT linked. | C4, O3 |
| 4:30 | Case → Legal | Suggest provisions. Banner: demo catalogue, unverified. Each suggestion cites passage and facts; Accept with a reason. | C3 |
| 5:15 | Drafts → Chargesheet | Draft from facts; yellow placeholders block submission; “persons named (officer to confirm who is charged)”. Fill, request review. Switch to `inv_vizag` → cannot approve; switch to `sup_vizag` → approve. Export. | C5, O2 |
| 6:30 | Copilot | “Which cases involve vehicle AP 31 TX 4521?” → cited quotes. As `inv_vizag` ask “Where was Munaswamy found?” → “Not found” (that case is Chittoor’s). | O5 |
| 7:15 | Audit Ledger + Quality & Governance | Every AI output and decision is logged. Show the held-out extraction scores **including the misses**, and Risk = “Not configured”: the brief never defines risk, so we refuse to invent a score. | Reviewable AI |
| 8:15 | Hotspots + close | Hotspots by place/station with coverage caveats; no map because text has no coordinates. Close with limits and open questions (docs/LIMITATIONS.md). | O4 |

## Accounts (password `demo123`)
`sup_vizag` (approve/audit) · `inv_vizag` (investigate) · `analyst_vizag` (read-only) · `inv_chittoor` · `inv_guntur` · `admin` (all districts, sees the cross-district Guntur link).

## If something goes wrong
Re-run `./run_demo.sh` (re-seeds everything). All state is local SQLite.
