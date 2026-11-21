import { Sparkles, Radio, CloudSun } from "lucide-react";

export default function ThinkingIndicator() {
  return (
    <div className="chat-message-row assistant-row thinking-row">
      <div className="message-avatar assistant-avatar" aria-hidden="true">
        <CloudSun size={18} className="thinking-avatar-icon" />
      </div>

      <div className="message-bubble assistant-bubble thinking-bubble">
        <div className="thinking-layout">
          {/* Animated Meteorological Radar Pulse */}
          <div className="radar-scanner-wrapper">
            <div className="radar-circle-ring ring-1" />
            <div className="radar-circle-ring ring-2" />
            <div className="radar-beacon">
              <Radio size={14} className="radar-beacon-icon" />
            </div>
          </div>

          <div className="thinking-text-block">
            <div className="thinking-headline">
              <span className="thinking-primary-msg">
                Querying Open-Meteo & Auditing Meteorological Claims
              </span>
              <span className="typing-sparkle-dot">
                <Sparkles size={12} />
              </span>
            </div>
            <p className="thinking-subline">
              Evaluating atmospheric trends, humidity indexes, and zero-hallucination evidence proofs...
            </p>
          </div>

          <div className="animated-wave-bars">
            <span className="bar bar-1" />
            <span className="bar bar-2" />
            <span className="bar bar-3" />
            <span className="bar bar-4" />
          </div>
        </div>
      </div>
    </div>
  );
}
