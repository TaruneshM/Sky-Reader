import { useEffect, useRef, useState, useCallback } from "react";
import handWebp from "../assets/intro/hand-cutout.webp";
import handPng from "../assets/intro/hand-cutout.png";

/**
 * Sky Reader One-Time Intro Animation
 * Sequence:
 *   0.0 - 0.8s: Sky & clouds visible; ambient stars fade in; form is hidden.
 *   0.6 - 2.0s: Hand fades in via soft mask sweep from wrist to fingertips;
 *               sways from wrist (+/- 6 deg, 2 swings); star particles drift off fingertips.
 *   1.8 - 3.4s: Particles stream towards centre & converge into "Sky Reader" text
 *               (sampled from offscreen canvas); crisp wordmark settles with light sweep.
 *   3.4 - 4.5s: Hand fades out; wordmark glides via FLIP transform into card brand position;
 *               glass card fades & rises in; intro finishes & focus moves to email.
 */
export default function SkyReaderIntro({ onComplete, onSkip, cardBrandRef }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const wordmarkRef = useRef(null);
  const handRef = useRef(null);
  const animFrameRef = useRef(null);
  const isSkippedRef = useRef(false);

  // Time tracking
  const startTimeRef = useRef(null);
  const pausedTimeRef = useRef(0);
  const lastHiddenTimeRef = useRef(null);

  const [wordmarkVisible, setWordmarkVisible] = useState(false);
  const [wordmarkStyle, setWordmarkStyle] = useState({});
  const [handStyle, setHandStyle] = useState({ opacity: 0 });

  const handleFinish = useCallback(() => {
    if (isSkippedRef.current) return;
    isSkippedRef.current = true;
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (onComplete) onComplete();
  }, [onComplete]);

  const handleSkip = useCallback(() => {
    if (isSkippedRef.current) return;
    isSkippedRef.current = true;
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

  // Check prefers-reduced-motion immediately on mount
  useEffect(() => {
    if (typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      handleSkip();
    }
  }, [handleSkip]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      // In non-canvas environments (SSR / test mocks), complete cleanly
      handleFinish();
      return;
    }

    let width = 0;
    let height = 0;
    let dpr = 1;
    let isMobile = false;

    // Build offscreen target points for "Sky Reader" text
    const sampleTextTargets = (w, h, mobileMode) => {
      const offscreen = document.createElement("canvas");
      const offCtx = offscreen.getContext("2d");
      const fontSize = mobileMode ? 36 : 56;
      const fontFamily = "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif";
      offCtx.font = `700 ${fontSize}px ${fontFamily}`;
      const text = "Sky Reader";
      const textMetrics = offCtx.measureText(text);
      const textW = Math.ceil(textMetrics.width);
      const textH = Math.ceil(fontSize * 1.3);

      offscreen.width = textW + 40;
      offscreen.height = textH + 40;
      offCtx.font = `700 ${fontSize}px ${fontFamily}`;
      offCtx.fillStyle = "#ffffff";
      offCtx.textBaseline = "middle";
      offCtx.fillText(text, 20, offscreen.height / 2);

      const imgData = offCtx.getImageData(0, 0, offscreen.width, offscreen.height);
      const rawPoints = [];
      const step = 2;

      for (let py = 0; py < offscreen.height; py += step) {
        for (let px = 0; px < offscreen.width; px += step) {
          const idx = (py * offscreen.width + px) * 4;
          if (imgData.data[idx + 3] > 120) {
            rawPoints.push({
              x: px - offscreen.width / 2,
              y: py - offscreen.height / 2,
            });
          }
        }
      }

      // Center of screen where text will form
      const centerX = (w || window.innerWidth) / 2;
      const centerY = (h || window.innerHeight) * (mobileMode ? 0.40 : 0.42);

      return {
        centerX,
        centerY,
        fontSize,
        points: rawPoints.map((pt) => ({
          x: centerX + pt.x,
          y: centerY + pt.y,
        })),
      };
    };

    let textTargetData = sampleTextTargets(window.innerWidth, window.innerHeight, window.innerWidth < 768);
    const particles = [];

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      isMobile = width < 768;
      textTargetData = sampleTextTargets(width, height, isMobile);
      if (particles.length > 0 && textTargetData.points.length > 0) {
        particles.forEach((p, i) => {
          const pt = textTargetData.points[i % textTargetData.points.length];
          p.targetX = pt.x + (Math.random() - 0.5) * 2;
          p.targetY = pt.y + (Math.random() - 0.5) * 2;
        });
      }
    };
    resize();

    const ro = new ResizeObserver(resize);
    ro.observe(document.body);

    // Particle Setup
    // Particle count: ~1200 desktop, ~500 mobile
    const PARTICLE_COUNT = isMobile ? 500 : 1200;
    const AMBIENT_STARS_COUNT = isMobile ? 40 : 80;

    // Fingertip region calculation
    const getFingertipEmitter = () => {
      const handW = isMobile ? Math.min(width * 0.72, 280) : Math.min(width * 0.4, 380);
      const handH = handW * (714 / 624);
      const handBottom = height;
      const handTop = handBottom - Math.min(handH, isMobile ? 300 : 420);
      const handCenter = width / 2;

      return {
        minX: handCenter - handW * 0.28,
        maxX: handCenter + handW * 0.28,
        minY: handTop,
        maxY: handTop + handH * 0.22,
      };
    };

    // Ambient stars (fade in 0.0 - 0.8s)
    const ambientStars = [];
    for (let i = 0; i < AMBIENT_STARS_COUNT; i++) {
      ambientStars.push({
        x: Math.random() * width,
        y: Math.random() * height * 0.75,
        r: Math.random() * 1.5 + 0.4,
        twinkleSpeed: Math.random() * 2 + 1,
        maxAlpha: Math.random() * 0.6 + 0.3,
      });
    }

    // Main particle field
    const emitter = getFingertipEmitter();

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      // Spawn around fingertips
      const startX = emitter.minX + Math.random() * (emitter.maxX - emitter.minX);
      const startY = emitter.maxY - Math.random() * (emitter.maxY - emitter.minY);

      // Target mapping
      const targetPoint = textTargetData.points[i % textTargetData.points.length] || {
        x: textTargetData.centerX + (Math.random() - 0.5) * 200,
        y: textTargetData.centerY + (Math.random() - 0.5) * 50,
      };

      const hues = [
        "rgba(255, 255, 255,",      // White
        "rgba(186, 230, 253,",      // Soft sky aqua
        "rgba(56, 189, 248,",       // Radiant aqua
        "rgba(96, 165, 250,",       // Royal accent blue
      ];
      const colorBase = hues[i % hues.length];

      particles.push({
        startX,
        startY,
        currentX: startX,
        currentY: startY,
        // Drift velocity when coming off fingertips
        vx: (Math.random() - 0.5) * 1.8,
        vy: -Math.random() * 1.8 - 0.4,
        driftPhase: Math.random() * Math.PI * 2,
        r: Math.random() * 1.8 + 0.6,
        colorBase,
        alpha: 0,
        targetX: targetPoint.x + (Math.random() - 0.5) * 2,
        targetY: targetPoint.y + (Math.random() - 0.5) * 2,
        streamDelay: Math.random() * 0.35, // slight stagger when flying to text
      });
    }

    // Pause / Resume on visibility change
    const handleVisibility = () => {
      if (document.hidden) {
        lastHiddenTimeRef.current = performance.now();
      } else if (lastHiddenTimeRef.current) {
        pausedTimeRef.current += performance.now() - lastHiddenTimeRef.current;
        lastHiddenTimeRef.current = null;
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);

    // Easing helper
    const easeInOutCubic = (t) =>
      t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

    // Animation Loop
    const TOTAL_DURATION = 4.5; // seconds

    const render = (now) => {
      if (isSkippedRef.current) return;
      if (!startTimeRef.current) startTimeRef.current = now;
      const effectiveNow = now - pausedTimeRef.current;
      const elapsed = Math.max(0, (effectiveNow - startTimeRef.current) / 1000);

      ctx.clearRect(0, 0, width, height);

      // --- SEQUENCE LOGIC ---

      // 1. 0.0 - 0.8s: Ambient Stars Fade In
      const ambientFade = Math.min(1, elapsed / 0.8);
      ambientStars.forEach((star) => {
        const twinkle = Math.sin(elapsed * star.twinkleSpeed) * 0.25 + 0.75;
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${ambientFade * star.maxAlpha * twinkle})`;
        ctx.fill();
      });

      // 2. 0.6 - 2.0s: Hand Fade-In & Sway
      let handOpacity = 0;
      let handRotation = 0;
      let handMaskPercent = 0;

      if (elapsed >= 0.6 && elapsed < 3.8) {
        // Fade in soft mask sweep from wrist to fingertips (0.6s - 1.3s)
        if (elapsed < 1.3) {
          const maskProgress = (elapsed - 0.6) / 0.7; // 0 -> 1
          handOpacity = maskProgress;
          handMaskPercent = Math.min(100, Math.round(maskProgress * 125));
        } else if (elapsed <= 3.3) {
          handOpacity = 1;
          handMaskPercent = 100;
        } else {
          // Fade out (3.3s - 3.8s)
          handOpacity = Math.max(0, 1 - (elapsed - 3.3) / 0.5);
          handMaskPercent = 100;
        }

        // Wrist sway: 0.8s - 2.2s (transform origin at wrist, +/- 6 degrees, 2 swings)
        if (elapsed >= 0.8 && elapsed <= 2.2) {
          const swayProgress = (elapsed - 0.8) / 1.4; // 0 -> 1
          const swayEnvelope = Math.sin(swayProgress * Math.PI); // smoothly ramp in and out
          handRotation = Math.sin(swayProgress * 4 * Math.PI) * 6 * swayEnvelope;
        }
      }

      // Update Hand DOM element styles
      setHandStyle({
        opacity: handOpacity,
        transform: `rotate(${handRotation.toFixed(2)}deg)`,
        maskImage:
          handMaskPercent >= 100
            ? "none"
            : `linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,1) ${handMaskPercent}%, rgba(0,0,0,0) ${handMaskPercent + 25}%)`,
        WebkitMaskImage:
          handMaskPercent >= 100
            ? "none"
            : `linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,1) ${handMaskPercent}%, rgba(0,0,0,0) ${handMaskPercent + 25}%)`,
      });

      // 3. Particles drift off fingertips (0.8s - 1.8s) -> Stream to text (1.8s - 3.4s)
      particles.forEach((p) => {
        // Fingertip emission phase
        if (elapsed >= 0.8 && elapsed < 1.8) {
          const emitProgress = Math.min(1, (elapsed - 0.8) / 0.5);
          p.alpha = Math.min(0.9, emitProgress * 0.9);
          // drift
          p.currentX += p.vx + Math.sin(elapsed * 2 + p.driftPhase) * 0.3;
          p.currentY += p.vy;
          // record position right before streaming
          p.preStreamX = p.currentX;
          p.preStreamY = p.currentY;
        } else if (elapsed >= 1.8 && elapsed <= 3.4) {
          // Streaming to text "Sky Reader"
          const streamStart = 1.8 + p.streamDelay;
          if (elapsed < streamStart) {
            p.currentX += p.vx * 0.3;
            p.currentY += p.vy * 0.3;
          } else {
            const streamProgress = Math.min(1, Math.max(0, (elapsed - streamStart) / 1.0));
            const ease = easeInOutCubic(streamProgress);
            const startX = p.preStreamX || p.startX;
            const startY = p.preStreamY || p.startY;

            p.currentX = startX + (p.targetX - startX) * ease;
            p.currentY = startY + (p.targetY - startY) * ease;
            p.alpha = 0.9;
          }
        } else if (elapsed > 3.4) {
          // Particles fade out as wordmark settles & glides
          const fadeOut = Math.max(0, 1 - (elapsed - 3.4) / 0.4);
          p.alpha = fadeOut * 0.9;
        }

        if (p.alpha > 0.01) {
          ctx.beginPath();
          ctx.arc(p.currentX, p.currentY, p.r, 0, Math.PI * 2);
          ctx.fillStyle = `${p.colorBase} ${p.alpha.toFixed(2)})`;
          ctx.fill();
        }
      });

      // 4. Wordmark Appearance & Light Sweep (2.8s - 3.4s) -> Glide FLIP (3.4s - 4.5s)
      if (elapsed >= 2.8) {
        setWordmarkVisible(true);

        if (elapsed < 3.4) {
          // Soft light sweep across wordmark
          const sweepProgress = (elapsed - 2.8) / 0.6; // 0 -> 1
          const sweepPercent = Math.round(sweepProgress * 150 - 25);
          const startX = textTargetData.centerX;
          const startY = textTargetData.centerY;
          setWordmarkStyle({
            opacity: Math.min(1, (elapsed - 2.8) / 0.3),
            transform: `translate3d(calc(${startX.toFixed(1)}px - 50%), calc(${startY.toFixed(1)}px - 50%), 0) scale(1)`,
            backgroundPosition: `${sweepPercent}% center`,
          });
        } else {
          // FLIP glide to card brand position (3.4s - 4.4s)
          const glideProgress = Math.min(1, (elapsed - 3.4) / 0.95);
          const easeGlide = easeInOutCubic(glideProgress);

          let targetX = width / 2;
          let targetY = height / 2 - 160;
          let targetScale = 0.44; // Scale down from ~56px to 22px

          if (cardBrandRef?.current) {
            const rect = cardBrandRef.current.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              targetX = rect.left + rect.width / 2;
              targetY = rect.top + rect.height / 2;
              targetScale = Math.max(0.35, Math.min(0.55, 22 / (isMobile ? 36 : 56)));
            }
          }

          const startX = textTargetData.centerX;
          const startY = textTargetData.centerY;

          const currentX = startX + (targetX - startX) * easeGlide;
          const currentY = startY + (targetY - startY) * easeGlide;
          const currentScale = 1 + (targetScale - 1) * easeGlide;
          const opacity = glideProgress >= 0.9 ? Math.max(0, 1 - (glideProgress - 0.9) * 10) : 1;

          setWordmarkStyle({
            opacity,
            transform: `translate3d(calc(${currentX.toFixed(1)}px - 50%), calc(${currentY.toFixed(1)}px - 50%), 0) scale(${currentScale.toFixed(3)})`,
            backgroundPosition: "150% center",
          });
        }
      }

      // 5. Completion at 4.5s
      if (elapsed >= TOTAL_DURATION) {
        handleFinish();
        return;
      }

      animFrameRef.current = requestAnimationFrame(render);
    };

    animFrameRef.current = requestAnimationFrame(render);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      document.removeEventListener("visibilitychange", handleVisibility);
      ro.disconnect();
    };
  }, [handleFinish, cardBrandRef]);

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
        height: "100dvh",
        zIndex: 50,
        pointerEvents: "auto",
        cursor: "pointer",
        overflow: "hidden",
      }}
    >
      {/* 2D Canvas for Stars & Converging Particles */}
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
          zIndex: 51,
        }}
      />

      {/* Galaxy Hand Artwork */}
      <div
        ref={handRef}
        className="intro-hand-wrapper"
        style={{
          position: "absolute",
          bottom: 0,
          left: "50%",
          transform: `translateX(-50%) ${handStyle.transform || ""}`,
          transformOrigin: "50% 95%",
          pointerEvents: "none",
          zIndex: 52,
          opacity: handStyle.opacity ?? 0,
          maskImage: handStyle.maskImage,
          WebkitMaskImage: handStyle.WebkitMaskImage,
          transition: "opacity 0.05s linear",
          maxHeight: "min(420px, 48vh)",
          display: "flex",
          justifyContent: "center",
          alignItems: "flex-end",
        }}
      >
        <picture>
          <source srcSet={handWebp} type="image/webp" />
          <img
            src={handPng}
            alt=""
            style={{
              maxHeight: "min(420px, 48vh)",
              maxWidth: "min(380px, 85vw)",
              width: "auto",
              height: "auto",
              objectFit: "contain",
              userSelect: "none",
              display: "block",
            }}
          />
        </picture>
      </div>

      {/* Converged Wordmark with Soft Light Sweep */}
      {wordmarkVisible && (
        <div
          ref={wordmarkRef}
          className="intro-wordmark"
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            pointerEvents: "none",
            zIndex: 55,
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif",
            fontWeight: 700,
            fontSize: "clamp(34px, 5.5vw, 56px)",
            letterSpacing: "-0.5px",
            color: "#ffffff",
            textShadow: "0 0 24px rgba(56, 189, 248, 0.65), 0 0 45px rgba(56, 189, 248, 0.35)",
            whiteSpace: "nowrap",
            backgroundImage:
              "linear-gradient(105deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,1) 40%, #7dd3fc 50%, rgba(255,255,255,1) 60%, rgba(255,255,255,0.9) 100%)",
            backgroundSize: "200% 100%",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            ...wordmarkStyle,
          }}
        >
          Sky Reader
        </div>
      )}

      {/* Accessible Skip Button */}
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
          top: 24,
          right: 24,
          padding: "8px 18px",
          borderRadius: 999,
          border: "1px solid rgba(255, 255, 255, 0.22)",
          background: "rgba(24, 49, 97, 0.45)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          color: "rgba(255, 255, 255, 0.9)",
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
          zIndex: 60,
          boxShadow: "0 4px 16px rgba(0, 0, 0, 0.25)",
          transition: "background 0.18s ease, transform 0.18s ease",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "rgba(56, 189, 248, 0.3)";
          e.currentTarget.style.transform = "scale(1.04)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "rgba(24, 49, 97, 0.45)";
          e.currentTarget.style.transform = "scale(1)";
        }}
      >
        Skip ✕
      </button>
    </div>
  );
}
