import { useRef, useEffect } from "react";

export default function ChatInput({
  input,
  setInput,
  onSend,
  loading,
  error,
  suggestions = [],
  onSelectSuggestion,
}) {
  const textareaRef = useRef(null);

  // Auto-focus input on mount
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!loading && input.trim()) {
        onSend();
      }
    }
  };

  return (
    <div className="chat-input-wrapper">
      {error && (
        <div className="chat-error-banner" role="alert">
          <span className="error-icon">⚠️</span>
          <span className="error-text">{error}</span>
        </div>
      )}

      {/* Suggested Prompts Bar */}
      {suggestions.length > 0 && (
        <div className="chat-suggestions-bar">
          <span className="suggestions-label">Suggestions:</span>
          <div className="suggestions-scroll">
            {suggestions.map((q, idx) => (
              <button
                key={idx}
                type="button"
                className="suggestion-chip"
                onClick={() => onSelectSuggestion(q)}
                disabled={loading}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Form Bar */}
      <div className="chat-input-bar">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder="Ask a weather question (e.g., 'Will it rain tomorrow in Paris?')..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          rows={1}
        />
        <button
          type="button"
          className="chat-send-btn"
          onClick={onSend}
          disabled={loading || !input.trim()}
          title="Send message (Enter)"
        >
          {loading ? (
            <span className="spinner-icon">⏳</span>
          ) : (
            <span className="send-icon">➤</span>
          )}
        </button>
      </div>
      <div className="chat-input-hint">
        Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for a new line. Context is preserved for follow-up questions.
      </div>
    </div>
  );
}
