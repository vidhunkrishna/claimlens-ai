# ClaimLens AI - Synthetic Motor Insurance Dataset

This directory contains the synthetic, deterministic motor insurance policy and claims dataset for testing and evaluating **ClaimLens AI** (`TRACK_ID=PS02`).

---

## 📋 Dataset Architecture

```text
data/
├── policy/
│   └── motor_policy.json         # Master Policy Document (Clauses POL-001 to POL-014)
├── claims/
│   ├── CLM-001/                  # Clean Normal Case (Car Accidental Damage)
│   │   ├── claim_form.json
│   │   ├── incident_description.json
│   │   ├── policy_schedule.json
│   │   └── repair_estimate.json
│   ├── CLM-002/                  # Contradiction Case (Two-Wheeler Date/Location/Driver Mismatch)
│   │   ├── claim_form.json
│   │   ├── incident_description.json
│   │   ├── policy_schedule.json
│   │   └── repair_estimate.json
│   ├── CLM-003/                  # Policy Block Case (Drunk Driving Exclusion breach)
│   │   ├── claim_form.json
│   │   ├── fir.json
│   │   ├── incident_description.json
│   │   ├── policy_schedule.json
│   │   └── repair_estimate.json
│   ├── CLM-004/                  # Missing Information Case (Missing Driving License & 55-Day Delay)
│   │   ├── claim_form.json
│   │   ├── incident_description.json
│   │   ├── policy_schedule.json
│   │   └── repair_estimate.json
│   └── CLM-005/                  # Theft Case (Two-Wheeler Total Theft with FIR & Key Surrender)
│       ├── claim_form.json
│       ├── fir.json
│       ├── incident_description.json
│       ├── key_declaration.json
│       └── policy_schedule.json
└── README.md
```

---

## 📜 Master Policy Clause Reference (`motor_policy.json`)

| Clause ID | Title | Category | Description |
| :--- | :--- | :--- | :--- |
| `POL-001` | Covered Incidents | Coverage | Accidental external means, fire, theft, flood, earthquake, transit. |
| `POL-002` | Intoxication Exclusion | Exclusion | Excludes loss if driver has BAC > 0.03% w/v or charged under Sec 185 MV Act. |
| `POL-003` | License Exclusion | Exclusion | Excludes loss if driver lacks valid, un-expired driving license. |
| `POL-004` | Commercial Use Exclusion | Exclusion | Excludes private vehicle used for commercial hire or racing. |
| `POL-005` | Wear & Tear Exclusion | Exclusion | Mechanical breakdown, wear and tear excluded unless part of collision. |
| `POL-006` | Consequential Loss | Exclusion | Indirect financial loss or loss of use excluded. |
| `POL-007` | Intimation Delay Exclusion| Exclusion | Intimation delay > 7 days for accident / > 48h for theft without proof repudiated. |
| `POL-008` | IDV & Total Loss | Valuation | CTL triggered if repair > 75% of IDV. |
| `POL-009` | Reporting Windows | Procedure | Accident intimation: 7 days. Theft: FIR in 24h, Insurer in 48h. |
| `POL-010` | Mandatory Documents | Documentation | Requires Claim Form, DL, RC, Estimate/FIR, and Key Surrender for theft. |
| `POL-011` | Repair & Survey | Claims | Empanelled surveyor inspection required prior to repair. |
| `POL-012` | Theft Settlement Rules | Claims | Theft requires FIR, Non-Traceable report, and surrender of BOTH original keys. |
| `POL-013` | Deductibles | Financial | Compulsory deductible ₹1,000 for Cars <=1500cc; ₹100 for Two-Wheelers. |
| `POL-014` | Liability Capping | Legal | Liability capped at IDV for own damage; ₹7.5L for Car TPPD / ₹1L for 2W TPPD. |

---

## 🧪 Synthetic Claim Scenarios Benchmark

### 1. `CLM-001` — Clean Normal Case
- **Vehicle**: Private Car (Hyundai i20, KA-01-MJ-4321)
- **Incident**: Reversing collision into parking pillar on 2026-08-10. Intimated in 2 days.
- **Evidence Consistency**: 100% consistent across Claim Form, Repair Estimate (₹18,500), and Incident Statement.
- **Expected Recommendation**: **`APPROVE`** (Net payable = Estimate ₹18,500 - Deductible ₹1,000 = ₹17,500).

### 2. `CLM-002` — Contradiction Case
- **Vehicle**: Two-Wheeler (TVS Jupiter, MH-02-CB-9876)
- **Contradictions Present**:
  - **Date Conflict**: Claim Form states `2026-08-15`, Incident Description states `2026-08-18`.
  - **Driver Conflict**: Claim Form names `Suresh Patel`, Incident Description names `Priya Sharma`.
  - **Location Conflict**: Claim Form specifies `Andheri West`, Description specifies `BKC`.
  - **Repair Date Conflict**: Repair Estimate dated `2026-08-14` (predates both incident dates!).
  - **Damaged Parts Conflict**: Claim Form lists `Front Fork`, Estimate lists `Rear Mudguard`.
- **Expected Recommendation**: **`REQUEST INFORMATION` / `ESCALATE`**

### 3. `CLM-003` — Policy Block Case
- **Vehicle**: Private Car (Honda City, DL-03-CC-5544)
- **Incident**: Highway guardrail crash on 2026-08-20 at 02:15 AM. Total repair ₹1,45,000.
- **Policy Violation**: Police FIR and Medical Report confirm driver Blood Alcohol Concentration (BAC) was **0.12% w/v** (exceeds legal 0.03% limit), charged under Sec 185 MV Act.
- **Exclusion Triggered**: Clause **`POL-002`** (Intoxication & Substance Abuse).
- **Expected Recommendation**: **`REJECT`** (Citing `POL-002`).

### 4. `CLM-004` — Missing Information Case
- **Vehicle**: Private Car (Maruti Swift, TN-09-AX-1234)
- **Deficiencies**:
  - `driver_license_number` field left **BLANK** / "NOT PROVIDED".
  - Driving License document missing from submission (violates `POL-010`).
  - Claim reported 55 days post incident without delay justification (violates `POL-007` & `POL-009`).
- **Expected Recommendation**: **`REQUEST INFORMATION`**

### 5. `CLM-005` — Theft Case
- **Vehicle**: Two-Wheeler (Yamaha FZ-S V3, KA-05-EV-7788)
- **Incident**: Motorcycle stolen from Metro Station parking overnight on 2026-08-05.
- **Compliance**:
  - FIR registered within 3.5 hours under Sec 379 IPC (satisfies `POL-009`).
  - Both original manufacturer keys surrendered and verified (satisfies `POL-012`).
  - Intimated to insurer within 24 hours (satisfies `POL-009`).
- **Expected Recommendation**: **`APPROVE`** (IDV payout ₹1,10,000 subject to final Non-Traceable Certificate under `POL-008` & `POL-012`).
