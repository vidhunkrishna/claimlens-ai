TRACK_ID=PS02
# ClaimLens AI 🔍⚖️ — Insurance Claims Evidence Review Assistant

> **Hackathon Problem Statement**: Insurance — Claims Evidence Review Assistant (`PS02`)  
> **Repository**: [https://github.com/vidhunkrishna/claimlens-ai.git](https://github.com/vidhunkrishna/claimlens-ai.git)

---

## 📌 Problem Statement & Solution

Motor insurance claim investigation requires evaluating unstructured and structured evidence from multiple independent sources:
1. **Claim Form** (Claimant info, loss date, vehicle details, driver details)
2. **Repair Estimate or Police FIR** (Parts list, labor costs, police incident report)
3. **Customer Incident Description** (Statement explaining how, when, and where the event occurred)
4. **Motor Insurance Policy Schedule & Master Terms** (Coverage clauses, exclusions, limits, deductibles)

**ClaimLens AI** is an evidence-grounded AI review assistant that automates document ingestion, evaluates document completeness, runs 7 deterministic insurance rules, detects pairwise cross-document contradictions, performs local RAG policy retrieval, and synthesizes structured 9-section investigation reports.

### Adjudication Decisions
- **`APPROVE`**: Clean claim, complete evidence, zero contradictions, all rules pass (`ConfidenceLevel.HIGH`).
- **`REJECT`**: Explicit policy exclusion breach (e.g. Drunk driving `POL-002`, Expired license `POL-003`, Repair exceeding IDV `POL-014`).
- **`REQUEST INFORMATION`**: Missing mandatory documentation or rule check requiring clarification.
- **`ESCALATE FOR INVESTIGATION`**: Cross-document evidence contradictions detected or unknown policy applicability (`ConfidenceLevel.LOW` or `UNKNOWN`). **ClaimLens AI refuses to smooth over conflicting evidence.**

---

## 🏗️ System Architecture

```text
claimlens-ai/
├── app.py                      # Main entrypoint (Serves backend & frontend on port 8000)
├── requirements.txt            # Lightweight Python dependencies
├── README.md                   # Hackathon submission documentation (First line: TRACK_ID=PS02)
├── .env.example                # Environment variable template (GEMINI_API_KEY)
├── .gitignore                  # Git ignore definitions
├── src/                        # Modular source code
│   ├── api/                    # FastAPI route handlers
│   │   ├── health.py           # Health endpoints (/health, /api/v1/health)
│   │   ├── ingestion.py        # Document ingestion endpoints
│   │   ├── rules.py            # Deterministic rules evaluation endpoints
│   │   ├── contradictions.py   # Cross-document contradiction detection endpoints
│   │   ├── retrieval.py        # Local vector RAG policy retrieval endpoints
│   │   ├── reasoning.py        # Gemini AI reasoning endpoints
│   │   ├── investigation.py    # Complete 9-section investigation review endpoints
│   │   └── main.py             # FastAPI app factory & static file mount
│   ├── core/                   # Application config & Pydantic BaseSettings
│   ├── models/                 # Pydantic data schemas
│   │   ├── evidence.py         # Evidence document & normalized package models
│   │   ├── rules.py            # Deterministic rule result models
│   │   ├── contradictions.py   # Pairwise contradiction models
│   │   ├── retrieval.py        # Policy retrieval query & match models
│   │   ├── gemini_reasoning.py # Gemini structured reasoning models
│   │   └── investigation_report.py # 9-section final report & confidence models
│   └── services/               # Decoupled domain services
│       ├── document_loader.py  # JSON file loading & typed document parsing
│       ├── document_validator.py # Document completeness & schema validator
│       ├── fact_extractor.py   # Normalized fact extraction with source provenance
│       ├── ingestion_service.py # End-to-end ingestion pipeline
│       ├── rules_engine.py     # 7 deterministic insurance rules
│       ├── contradiction_detector.py # Pairwise cross-document evidence checker
│       ├── retrieval_service.py # Local policy clause vector RAG index
│       ├── citation_validator.py # Citation sanitization & anti-hallucination layer
│       ├── gemini_service.py   # Gemini 2.5 Flash reasoning with safe fallback
│       └── investigation_engine.py # Pipeline orchestrator & report builder
├── static/                     # Built investigator web frontend (HTML5/CSS3/Vanilla JS)
│   ├── index.html              # Judge dashboard SPA template
│   ├── styles.css              # Glassmorphism design system & status badges
│   └── app.js                  # Frontend controller & interactive evidence drawers
├── data/                       # Local dataset & master policy
│   ├── policy/                 # Master motor policy terms (motor_policy.json)
│   └── claims/                 # Synthetic claim packages (CLM-001 to CLM-005)
├── demo/                       # Demo walkthrough guide for hackathon judges
│   └── README.md               # 2-5 minute step-by-step judge testing guide
└── tests/                      # 70 automated pytest verification tests
```

---

## 🛠️ Technology Stack

- **Core**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2
- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Vanilla CSS3 (Glassmorphism design system), served directly by FastAPI static files (`StaticFiles`)
- **AI & LLM Reasoning**: Gemini API (`gemini-2.5-flash`) via `google-genai` SDK
- **Local Retrieval (RAG)**: In-memory vector policy index over `motor_policy.json` (Zero external vector databases)
- **Testing**: `pytest` with `fastapi.testclient`

---

## 📄 Dataset & Documents Created

Located in `data/claims/` and `data/policy/`:
1. **Master Motor Policy Schedule (`data/policy/motor_policy.json`)**:
   - 14 clauses (`POL-001` through `POL-014`) covering accidental damage, theft, intoxication exclusions, reporting windows, IDV valuation limits, deductible rules, and key surrender requirements.
2. **Synthetic Claims Suite (`CLM-001` to `CLM-005`)**:
   - **`CLM-001`**: Clean accidental damage claim for private car (Expected: `APPROVE`).
   - **`CLM-002`**: Severe contradiction claim with 7 cross-document mismatches in date, location, driver identity, and damaged parts (Expected: `ESCALATE FOR INVESTIGATION`).
   - **`CLM-003`**: Drunk driving exclusion claim with police FIR recording BAC 0.12% (Expected: `REJECT`).
   - **`CLM-004`**: 55-day intimation delay exceeding 7-day reporting window & missing driver license (Expected: `REQUEST INFORMATION`).
   - **`CLM-005`**: Parked EV total theft claim with police FIR and key declaration compliance (Expected: `APPROVE`).

---

## ⚙️ Deterministic Insurance Rules Engine

ClaimLens AI enforces 7 programmatic rules BEFORE AI reasoning:
1. `RULE-DOC-COMPLETENESS` (`POL-010`): Checks presence of Claim Form, FIR/Estimate, and Incident Statement.
2. `RULE-CLAIM-WINDOW` (`POL-007`/`POL-009`): Verifies intimation delay vs mandatory 7-day window (2-day for theft).
3. `RULE-DRIVER-LICENSE` (`POL-003`): Validates driving license availability and expiry date.
4. `RULE-INTOXICATION-EXCLUSION` (`POL-002`): Checks blood alcohol concentration (BAC) and MVA charges.
5. `RULE-REPAIR-VS-IDV` (`POL-008`/`POL-014`): Evaluates repair estimate vs Insured Declared Value (75% CTL warning, 100% limit breach).
6. `RULE-DEDUCTIBLE-CALCULATION` (`POL-013`): Computes compulsory deductible based on vehicle type and engine CC.
7. `RULE-THEFT-KEY-SURRENDER` (`POL-012`): Verifies surrender of both original ignition keys for theft claims.

---

## 🤖 Gemini Reasoning & Citation Fidelity

- **Role**: Gemini (`gemini-2.5-flash`) interprets unstructured text statements, compares semantic descriptions, and explains policy relevance.
- **Strict Evidence Grounding**: Gemini is provided ONLY evidence IDs (e.g. `DOC-CLM001-CF`) and policy IDs (`POL-002`) in its prompt context.
- **100% Citation Text Fidelity**: The final report builder retrieves exact source document excerpts and policy text directly from stored memory (`BaseDocument` and `motor_policy.json`). **The LLM is forbidden from inventing or outputting source quotations.**
- **Safe Fallback**: If `GEMINI_API_KEY` is unconfigured, network times out, or output is unparseable, `create_fallback_reasoning_output()` routes the case safely to `MANUAL REVIEW REQUIRED` without throwing HTTP 500 errors.

---

## 🔎 Contradiction Detection & Human Escalation

- **Pairwise Cross-Checker**: Programmatically compares facts extracted across all documents.
- **Checked Fields**: Incident date, repair estimate date, driver identity, incident location, damaged parts vs estimate line items, vehicle registration, incident time.
- **Never Guess Principle**: When evidence contradicts or documentation is missing, ClaimLens AI sets `requires_human_review = True`, assigns `ConfidenceLevel.LOW`, and generates an itemized escalation checklist.

---

## 🚀 How to Run (Single Terminal Command)

### 1. Installation
Install the lightweight Python dependencies:
```bash
pip install -r requirements.txt
```

### 2. Environment Variable (Optional for Gemini)
Set your Gemini API Key in environment or `.env`:
```bash
export GEMINI_API_KEY=your_gemini_api_key_here
```
*(If no API key is provided, the application runs deterministically in offline fallback mode).*

### 3. Launch Application
Start the unified application server with a single command:
```bash
python app.py
```

The application will launch on: **[http://localhost:8000](http://localhost:8000)**

---

## 🎯 Demo & Judging Walkthrough

1. Open **[http://localhost:8000](http://localhost:8000)** in your browser.
2. **Demo 1 (Normal Claim)**: Click **CLM-001** preset card. Watch 6-step progress indicator and view the green `APPROVE` report (`ConfidenceLevel.HIGH`).
3. **Demo 2 (Difficult Contradiction Claim)**: Click **CLM-002** preset card. View the purple `ESCALATE FOR INVESTIGATION` report (`ConfidenceLevel.LOW`) and inspect the side-by-side evidence contradiction cards (Date mismatch: 12 Aug vs 14 Aug, Location mismatch: Andheri vs BKC, Driver mismatch, Damaged parts mismatch). Click `[View Evidence]` to inspect raw document source text.

For full step-by-step judge instructions, refer to [`demo/README.md`](file:///c:/Users/vidhu/Downloads/Claim-lens/demo/README.md).

---

## 🧪 Testing

Run the complete 70-test automated verification suite:
```bash
pytest tests -v
```
**Results**: `70 passed in 1.34s`

---

## ⚠️ Known Limitations

1. **Synthetic Data**: Operating on synthetic motor claim datasets; real-world claims require OCR preprocessing for raw PDF scans.
2. **Single-Vehicle Focus**: Current policy schema is tailored for private cars and two-wheelers.

---

## 📜 License
MIT License — ClaimLens AI Team
