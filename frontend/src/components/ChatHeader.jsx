import {
  LayoutGrid,
  Pencil,
  Sun,
  Moon,
} from "lucide-react";
import AtmosphereSelector from "./AtmosphereSelector";

export default function ChatHeader({
  onNewChat,
  onToggleSidebar,
  theme,
  onToggleTheme,
  atmosphereMode,
  onSelectAtmosphereMode,
  chatTitle = "New chat",
}) {
  return (
    <header className="chat-header">
      <div className="chat-header-left">
        {/* Sidebar Toggle Button */}
        <button
          type="button"
          className="header-icon-btn sidebar-trigger-btn"
          onClick={onToggleSidebar}
          title="Toggle Navigation Menu"
          aria-label="Toggle navigation menu"
        >
          <LayoutGrid size={18} />
        </button>
      </div>

      <div className="chat-header-center">
        <span className="chat-header-title" title={chatTitle}>{chatTitle}</span>
      </div>

      <div className="chat-header-actions">
        {/* Ambient Atmosphere Scene Selector */}
        <AtmosphereSelector
          selectedMode={atmosphereMode}
          onSelectMode={onSelectAtmosphereMode}
        />

        {/* Quick Theme Toggle */}
        <button
          type="button"
          className="header-icon-btn theme-quick-btn"
          onClick={onToggleTheme}
          title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
          aria-label="Toggle light or dark theme"
        >
          {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        <button
          type="button"
          className="new-chat-btn"
          onClick={onNewChat}
          title="Start fresh consultation"
          aria-label="New Chat"
        >
          <Pencil size={15} aria-hidden="true" />
          <span className="new-chat-label">New Chat</span>
        </button>
      </div>
    </header>
  );
}
