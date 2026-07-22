# Presenter Cheat-Sheet — Momentum Life demo (one page)

The tight talk track. For click-by-click detail see DEMO_RUNBOOK.md (claims) /
UW_DEMO_RUNBOOK.md (underwriting). App:
https://momentum-claims-portal-7474654808133980.aws.databricksapps.com

**Before you start:** warehouse warm? (Medium, 120-min auto-stop — fire any page
~2 min early if it auto-stopped). Open on the **Executive Overview**.

---

## The one-line pitch
> "One governed platform — Unity Catalog, Mosaic AI, AI/BI — across both
> underwriting and claims. You don't need another tool."

## The arc (≈10 min)
1. **Executive Overview (`/`)** — "Both books, one screen." UW: 29.9% STP,
   28.9% NTU, 19d turnaround · Claims: 13.8d cycle, 17.3% NTU, 75.7% SLA.
   *"One governed lakehouse; no per-seat licence."*
2. **Underwriting Co-Pilot (`/underwriting`)** — the hero. Pick **UW-NTU-RISK**.
   - Left: unified case view (AS400 + BPM + notepad, keyed on policy no) —
     *"kills the swivel chair."*
   - Right: AI risk synopsis (advisory, never binds) + **91% NTU propensity**
     with interventions. *"Predict drop-off, act before the case goes quiet."*
   - Point at "Similar prior cases · [VS:notes]" — *"Vector Search over the
     notepad — Leon's pgvector POC, re-built natively and governed."*
3. **UW Analytics (`/uw-analytics`)** — journey split, decision mix, **NTU
   drop-off** (62% "requirements never returned" — *"a single addressable failure
   mode"*). Then the Genie box: type *"Which open cases set requirements over 14
   days ago with no result, ranked by sum at risk?"*
4. **Claims Co-Pilot + Claim Detail** — open **CLM-DISAB-DISCREP**: occupation
   **Clerk ≠ Boilermaker** (red) + outstanding specialist report → synopsis
   recommends REFER, every claim cited. *"The AI drafts; the assessor decides."*
5. **Executive views / dashboards** — *"Same governed metrics, exec-ready, replacing
   the Power BI roll-ups."*

## Landmines to avoid (say these)
- **Not replacing AS400 or IBM BPM** — Databricks owns the governed read layer +
  AI assist + analytics. Phasing: analytics now → unified case view → operational.
- **Synthetic data**; fraud scores are **[MOCKED]** (Phase 2+).
- **Residency:** production targets **eu-west-1 (Ireland)** — out of the USA.
  (af-south-1 isn't a Databricks region.)

## If asked "is it real?"
- Vector Search RAG (cited), Claude synopsis (advisory-only, guardrailed), Genie
  NL, UC Metric Views, 2 MLflow agent evals at 1.0, 2 security reviews passed.

## Confirm-before-ROI (open questions to raise, not answer)
Underwriter headcount (15–50?) · AS400 CDC mechanism/latency · FileNet volume/
formats · agreed "real-time" definition · Power BI coexist-or-replace.

## If something lags
First click after idle = warehouse cold-start (~20s) — pre-warm. AI synopsis is
~5s (Haiku); seeded cases are pre-cached on app start, so open them first.
