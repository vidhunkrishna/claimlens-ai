/* ClaimLens AI - Investigator Dashboard Frontend Logic */

// Global State
let currentReportData = null;

// Tab Navigation
function showScreen(screenId) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));

  const targetScreen = document.getElementById(screenId);
  if (targetScreen) targetScreen.classList.add('active');

  const tabId = screenId.replace('screen-', 'tab-');
  const targetTab = document.getElementById(tabId);
  if (targetTab) targetTab.classList.add('active');
}

// Health Check API Ping
async function checkApiHealth() {
  try {
    const res = await fetch('/health');
    if (res.ok) {
      document.getElementById('api-status-text').innerText = 'API ONLINE';
    } else {
      document.getElementById('api-status-text').innerText = 'API OFFLINE';
    }
  } catch (err) {
    document.getElementById('api-status-text').innerText = 'DISCONNECTED';
  }
}

// Analyze Synthetic Preset Claim
async function analyzePreset(claimId) {
  showScreen('screen-analysis');
  resetAnalysisSteps();

  try {
    // Step 1: Ingestion
    await updateStep(1, 'active');
    await delay(300);
    await updateStep(1, 'done');

    // Step 2: Rules
    await updateStep(2, 'active');
    await delay(300);
    await updateStep(2, 'done');

    // Step 3: Contradictions
    await updateStep(3, 'active');
    await delay(300);
    await updateStep(3, 'done');

    // Step 4: RAG Policy Retrieval
    await updateStep(4, 'active');
    await delay(300);
    await updateStep(4, 'done');

    // Step 5: Gemini Reasoning
    await updateStep(5, 'active');
    
    // Fetch full end-to-end report from backend API
    const response = await fetch(`/api/v1/investigation/review/${claimId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    const reportData = await response.json();
    currentReportData = reportData;

    await updateStep(5, 'done');

    // Step 6: Report Generation
    await updateStep(6, 'active');
    await delay(300);
    await updateStep(6, 'done');

    // Render report and display screen-report
    renderReport(reportData);
    showScreen('screen-report');

  } catch (err) {
    alert(`Failed to analyze claim ${claimId}: ${err.message}`);
    showScreen('screen-dashboard');
  }
}

function startAnalysisFromDropdown() {
  const val = document.getElementById('preset-dropdown').value;
  analyzePreset(val);
}

function resetAnalysisSteps() {
  for (let i = 1; i <= 6; i++) {
    const el = document.getElementById(`step-${i}`);
    if (el) {
      el.classList.remove('active', 'done');
    }
  }
}

function updateStep(stepNum, status) {
  return new Promise(resolve => {
    const el = document.getElementById(`step-${stepNum}`);
    if (el) {
      el.classList.remove('active', 'done');
      el.classList.add(status);
    }
    resolve();
  });
}

function delay(ms) {
  return new Promise(res => setTimeout(res, ms));
}

// Render Complete 9-Section Investigation Report
function renderReport(report) {
  const container = document.getElementById('report-content');
  if (!container) return;

  const resultClass = report.executive_result.toLowerCase().replace(/_/g, '-');
  const overview = report.claim_overview;
  const docs = report.document_completeness;
  const consistency = report.consistency_analysis;
  const escalation = report.human_escalation;

  let html = `
    <!-- SECTION 1: Executive Result Banner -->
    <div class="exec-banner ${resultClass}">
      <div>
        <div class="exec-status-title">EXECUTIVE DECISION RESULT</div>
        <div class="exec-result-text">${report.executive_result.replace(/_/g, ' ')}</div>
        <div class="exec-rationale">${report.recommendation_rationale}</div>
      </div>
      <div style="text-align: right;">
        <span class="preset-badge ${resultClass === 'approve' ? 'approve' : (resultClass === 'reject' ? 'reject' : 'escalate')}" style="font-size: 0.9rem; padding: 0.4rem 0.8rem;">
          ${report.executive_result}
        </span>
      </div>
    </div>
  `;

  // SECTION 9: Human Escalation Warning Box (if required)
  if (escalation.requires_human_review) {
    html += `
      <div class="warning-box">
        <div class="warning-icon">⚠️</div>
        <div>
          <h4>CRITICAL: HUMAN INVESTIGATOR REVIEW REQUIRED</h4>
          <p>${escalation.reason}</p>
          <ul>
            ${escalation.escalation_points.map(pt => `<li>${pt}</li>`).join('')}
          </ul>
        </div>
      </div>
    `;
  }

  // SECTION 2: Claim Overview & SECTION 3: Document Completeness
  html += `
    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem;">
      <div class="report-card">
        <div class="report-card-title">📋 Claim Overview</div>
        <div class="overview-grid">
          <div class="info-item">
            <span class="info-label">Claim ID</span>
            <span class="info-val">${overview.claim_id}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Vehicle Registration</span>
            <span class="info-val">${overview.vehicle_registration}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Make / Model</span>
            <span class="info-val">${overview.vehicle_make_model}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Claim Type</span>
            <span class="info-val">${overview.claim_type}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Incident Date</span>
            <span class="info-val">${overview.incident_date}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Intimation Date</span>
            <span class="info-val">${overview.intimation_date}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Insured Name</span>
            <span class="info-val">${overview.insured_name}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Vehicle IDV</span>
            <span class="info-val">₹${overview.idv.toLocaleString()}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Estimated Claim Amount</span>
            <span class="info-val">₹${overview.estimated_amount.toLocaleString()}</span>
          </div>
        </div>
      </div>

      <div class="report-card">
        <div class="report-card-title">📁 Document Completeness</div>
        <div class="doc-checklist" style="flex-direction: column; gap: 0.75rem;">
          <div class="doc-pill ${docs.has_claim_form ? 'present' : 'missing'}">
            ${docs.has_claim_form ? '✓' : '❌'} Claim Form
          </div>
          <div class="doc-pill ${docs.has_fir_or_estimate ? 'present' : 'missing'}">
            ${docs.has_fir_or_estimate ? '✓' : '❌'} FIR / Repair Estimate
          </div>
          <div class="doc-pill ${docs.has_incident_description ? 'present' : 'missing'}">
            ${docs.has_incident_description ? '✓' : '❌'} Incident Statement
          </div>
        </div>
        ${docs.missing_documents.length > 0 ? `
          <div style="margin-top: 1rem; font-size: 0.8rem; color: var(--color-reject);">
            <strong>Missing Required Docs:</strong> ${docs.missing_documents.join(', ')}
          </div>
        ` : ''}
      </div>
    </div>
  `;

  // SECTION 4: Cross-Document Contradiction Analysis
  html += `
    <div class="report-card">
      <div class="report-card-title">
        ⚡ Consistency Analysis & Contradictions 
        <span class="preset-badge ${consistency.contradictions_count > 0 ? 'reject' : 'approve'}" style="margin-left: auto;">
          ${consistency.contradictions_count} CONTRADICTIONS DETECTED
        </span>
      </div>
  `;

  if (consistency.contradictions_count === 0) {
    html += `
      <div style="padding: 1rem; background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: var(--radius-sm); color: var(--color-approve); font-size: 0.9rem;">
        ✓ Zero cross-document evidence contradictions detected. All reported dates, locations, vehicle details, and damage descriptions are fully consistent across documents.
      </div>
    `;
  } else {
    html += `<div class="contradiction-cards">`;
    consistency.contradictions.forEach((c, idx) => {
      html += `
        <div class="contradiction-card">
          <div class="contradiction-header">
            <span class="contradiction-title">⚠️ CONTRADICTION: ${c.field_name.replace(/_/g, ' ').toUpperCase()}</span>
            <span class="preset-badge reject">${c.severity} SEVERITY</span>
          </div>
          <div class="side-by-side-evidence">
            <div class="evidence-box">
              <span class="evidence-box-label">${c.source_document_a_type} (${c.source_document_a_id})</span>
              <span class="evidence-box-val">${c.source_value_a}</span>
            </div>
            <div class="evidence-box">
              <span class="evidence-box-label">${c.source_document_b_type} (${c.source_document_b_id})</span>
              <span class="evidence-box-val">${c.source_value_b}</span>
            </div>
          </div>
          <p style="font-size: 0.85rem; color: var(--text-main); margin-bottom: 0.75rem;">${c.explanation}</p>
          <button class="view-evidence-btn" onclick="openEvidenceModal('Contradiction Evidence: ${c.field_name}', '${c.source_document_a_id}: ${c.source_value_a}\\n${c.source_document_b_id}: ${c.source_value_b}\\n\\nExplanation: ${c.explanation}')">
            [View Evidence]
          </button>
        </div>
      `;
    });
    html += `</div>`;
  }
  html += `</div>`;

  // SECTION 5: Policy Analysis
  html += `
    <div class="report-card">
      <div class="report-card-title">📜 Relevant Policy Analysis (RAG Local Retrieval)</div>
      <div class="policy-list">
        ${report.policy_analysis.map(p => `
          <div class="policy-item">
            <div class="policy-header">
              <span class="clause-badge">${p.clause_id}: ${p.title}</span>
              <span class="effect-badge ${p.effect.toLowerCase()}">${p.effect} CLAIM</span>
            </div>
            <div class="exact-clause-text">${p.exact_clause_text}</div>
            <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.35rem;">
              <strong>Finding:</strong> ${p.explanation}
            </div>
            <div style="margin-top: 0.5rem;">
              <button class="view-evidence-btn" onclick="openEvidenceModal('Policy Clause ${p.clause_id} - ${p.title}', 'CLAUSE ID: ${p.clause_id}\\nTITLE: ${p.title}\\nEFFECT: ${p.effect}\\n\\nEXACT CLAUSE TEXT:\\n${p.exact_clause_text.replace(/'/g, "\\'")}\\n\\nCITED DOCUMENTS: ${p.cited_evidence_ids.join(', ')}')">
                [View Policy Clause]
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  // SECTION 6: Deterministic Rule Results
  html += `
    <div class="report-card">
      <div class="report-card-title">⚙️ Deterministic Rule Results</div>
      <table class="rules-table">
        <thead>
          <tr>
            <th>Rule Name</th>
            <th>Policy Clause</th>
            <th>Status</th>
            <th>Explanation</th>
          </tr>
        </thead>
        <tbody>
          ${report.rule_results.map(r => `
            <tr>
              <td><strong>${r.rule_name}</strong></td>
              <td><span class="clause-badge" style="font-size: 0.75rem;">${r.policy_clause_id || 'N/A'}</span></td>
              <td><span class="rule-badge ${r.status.toLowerCase()}">${r.status}</span></td>
              <td style="font-size: 0.8rem; color: var(--text-muted);">${r.explanation}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  // SECTION 7: Evidence Findings
  html += `
    <div class="report-card">
      <div class="report-card-title">🔎 Itemized Evidence Findings (${report.evidence_findings.length})</div>
      <div style="display: flex; flex-direction: column; gap: 0.85rem;">
        ${report.evidence_findings.map(f => `
          <div style="background: rgba(0, 0, 0, 0.3); border: 1px solid var(--border-color); padding: 1rem; border-radius: var(--radius-sm);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
              <span style="font-weight: 700; color: #fff; font-size: 0.9rem;">${f.finding_id}: ${f.title}</span>
              <span class="rule-badge ${f.severity === 'HIGH' ? 'fail' : 'warn'}">${f.severity} SEVERITY</span>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">${f.explanation}</p>
            <div style="font-family: var(--font-mono); font-size: 0.775rem; background: rgba(0,0,0,0.5); padding: 0.5rem; border-radius: 4px; color: #6ee7b7;">
              Source (${f.source_document_id}): "${f.exact_source_text}"
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  container.innerHTML = html;
}

// Modal Viewer
function openEvidenceModal(title, textContent) {
  document.getElementById('modal-title').innerText = title;
  document.getElementById('modal-body').innerText = textContent;
  document.getElementById('evidence-modal').classList.add('active');
}

function closeModal() {
  document.getElementById('evidence-modal').classList.remove('active');
}

// Close modal on escape or overlay click
window.onclick = function(event) {
  const modal = document.getElementById('evidence-modal');
  if (event.target === modal) {
    closeModal();
  }
};

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeModal();
});

// Run health check on startup
document.addEventListener('DOMContentLoaded', () => {
  checkApiHealth();
});
