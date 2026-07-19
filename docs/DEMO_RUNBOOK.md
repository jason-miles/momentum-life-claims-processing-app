# Demo Runbook — Momentum Life Claims Processing

A click-by-click walk of the five demo scenarios (DS1–DS5) for the validation
session with Jurgens Krynauw and claims leadership. Each step lists exactly what
to click, what to say, and what to expect.

**Open with:** the *Claim Detail* page on `CLM-DISAB-DISCREP` — it's the single
most persuasive screen (unified case view + AI synopsis + discrepancy flags).

---

## Setup (before the room)

1. Start the serverless SQL warehouse (`dcb1c3dd8d1570d6`) — or let auto-start
   warm it with the first query.
2. Open the app: **Assessment Analytics Portal** (`momentum-claims-portal`).
3. Have the **Genie space** ("Momentum Claims Analyst") open in a second tab.
4. Confirm the three seeded claims resolve (Inbox → search `CLM-`).

---

## DS1 — Straight-through death claim (clean)  ·  proves SC1, SC2, SC4

**Claim:** `CLM-DEATH-CLEAN`

1. **Claims Inbox** → filter claim type = *death* → open `CLM-DEATH-CLEAN`.
2. **Claim Detail / left panel** — narrate the *unified case view*: policy in
   force ✔, death benefit R1,800,000 in force ✔, occupation consistent
   (Accountant = Accountant), **requirements 5/5 received**, VPD confirms
   deceased, timeline initiated → lodged → in_assessment.
   > *"Everything an assessor used to gather across ten screens, on one screen."*
3. **Right panel — AI Synopsis** — read the drafted, source-cited synopsis.
   Point out the citation chips `[POL] [DOC-…] [VPD]` and the
   **Recommend: PAY** (advisory) line.
   > *"The AI drafts; the assessor decides. It never issues the decision itself."*

**Expected:** clean synopsis, no discrepancy badges, recommend pay, every
material statement cited.

---

## DS2 — Complex disability claim (discrepancy)  ·  proves SC2, SC3

**Claim:** `CLM-DISAB-DISCREP` — **the money shot.**

1. **Inbox** → open `CLM-DISAB-DISCREP` (note the ⚠ mismatch badge in the queue).
2. **Left panel** — occupation **at inception: Clerk** vs **at claim: Boilermaker**
   (rendered in red), **requirements 4/5** with **REQ-SPECIALIST outstanding**.
3. **Right panel — AI Synopsis** — the agent flags:
   - ⚠ occupation-at-claim "Boilermaker" ≠ at-inception "Clerk"
   - ⚠ Outstanding: specialist medical report
   - **Recommend: REFER** to medical + request the outstanding report
   - Sources: `[POL] [DOC-91] [REQ-5] [silver.life]`
4. **Copilot** (right panel chat) → type: *"Has this life claimed elsewhere in
   the last 3 years?"* → read the grounded answer.

**Expected:** both planted discrepancies flagged, recommend refer, cited.

---

## DS3 — Suspicious claim (fraud signals)  ·  proves honest scoping, FR-FRD-1

**Claim:** `CLM-SUSPECT-FRAUD`

1. **Inbox** → open `CLM-SUSPECT-FRAUD`.
2. **Left panel** — event **50 days after inception** (early-claim), **benefit
   status: lapsed** (mismatch vs a claim being pursued).
3. **Right panel** — synopsis raises **early-claim** + **benefit-status** flags,
   **Recommend: INVESTIGATE**.
4. **Bottom bar** — point at the **fraud score `[MOCKED]`** and say so plainly.
   > *"Fraud scoring is mocked in this demo — the point is that the platform
   > surfaces the signals and routes to investigation. Real models are Phase 2+."*

**Expected:** early-claim + benefit flags, recommend investigate, clearly
labelled heuristic/mocked.

---

## DS4 — Assessor copilot / natural language  ·  proves SC4, SC7

Use the **AI Copilot** page (or the Genie tab). Ask, in order:

1. *"Which claims have an occupation mismatch?"*
2. *"Show me pre-lodge claims at risk of drop-off, highest first."*
3. *"What's the average cycle time for disability claims?"*
4. *"How many death claims were declined this year?"*
5. *"List outstanding requirements for CLM-DISAB-DISCREP."*

> *"This is the same Claude + retrieval + tool-calling pattern Leon du Plessis
> prototyped on pgvector — re-implemented natively on Vector Search and the
> Agent Framework, governed by Unity Catalog."* (SC7)

**Expected:** consistent terminology (NTU, SLA, occupation mismatch), correct
numbers matching the dashboards.

---

## DS5 — Manager / executive reporting  ·  proves SC5, SC6

1. **NTU / Ops Dashboard** — walk the NTU funnel by claim type, the **at-risk
   pre-lodge list** (sorted by drop-off propensity), SLA breaches, per-assessor
   throughput.
   > *"Drop-off — Not Taken Up — is where revenue leaks in the 1–2 weeks before
   > a claim is lodged. This is the early-warning list to act on."* (SC5)
2. **Executive View** — KPI tiles from the Metric Views (cycle time, NTU rate,
   SLA attainment, decision split), decision-split donut, embedded Genie box.
   Show it resizing for phone.
3. **The commercial line (SC6):**
   > *"Every chart here is governed AI/BI on the lakehouse — no per-seat Power BI
   > licence. This is the reporting you just started paying per-seat for, at no
   > per-seat cost."*

**Expected:** dashboards match the copilot's numbers; exec view is phone-friendly.

---

## Guardrails to name out loud

- The agent **never** issues a final pay/decline decision — advisory only.
- It says **"insufficient information"** rather than inferring when data is missing.
- Every synopsis is an **editable draft**; referrals are **human**.
- Every statement is **cited**; tool calls + citations are logged (MLflow traces).
- No unmasked PII beyond the caller's role (UC masking in production).

## If something misbehaves

- **Warehouse cold** → first query is slow; pre-warm before the room.
- **Agent slow/unavailable** → the app falls back to a UC-tool + `ai_query`
  synopsis; the discrepancy flags on the left panel are pure SQL and always render.
- **Genie odd answer** → fall back to the AI Copilot page or the dashboards.
