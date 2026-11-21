import {
  LayoutGrid,
  Plus,
  Sun,
  Moon,
} from "lucide-react";
import AtmosphereSelector from "./AtmosphereSelector";
import ModelSelector from "./ModelSelector";

export default function ChatHeader({
  onNewChat,
  onToggleSidebar,
  theme,
  onToggleTheme,
  atmosphereMode,
  onSelectAtmosphereMode,
  activeScene,
  selectedModel,
  onSelectModel,
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

      {/* Center: Model / Version Selector Pill (Matches Video 1) */}
      <div className="chat-header-center">
        <ModelSelector
          selectedModel={selectedModel}
          onSelectModel={onSelectModel}
        />
      </div>

      <div className="chat-header-actions">
        {/* Ambient Atmosphere Scene Selector */}
        <AtmosphereSelector
          selectedMode={atmosphereMode}
          onSelectMode={onSelectAtmosphereMode}
          activeScene={activeScene}
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

        {/* New Chat Button (Matches Video 1: "+ New Chat") */}
        <button
          type="button"
          className="new-chat-btn"
          onClick={onNewChat}
          title="Start fresh consultation"
        >
          <Plus size={15} />
          <span className="new-chat-label">New Chat</span>
        </button>
      </div>
    </header>
  );
}
