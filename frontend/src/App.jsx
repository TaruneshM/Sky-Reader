import { useState, useRef, useEffect } from "react";
import ChatHeader from "./components/ChatHeader";
import ChatMessage from "./components/ChatMessage";
import ThinkingIndicator from "./components/ThinkingIndicator";
import ChatInput from "./components/ChatInput";
import WelcomeHero from "./components/WelcomeHero";
import CityLookup from "./components/CityLookup";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState("agent"); // "agent" or "lookup"
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of conversation
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const followUpSuggestions = [
    "Should I carry an umbrella?",
    "Is it suitable for travelling?",
    "What are the temperature trends?",
    "What is the best time for outdoor activities?",
  ];

  // Send message to agent with multi-turn conversation history
  async function handleSendMessage(customText) {
    const queryText = (customText !== undefined ? customText : input).trim();
    if (!queryText || loading) return;

    setError("");
    setInput("");

    const timestamp = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    const userMsg = {
      id: `usr_${Date.now()}`,
      sender: "user",
      text: queryText,
      timestamp,
    };

    // Prepare history BEFORE adding the new user message (since backend takes message + previous history)
    const historyPayload = messages.map((m) => ({
      role: m.sender === "user" ? "user" : "assistant",
      content: m.text,
    }));

    // Update UI immediately with user message
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/agent/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: queryText,
          conversation_history: historyPayload,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Sky Reader agent failed to process request.");
      }

      const assistantMsg = {
        id: `asst_${Date.now()}`,
        sender: "assistant",
        text: data.response || "No response received.",
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        toolCalls: data.tool_calls || [],
        iterations: data.iterations || 1,
        claims: data.claims || [],
        validationReport: data.validation_report || null,
        explanation: data.explanation || null,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err.message || "Failed to communicate with Sky Reader backend.");
    } finally {
      setLoading(false);
    }
  }

  // Reset entire conversation state and context
  function handleNewChat() {
    setMessages([]);
    setInput("");
    setError("");
    setLoading(false);
  }

  return (
    <div className="skyreader-chat-app">
      <div className="chat-layout-container">
        {/* Header with Navigation and New Chat */}
        <ChatHeader
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          onNewChat={handleNewChat}
          messageCount={messages.length}
        />

        {/* Tab 1: ChatGPT-style Agentic Chatbot */}
        {activeTab === "agent" && (
          <main className="chat-interface-wrapper">
            <div className="chat-messages-scroll-area">
              {messages.length === 0 ? (
                <WelcomeHero onSelectPrompt={(q) => handleSendMessage(q)} />
              ) : (
                <div className="chat-thread-list">
                  {messages.map((msg) => (
                    <ChatMessage key={msg.id} message={msg} />
                  ))}

                  {loading && <ThinkingIndicator />}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Sticky Bottom Input Bar */}
            <ChatInput
              input={input}
              setInput={setInput}
              onSend={() => handleSendMessage()}
              loading={loading}
              error={error}
              suggestions={messages.length > 0 ? followUpSuggestions : []}
              onSelectSuggestion={(q) => handleSendMessage(q)}
            />
          </main>
        )}

        {/* Tab 2: Preserved Phase 1 City Lookup */}
        {activeTab === "lookup" && (
          <main className="city-lookup-wrapper">
            <CityLookup />
          </main>
        )}
      </div>
    </div>
  );
}
