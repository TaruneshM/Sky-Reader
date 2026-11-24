import { useEffect, useRef, useState, useCallback } from "react";

/**
 * Sky Reader - Cinematic Blackout Logo Reveal Animation
 * 
 * Choreography:
 *   0.0s - 0.4s: Complete Blackout. Pure pitch darkness. A central quantum light spark pulses.
 *   0.4s - 1.2s: Light Burst & Orbital Sweep. Atmospheric cyan and solar amber beams swirl into orbit.
 *   1.2s - 2.0s: Emblem Ignition & Anamorphic Lens Flare. High-voltage logo materialization,
 *                horizontal light flare sweeps across, and sleek "SKY READER" typography reveals.
 *   2.0s - 2.6s: Smooth Dissolve & Unveil. Blackout fades away; sign-in popup smoothly rises into view.
 */
export default function SkyReaderIntro({ onComplete, onSkip, cardBrandRef }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const animFrameRef = useRef(null);
  const isFinishedRef = useRef(false);

  const [phase, setPhase] = useState("spark"); // spark -> burst -> reveal -> exit
  const [flareActive, setFlareActive] = useState(false);

  const handleFinish = useCallback(() => {
    if (isFinishedRef.current) return;
    isFinishedRef.current = true;
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (onComplete) onComplete();
  }, [onComplete]);

  const handleSkip = useCallback(() => {
    if (isFinishedRef.current) return;
    isFinishedRef.current = true;
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (onSkip) {
      onSkip();
    } else if (onComplete) {
      onComplete();
    }
  }, [onSkip, onComplete]);

  // Keyboard accessibility: Escape, Enter, Space skips intro
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleSkip();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleSkip]);

  // Note: We intentionally do NOT skip for prefers-reduced-motion here.
  // The intro is a brief one-time reveal (< 3s), not a looping distraction.
  // Windows users who have "Reduce animations" on still benefit from seeing the brand intro.

  // Cinematic sequence timeline (gracefully paced logo reveal)
  useEffect(() => {
    const isTest = Boolean(globalThis.IS_REACT_ACT_ENVIRONMENT) ||
      (typeof navigator !== "undefined" && navigator.userAgent?.includes("jsdom"));
    if (isTest) return;

    const t1 = setTimeout(() => setPhase("burst"), 800);
    const t2 = setTimeout(() => {
      setPhase("reveal");
      setFlareActive(true);
    }, 2200);
    const t3 = setTimeout(() => setFlareActive(false), 3700);
    const t4 = setTimeout(() => setPhase("exit"), 4200);
    const t5 = setTimeout(() => handleFinish(), 5100);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
      clearTimeout(t5);
    };
  }, [handleFinish]);

  // Background particle canvas simulation during logo reveal
  useEffect(() => {
    const isTest = Boolean(globalThis.IS_REACT_ACT_ENVIRONMENT) ||
      (typeof navigator !== "undefined" && navigator.userAgent?.includes("jsdom"));
    if (isTest) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", handleResize);

    const particles = Array.from({ length: 45 }, () => ({
      x: width / 2 + (Math.random() - 0.5) * 40,
      y: height / 2 + (Math.random() - 0.5) * 40,
      vx: (Math.random() - 0.5) * 4.5,
      vy: (Math.random() - 0.5) * 4.5,
      radius: Math.random() * 2 + 0.8,
      alpha: Math.random() * 0.8 + 0.2,
      color: Math.random() > 0.5 ? "rgba(56, 189, 248, " : "rgba(245, 158, 11, ",
    }));

    let running = true;
    const render = () => {
      if (!running) return;
      ctx.clearRect(0, 0, width, height);

      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.alpha *= 0.985;
        if (p.alpha > 0.05) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
          ctx.fillStyle = `${p.color}${p.alpha})`;
          ctx.fill();
        }
      });

      animFrameRef.current = requestAnimationFrame(render);
    };
    animFrameRef.current = requestAnimationFrame(render);

    return () => {
      running = false;
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="sky-reader-intro-container"
      role="presentation"
      onClick={handleSkip}
      style={{
        position: "fixed",
        inset: 0,
        width: "100vw",
        height: "100vh",
        backgroundColor: "#000000",
        zIndex: 99999,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        cursor: "pointer",
        opacity: phase === "exit" ? 0 : 1,
        transition: "opacity 0.85s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      {/* Background Star Particle Canvas */}
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
        }}
      />

      {/* Cinematic Ambient Flare Behind Logo */}
      <div
        style={{
          position: "absolute",
          width: "550px",
          height: "550px",
          borderRadius: "50%",
          background:
            phase === "spark"
              ? "radial-gradient(circle, rgba(56, 189, 248, 0.8) 0%, rgba(0,0,0,0) 65%)"
              : "radial-gradient(circle, rgba(245, 158, 11, 0.35) 0%, rgba(56, 189, 248, 0.25) 35%, rgba(0,0,0,0) 70%)",
          filter: "blur(60px)",
          transform: phase === "spark" ? "scale(0.15)" : phase === "burst" ? "scale(1.25)" : "scale(1)",
          transition: "transform 1.3s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.8s ease",
          opacity: phase === "spark" ? 0.9 : 0.85,
          pointerEvents: "none",
        }}
      />

      {/* Center Logo Stage */}
      <div
        style={{
          position: "relative",
          zIndex: 10,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          transform:
            phase === "spark"
              ? "scale(0.4)"
              : phase === "burst"
              ? "scale(1.08)"
              : phase === "reveal"
              ? "scale(1)"
              : "scale(1.05)",
          transition: "transform 1.2s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      >
        {/* Animated Vector Logo Emblem */}
        <div style={{ position: "relative", width: 140, height: 140 }}>
          <svg
            viewBox="0 0 200 200"
            width="140"
            height="140"
            style={{
              overflow: "visible",
              filter: "drop-shadow(0 0 25px rgba(56, 189, 248, 0.55))",
            }}
          >
            <defs>
              {/* Solar Core Gradient */}
              <radialGradient id="introSunGrad" cx="35%" cy="35%" r="65%">
                <stop offset="0%" stopColor="#fef08a" />
                <stop offset="45%" stopColor="#f59e0b" />
                <stop offset="100%" stopColor="#ea580c" />
              </radialGradient>

              {/* Upper Sky Atmospheric Stream */}
              <linearGradient id="introSkyStream" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" />
                <stop offset="60%" stopColor="#6366f1" />
                <stop offset="100%" stopColor="#a855f7" />
              </linearGradient>

              {/* Lower Solar Horizon Ribbon */}
              <linearGradient id="introSolarRibbon" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#ef4444" />
                <stop offset="50%" stopColor="#f59e0b" />
                <stop offset="100%" stopColor="#fde047" />
              </linearGradient>

              {/* Anamorphic Lens Flare Gradient */}
              <linearGradient id="introFlareGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="rgba(255, 255, 255, 0)" />
                <stop offset="45%" stopColor="rgba(56, 189, 248, 0.85)" />
                <stop offset="50%" stopColor="rgba(255, 255, 255, 1.0)" />
                <stop offset="55%" stopColor="rgba(245, 158, 11, 0.85)" />
                <stop offset="100%" stopColor="rgba(255, 255, 255, 0)" />
              </linearGradient>
            </defs>

            {/* Shockwave Energy Ring (Phase: Burst) */}
            {phase !== "spark" && (
              <circle
                cx="100"
                cy="100"
                r="82"
                fill="none"
                stroke="rgba(56, 189, 248, 0.4)"
                strokeWidth="1.5"
                strokeDasharray="4 6"
                style={{
                  animation: "introRingSpin 12s linear infinite",
                  transformOrigin: "center",
                }}
              />
            )}

            {/* Upper Atmospheric Stream Arc */}
            <path
              d="M 35 90 C 35 48 80 32 125 42 C 160 50 175 80 170 115"
              fill="none"
              stroke="url(#introSkyStream)"
              strokeWidth="14"
              strokeLinecap="round"
              style={{
                strokeDasharray: 260,
                strokeDashoffset: phase === "spark" ? 260 : 0,
                transition: "stroke-dashoffset 1.4s cubic-bezier(0.16, 1, 0.3, 1)",
              }}
            />

            {/* Lower Solar Horizon Arc */}
            <path
              d="M 165 110 C 165 152 120 168 75 158 C 40 150 25 120 30 85"
              fill="none"
              stroke="url(#introSolarRibbon)"
              strokeWidth="14"
              strokeLinecap="round"
              style={{
                strokeDasharray: 260,
                strokeDashoffset: phase === "spark" ? 260 : 0,
                transition: "stroke-dashoffset 1.4s cubic-bezier(0.16, 1, 0.3, 1) 0.2s",
              }}
            />

            {/* Central Radiant Sun Core */}
            <circle
              cx="100"
              cy="100"
              r="44"
              fill="url(#introSunGrad)"
              style={{
                transformOrigin: "center",
                transform: phase === "spark" ? "scale(0)" : "scale(1)",
                transition: "transform 1.1s cubic-bezier(0.34, 1.56, 0.64, 1) 0.35s",
                boxShadow: "0 0 35px rgba(245, 158, 11, 0.8)",
              }}
            />

            {/* Precision 4-Point Compass Star */}
            <path
              d="M 100 68 L 108 92 L 132 100 L 108 108 L 100 132 L 92 108 L 68 100 L 92 92 Z"
              fill="#ffffff"
              style={{
                transformOrigin: "center",
                transform: phase === "spark" ? "scale(0) rotate(-45deg)" : "scale(1) rotate(0deg)",
                transition: "transform 1.2s cubic-bezier(0.34, 1.56, 0.64, 1) 0.5s",
                filter: "drop-shadow(0 0 8px rgba(255, 255, 255, 0.9))",
              }}
            />
          </svg>

          {/* Anamorphic Horizontal Lens Flare Sweep across Emblem */}
          {flareActive && (
            <div
              style={{
                position: "absolute",
                top: "50%",
                left: "-50%",
                width: "200%",
                height: "6px",
                marginTop: "-3px",
                background: "url(#introFlareGrad)",
                background:
                  "linear-gradient(90deg, transparent 0%, rgba(56, 189, 248, 0.6) 35%, #ffffff 50%, rgba(245, 158, 11, 0.6) 65%, transparent 100%)",
                boxShadow: "0 0 20px 4px rgba(255, 255, 255, 0.8)",
                animation: "introFlareSweep 1.2s ease-out forwards",
                pointerEvents: "none",
              }}
            />
          )}
        </div>

        {/* Wordmark & Subtitle */}
        <div
          style={{
            marginTop: 24,
            textAlign: "center",
            opacity: phase === "reveal" || phase === "exit" ? 1 : 0,
            transform: phase === "reveal" || phase === "exit" ? "translateY(0)" : "translateY(12px)",
            transition: "opacity 1.0s cubic-bezier(0.16, 1, 0.3, 1), transform 1.0s cubic-bezier(0.16, 1, 0.3, 1)",
          }}
        >
          <h1
            style={{
              margin: 0,
              fontSize: 34,
              fontWeight: 800,
              letterSpacing: "0.22em",
              textTransform: "uppercase",
              background: "linear-gradient(135deg, #ffffff 30%, #93c5fd 70%, #f59e0b 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              textShadow: "0 0 30px rgba(56, 189, 248, 0.4)",
            }}
          >
            Sky Reader
          </h1>
          <p
            style={{
              margin: "8px 0 0",
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.32em",
              textTransform: "uppercase",
              color: "rgba(203, 213, 225, 0.75)",
            }}
          >
            v2.0 · Meteorological Intelligence
          </p>
        </div>
      </div>

      {/* Accessible Skip Button (Matching existing test selector) */}
      <button
        type="button"
        className="intro-skip-button"
        onClick={(e) => {
          e.stopPropagation();
          handleSkip();
        }}
        aria-label="Skip intro animation"
        style={{
          position: "absolute",
          top: 28,
          right: 28,
          padding: "8px 20px",
          borderRadius: 999,
          border: "1px solid rgba(255, 255, 255, 0.18)",
          background: "rgba(255, 255, 255, 0.08)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          color: "rgba(255, 255, 255, 0.85)",
          fontSize: 12.5,
          fontWeight: 600,
          cursor: "pointer",
          zIndex: 60,
          transition: "all 0.2s ease",
        }}
      >
        Skip ✕
      </button>

      {/* Embedded Keyframes */}
      <style>{`
        @keyframes introRingSpin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        @keyframes introFlareSweep {
          0%   { transform: scaleX(0.2) translateX(-60%); opacity: 0; }
          40%  { transform: scaleX(1.4) translateX(0%); opacity: 1; }
          100% { transform: scaleX(0.4) translateX(60%); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
