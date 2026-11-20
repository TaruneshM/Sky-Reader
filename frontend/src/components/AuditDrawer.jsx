import { useState } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Terminal,
  Database,
  Info,
  CheckCircle2,
  XCircle,
  HelpCircle,
} from "lucide-react";

export default function AuditDrawer({ validationReport, explanation, toolCalls = [] }) {
  const [isOpen, setIsOpen] = useState(false);

  // If no audit report or tools were executed, return null
  if (!validationReport && toolCalls.length === 0) {
    return null;
  }

  const isTrustworthy = validationReport?.is_trustworthy ?? true;
  const totalClaims = validationReport?.total_claims || 0;
  const supportedClaims = validationReport?.supported_claims || 0;
  const contradictedClaims = validationReport?.contradicted_claims || 0;
  const statusLabel = explanation?.claim_validation_status || (
    isTrustworthy ? "Verified Grounded" : "Audited with Flags"
  );

  return (
    <div className="audit-drawer-container">
      <button
        type="button"
        className={`audit-toggle-btn ${isTrustworthy ? "trustworthy" : "warning"}`}
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <span className="audit-badge-icon">
          {isTrustworthy ? (
            <ShieldCheck size={16} className="audit-shield-icon" />
          ) : (
            <AlertTriangle size={16} className="audit-warning-icon" />
          )}
        </span>

        <span className="audit-badge-text">
          {totalClaims > 0 ? statusLabel : "Execution & Provenance Log"}
        </span>

        <span className="audit-badge-meta">
          {totalClaims > 0 && `(${supportedClaims}/${totalClaims} verified)`}
        </span>

        <span className="audit-toggle-chevron">
          {isOpen ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </span>
      </button>

      {isOpen && (
        <div className="audit-drawer-content">
          {/* 1. Summary Metrics */}
          {validationReport && (
            <div className="audit-metrics-row">
              <div className="audit-metric-pill">
                <span className="pill-label">Total Claims</span>
                <strong className="pill-value">{totalClaims}</strong>
              </div>
              <div className="audit-metric-pill supported">
                <span className="pill-label">Supported</span>
                <strong className="pill-value">{supportedClaims}</strong>
              </div>
              {contradictedClaims > 0 && (
                <div className="audit-metric-pill contradicted">
                  <span className="pill-label">Contradicted</span>
                  <strong className="pill-value">{contradictedClaims}</strong>
                </div>
              )}
              {explanation?.hallucination_risk && (
                <div className="audit-metric-pill risk">
                  <span className="pill-label">Risk Rating</span>
                  <strong className="pill-value">{explanation.hallucination_risk}</strong>
                </div>
              )}
            </div>
          )}

          {/* 2. Audited Factual Claims List */}
          {validationReport?.validation_results && validationReport.validation_results.length > 0 && (
            <div className="audit-section">
              <div className="audit-section-header">
                <ShieldCheck size={14} className="section-title-icon" />
                <h4 className="audit-section-title">Deterministic Factual Claims Audit</h4>
              </div>

              <div className="audit-claims-list">
                {validationReport.validation_results.map((res, idx) => {
                  const status = res.status;
                  const claim = res.claim;
                  const statusClass =
                    status === "SUPPORTED"
                      ? "status-supported"
                      : status === "PARTIALLY_SUPPORTED"
                      ? "status-partial"
                      : status === "CONTRADICTED"
                      ? "status-contradicted"
                      : "status-unsupported";

                  return (
                    <div key={idx} className={`audit-claim-item ${statusClass}`}>
                      <div className="claim-header">
                        <span className={`claim-status-badge ${statusClass}`}>
                          {status === "SUPPORTED" && <CheckCircle2 size={12} className="inline-badge-icon" />}
                          {status === "CONTRADICTED" && <XCircle size={12} className="inline-badge-icon" />}
                          {(status === "PARTIALLY_SUPPORTED" || status === "INSUFFICIENT_EVIDENCE") && (
                            <HelpCircle size={12} className="inline-badge-icon" />
                          )}
                          <span>{status}</span>
                        </span>
                        <span className="claim-variable">
                          {claim.variable.replace(/_/g, " ")}
                        </span>
                        <span className="claim-value">
                          {String(claim.claimed_value)} {claim.unit || ""}
                        </span>
                      </div>
                      <p className="claim-explanation">{res.explanation}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 3. Executed Weather Tools */}
          {toolCalls && toolCalls.length > 0 && (
            <div className="audit-section">
              <div className="audit-section-header">
                <Terminal size={14} className="section-title-icon" />
                <h4 className="audit-section-title">Autonomous Tools Executed</h4>
              </div>
              <div className="audit-tools-list">
                {toolCalls.map((tc, idx) => (
                  <div key={idx} className="tool-execution-badge">
                    <span className="tool-name">
                      <Terminal size={12} className="tool-icon-inner" />
                      {tc.tool}
                    </span>
                    {tc.arguments && Object.keys(tc.arguments).length > 0 && (
                      <span className="tool-args">
                        {JSON.stringify(tc.arguments)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 4. Data Sources & Provenance */}
          {explanation?.data_sources && explanation.data_sources.length > 0 && (
            <div className="audit-section">
              <div className="audit-section-header">
                <Database size={14} className="section-title-icon" />
                <h4 className="audit-section-title">Observation Provenance</h4>
              </div>
              <ul className="audit-sources-list">
                {explanation.data_sources.map((src, idx) => (
                  <li key={idx}>
                    <Database size={12} className="source-bullet-icon" />
                    <span>{src}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 5. Meteorological Limitations */}
          {explanation?.limitations_and_uncertainty && (
            <div className="audit-section limitations">
              <div className="limitations-header">
                <Info size={13} className="limitations-icon" />
                <span className="limitations-label">Meteorological Uncertainty:</span>
              </div>
              <p className="limitations-text">
                {explanation.limitations_and_uncertainty}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
