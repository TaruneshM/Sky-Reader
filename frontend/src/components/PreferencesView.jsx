import { useState, useEffect } from "react";
import {
  Sliders,
  Moon,
  Sun,
  Thermometer,
  Sparkles,
  ShieldCheck,
  RotateCcw,
  User,
  Check,
  CloudSun,
} from "lucide-react";
import { WEATHER_SCENES } from "../utils/weatherAtmosphere";

export default function PreferencesView({
  theme,
  onToggleTheme,
  atmosphereMode,
  onSelectAtmosphereMode,
  user,
  onClearHistory,
  onResetPreferences,
}) {
  // Meteorological Units Preferences (stored in localStorage)
  const [tempUnit, setTempUnit] = useState(() => {
    return localStorage.getItem("skyreader_temp_unit") || "C";
  });
  const [windUnit, setWindUnit] = useState(() => {
    return localStorage.getItem("skyreader_wind_unit") || "kmh";
  });
  const [pressureUnit, setPressureUnit] = useState(() => {
    return localStorage.getItem("skyreader_pressure_unit") || "hpa";
  });
  const [precipUnit, setPrecipUnit] = useState(() => {
    return localStorage.getItem("skyreader_precip_unit") || "mm";
  });

  // AI & Display Settings
  const [strictValidation, setStrictValidation] = useState(() => {
    return localStorage.getItem("skyreader_strict_val") !== "false";
  });
  const [autoExpandAudit, setAutoExpandAudit] = useState(() => {
    return localStorage.getItem("skyreader_auto_audit") === "true";
  });
  const [particleAnimations, setParticleAnimations] = useState(() => {
    return localStorage.getItem("skyreader_particles") !== "false";
  });

  const [savedSuccess, setSavedSuccess] = useState(false);

  // Sync state to localStorage
  useEffect(() => {
    localStorage.setItem("skyreader_temp_unit", tempUnit);
    localStorage.setItem("skyreader_wind_unit", windUnit);
    localStorage.setItem("skyreader_pressure_unit", pressureUnit);
    localStorage.setItem("skyreader_precip_unit", precipUnit);
    localStorage.setItem("skyreader_strict_val", strictValidation);
    localStorage.setItem("skyreader_auto_audit", autoExpandAudit);
    localStorage.setItem("skyreader_particles", particleAnimations);
  }, [
    tempUnit,
    windUnit,
    pressureUnit,
    precipUnit,
    strictValidation,
    autoExpandAudit,
    particleAnimations,
  ]);

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
  };

  const handleReset = () => {
    setTempUnit("C");
    setWindUnit("kmh");
    setPressureUnit("hpa");
    setPrecipUnit("mm");
    setStrictValidation(true);
    setAutoExpandAudit(false);
    setParticleAnimations(true);
    if (onResetPreferences) onResetPreferences();
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
  };

  return (
    <div className="preferences-viewport-container">
      <div className="preferences-scroll-area">
        {/* Header */}
        <div className="preferences-header-block">
          <div className="preferences-title-row">
            <div className="preferences-title-icon-box">
              <Sliders size={20} />
            </div>
            <div>
              <h2 className="preferences-main-title">Preferences & Settings</h2>
              <p className="preferences-subtitle">
                Customize units, atmospheric particle simulations, themes, and AI verification tolerances.
              </p>
            </div>
          </div>

          <div className="preferences-header-actions">
            <button
              type="button"
              className="pref-reset-btn"
              onClick={handleReset}
              title="Reset all settings to defaults"
            >
              <RotateCcw size={14} />
              <span>Reset Defaults</span>
            </button>
            <button
              type="button"
              className="pref-save-btn"
              onClick={handleSave}
              title="Apply settings"
            >
              {savedSuccess ? (
                <>
                  <Check size={14} className="text-emerald" />
                  <span>Saved!</span>
                </>
              ) : (
                <span>Save Changes</span>
              )}
            </button>
          </div>
        </div>

        {/* Settings Grid */}
        <div className="preferences-cards-grid">
          {/* Section 1: Visual Theme & Atmospheric Environment */}
          <div className="pref-card">
            <div className="pref-card-header">
              <CloudSun size={18} className="pref-section-icon text-amber" />
              <h3 className="pref-card-title">Theme & Atmospheric Ambience</h3>
            </div>
            <div className="pref-card-body">
              {/* Theme Mode Toggle */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Display Appearance</span>
                  <span className="pref-setting-sub">
                    Switch between Calming Twilight (Night) and Soft Day Sky (Light)
                  </span>
                </div>
                <div className="pref-segmented-switch">
                  <button
                    type="button"
                    className={`segmented-btn ${theme === "dark" ? "active" : ""}`}
                    onClick={() => theme !== "dark" && onToggleTheme()}
                  >
                    <Moon size={14} />
                    <span>Night Mode</span>
                  </button>
                  <button
                    type="button"
                    className={`segmented-btn ${theme === "light" ? "active" : ""}`}
                    onClick={() => theme !== "light" && onToggleTheme()}
                  >
                    <Sun size={14} />
                    <span>Day Mode</span>
                  </button>
                </div>
              </div>

              {/* Particle Simulation Toggle */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Weather Particle Engine</span>
                  <span className="pref-setting-sub">
                    Render live rain drops, blowing leaves, stars, snowflakes, and sunbeams
                  </span>
                </div>
                <label className="pref-toggle-switch">
                  <input
                    type="checkbox"
                    checked={particleAnimations}
                    onChange={(e) => setParticleAnimations(e.target.checked)}
                  />
                  <span className="toggle-slider" />
                </label>
              </div>

              {/* Active Weather Scene Selector */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Atmospheric Scene Override</span>
                  <span className="pref-setting-sub">
                    Lock simulation to a specific condition or sync with live weather
                  </span>
                </div>
                <select
                  className="pref-select-dropdown"
                  value={atmosphereMode}
                  onChange={(e) => onSelectAtmosphereMode(e.target.value)}
                >
                  {WEATHER_SCENES.map((scene) => (
                    <option key={scene.id} value={scene.id}>
                      {scene.icon} {scene.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Section 2: Meteorological Units of Measurement */}
          <div className="pref-card">
            <div className="pref-card-header">
              <Thermometer size={18} className="pref-section-icon text-sky" />
              <h3 className="pref-card-title">Meteorological Units</h3>
            </div>
            <div className="pref-card-body">
              {/* Temperature Unit */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Temperature Unit</span>
                  <span className="pref-setting-sub">Celsius (°C) or Fahrenheit (°F)</span>
                </div>
                <div className="pref-segmented-switch">
                  <button
                    type="button"
                    className={`segmented-btn ${tempUnit === "C" ? "active" : ""}`}
                    onClick={() => setTempUnit("C")}
                  >
                    °C Celsius
                  </button>
                  <button
                    type="button"
                    className={`segmented-btn ${tempUnit === "F" ? "active" : ""}`}
                    onClick={() => setTempUnit("F")}
                  >
                    °F Fahrenheit
                  </button>
                </div>
              </div>

              {/* Wind Speed Unit */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Wind Velocity</span>
                  <span className="pref-setting-sub">Display speed in km/h, mph, or m/s</span>
                </div>
                <div className="pref-segmented-switch">
                  <button
                    type="button"
                    className={`segmented-btn ${windUnit === "kmh" ? "active" : ""}`}
                    onClick={() => setWindUnit("kmh")}
                  >
                    km/h
                  </button>
                  <button
                    type="button"
                    className={`segmented-btn ${windUnit === "mph" ? "active" : ""}`}
                    onClick={() => setWindUnit("mph")}
                  >
                    mph
                  </button>
                  <button
                    type="button"
                    className={`segmented-btn ${windUnit === "ms" ? "active" : ""}`}
                    onClick={() => setWindUnit("ms")}
                  >
                    m/s
                  </button>
                </div>
              </div>

              {/* Pressure Unit */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Surface Pressure</span>
                  <span className="pref-setting-sub">hPa (hectopascals) or inHg</span>
                </div>
                <div className="pref-segmented-switch">
                  <button
                    type="button"
                    className={`segmented-btn ${pressureUnit === "hpa" ? "active" : ""}`}
                    onClick={() => setPressureUnit("hpa")}
                  >
                    hPa
                  </button>
                  <button
                    type="button"
                    className={`segmented-btn ${pressureUnit === "inhg" ? "active" : ""}`}
                    onClick={() => setPressureUnit("inhg")}
                  >
                    inHg
                  </button>
                </div>
              </div>

              {/* Precipitation Unit */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Precipitation Volume</span>
                  <span className="pref-setting-sub">Millimeters (mm) or Inches (in)</span>
                </div>
                <div className="pref-segmented-switch">
                  <button
                    type="button"
                    className={`segmented-btn ${precipUnit === "mm" ? "active" : ""}`}
                    onClick={() => setPrecipUnit("mm")}
                  >
                    mm
                  </button>
                  <button
                    type="button"
                    className={`segmented-btn ${precipUnit === "in" ? "active" : ""}`}
                    onClick={() => setPrecipUnit("in")}
                  >
                    in
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: AI Verification & Agent Tolerances */}
          <div className="pref-card">
            <div className="pref-card-header">
              <ShieldCheck size={18} className="pref-section-icon text-emerald" />
              <h3 className="pref-card-title">AI Evidence & Validation Engine</h3>
            </div>
            <div className="pref-card-body">
              {/* Strict Zero-Hallucination Mode */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Strict Meteorological Audit</span>
                  <span className="pref-setting-sub">
                    Enforces ±1.0°C and ±3% RH tolerances against raw Open-Meteo telemetry
                  </span>
                </div>
                <label className="pref-toggle-switch">
                  <input
                    type="checkbox"
                    checked={strictValidation}
                    onChange={(e) => setStrictValidation(e.target.checked)}
                  />
                  <span className="toggle-slider" />
                </label>
              </div>

              {/* Auto-Expand Audit Drawer */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Auto-Expand Evidence Drawer</span>
                  <span className="pref-setting-sub">
                    Automatically expand the Phase 4 audit report on assistant responses
                  </span>
                </div>
                <label className="pref-toggle-switch">
                  <input
                    type="checkbox"
                    checked={autoExpandAudit}
                    onChange={(e) => setAutoExpandAudit(e.target.checked)}
                  />
                  <span className="toggle-slider" />
                </label>
              </div>

              {/* Engine Model */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Reasoning LLM Backbone</span>
                  <span className="pref-setting-sub">
                    Connected to Groq Cloud LLM for tool-dispatch and synthesis
                  </span>
                </div>
                <span className="pref-status-pill">
                  <Sparkles size={11} className="inline-sparkle" />
                  Groq LLM 120B (Active)
                </span>
              </div>
            </div>
          </div>

          {/* Section 4: Account & Local Data */}
          <div className="pref-card">
            <div className="pref-card-header">
              <User size={18} className="pref-section-icon text-purple" />
              <h3 className="pref-card-title">Account & Conversation Storage</h3>
            </div>
            <div className="pref-card-body">
              {/* Profile Details */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Signed-In Account</span>
                  <span className="pref-setting-sub">
                    {user ? `${user.name} (${user.email})` : "Guest Explorer"}
                  </span>
                </div>
                <span className={`pref-status-pill${user ? " authenticated" : ""}`}>
                  {user ? "Signed in" : "Guest"}
                </span>
              </div>

              {/* Clear History Button */}
              <div className="pref-setting-row">
                <div className="pref-setting-info">
                  <span className="pref-setting-label">Clear Consultation Threads</span>
                  <span className="pref-setting-sub">
                    Delete conversation history for this account or guest in this browser
                  </span>
                </div>
                <button
                  type="button"
                  className="pref-danger-btn"
                  onClick={() => {
                    if (window.confirm("Are you sure you want to clear all consultation history?")) {
                      if (onClearHistory) onClearHistory();
                    }
                  }}
                >
                  Clear History
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
