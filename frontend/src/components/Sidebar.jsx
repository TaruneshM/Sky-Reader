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
import { NavLink, useMatch } from "react-router-dom";

const navigation = [
  { path: "/chat", label: "Chat", Icon: MessageSquare },
  { path: "/dashboard", label: "Dashboard & Trips", Icon: Compass },
  { path: "/saved", label: "Saved Places", Icon: Bookmark },
  { path: "/preferences", label: "Preferences", Icon: Sliders },
  { path: "/notifications", label: "Notifications", Icon: Bell },
];

export default function Sidebar({
  isOpen,
  onClose,
  onLogout,
  user,
  chatSessions = [],
}) {
  const activeId = useMatch("/chat/:conversationId")?.params.conversationId;
  const recent = chatSessions.slice(0, 10);
  const activeChat = chatSessions.find((thread) => thread.id === activeId);
  if (activeChat && !recent.includes(activeChat)) recent.push(activeChat);

  function closeOnMobile() {
    if (window.innerWidth < 1024) onClose();
  }

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
          {navigation.map(({ path, label, Icon }) => (
            <NavLink key={path} to={path} end className="nav-pill-btn" onClick={closeOnMobile}>
              <Icon size={17} className="nav-item-icon" aria-hidden="true" />
              <span className="nav-item-text">{label}</span>
            </NavLink>
          ))}

          {recent.length > 0 && (
            <div className="sidebar-recents-group">
              <span className="sidebar-recents-heading">Recent Inquiries</span>
              <div className="sidebar-recents-list">
                {recent.map((thread) => (
                  <NavLink
                    key={thread.id}
                    to={`/chat/${encodeURIComponent(thread.id)}`}
                    end
                    className="sidebar-recent-item-btn"
                    onClick={closeOnMobile}
                    title={thread.title}
                  >
                    <MessageSquare size={13} className="recent-msg-icon" aria-hidden="true" />
                    <span className="recent-msg-title">{thread.title}</span>
                  </NavLink>
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
            onClick={onLogout}
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
