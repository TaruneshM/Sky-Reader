export default function ThinkingIndicator() {
  return (
    <div className="chat-message-row assistant-row thinking-row">
      <div className="message-avatar assistant-avatar" aria-hidden="true">
        🌦️
      </div>

      <div className="message-bubble assistant-bubble thinking-bubble">
        <div className="thinking-content">
          <span className="thinking-label">
            Sky Reader is reasoning and analyzing meteorological data
          </span>
          <div className="typing-dots">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        </div>
      </div>
    </div>
  );
}
