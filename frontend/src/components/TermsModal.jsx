import { useEffect } from "react";
import { ShieldCheck, X } from "lucide-react";

export default function TermsModal({
  isOpen,
  onClose,
  isLight = false,
  welcomeUser = null,
}) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="terms-modal-title"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(3, 7, 18, 0.75)",
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
        animation: "termsBackdropFade 0.22s ease-out",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "relative",
          width: "100%",
          maxWidth: 560,
          maxHeight: "85vh",
          background: isLight ? "#fffdfa" : "rgba(15, 23, 42, 0.96)",
          border: isLight ? "1px solid rgba(210,190,165,0.6)" : "1px solid rgba(255,255,255,0.18)",
          borderRadius: 24,
          boxShadow: isLight
            ? "0 25px 60px -15px rgba(120,80,30,0.35)"
            : "0 25px 60px -15px rgba(0,0,0,0.85)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          animation: "termsModalZoom 0.25s cubic-bezier(0.16,1,0.3,1)",
          color: isLight ? "#2c2520" : "#f1f5f9",
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "20px 24px 16px",
            borderBottom: isLight ? "1px solid rgba(230,220,205,0.8)" : "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 12,
                background: isLight ? "rgba(245,158,11,0.15)" : "rgba(192,132,252,0.18)",
                color: isLight ? "#d97706" : "#c084fc",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <ShieldCheck size={20} />
            </div>
            <div>
              <h2 id="terms-modal-title" style={{ margin: 0, fontSize: 17.5, fontWeight: 700 }}>
                {welcomeUser ? `Welcome, ${welcomeUser}!` : "Terms & Conditions"}
              </h2>
              <p style={{ margin: "2px 0 0", fontSize: 11.5, color: isLight ? "#8c7e72" : "#94a3b8" }}>
                {welcomeUser
                  ? "Please review and accept our platform terms & meteorological advisories."
                  : "Sky Reader v2.0 AI Meteorological Platform"}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close Terms & Conditions"
            style={{
              background: isLight ? "rgba(0,0,0,0.05)" : "rgba(255,255,255,0.08)",
              border: "none",
              borderRadius: "50%",
              width: 32,
              height: 32,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: isLight ? "#5c5045" : "#cbd5e1",
              cursor: "pointer",
              transition: "background 0.2s ease",
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div
          style={{
            padding: "20px 24px",
            overflowY: "auto",
            fontSize: 13,
            lineHeight: 1.6,
            color: isLight ? "#4a3e35" : "#cbd5e1",
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          <div>
            <h3 style={{ margin: "0 0 4px", fontSize: 13.5, fontWeight: 700, color: isLight ? "#1e1b18" : "#f8fafc" }}>
              1. Acceptance of Terms
            </h3>
            <p style={{ margin: 0 }}>
              By accessing, registering an account, or interacting with Sky Reader, you agree to comply with and be bound by these Terms and Conditions. If you do not agree with any part of these terms, you may not use the services.
            </p>
          </div>

          <div>
            <h3 style={{ margin: "0 0 4px", fontSize: 13.5, fontWeight: 700, color: isLight ? "#1e1b18" : "#f8fafc" }}>
              2. Meteorological Data &amp; Decision Advisory
            </h3>
            <p style={{ margin: 0 }}>
              Observational weather telemetry, forecasts, and synoptic charts are retrieved from Open-Meteo and global numerical weather prediction models. All metrics are advisory decision-support information. Sky Reader is not an official government emergency warning authority and should not be used as sole life-safety guidance during severe natural disasters or storm events.
            </p>
          </div>

          <div>
            <h3 style={{ margin: "0 0 4px", fontSize: 13.5, fontWeight: 700, color: isLight ? "#1e1b18" : "#f8fafc" }}>
              3. AI Synthesis &amp; Grounded Verification
            </h3>
            <p style={{ margin: 0 }}>
              Sky Reader utilizes large language models paired with deterministic parameter verification engines to reduce hallucination risk. While answers are strictly bounded by physical data ranges, automated conversational predictions should be verified against local meteorological authorities.
            </p>
          </div>

          <div>
            <h3 style={{ margin: "0 0 4px", fontSize: 13.5, fontWeight: 700, color: isLight ? "#1e1b18" : "#f8fafc" }}>
              4. Privacy, Credentials &amp; Database Architecture
            </h3>
            <p style={{ margin: 0 }}>
              Your privacy is foundational to Sky Reader. Passwords are encrypted using PBKDF2 with unique salts, and session tokens are strictly scoped. Multi-engine database configurations (Neon Serverless PostgreSQL or local SQLite) preserve thread privacy without selling user telemetry.
            </p>
          </div>

          <div>
            <h3 style={{ margin: "0 0 4px", fontSize: 13.5, fontWeight: 700, color: isLight ? "#1e1b18" : "#f8fafc" }}>
              5. Acceptable Use
            </h3>
            <p style={{ margin: 0 }}>
              You agree to use Sky Reader responsibly. Automated denial-of-service attempts, unauthorized reverse-engineering, scraping behind rate limits, and injection attacks are strictly prohibited.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: isLight ? "1px solid rgba(230,220,205,0.8)" : "1px solid rgba(255,255,255,0.08)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            background: isLight ? "rgba(255,250,242,0.6)" : "rgba(10,16,30,0.5)",
          }}
        >
          <span style={{ fontSize: 11, color: isLight ? "#8c7e72" : "#94a3b8" }}>
            Last updated: November 2026
          </span>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: "9px 22px",
              borderRadius: 12,
              border: "none",
              background: isLight
                ? "linear-gradient(135deg,#d97706 0%,#b45309 100%)"
                : "linear-gradient(135deg,#8b5cf6 0%,#6d28d9 100%)",
              color: "#ffffff",
              fontSize: 12.5,
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: "0 4px 14px rgba(0,0,0,0.2)",
              transition: "transform 0.15s ease",
            }}
          >
            I Understand &amp; Agree
          </button>
        </div>
      </div>
    </div>
  );
}
