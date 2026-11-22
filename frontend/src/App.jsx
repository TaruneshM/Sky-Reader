import { useState, useRef, useEffect, useCallback, useSyncExternalStore } from "react";
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
import { createAuthSession } from "./utils/authSession";
import { createConversations } from "./utils/conversations";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function App() {
  const [session] = useState(() => createAuthSession({ api: API_BASE_URL }));
  const auth = useSyncExternalStore(session.subscribe, session.getSnapshot, session.getSnapshot);
  useEffect(() => {
    session.validate();
    return session.cancel;
  }, [session]);

  const signedIn = auth.phase === "account" || auth.phase === "guest";
  const workspaceKey = auth.user ? `account:${auth.user.id}` : signedIn ? "guest" : "signin";
  return <SkyReader key={workspaceKey} auth={auth} session={session} signedIn={signedIn} />;
}

async function sendChat(payload, signal) {
  const response = await fetch(`${API_BASE_URL}/api/agent/chat`, {
    method: "POST", signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok || !data) {
    throw new Error(typeof data?.detail === "string" ? data.detail : "Sky Reader could not process this request.");
  }
  return data;
}

function chatObservation(message) {
  if (!message) return null;
  const rain = message.claims?.find((claim) => claim.variable === "precipitation_probability");
  const wind = message.claims?.find((claim) => claim.variable === "wind_speed")?.claimed_value ?? 0;
  const text = message.text.toLowerCase();
  let condition;
  if (/thunder|storm/.test(text)) condition = "thunderstorm";
  else if (/snow|blizzard/.test(text)) condition = "snow";
  else if (/rain|shower/.test(text) || rain?.claimed_value > 40) condition = "rain";
  else if (wind > 20) condition = "wind";
  else if (/sunny|clear/.test(text)) condition = "clear";
  else if (/cloud|overcast/.test(text)) condition = "cloudy";
  return condition ? { condition, wind_speed: wind } : null;
}

function SkyReader({ auth, session, signedIn }) {
  const user = auth.user;
  const [conversations] = useState(() => {
    const controller = createConversations({ send: sendChat });
    controller.setOwner(user?.id, signedIn);
    return controller;
  });
  const { sessions: chatSessions, messages, loading, error } = useSyncExternalStore(
    conversations.subscribe, conversations.getSnapshot, conversations.getSnapshot,
  );
  useEffect(() => conversations.cancel, [conversations]);
  const [activeTab, setActiveTab] = useState("agent"); // "agent" or "lookup"
  const [input, setInput] = useState("");
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
    try { localStorage.setItem("skyreader_theme", theme); } catch { /* Keep the current theme. */ }
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
  function handleSendMessage(customText = input) {
    const query = customText.trim();
    if (!query || conversations.getSnapshot().loading) return;
    setInput("");
    void conversations.send(query);
  }

  function handleNewChat() {
    conversations.newChat();
    setInput("");
    setActiveTab("agent");
  }

  function handleSelectSession(sessionId) {
    conversations.select(sessionId);
    setInput("");
    setActiveTab("agent");
  }

  function handleLogout() {
    conversations.setOwner(null, false);
    void session.logout();
  }

  const observation = activeTab === "agent"
    ? chatObservation(messages.findLast((message) => message.sender === "assistant")) ?? liveObservation
    : liveObservation;

  // Determine active ambient weather scene
  const activeScene =
    atmosphereMode === "auto"
      ? detectWeatherScene({
          weatherCode: observation?.weather_code,
          condition: observation?.condition,
          windSpeed: observation?.wind_speed,
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
      {auth.phase === "checking" ? (
        <div className="floating-app-window-frame" role="status">Checking your session…</div>
      ) : !signedIn ? (
        <LoginPage
          onAuthenticate={session.signIn}
          onContinueAsGuest={session.continueAsGuest}
          onRetrySession={auth.phase === "unavailable" ? session.validate : undefined}
          authError={auth.notice}
          isSubmitting={auth.phase === "submitting"}
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
                  />
                )}
              </main>
            )}

            {/* Content Body: Visual Weather Dashboard Tab */}
            {activeTab === "lookup" && (
              <main className="city-lookup-wrapper">
                <CityLookup
                  onConsultAgent={(prompt) => {
                    setActiveTab("agent");
                    handleSendMessage(prompt);
                  }}
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
                    conversations.clear();
                    setInput("");
                    setLiveObservation(null);
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
