TRACK_ID=PS02
# ClaimLens AI 🔍⚖️ — Insurance Claims Evidence Review Assistant

> **Hackathon Problem Statement**: Insurance — Claims Evidence Review Assistant (`PS02`)  
> **Repository**: [https://github.com/vidhunkrishna/claimlens-ai.git](https://github.com/vidhunkrishna/claimlens-ai.git)

---

## 📌 Problem Statement & Solution

Motor insurance claim investigation requires evaluating unstructured and structured evidence from multiple independent sources:
1. **Claim Form**: Claimant details, loss date, vehicle registration, driver identity, estimated claim amount.
2. **Repair Estimate / Police FIR**: Parts replacement list, labor costs, or police incident intimation report.
3. **Customer Incident Description**: Written narrative explaining how, when, and where the loss occurred.
4. **Motor Insurance Policy Schedule & Master Terms**: Coverage clauses, exclusions, deductibles, and limits.

### The Challenge
Incomplete or contradictory claim evidence creates significant operational friction:
- **Cross-Document Inconsistencies**: Incident dates, driver names, or damaged parts reported in the claim form often conflict with police reports or garage estimates.
- **Subjective Review Bias**: Manual review of long policy documents and unstructured statements leads to inconsistent claim decisions.
- **Hallucination Risk**: Off-the-shelf LLMs used without strict grounding can invent policy clauses or hallucinate non-existent evidence.

### What ClaimLens AI Does
**ClaimLens AI** is an evidence-grounded AI copilot that automates document processing while maintaining strict human-in-the-loop oversight:
- **Ingestion & Fact Normalization**: Parses JSON claim packages and extracts structured facts with source provenance.
- **7 Deterministic Insurance Rules**: Programmatically enforces policy windows, intoxication exclusions, DL requirements, repair-to-IDV ratios, deductibles, and key surrender rules.
- **Local Vector Policy RAG**: Retrieves relevant policy clauses from master terms using in-memory TF-IDF and Cosine Similarity vector indexing.
- **Gemini Reasoning**: Uses Gemini (`gemini-3.6-flash`) for semantic text comparison and policy relevance evaluation.
- **Pairwise Contradiction Detection**: Programmatically compares dates, driver identities, locations, and damaged parts across documents.
- **Structured 9-Section Report**: Assembles a audit-ready report with exact source citations.

### Adjudication Outcomes
- **`APPROVE`**: Clean claim, complete evidence, zero contradictions, all rules pass (`ConfidenceLevel.HIGH`).
- **`REJECT`**: Explicit policy exclusion breach (e.g., Drunk driving `POL-002`, Expired license `POL-003`, CTL threshold `POL-014`).
- **`REQUEST INFORMATION`**: Missing mandatory documentation or unverified policy condition (`ConfidenceLevel.MEDIUM`).
- **`ESCALATE FOR INVESTIGATION`**: Cross-document evidence contradictions detected or unknown policy applicability (`ConfidenceLevel.LOW`). **ClaimLens AI refuses to smooth over conflicting evidence.**

---

## 👤 Human-in-the-Loop Boundary & Safeguards

ClaimLens AI is designed strictly as an **investigator copilot**, not an autonomous claim denial/approval engine:

| Automated Tasks by ClaimLens AI | Human Investigator Responsibility |
| :--- | :--- |
| Extracting facts & source provenance from documents | Evaluating physical vehicle damage or field inspection notes |
| Evaluating 7 programmatic insurance policy rules | Making final legally binding claim approval or rejection decisions |
| Flagging cross-document contradictions & date mismatches | Resolving flagged contradictions via claimant interviews |
| Retrieving relevant policy clauses via local vector RAG | Approving policy exception waivers or special approvals |
| Assembling structured 9-section investigation report | Reviewing itemized escalation checklist before payout |

### Mandatory Escalation Triggers
The system automatically sets `requires_human_review = True` and downgrades confidence to `LOW` when:
1. One or more cross-document contradictions are detected (e.g. date mismatch, driver mismatch).
2. Mandatory documentation (Claim Form, FIR/Estimate, Incident Statement) is missing.
3. Policy coverage applicability is marked `UNKNOWN` or ambiguous.
4. Gemini API fallback mode is triggered (missing key, timeout, or network exception).

---

## 🛡️ Grounded GenAI & Anti-Hallucination Architecture

- **Targeted Gemini Role**: Gemini (`gemini-3.6-flash` via `google-genai` SDK) is used exclusively for high-level semantic reasoning over unstructured narrative statements.
- **Strict Prompt Grounding**: Prompts contain ONLY explicit evidence document IDs (e.g. `DOC-CLM001-CF`) and policy clause IDs (`POL-002`).
- **Deterministic Source Grounding**: The final report builder retrieves exact source document excerpts and policy text directly from stored memory (BaseDocument and motor_policy.json) rather than relying on LLM text generation. The model is restricted from inventing or paraphrasing source quotations.
- **Offline Fallback Mode**: If `GEMINI_API_KEY` is missing, unconfigured, or network fails, `create_fallback_reasoning_output()` gracefully routes the case to `MANUAL REVIEW REQUIRED` without crashing or returning HTTP 500 errors.

---

## 🏗️ System Architecture & Data Flow

```text
                               ┌─────────────────────────┐
                               │ Raw Claim Documents     │
                               │ (JSON / Uploaded Package)│
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Ingestion & Validation  │
                               │ Fact Extraction + Schema│
                               └────────────┬────────────┘
                                            │
                                ┌───────────┴───────────┐
                                ▼                       ▼
                   ┌────────────────────────┐ ┌────────────────────┐
                   │ 7 Programmatic Rules   │ │ Pairwise           │
                   │ (Completeness, DL,     │ │ Contradiction      │
                   │ Delay, Deductible, etc)│ │ Detector           │
                   └────────────┬───────────┘ └─────────┬──────────┘
                                │                       │
                                └───────────┬───────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Local Vector RAG        │
                               │ (TF-IDF & Cosine Search)│
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Gemini 3.6 Flash        │
                               │ Semantic Reasoning      │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Citation Sanitization & │
                               │ 9-Section Report Builder│
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Human Claims            │
                               │ Investigator Dashboard  │
                               └─────────────────────────┘
```

---

## 📁 Repository Structure

```text
claimlens-ai/
├── app.py                      # Single-command entrypoint (Serves API & Frontend on port 8000)
├── requirements.txt            # Python dependencies (FastAPI, Uvicorn, Pydantic, Gemini, NumPy, Pytest)
├── README.md                   # Hackathon submission documentation (First line: TRACK_ID=PS02)
├── .env.example                # Environment variable template
├── src/                        # Modular Python backend package
│   ├── api/                    # FastAPI route handlers
│   │   ├── health.py           # System & API health endpoints
│   │   ├── ingestion.py        # Document ingestion API
│   │   ├── rules.py            # Programmatic rules evaluation API
│   │   ├── contradictions.py   # Cross-document contradiction API
│   │   ├── retrieval.py        # Vector policy retrieval RAG API
│   │   ├── reasoning.py        # Gemini AI reasoning API
│   │   ├── investigation.py    # Complete 9-section investigation review API
│   │   └── main.py             # FastAPI app factory & static file mounting
│   ├── core/                   # Application settings (Pydantic BaseSettings & .env support)
│   ├── models/                 # Strongly-typed Pydantic schemas
│   │   ├── evidence.py         # Document & normalized package models
│   │   ├── rules.py            # Rule result models
│   │   ├── contradictions.py   # Pairwise contradiction models
│   │   ├── retrieval.py        # Policy retrieval match models
│   │   ├── gemini_reasoning.py # Gemini structured output models
│   │   └── investigation_report.py # 9-section report & confidence models
│   └── services/               # Decoupled domain service layer
│       ├── document_loader.py  # File loading & typed document parsing
│       ├── document_validator.py # Document completeness validator
│       ├── fact_extractor.py   # Fact extraction with source provenance
│       ├── ingestion_service.py # Ingestion pipeline orchestrator
│       ├── rules_engine.py     # 7 deterministic insurance rules
│       ├── contradiction_detector.py # Pairwise cross-document evidence checker
│       ├── retrieval_service.py # Local policy clause vector index (NumPy TF-IDF)
│       ├── citation_validator.py # Anti-hallucination citation validator
│       ├── gemini_service.py   # Gemini 3.6 Flash service with safe fallback
│       └── investigation_engine.py # Pipeline orchestrator & report builder
├── static/                     # Built investigator web frontend (Single-Page Application)
│   ├── index.html              # Dashboard UI template
│   ├── styles.css              # Glassmorphism design system
│   └── app.js                  # Frontend controller & interactive evidence drawers
├── data/                       # Local dataset & policy files
│   ├── policy/                 # Master motor policy terms (motor_policy.json)
│   ├── claims/                 # Synthetic claim packages (CLM-001 to CLM-005)
│   └── upload_fixtures/        # Custom JSON upload fixtures for testing
└── tests/                      # 75 automated pytest verification tests
```

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2, Pydantic-Settings, python-dotenv
- **AI & Reasoning**: Gemini API (`gemini-3.6-flash`) via `google-genai` SDK
- **Vector Retrieval (RAG)**: In-memory vector policy search using TF-IDF & Cosine Similarity (`numpy`) over `motor_policy.json` (Zero external vector database dependency)
- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Vanilla CSS3 (Glassmorphism design system), served directly by FastAPI static files (`StaticFiles`)
- **Testing**: `pytest` with `fastapi.testclient` (75 passing tests)

---

## 📄 Dataset & Documents Created

Located in `data/claims/`, `data/policy/`, and `data/upload_fixtures/`:
1. **Master Motor Policy Terms (`data/policy/motor_policy.json`)**:
   - 14 policy clauses (`POL-001` through `POL-014`) covering accidental damage, theft, intoxication exclusions, reporting windows, IDV valuation limits, deductible rules, and key surrender requirements.
2. **Synthetic Claims Suite (`CLM-001` to `CLM-005`)**:
   - **`CLM-001`**: Clean accidental damage claim for private car (Expected: `APPROVE`).
   - **`CLM-002`**: Severe contradiction claim with 7 cross-document mismatches (Expected: `ESCALATE FOR INVESTIGATION`).
   - **`CLM-003`**: Drunk driving exclusion claim with FIR recording BAC 0.12% (Expected: `REJECT`).
   - **`CLM-004`**: 55-day intimation delay exceeding 7-day reporting window & missing driver license (Expected: `REQUEST INFORMATION`).
   - **`CLM-005`**: Parked EV total theft claim with police FIR and key declaration compliance (Expected: `APPROVE`).
3. **Upload Fixtures (`data/upload_fixtures/`)**: Pre-formatted JSON documents for testing custom file uploads in the UI.

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

## 🚀 How to Run (Single Terminal Command)

### 1. Installation
Install the required Python dependencies:
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration (Optional for Gemini)
Set your Gemini API key in a local `.env` file or environment variable:
```bash
# In .env or shell environment:
GEMINI_API_KEY=your_gemini_api_key_here
```
*(If no API key is provided, ClaimLens AI operates seamlessly in offline fallback mode).*

### 3. Launch Server
Start the unified application with a single command:
```bash
python app.py
```

The application will launch on: **[http://localhost:8000](http://localhost:8000)**

---

## 🎯 Demo & Judging Walkthrough

1. Open **[http://localhost:8000](http://localhost:8000)** in your browser.
2. **Preset Demo 1 (Clean Claim — Approval)**: Click **CLM-001** preset card. Watch the 6-step analysis progress bar and view the green `APPROVE` report (`ConfidenceLevel.HIGH`).
3. **Preset Demo 2 (Contradiction Claim — Escalation)**: Click **CLM-002** preset card. View the purple `ESCALATE FOR INVESTIGATION` report (`ConfidenceLevel.LOW`) and inspect 7 cross-document evidence contradictions. Click `[View Evidence]` on any finding to open the source document viewer.
4. **Preset Demo 3 (Exclusion Claim — Rejection)**: Click **CLM-003** preset card. View the red `REJECT` report highlighting the Drunk Driving Exclusion clause breach (`POL-002`).
5. **Custom Upload Demo**: Navigate to **Upload & Select** tab. Click the upload dropzones to select custom JSON documents (e.g. from `data/upload_fixtures/CLM-004/`), then click **Initiate Investigation**.

For full step-by-step judge instructions, refer to [`demo/README.md`](file:///c:/Users/vidhu/Downloads/Claim-lens/demo/README.md).

---

## 📹 Demo Video

- **Video URL Placeholder**: [ClaimLens AI Demo Video](#) *(Video demonstration of preset analysis, contradiction detection, custom upload, and report viewing).*

---

## 🧪 Testing

Run the complete 75-test automated verification suite:
```bash
pytest tests -q
```
**Result**: `75 passed in 2.23s`

---

## 🏆 Engineering Quality & Hackathon Compliance

- **Strict Separation of Concerns**: Programmatic rules engine and pairwise contradiction checker execute deterministically before GenAI reasoning is invoked.
- **Type Safety & Schemas**: End-to-end Pydantic v2 data models for evidence documents, rule outputs, contradiction reports, RAG matches, and 9-section investigation reports.
- **Graceful Failure**: Automatic fallback to `MANUAL REVIEW REQUIRED` ensures zero application crashes during LLM timeouts or missing API keys.
- **One-Command Startup**: Complies fully with the hackathon requirement (`python app.py` serving backend & frontend on port 8000).
- **Python Backend**: Pure Python/FastAPI implementation matching track `PS02` specifications.

---

## 📜 License
MIT License — ClaimLens AI Team
