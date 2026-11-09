export default function ChatHeader({ activeTab, setActiveTab, onNewChat }) {
  return (
    <header className="chat-header">
      <div className="chat-header-brand">
        <span className="brand-icon">🌦️</span>
        <div>
          <div className="brand-title-row">
            <h1 className="brand-title">Sky Reader</h1>
            <span className="brand-badge">AI Agent</span>
          </div>
          <p className="brand-subtitle">Agentic Meteorological Intelligence</p>
        </div>
      </div>

      <div className="chat-header-actions">
        <div className="view-mode-tabs">
          <button
            type="button"
            className={`mode-btn ${activeTab === "agent" ? "active" : ""}`}
            onClick={() => setActiveTab("agent")}
            title="Chat with AI Weather Agent"
          >
            💬 Chat
          </button>
          <button
            type="button"
            className={`mode-btn ${activeTab === "lookup" ? "active" : ""}`}
            onClick={() => setActiveTab("lookup")}
            title="Direct City Lookup"
          >
            📍 City Lookup
          </button>
        </div>

        {activeTab === "agent" && (
          <button
            type="button"
            className="new-chat-btn"
            onClick={onNewChat}
            title="Clear conversation and start fresh"
          >
            <span className="btn-icon">✨</span>
            <span>New Chat</span>
          </button>
        )}
      </div>
    </header>
  );
}
