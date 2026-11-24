import { useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import ChatHeader from "./ChatHeader";
import Sidebar from "./Sidebar";
import WeatherAtmosphere from "./WeatherAtmosphere";

function canReturnTo(path) {
  return typeof path === "string" && /^\/(?![/\\])/.test(path)
    && /^\/(?:dashboard|preferences|saved|notifications)\/?(?:[?#]|$)/i.test(path);
}

export function WeatherLayout({ activeScene, theme, children }) {
  return (
    <div className={`skyreader-root-environment atmosphere-active-${activeScene}`}>
      <WeatherAtmosphere scene={activeScene} isNight={theme === "dark"} />
      <div className="video1-sky-cloud-layer" aria-hidden="true">
        <div className="sky-cloud-puff puff-1" />
        <div className="sky-cloud-puff puff-2" />
        <div className="sky-cloud-puff puff-3" />
        <div className="sky-cloud-puff puff-4" />
      </div>
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

export function AppLayout({ signedIn, user, onLogout, chatSessions, header, notice }) {
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
