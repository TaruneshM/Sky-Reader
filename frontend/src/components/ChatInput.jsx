import { useRef, useEffect } from "react";
import { Send, Sparkles, AlertCircle, Loader2 } from "lucide-react";

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

  // Auto-adjust textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        140
      )}px`;
    }
  }, [input]);

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
      {/* Error banner */}
      {error && (
        <div className="chat-error-banner" role="alert">
          <AlertCircle size={16} className="error-icon-svg" />
          <span className="error-text">{error}</span>
        </div>
      )}

      {/* Suggested Follow-ups Bar */}
      {suggestions.length > 0 && (
        <div className="chat-suggestions-bar">
          <span className="suggestions-label">
            <Sparkles size={12} className="suggestions-sparkle" />
            Suggestions:
          </span>
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

      {/* Modern floating input bar */}
      <div className="chat-input-bar">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          rows={1}
          placeholder="Ask anything about the weather (e.g., 'Will it rain in London tomorrow evening?')..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />

        <button
          type="button"
          className="chat-send-btn"
          onClick={() => {
            if (!loading && input.trim()) onSend();
          }}
          disabled={loading || !input.trim()}
          title="Send inquiry (Enter)"
          aria-label="Send message"
        >
          {loading ? (
            <Loader2 size={18} className="spinner-animate" />
          ) : (
            <Send size={18} />
          )}
        </button>
      </div>

      <div className="chat-input-footnote">
        <span>Press <kbd>Enter</kbd> to submit, <kbd>Shift + Enter</kbd> for newline • Powered by Open-Meteo & Groq</span>
      </div>
    </div>
  );
}
