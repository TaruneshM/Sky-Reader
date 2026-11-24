import { useState } from "react";

export default function RiskCard({ riskAssessment }) {
  const [showDetails, setShowDetails] = useState(false);

  if (!riskAssessment || !riskAssessment.overall_risk_level) {
    return null;
  }

  const level = String(riskAssessment.overall_risk_level).toUpperCase();
  const detectedRisks = riskAssessment.detected_risks || [];
  const recommendations = riskAssessment.safety_recommendations || [];
  const uncertaintyNotes = riskAssessment.uncertainty_notes || [];
  const dataLimitations = riskAssessment.data_limitations || [];

  const levelMeta = {
    LOW: {
      colorClass: "risk-low",
      icon: "🛡️",
      title: "Low Weather Risk",
      bgTint: "rgba(16, 185, 129, 0.1)",
      border: "rgba(16, 185, 129, 0.3)",
    },
    MODERATE: {
      colorClass: "risk-moderate",
      icon: "⚠️",
      title: "Moderate Weather Risk",
      bgTint: "rgba(245, 158, 11, 0.12)",
      border: "rgba(245, 158, 11, 0.4)",
    },
    HIGH: {
      colorClass: "risk-high",
      icon: "🚨",
      title: "High Weather Risk",
      bgTint: "rgba(249, 115, 22, 0.15)",
      border: "rgba(249, 115, 22, 0.45)",
    },
    SEVERE: {
      colorClass: "risk-severe",
      icon: "⚡",
      title: "Severe Weather Hazard",
      bgTint: "rgba(239, 68, 68, 0.18)",
      border: "rgba(239, 68, 68, 0.5)",
    },
  }[level] || {
    colorClass: "risk-low",
    icon: "🛡️",
    title: "Weather Safety Assessment",
    bgTint: "rgba(100, 116, 139, 0.1)",
    border: "rgba(100, 116, 139, 0.3)",
  };

  return (
    <div
      className={`risk-assessment-card ${levelMeta.colorClass}`}
      style={{
        "--risk-tint": levelMeta.bgTint,
        borderColor: levelMeta.border,
      }}
    >
      {/* Header with Risk Level Badge */}
      <div className="risk-card-header">
        <div className="risk-badge-group">
          <span className="risk-icon" aria-hidden="true">
            {levelMeta.icon}
          </span>
          <span className="risk-title">{levelMeta.title}</span>
          <span className={`risk-level-pill ${levelMeta.colorClass}`}>
            {level}
          </span>
        </div>
        {riskAssessment.forecast_period && (
          <span className="risk-forecast-period">
            📅 {riskAssessment.forecast_period}
          </span>
        )}
      </div>

      {/* Official Alert vs AI Assessment Disclaimer */}
      <div className="risk-disclaimer-banner">
        <span className="disclaimer-badge">AI Risk Assessment</span>
        <span className="disclaimer-text">
          Not an official government emergency alert. Calculated from numerical
          model forecasts & deterministic thresholds.
        </span>
      </div>

      {/* Summary */}
      <div className="risk-summary">
        {riskAssessment.overall_summary}
      </div>

      {/* Detected Risks List */}
      {detectedRisks.length > 0 && (
        <div className="detected-risks-section">
          <div className="section-label">Detected Weather Hazards:</div>
          <div className="hazard-items-list">
            {detectedRisks.map((item, idx) => (
              <div key={idx} className="hazard-item-row">
                <div className="hazard-header">
                  <span className="hazard-condition">
                    {item.condition}
                  </span>
                  <span className={`hazard-severity-tag risk-${String(item.severity).toLowerCase()}`}>
                    {item.severity}
                  </span>
                </div>
                <div className="hazard-reason">{item.reason}</div>
                {item.measurements && Object.keys(item.measurements).length > 0 && (
                  <div className="hazard-measurements">
                    {Object.entries(item.measurements).map(([k, v]) => (
                      <span key={k} className="measurement-tag">
                        <strong>{k.replace(/_/g, " ")}:</strong> {String(v)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Precautions */}
      {recommendations.length > 0 && (
        <div className="risk-recommendations-section">
          <div className="section-label">Recommended Precautions:</div>
          <ul className="precautions-list">
            {recommendations.map((rec, idx) => (
              <li key={idx} className="precaution-item">
                <span className="precaution-bullet">✓</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Uncertainty & Limitations Toggle */}
      {(uncertaintyNotes.length > 0 || dataLimitations.length > 0) && (
        <div className="risk-footer-section">
          <button
            type="button"
            className="toggle-uncertainty-btn"
            onClick={() => setShowDetails(!showDetails)}
          >
            {showDetails ? "▼ Hide Uncertainty & Data Notes" : "▶ View Uncertainty & Forecast Notes"}
          </button>

          {showDetails && (
            <div className="uncertainty-details-box">
              {uncertaintyNotes.length > 0 && (
                <div className="uncertainty-block">
                  <strong>Uncertainty Communication:</strong>
                  <ul>
                    {uncertaintyNotes.map((note, idx) => (
                      <li key={idx}>{note}</li>
                    ))}
                  </ul>
                </div>
              )}
              {dataLimitations.length > 0 && (
                <div className="limitations-block">
                  <strong>Data Limitations:</strong>
                  <ul>
                    {dataLimitations.map((lim, idx) => (
                      <li key={idx}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
