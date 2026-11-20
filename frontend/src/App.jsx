import { useState, useRef, useEffect, useCallback } from "react";
import ChatHeader from "./components/ChatHeader";
import ChatMessage from "./components/ChatMessage";
import ThinkingIndicator from "./components/ThinkingIndicator";
import ChatInput from "./components/ChatInput";
import WelcomeHero from "./components/WelcomeHero";
import CityLookup from "./components/CityLookup";
import Sidebar from "./components/Sidebar";
import WeatherAtmosphere from "./components/WeatherAtmosphere";
import LoginPage from "./components/LoginPage";
import PreferencesView from "./components/PreferencesView";
import { detectWeatherScene } from "./utils/weatherAtmosphere";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function App() {
  // View mode: 'app' (Main Dashboard) or 'login' (Login Page from Video 2)
  // New users (no stored token) start on login page
  const [viewMode, setViewMode] = useState(() => {
    try {
      const hasToken = !!localStorage.getItem("skyreader_token");
      const hasUser = !!localStorage.getItem("skyreader_user");
      return hasToken && hasUser ? "app" : "login";
    } catch {
      return "login";
    }
  });
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem("skyreader_user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [activeTab, setActiveTab] = useState("agent"); // "agent" or "lookup"
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Atmospheric simulation scene mode: 'auto' | 'sun' | 'rain' | 'stars' | 'wind' | 'snow' | 'thunder' | 'clouds'
  const [atmosphereMode, setAtmosphereMode] = useState(() => {
    try {
      return localStorage.getItem("skyreader_atmosphere_mode") || "auto";
    } catch {
      return "auto";
    }
  });

  // Track latest meteorological observations (from lookup or chat)
  const [liveObservation, setLiveObservation] = useState(null);

  useEffect(() => {
    try {
      localStorage.setItem("skyreader_atmosphere_mode", atmosphereMode);
    } catch (e) {
      console.warn("Could not save atmosphere mode:", e);
    }
  }, [atmosphereMode]);

  // Chat sessions state (stored in localStorage)
  const [chatSessions, setChatSessions] = useState(() => {
    try {
      const saved = localStorage.getItem("skyreader_sessions");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [currentSessionId, setCurrentSessionId] = useState(() => `sess_${Date.now()}`);

  // Theme state: dark (default, calming) or light
  const [theme, setTheme] = useState(() => {
    try {
      const savedTheme = localStorage.getItem("skyreader_theme");
      if (savedTheme) return savedTheme;
      return "dark";
    } catch {
      return "dark";
    }
  });

  // Apply theme to root document element
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("skyreader_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Save current thread into sessions
  const syncSessionHistory = (newMessages) => {
    if (newMessages.length === 0) return;

    setChatSessions((prev) => {
      const firstUserMsg = newMessages.find((m) => m.sender === "user");
      const title = firstUserMsg
        ? firstUserMsg.text.length > 36
          ? `${firstUserMsg.text.slice(0, 36)}...`
          : firstUserMsg.text
        : "Weather Consultation";

      const existingIndex = prev.findIndex((s) => s.id === currentSessionId);
      let updated;
      if (existingIndex >= 0) {
        updated = [...prev];
        updated[existingIndex] = {
          ...updated[existingIndex],
          messages: newMessages,
          updatedAt: Date.now(),
        };
      } else {
        const newSession = {
          id: currentSessionId,
          title,
          messages: newMessages,
          updatedAt: Date.now(),
        };
        updated = [newSession, ...prev];
      }

      try {
        localStorage.setItem("skyreader_sessions", JSON.stringify(updated));
      } catch (e) {
        console.warn("Could not save sessions:", e);
      }
      return updated;
    });
  };

  const followUpSuggestions = [
    "Should I carry an umbrella tomorrow?",
    "What are the diurnal temperature trends?",
    "Is it suitable for travelling this weekend?",
    "What is the optimal 6-hour outdoor window?",
  ];

  // Callback when CityLookup loads weather
  const handleWeatherLoaded = useCallback((weatherData) => {
    if (weatherData && weatherData.current) {
      setLiveObservation({
        weather_code: weatherData.current.weather_code,
        condition: weatherData.current.condition,
        wind_speed: weatherData.current.wind_speed,
      });
    }
  }, []);

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

    const historyPayload = messages.map((m) => ({
      role: m.sender === "user" ? "user" : "assistant",
      content: m.text,
    }));

    const updatedMessagesWithUser = [...messages, userMsg];
    setMessages(updatedMessagesWithUser);
    syncSessionHistory(updatedMessagesWithUser);
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

      // Check if claims or text indicate weather for ambient scene detection
      const claims = data.claims || [];
      const rainClaim = claims.find((c) => c.variable === "precipitation_probability");
      const windClaim = claims.find((c) => c.variable === "wind_speed");
      if (rainClaim || windClaim || data.response) {
        const textLower = (data.response || "").toLowerCase();
        let detectedCond = "";
        if (textLower.includes("thunder") || textLower.includes("storm")) detectedCond = "thunderstorm";
        else if (textLower.includes("snow") || textLower.includes("blizzard")) detectedCond = "snow";
        else if (textLower.includes("rain") || textLower.includes("shower") || (rainClaim && rainClaim.claimed_value > 40)) detectedCond = "rain";
        else if (windClaim && windClaim.claimed_value > 20) detectedCond = "wind";
        else if (textLower.includes("sunny") || textLower.includes("clear")) detectedCond = "clear";
        else if (textLower.includes("cloud") || textLower.includes("overcast")) detectedCond = "cloudy";

        if (detectedCond) {
          setLiveObservation({
            condition: detectedCond,
            wind_speed: windClaim ? windClaim.claimed_value : 0,
          });
        }
      }

      const assistantMsg = {
        id: `asst_${Date.now()}`,
        sender: "assistant",
        text: data.response || "No meteorological response received.",
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

      const finalMessages = [...updatedMessagesWithUser, assistantMsg];
      setMessages(finalMessages);
      syncSessionHistory(finalMessages);
    } catch (err) {
      setError(err.message || "Failed to communicate with Sky Reader backend.");
    } finally {
      setLoading(false);
    }
  }

  // Reset entire conversation state and context for fresh chat
  function handleNewChat() {
    setMessages([]);
    setInput("");
    setError("");
    setLoading(false);
    setCurrentSessionId(`sess_${Date.now()}`);
  }

  // Select a past session
  const handleSelectSession = (sessionId) => {
    const session = chatSessions.find((s) => s.id === sessionId);
    if (session) {
      setCurrentSessionId(session.id);
      setMessages(session.messages || []);
      setInput("");
      setError("");
      setActiveTab("agent");
    }
  };

  // Action from dashboard or sidebar to consult agent
  const handleConsultAgentFromOther = (promptText) => {
    setActiveTab("agent");
    handleSendMessage(promptText);
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    localStorage.setItem("skyreader_user", JSON.stringify(userData));
    setViewMode("app");
  };

  const handleLogout = () => {
    localStorage.removeItem("skyreader_token");
    localStorage.removeItem("skyreader_user");
    setUser(null);
    setViewMode("login");
  };

  // Determine active ambient weather scene
  const activeScene =
    atmosphereMode === "auto"
      ? detectWeatherScene({
          weatherCode: liveObservation?.weather_code,
          condition: liveObservation?.condition,
          windSpeed: liveObservation?.wind_speed,
          isNight: theme === "dark",
        })
      : atmosphereMode;

  return (
    <div className={`skyreader-root-environment atmosphere-active-${activeScene}`}>
      {/* Dynamic atmospheric particle simulation canvas (Rain, Sun, Stars, Wind Leaves, Snow...) */}
      <WeatherAtmosphere scene={activeScene} isNight={theme === "dark"} />

      {/* Realistic Moving Sky Clouds Layer (Matches Video 1) */}
      <div className="video1-sky-cloud-layer" aria-hidden="true">
        <div className="sky-cloud-puff puff-1" />
        <div className="sky-cloud-puff puff-2" />
        <div className="sky-cloud-puff puff-3" />
        <div className="sky-cloud-puff puff-4" />
      </div>

      {/* Conditionally Render: Login Page (Video 2) or Floating App Canvas (Video 1) */}
      {viewMode === "login" ? (
        <LoginPage
          onLoginSuccess={handleLoginSuccess}
          onBackToApp={() => setViewMode("app")}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
      ) : (
        /* Floating Glass Application Window (Matches Video 1) */
        <div className="floating-app-window-frame">
          {/* Left Sidebar inside Floating Window */}
          <Sidebar
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            onOpenLogin={handleLogout}
            user={user}
            chatSessions={chatSessions}
            onSelectSession={handleSelectSession}
          />

          {/* Right Main Content Area inside Floating Window */}
          <div className="floating-main-canvas">
            {/* Top Navigation Bar with Model Selector and New Chat button */}
            <ChatHeader
              onNewChat={handleNewChat}
              onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
              theme={theme}
              onToggleTheme={toggleTheme}
              atmosphereMode={atmosphereMode}
              onSelectAtmosphereMode={setAtmosphereMode}
              activeScene={activeScene}
            />

            {/* Content Body: Chat Agent Tab */}
            {activeTab === "agent" && (
              <main className="chat-interface-wrapper">
                <div className="chat-messages-scroll-area">
                  {messages.length === 0 ? (
                    <WelcomeHero
                      onSelectPrompt={(q) => handleSendMessage(q)}
                      onSendQuery={(q) => handleSendMessage(q)}
                    />
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

                {/* Sticky Bottom Input Bar (shown when thread is active) */}
                {messages.length > 0 && (
                  <ChatInput
                    input={input}
                    setInput={setInput}
                    onSend={() => handleSendMessage()}
                    loading={loading}
                    error={error}
                    suggestions={followUpSuggestions}
                    onSelectSuggestion={(q) => handleSendMessage(q)}
                  />
                )}
              </main>
            )}

            {/* Content Body: Visual Weather Dashboard Tab */}
            {activeTab === "lookup" && (
              <main className="city-lookup-wrapper">
                <CityLookup
                  onConsultAgent={handleConsultAgentFromOther}
                  onWeatherLoaded={handleWeatherLoaded}
                />
              </main>
            )}

            {/* Content Body: Preferences & Settings Tab */}
            {activeTab === "preferences" && (
              <main className="preferences-tab-wrapper">
                <PreferencesView
                  theme={theme}
                  onToggleTheme={toggleTheme}
                  atmosphereMode={atmosphereMode}
                  onSelectAtmosphereMode={setAtmosphereMode}
                  user={user}
                  onClearHistory={() => {
                    setChatSessions([]);
                    localStorage.removeItem("skyreader_sessions");
                    handleNewChat();
                  }}
                />
              </main>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
