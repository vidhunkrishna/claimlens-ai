# ClaimLens AI — Judge Demo Guide (2–5 Minutes)

This guide provides a step-by-step walkthrough for testing and judging **ClaimLens AI** (`TRACK_ID=PS02`).

---

## 🚀 Quick Launch (Single Terminal Command)

```bash
pip install -r requirements.txt
python app.py
```

Open your browser and navigate to: **[http://localhost:8000](http://localhost:8000)**

---

## 🎬 Demo Scenario 1: Clean Normal Claim (`CLM-001`)

**Goal**: Demonstrate automated adjudication of a clean, fully consistent accidental damage claim.

1. **Step 1**: On the Dashboard screen of **[http://localhost:8000](http://localhost:8000)**, click on the **CLM-001 Card** (`Analyze CLM-001 →`).
2. **Step 2**: Watch the **Analysis Progress Bar** (Ingestion → Rules → Contradictions → RAG Retrieval → Gemini Reasoning → Final Report Assembly).
3. **Step 3**: Inspect the **Investigation Report**:
   - **Executive Decision Result**: `APPROVE` (Green Banner).
   - **Evidence Confidence**: `HIGH`.
   - **Document Completeness**: `✓ Claim Form`, `✓ Repair Estimate`, `✓ Incident Statement`.
   - **Consistency Analysis**: `0 Contradictions Detected`.
   - **Policy Analysis**: Supporting clause `POL-001` (Accidental Damage Coverage) displayed with exact stored clause text.
   - **Deterministic Rules**: All 7 rules show `PASS`.
   - **Human Review**: `No human escalation required`.

---

## 🎬 Demo Scenario 2: Difficult Contradiction Claim (`CLM-002`)

**Goal**: Demonstrate that ClaimLens AI **refuses to smooth over conflicting evidence** and surfaces contradictions for human investigator review.

1. **Step 1**: Click **Dashboard** in top navigation, then click the **CLM-002 Card** (`Analyze CLM-002 →`).
2. **Step 2**: Observe the progress breakdown as the contradiction engine runs pairwise cross-document analysis.
3. **Step 3**: Inspect the **Investigation Report**:
   - **Executive Decision Result**: `ESCALATE FOR INVESTIGATION` (Purple Banner).
   - **Evidence Confidence**: `LOW`.
   - **Critical Warning Box**: `⚠️ CRITICAL: HUMAN INVESTIGATOR REVIEW REQUIRED`.
   - **Contradiction Cards (Side-by-Side Evidence UX)**:
     - **Incident Date Mismatch**: Claim Form (`12 August 2026`) vs Police FIR (`14 August 2026`).
     - **Incident Location Mismatch**: Claim Form (`Andheri West`) vs Police FIR (`Bandral Kurla Complex / BKC`).
     - **Driver Identity Mismatch**: Claim Form (`Suresh Patel`) vs Incident Statement (`Priya Sharma`).
     - **Damaged Parts Mismatch**: Claim Form (`Front Bumper & Headlight`) vs Repair Estimate (`Rear Mudguard & Tail Light`).
   - **Interactive Evidence Viewer**: Click `[View Evidence]` on any card to reveal raw source text snippets.

---

## 🎬 Demo Scenario 3: Policy Exclusion Rejection (`CLM-003`)

**Goal**: Demonstrate policy exclusion enforcement.

1. **Step 1**: Click **Analyze CLM-003 →**.
2. **Step 2**: Inspect decision:
   - **Executive Decision Result**: `REJECT` (Red Banner).
   - **Policy Exclusion**: `POL-002` (Intoxication & Substance Abuse Exclusion).
   - **Evidence Finding**: Police FIR records BAC `0.12%` and charges under `Sec 185 Motor Vehicles Act`.
