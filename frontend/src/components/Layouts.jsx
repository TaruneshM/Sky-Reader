import { useEffect, useRef, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import ChatHeader from "./ChatHeader";
import Sidebar from "./Sidebar";
import WeatherAtmosphere from "./WeatherAtmosphere";

function canReturnTo(path) {
  return typeof path === "string" && /^\/(?![/\\])/.test(path)
    && /^\/(?:dashboard|preferences|saved|notifications)\/?(?:[?#]|$)/i.test(path);
}

function CloudBank() {
  const layer = useRef(null);
  useEffect(() => {
    const clouds = layer.current;
    const syncVisibility = () => clouds.toggleAttribute("data-paused", document.hidden);
    syncVisibility();
    document.addEventListener("visibilitychange", syncVisibility);
    return () => document.removeEventListener("visibilitychange", syncVisibility);
  }, []);

  return (
    <div className="sky-cloud-layer" ref={layer} aria-hidden="true">
      <div className="sky-cloud-sprite cloud-shelf" />
      <div className="sky-cloud-sprite cloud-ridge" />
      <div className="sky-cloud-sprite cloud-tower" />
      <div className="sky-cloud-sprite cloud-bank" />
    </div>
  );
}

function AnimatedSkyBackground() {
  return (
    <div className="skyreader-ambient-bg" aria-hidden="true">
      <div className="skyreader-ambient-glow glow-primary" />
      <div className="skyreader-ambient-glow glow-secondary" />
      <div className="skyreader-ambient-glow glow-tertiary" />
      <div className="skyreader-ambient-glow glow-warm" />
      <div className="skyreader-aurora-ribbon" />
    </div>
  );
}

export function WeatherLayout({ scene, theme, children }) {
  const sceneClass = scene === "none" ? "" : ` atmosphere-active-${scene}`;
  return (
    <div className={`skyreader-root-environment${sceneClass}`}>
      <AnimatedSkyBackground />
      <CloudBank />
      <WeatherAtmosphere scene={scene} isNight={theme === "dark"} />
      {children}
    </div>
  );
}

export function AuthLayout({ phase, signedIn }) {
  const location = useLocation();
  const from = location.state?.from;
  const returnPath = canReturnTo(from) ? from : null;
  if (signedIn) {
    const next = phase === "account" && returnPath ? returnPath : "/chat";
    return <Navigate to={next} replace />;
  }
  if (phase === "unavailable" && location.pathname.toLowerCase() !== "/login") {
    return <Navigate to="/login" replace state={returnPath ? { from: returnPath } : undefined} />;
  }
  return <Outlet />;
}

export function AppLayout({ signedIn, user, onLogout, onOpenTerms, chatSessions, header, notice }) {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  if (!signedIn) {
    const from = location.pathname + location.search + location.hash;
    return <Navigate to="/login" replace state={canReturnTo(from) ? { from } : undefined} />;
  }

  return (
    <div className="floating-app-window-frame">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onLogout={onLogout}
        onOpenTerms={onOpenTerms}
        user={user}
        chatSessions={chatSessions}
      />
      <div className="floating-main-canvas">
        <ChatHeader {...header} onToggleSidebar={() => setSidebarOpen((open) => !open)} />
        {notice && <p role="alert">{notice}</p>}
        <Outlet />
      </div>
    </div>
  );
}
