import {
  MessageSquare,
  Compass,
  Bookmark,
  Sliders,
  Bell,
  LogOut,
  X,
  LayoutGrid,
} from "lucide-react";

export default function Sidebar({
  isOpen,
  onClose,
  activeTab,
  setActiveTab,
  onOpenLogin,
  user,
  chatSessions = [],
  onSelectSession,
}) {
  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isOpen && (
        <div
          className="sidebar-backdrop"
          onClick={onClose}
          aria-label="Close sidebar overlay"
        />
      )}

      <aside className={`sky-sidebar ${isOpen ? "open" : "collapsed"}`}>
        {/* Sidebar Header with Orange Gradient Brand Emblem (Matches Video 1) */}
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <div className="brand-logo-amber-box">
              <span className="brand-letter-e">S</span>
            </div>
            <div className="brand-meta">
              <h2 className="brand-name">Sky Reader</h2>
              <span className="brand-version-sub">v2.0 AI</span>
            </div>
          </div>

          <button
            type="button"
            className="sidebar-collapse-grid-btn"
            onClick={onClose}
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <LayoutGrid size={17} />
          </button>
          <button
            type="button"
            className="sidebar-mobile-close-btn"
            onClick={onClose}
            title="Close sidebar"
            aria-label="Close sidebar"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation Menu List (Matches Video 1 layout exactly) */}
        <nav className="sidebar-nav-menu" aria-label="Main App Navigation">
          <button
            type="button"
            className={`nav-pill-btn ${activeTab === "agent" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("agent");
              if (window.innerWidth < 1024) onClose();
            }}
          >
            <MessageSquare size={17} className="nav-item-icon" />
            <span className="nav-item-text">Chat</span>
          </button>

          <button
            type="button"
            className={`nav-pill-btn ${activeTab === "lookup" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("lookup");
              if (window.innerWidth < 1024) onClose();
            }}
          >
            <Compass size={17} className="nav-item-icon" />
            <span className="nav-item-text">Dashboard & Trips</span>
          </button>

          <button
            type="button"
            className={`nav-pill-btn ${activeTab === "saved" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("lookup");
              if (window.innerWidth < 1024) onClose();
            }}
          >
            <Bookmark size={17} className="nav-item-icon" />
            <span className="nav-item-text">Saved Places</span>
          </button>

          <button
            type="button"
            className={`nav-pill-btn ${activeTab === "preferences" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("preferences");
              if (window.innerWidth < 1024) onClose();
            }}
          >
            <Sliders size={17} className="nav-item-icon" />
            <span className="nav-item-text">Preferences</span>
          </button>

          <button
            type="button"
            className={`nav-pill-btn ${activeTab === "notifications" ? "active" : ""}`}
            onClick={() => {
              alert("No critical weather front warnings for your saved locations.");
            }}
          >
            <Bell size={17} className="nav-item-icon" />
            <span className="nav-item-text">Notifications</span>
            <span className="nav-item-badge">Live</span>
          </button>

          {/* Recent Consultation Threads */}
          {chatSessions.length > 0 && (
            <div className="sidebar-recents-group">
              <span className="sidebar-recents-heading">Recent Inquiries</span>
              <div className="sidebar-recents-list">
                {chatSessions.slice(0, 4).map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className="sidebar-recent-item-btn"
                    onClick={() => {
                      if (onSelectSession) onSelectSession(s.id);
                      if (window.innerWidth < 1024) onClose();
                    }}
                    title={s.title}
                  >
                    <MessageSquare size={13} className="recent-msg-icon" />
                    <span className="recent-msg-title">{s.title}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </nav>

        {/* Sidebar Footer with Log Out Action */}
        <div className="sidebar-footer">
          <div className="sidebar-user-preview">
            <div className="user-avatar-dot" />
            <div className="user-text-info">
              <span className="user-display-name">{user?.name || "Guest session"}</span>
              <span className="user-email-sub">{user?.email || "History stays in this browser"}</span>
            </div>
          </div>

          <button
            type="button"
            className="sidebar-logout-btn"
            onClick={onOpenLogin}
            title={user ? "Log out" : "Sign in"}
          >
            <LogOut size={16} className="logout-icon" />
            <span>{user ? "Log Out" : "Sign In"}</span>
          </button>
        </div>
      </aside>
    </>
  );
}
