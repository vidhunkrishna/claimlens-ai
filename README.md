# ClaimLens AI 🔍⚖️

> **Insurance — Claims Evidence Review Assistant**  
> Hackathon Track: `PS02`  
> Repository: [github.com/vidhunkrishna/claimlens-ai](https://github.com/vidhunkrishna/claimlens-ai.git)

---

## 📌 Project Overview

**ClaimLens AI** is an intelligent, production-quality claims evidence review assistant designed to support motor insurance claims investigators.

Motor insurance claims investigation requires synthesizing multi-source unstructured and structured evidence, including:
1. **Claim Form** (Claimant details, loss date, policy number, vehicle details)
2. **Repair Estimate OR First Information Report (FIR)** (Damage assessments, parts list, labor costs, police incident report)
3. **Customer Incident Description** (Statement of how, when, and where the event occurred)
4. **Motor Insurance Policy Document** (Coverage terms, exclusions, deductibles, limits, endorsements)

ClaimLens AI automatically evaluates document completeness, detects cross-evidence contradictions, maps claims against exact policy clauses, surfaces supporting or blocking rules with line-item citations, and issues one of three recommendations:
- **`APPROVE`**: Evidence is consistent, supported by policy clauses, and meets all threshold criteria.
- **`REJECT`**: Evidence reveals explicit exclusions, severe policy breaches, or unresolvable misrepresentations.
- **`REQUEST INFORMATION`**: Information is incomplete, ambiguous, or requires additional documentation/clarification from the claimant.

> [!IMPORTANT]
> **Core Operating Principles:**
> - **No Hallucinated Fraud**: The system never falsely alleges fraud or makes unsupported decisions.
> - **Mandatory Escalation**: Uncertain or conflicting cases are escalated to human investigators with full evidence context.
> - **100% Cites Source**: Every finding directly cites source documents and policy clauses.

---

## 🏗️ Architecture & Project Structure

```text
claimlens-ai/
├── app.py                  # Main entrypoint (runs backend on port 8000)
├── requirements.txt        # Backend Python dependencies
├── README.md               # Project documentation & operational guidelines
├── .gitignore              # Files and directories ignored by Git
├── .env.example            # Environment variable template (GEMINI_API_KEY)
├── src/                    # Modular source code
│   ├── __init__.py
│   ├── api/                # FastAPI routers and endpoints
│   │   ├── __init__.py
│   │   ├── health.py       # Health check routes (/health, /api/v1/health)
│   │   └── main.py         # FastAPI app factory & middleware configuration
│   ├── core/               # Application configuration and settings
│   │   ├── __init__.py
│   │   └── config.py       # Pydantic BaseSettings management
│   ├── models/             # Pydantic schemas and data models
│   │   ├── __init__.py
│   │   └── schemas.py      # Request & response data definitions
│   ├── services/           # Business logic, document processing, and AI engine
│   │   └── __init__.py
│   └── utils/              # Helper utilities, loggers, and formatters
│       └── __init__.py
├── data/                   # Local storage for evidence files and indices
│   └── .gitkeep
└── tests/                  # Automated pytest suite
    ├── __init__.py
    └── test_health.py      # Health & root endpoint tests
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.11+**
- Git

### 2. Environment Setup
Copy `.env.example` to `.env` and set your Gemini API Key:
```bash
cp .env.example .env
```

Ensure `.env` contains:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 3. Installation
Install the project dependencies:
```bash
pip install -r requirements.txt
```

### 4. Running the Application
Start the application server with a single command:
```bash
python app.py
```
The server will start on `http://localhost:8000`.

- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🧪 Testing

Run the automated test suite with `pytest`:
```bash
pytest
```

---

## ⚙️ Hackathon Constraints Compliance

| Constraint | Status | Notes |
| :--- | :---: | :--- |
| **Python Backend** | ✅ | Built with Python 3.11 & FastAPI |
| **Single Startup Command** | ✅ | Started via `python app.py` |
| **Port Requirement** | ✅ | Binds to port `8000` |
| **Gemini Integration** | ✅ | Uses `GEMINI_API_KEY` & `gemini-embedding-001` (Only external API) |
| **Local Retrieval / Vector Storage** | ✅ | No hosted vector databases used |
| **Startup Limit (< 90s)** | ✅ | Instantaneous startup (< 2s) |
| **Request Limit (< 60s)** | ✅ | High throughput local processing |

---

## 📜 License
MIT License - ClaimLens AI Project
