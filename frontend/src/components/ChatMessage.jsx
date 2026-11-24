import { useState } from "react";
import { Copy, Check, Sparkles } from "lucide-react";
import WeatherSnapshot from "./WeatherSnapshot";
import AuditDrawer from "./AuditDrawer";
import RiskCard from "./RiskCard";
import botAvatar from "../assets/avatars/bot-avatar.png";
import botAvatar2x from "../assets/avatars/bot-avatar@2x.png";
import userAvatar from "../assets/avatars/user-avatar.png";
import userAvatar2x from "../assets/avatars/user-avatar@2x.png";

function renderFormattedText(text) {
  if (!text) return null;

  // Split into lines to format basic markdown-style blocks
  const lines = text.split("\n");
  const elements = [];
  let inTable = false;
  let tableRows = [];

  const flushTable = (key) => {
    if (tableRows.length > 0) {
      elements.push(
        <div className="table-responsive-wrapper" key={`table-${key}`}>
          <table className="chat-table">
            <tbody>
              {tableRows.map((row, rIdx) => {
                const cols = row
                  .split("|")
                  .map((c) => c.trim())
                  .filter((c, cIdx, arr) => cIdx > 0 && cIdx < arr.length);

                // Skip separator rows like |---|---|
                if (cols.some((c) => /^[-:]+$/.test(c))) return null;

                const isHeader = rIdx === 0 && !tableRows.some((r, i) => i > 0 && r.includes("---"));
                return (
                  <tr key={rIdx}>
                    {cols.map((col, cIdx) =>
                      isHeader ? (
                        <th key={cIdx}>{formatInlineText(col)}</th>
                      ) : (
                        <td key={cIdx}>{formatInlineText(col)}</td>
                      )
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      );
      tableRows = [];
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Table rows
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      inTable = true;
      tableRows.push(trimmed);
      return;
    } else if (inTable) {
      inTable = false;
      flushTable(idx);
    }

    if (!trimmed) {
      elements.push(<div key={`empty-${idx}`} className="chat-spacer" />);
      return;
    }

    // Markdown Headers ###
    if (trimmed.startsWith("### ")) {
      elements.push(
        <h4 key={`h3-${idx}`} className="chat-heading-3">
          {formatInlineText(trimmed.replace("### ", ""))}
        </h4>
      );
      return;
    }
    if (trimmed.startsWith("## ")) {
      elements.push(
        <h3 key={`h2-${idx}`} className="chat-heading-2">
          {formatInlineText(trimmed.replace("## ", ""))}
        </h3>
      );
      return;
    }
    if (trimmed.startsWith("# ")) {
      elements.push(
        <h2 key={`h1-${idx}`} className="chat-heading-1">
          {formatInlineText(trimmed.replace("# ", ""))}
        </h2>
      );
      return;
    }

    // Bullet points
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      elements.push(
        <div key={`bullet-${idx}`} className="chat-bullet-item">
          <span className="bullet-dot">•</span>
          <span>{formatInlineText(trimmed.substring(2))}</span>
        </div>
      );
      return;
    }

    // Standard paragraph
    elements.push(
      <p key={`p-${idx}`} className="chat-paragraph">
        {formatInlineText(trimmed)}
      </p>
    );
  });

  if (tableRows.length > 0) {
    flushTable("end");
  }

  return elements;
}

function formatInlineText(text) {
  if (!text) return "";
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i} className="inline-code">{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

export default function ChatMessage({ message }) {
  const isUser = message.sender === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!message.text) return;
    navigator.clipboard.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`chat-message-row ${isUser ? "user-row" : "assistant-row"}`}>
      {!isUser && (
        <div className="message-avatar assistant-avatar" aria-hidden="true">
          <img
            src={botAvatar}
            srcSet={`${botAvatar} 1x, ${botAvatar2x} 2x`}
            alt=""
            aria-hidden="true"
            width={40}
            height={40}
            loading="eager"
            draggable={false}
          />
        </div>
      )}

      <div className={`message-bubble ${isUser ? "user-bubble" : "assistant-bubble"}`}>
        <div className="message-header-meta">
          <div className="header-meta-left">
            <span className="sender-name">
              {isUser ? "You" : "Sky Reader Agent"}
            </span>
            {message.iterations > 1 && (
              <span className="iterations-tag" title="Agent reasoning loops executed">
                <Sparkles size={11} className="tag-sparkle" />
                {message.iterations} steps
              </span>
            )}
          </div>

          <div className="header-meta-right">
            <span className="message-time">{message.timestamp}</span>
            {!isUser && (
              <button
                type="button"
                className="message-copy-btn"
                onClick={handleCopy}
                title="Copy response"
                aria-label="Copy response"
              >
                {copied ? <Check size={13} className="text-emerald" /> : <Copy size={13} />}
              </button>
            )}
          </div>
        </div>

        <div className="message-body">
          {renderFormattedText(message.text)}
        </div>

        {/* Embedded Weather Snapshot Cards for assistant */}
        {!isUser && (
          <WeatherSnapshot
            claims={message.claims || []}
            text={message.text || ""}
          />
        )}

        {/* Phase 6 Safety & Weather Risk Assessment Card */}
        {!isUser && message.riskAssessment && (
          <RiskCard riskAssessment={message.riskAssessment} />
        )}

        {/* Audited Evidence Drawer (Phase 4) for assistant */}
        {!isUser && (
          <AuditDrawer
            validationReport={message.validationReport}
            explanation={message.explanation}
            toolCalls={message.toolCalls || []}
          />
        )}
      </div>

      {isUser && (
        <div className="message-avatar user-avatar" aria-hidden="true">
          <img
            src={userAvatar}
            srcSet={`${userAvatar} 1x, ${userAvatar2x} 2x`}
            alt=""
            aria-hidden="true"
            width={40}
            height={40}
            loading="eager"
            draggable={false}
          />
        </div>
      )}
    </div>
  );
}
