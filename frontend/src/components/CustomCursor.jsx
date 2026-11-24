import { useEffect, useRef, useState } from "react";

/**
 * CustomCursor:
 * Modern, hardware-accelerated glowing cosmic weather cursor.
 * Features:
 * - Fluid dual-layer (precision luminous dot + trailing atmospheric aura ring).
 * - Context-aware magnetic scaling when hovering clickable elements.
 * - Click-down pulse feedback.
 * - Automatic touch/mobile suppression.
 */
export default function CustomCursor() {
  const dotRef = useRef(null);
  const ringRef = useRef(null);
  const mousePos = useRef({ x: -100, y: -100 });
  const ringPos = useRef({ x: -100, y: -100 });
  const animFrameId = useRef(null);

  const [isHovered, setIsHovered] = useState(false);
  const [isClicked, setIsClicked] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [isTouch, setIsTouch] = useState(false);

  useEffect(() => {
    // Disable on touch devices
    if (typeof window !== "undefined" && ("ontouchstart" in window || navigator.maxTouchPoints > 0)) {
      setIsTouch(true);
      return;
    }

    const onMouseMove = (e) => {
      mousePos.current = { x: e.clientX, y: e.clientY };
      if (!isVisible) setIsVisible(true);

      // Instantly position the center precision dot
      if (dotRef.current) {
        dotRef.current.style.transform = `translate3d(${e.clientX}px, ${e.clientY}px, 0)`;
      }

      // Check if hovering clickable or interactive elements
      const target = e.target;
      if (target && typeof target.closest === "function") {
        const interactive = target.closest(
          "button, a, input, select, textarea, [role='button'], [tabindex='0'], label, .clickable, .sidebar-terms-btn, .sidebar-logout-btn, .sidebar-recent-item-btn"
        );
        setIsHovered(Boolean(interactive));
      }
    };

    const onMouseDown = () => setIsClicked(true);
    const onMouseUp = () => setIsClicked(false);
    const onMouseLeave = () => setIsVisible(false);
    const onMouseEnter = () => setIsVisible(true);

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mouseup", onMouseUp);
    document.addEventListener("mouseleave", onMouseLeave);
    document.addEventListener("mouseenter", onMouseEnter);

    // Smooth spring lerp for the trailing aura ring
    const renderLoop = () => {
      const lerp = 0.22;
      ringPos.current.x += (mousePos.current.x - ringPos.current.x) * lerp;
      ringPos.current.y += (mousePos.current.y - ringPos.current.y) * lerp;

      if (ringRef.current) {
        ringRef.current.style.transform = `translate3d(${ringPos.current.x}px, ${ringPos.current.y}px, 0)`;
      }

      animFrameId.current = requestAnimationFrame(renderLoop);
    };

    animFrameId.current = requestAnimationFrame(renderLoop);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mouseup", onMouseUp);
      document.removeEventListener("mouseleave", onMouseLeave);
      document.removeEventListener("mouseenter", onMouseEnter);
      if (animFrameId.current) cancelAnimationFrame(animFrameId.current);
    };
  }, [isVisible]);

  if (isTouch) return null;

  return (
    <div
      className="custom-cursor-layer"
      aria-hidden="true"
      style={{
        position: "fixed",
        inset: 0,
        pointerEvents: "none",
        zIndex: 999999,
        opacity: isVisible ? 1 : 0,
        transition: "opacity 0.2s ease",
      }}
    >
      {/* Trailing Atmospheric Aura Ring */}
      <div
        ref={ringRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: isHovered ? 52 : isClicked ? 24 : 36,
          height: isHovered ? 52 : isClicked ? 24 : 36,
          marginTop: isHovered ? -26 : isClicked ? -12 : -18,
          marginLeft: isHovered ? -26 : isClicked ? -12 : -18,
          borderRadius: "50%",
          border: isHovered
            ? "1.5px solid rgba(245, 158, 11, 0.85)"
            : "1.5px solid rgba(56, 189, 248, 0.65)",
          background: "transparent",
          boxShadow: isHovered
            ? "0 0 16px rgba(245, 158, 11, 0.35)"
            : "0 0 12px rgba(56, 189, 248, 0.25)",
          pointerEvents: "none",
          transition:
            "width 0.22s cubic-bezier(0.16, 1, 0.3, 1), height 0.22s cubic-bezier(0.16, 1, 0.3, 1), margin 0.22s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.2s ease",
          willChange: "transform",
        }}
      />

      {/* Crisp Precision Center Dot */}
      <div
        ref={dotRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: isHovered ? 6 : 7,
          height: isHovered ? 6 : 7,
          marginTop: isHovered ? -3 : -3.5,
          marginLeft: isHovered ? -3 : -3.5,
          borderRadius: "50%",
          background: isHovered ? "#fbbf24" : "#38bdf8",
          boxShadow: isHovered
            ? "0 0 10px #fbbf24, 0 0 18px rgba(245, 158, 11, 0.8)"
            : "0 0 8px #38bdf8, 0 0 16px rgba(56, 189, 248, 0.7)",
          pointerEvents: "none",
          transition: "background 0.2s ease, box-shadow 0.2s ease",
          willChange: "transform",
        }}
      />
    </div>
  );
}
