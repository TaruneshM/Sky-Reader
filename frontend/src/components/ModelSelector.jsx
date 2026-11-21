import { useState, useRef, useEffect } from "react";
import { Sparkles, ChevronDown, Check, Zap, Gauge, Layers } from "lucide-react";

const SKY_MODELS = [
  {
    id: "Sky Reader 4",
    name: "Sky Reader 4",
    tagline: "Flagship Precision",
    badge: "Precision",
    description:
      "Deep meteorological synthesis with rigorous factual claim audit and zero-hallucination verification.",
    icon: Sparkles,
    badgeColor: "var(--accent-amber)",
  },
  {
    id: "Sky Reader 4 Turbo",
    name: "Sky Reader 4 Turbo",
    tagline: "High Velocity",
    badge: "Turbo",
    description:
      "Rapid multi-point hourly telemetry, swift radar analytics and dynamic trip planning.",
    icon: Zap,
    badgeColor: "var(--accent-sky)",
  },
  {
    id: "Sky Reader 3.5 Flash",
    name: "Sky Reader 3.5 Flash",
    tagline: "Ultra Low Latency",
    badge: "Fast",
    description:
      "Instant responses for daily temperature checks, quick questions and ambient summaries.",
    icon: Gauge,
    badgeColor: "var(--accent-emerald)",
  },
  {
    id: "Sky Reader Ensemble",
    name: "Sky Reader Ensemble",
    tagline: "Consensus Audit",
    badge: "Ensemble",
    description:
      "Blends ECMWF and Open-Meteo observations with strict deterministic cross-validation.",
    icon: Layers,
    badgeColor: "var(--accent-purple)",
  },
];

export default function ModelSelector({ selectedModel = "Sky Reader 4", onSelectModel }) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const activeModelObj =
    SKY_MODELS.find((m) => m.id === selectedModel) || SKY_MODELS[0];

  return (
    <div className="model-selector-container" ref={containerRef}>
      <button
        type="button"
        className={`model-selector-pill ${isOpen ? "active-open" : ""}`}
        onClick={() => setIsOpen((prev) => !prev)}
        title="Select AI Meteorological Model Engine"
        aria-expanded={isOpen}
      >
        <span className="model-pill-dot" />
        <span className="model-name-text">{activeModelObj.name}</span>
        <ChevronDown
          size={14}
          className={`model-chevron ${isOpen ? "rotate" : ""}`}
        />
      </button>

      {isOpen && (
        <div className="model-dropdown-menu">
          <div className="model-dropdown-header">
            <div className="dropdown-header-title-row">
              <Sparkles size={13} className="sparkle-menu-icon" />
              <span>Meteorological AI Engine</span>
            </div>
            <span className="model-count-tag">{SKY_MODELS.length} Models</span>
          </div>

          <div className="model-dropdown-list">
            {SKY_MODELS.map((model) => {
              const isSelected = selectedModel === model.id;
              const ModelIcon = model.icon;
              return (
                <button
                  key={model.id}
                  type="button"
                  className={`model-dropdown-item-btn ${isSelected ? "selected" : ""}`}
                  onClick={() => {
                    onSelectModel(model.id);
                    setIsOpen(false);
                  }}
                >
                  <div
                    className="model-item-icon-box"
                    style={{
                      background: isSelected
                        ? "rgba(245, 158, 11, 0.2)"
                        : "rgba(255, 255, 255, 0.06)",
                      color: isSelected ? "var(--accent-amber)" : "var(--text-secondary)",
                    }}
                  >
                    <ModelIcon size={16} />
                  </div>

                  <div className="model-item-content">
                    <div className="model-item-top-row">
                      <span className="model-item-title">{model.name}</span>
                      <span
                        className="model-item-badge"
                        style={{
                          borderColor: model.badgeColor,
                          color: model.badgeColor,
                        }}
                      >
                        {model.badge}
                      </span>
                    </div>
                    <p className="model-item-desc">{model.description}</p>
                  </div>

                  {isSelected && (
                    <div className="model-selected-check">
                      <Check size={15} />
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          <div className="model-dropdown-footer">
            <span className="footer-audit-note">
              🛡️ Zero-hallucination deterministic validation enabled
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
