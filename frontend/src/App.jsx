import { useState } from "react";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const [activeTab, setActiveTab] = useState("agent"); // "agent" or "lookup"

  // AI Agent state
  const [agentQuery, setAgentQuery] = useState("");
  const [agentResponse, setAgentResponse] = useState(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentError, setAgentError] = useState("");

  // Direct Lookup state (Phase 1)
  const [location, setLocation] = useState("");
  const [weather, setWeather] = useState(null);
  const [lookupError, setLookupError] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);

  const suggestedQuestions = [
    "What's the current weather in Dehradun?",
    "Will it rain tomorrow in Dehradun?",
    "What is the weather right now in Paris, and how will it change over the next few hours?",
    "What causes lightning and thunder?",
  ];

  async function handleAskAgent(queryToAsk) {
    const question = (queryToAsk || agentQuery).trim();
    if (!question) {
      setAgentError("Please enter a question.");
      return;
    }

    setAgentLoading(true);
    setAgentError("");
    setAgentResponse(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/agent/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: question }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Agent could not process request.");
      }

      setAgentResponse({
        query: question,
        text: data.response,
        toolCalls: data.tool_calls || [],
        iterations: data.iterations || 1,
      });
    } catch (err) {
      setAgentError(err.message || "Failed to communicate with AI agent.");
    } finally {
      setAgentLoading(false);
    }
  }

  async function searchWeather() {
    if (!location.trim()) {
      setLookupError("Please enter a city name.");
      return;
    }

    setLookupLoading(true);
    setLookupError("");
    setWeather(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/weather?location=${encodeURIComponent(location)}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not fetch weather.");
      }

      setWeather(data);
    } catch (err) {
      setLookupError(err.message);
    } finally {
      setLookupLoading(false);
    }
  }

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <h1>🌦️ Sky Reader</h1>
          <p>Agentic AI Weather Intelligence System</p>
        </header>

        {/* Tab navigation */}
        <div className="mode-tabs">
          <button
            className={`tab-btn ${activeTab === "agent" ? "active" : ""}`}
            onClick={() => setActiveTab("agent")}
          >
            🤖 AI Agent Chat
          </button>
          <button
            className={`tab-btn ${activeTab === "lookup" ? "active" : ""}`}
            onClick={() => setActiveTab("lookup")}
          >
            📍 City Lookup
          </button>
        </div>

        {/* --- TAB 1: AI Agent --- */}
        {activeTab === "agent" && (
          <div>
            <div className="search-box">
              <input
                type="text"
                placeholder="Ask anything, e.g. 'What's the weather in Dehradun right now?'"
                value={agentQuery}
                onChange={(e) => setAgentQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !agentLoading) {
                    handleAskAgent();
                  }
                }}
              />
              <button
                onClick={() => handleAskAgent()}
                disabled={agentLoading}
              >
                {agentLoading ? "Thinking..." : "Ask Agent"}
              </button>
            </div>

            {/* Quick suggested chips */}
            <div className="suggested-chips">
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  className="chip-btn"
                  onClick={() => {
                    setAgentQuery(q);
                    handleAskAgent(q);
                  }}
                  disabled={agentLoading}
                >
                  {q}
                </button>
              ))}
            </div>

            {agentError && <div className="error">⚠️ {agentError}</div>}

            {agentLoading && (
              <div className="agent-response-card" style={{ textAlign: "center", color: "#6b7280" }}>
                <p>⏳ Sky Reader is reasoning and calling weather tools...</p>
              </div>
            )}

            {agentResponse && !agentLoading && (
              <div className="agent-response-card">
                <div className="agent-query-header">
                  <h3>💬 {agentResponse.query}</h3>
                  <span className="agent-iterations-badge">
                    {agentResponse.iterations} iteration{agentResponse.iterations > 1 ? "s" : ""}
                  </span>
                </div>

                <div className="agent-text">{agentResponse.text}</div>

                {agentResponse.toolCalls && agentResponse.toolCalls.length > 0 && (
                  <div className="agent-tools-used">
                    <span className="agent-tools-label">Tools Executed:</span>
                    <div className="tool-tags-list">
                      {agentResponse.toolCalls.map((tc, index) => (
                        <span key={index} className="tool-tag">
                          🔧 {tc.tool}
                          {tc.arguments?.location
                            ? ` (${tc.arguments.location})`
                            : tc.arguments?.latitude
                            ? ` (${tc.arguments.latitude.toFixed(2)}, ${tc.arguments.longitude.toFixed(2)})`
                            : ""}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* --- TAB 2: Direct City Lookup (Phase 1 preserved) --- */}
        {activeTab === "lookup" && (
          <div>
            <div className="search-box">
              <input
                type="text"
                placeholder="Enter a city name..."
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !lookupLoading) {
                    searchWeather();
                  }
                }}
              />
              <button onClick={searchWeather} disabled={lookupLoading}>
                {lookupLoading ? "Searching..." : "Search"}
              </button>
            </div>

            {lookupError && <div className="error">⚠️ {lookupError}</div>}

            {weather && (
              <div className="weather-card">
                <div className="location">
                  <h2>{weather.location.name}</h2>
                  <p>
                    {weather.location.region}, {weather.location.country}
                  </p>
                </div>

                <div className="temperature">{weather.current.temperature}°C</div>
                <div className="condition">
                  <span className="condition-icon">{weather.current.icon}</span>
                  <span>{weather.current.condition}</span>
                </div>

                <div className="weather-details">
                  <div className="detail">
                    <span>🌡️</span>
                    <p>Feels like</p>
                    <strong>{weather.current.feels_like}°C</strong>
                  </div>

                  <div className="detail">
                    <span>💧</span>
                    <p>Humidity</p>
                    <strong>{weather.current.humidity}%</strong>
                  </div>

                  <div className="detail">
                    <span>💨</span>
                    <p>Wind</p>
                    <strong>{weather.current.wind_speed} km/h</strong>
                  </div>
                </div>

                <div className="forecast-section">
                  <h3>Next 24 Hours</h3>
                  <div className="forecast-list">
                    {weather.forecast.map((hour) => (
                      <div className="forecast-item" key={hour.time}>
                        <span className="forecast-time">
                          {new Date(hour.time).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                        <span className="forecast-icon">{hour.icon}</span>
                        <span className="forecast-temperature">
                          {hour.temperature}°C
                        </span>
                        <span className="forecast-condition">
                          {hour.condition}
                        </span>
                        <span className="forecast-rain">
                          🌧️ {hour.precipitation_probability}%
                        </span>
                        <span className="forecast-wind">
                          💨 {hour.wind_speed} km/h
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="updated">Updated: {weather.current.time}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
