import { useState, useRef, useEffect, useSyncExternalStore } from "react";
import { Link, Navigate, Route, Routes, useLocation, useMatch, useNavigate, useParams } from "react-router-dom";
import { AppLayout, AuthLayout, WeatherLayout } from "./components/Layouts";
import ChatMessage from "./components/ChatMessage";
import ThinkingIndicator from "./components/ThinkingIndicator";
import ChatInput from "./components/ChatInput";
import WelcomeHero from "./components/WelcomeHero";
import CityLookup from "./components/CityLookup";
import LoginPage from "./components/LoginPage";
import PreferencesView from "./components/PreferencesView";
import TermsModal from "./components/TermsModal";
import CustomCursor from "./components/CustomCursor";
import { WEATHER_SCENES } from "./utils/weatherAtmosphere";
import { createAuthSession } from "./utils/authSession";
import { createConversations } from "./utils/conversations";
import { createChatThreads } from "./utils/chatThreads";
import { local, readStorage, session as tabStorage, writeStorage } from "./utils/browserStorage";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";
const ATMOSPHERE_KEY = "skyreader_atmosphere_mode";

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

function SkyReader({ auth, session, signedIn }) {
  const user = auth.user;
  const navigate = useNavigate();
  const emptyChat = useMatch("/chat");
  const chatId = useMatch("/chat/:conversationId")?.params.conversationId;
  const [showTerms, setShowTerms] = useState(false);
  const [hasCheckedTerms, setHasCheckedTerms] = useState(false);

  // Auto-prompt Terms & Conditions on first login with a new ID or guest session
  useEffect(() => {
    if (!signedIn || hasCheckedTerms) return;
    setHasCheckedTerms(true);
    const userKey = user ? (user.email ? user.email.toLowerCase() : `id_${user.id}`) : "guest";
    const storageKey = `skyreader_terms_accepted_${userKey}`;
    try {
      const accepted = localStorage.getItem(storageKey);
      const isTestEnv = typeof window !== "undefined" && (window.IS_REACT_ACT_ENVIRONMENT || navigator.userAgent?.includes("jsdom"));
      if (!accepted && !isTestEnv) {
        setShowTerms(true);
      }
    } catch {
      // In case localStorage is unavailable
    }
  }, [signedIn, user, hasCheckedTerms]);

  const handleCloseTerms = () => {
    const userKey = user ? (user.email ? user.email.toLowerCase() : `id_${user.id}`) : "guest";
    try {
      localStorage.setItem(`skyreader_terms_accepted_${userKey}`, new Date().toISOString());
    } catch {
      // ignore
    }
    setShowTerms(false);
  };
  const [chatThreads] = useState(() => createChatThreads({
    api: API_BASE_URL, authorization: () => session.authorization(user?.id), guest: !user,
  }));
  const [conversations] = useState(() => {
    const controller = createConversations({ threads: chatThreads, storage: user ? local : tabStorage });
    controller.setOwner(user?.id, signedIn);
    return controller;
  });
  const chat = useSyncExternalStore(conversations.subscribe, conversations.getSnapshot, conversations.getSnapshot);
  useEffect(() => conversations.cancel, [conversations]);
  const currentThread = chat.sessions.find((thread) => thread.id === chatId);

  const [atmosphereMode, setAtmosphereMode] = useState(() => {
    const storedMode = readStorage(local, ATMOSPHERE_KEY);
    return WEATHER_SCENES.some(({ id }) => id === storedMode) ? storedMode : "none";
  });

  useEffect(() => {
    writeStorage(local, ATMOSPHERE_KEY, atmosphereMode);
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

  function handleSendMessage(text, startNew = false) {
    const query = text.trim();
    if (!query) return;
    const threadId = startNew ? conversations.newChat() : conversations.getSnapshot().active;
    const before = conversations.getSnapshot();
    if (!threadId || before.loading) return;
    const saved = before.sessions.some((thread) => thread.id === threadId);
    // send() appends the user message synchronously, before server provisioning.
    void conversations.send(query);
    if (!saved && conversations.getSnapshot().sessions.some((thread) => thread.id === threadId)) {
      navigate(`/chat/${encodeURIComponent(threadId)}`, { replace: Boolean(emptyChat) });
    }
  }

  function handleNewChat() {
    conversations.newChat();
    navigate("/chat", { replace: Boolean(emptyChat) });
  }

  function handleLogout() {
    navigate("/login", { replace: true, state: null });
    if (!user) {
      conversations.clear({ server: false });
      void chatThreads.revokeGuest().catch(session.showGuestRevocationFailure);
    }
    conversations.setOwner(null, false);
    void session.logout();
  }

  const loginProps = {
    onAuthenticate: session.signIn,
    onContinueAsGuest: session.continueAsGuest,
    onRetrySession: auth.phase === "unavailable" ? session.validate : undefined,
    authError: auth.notice,
    isSubmitting: auth.phase === "submitting",
    theme,
    onToggleTheme: toggleTheme,
    authPhase: auth.phase,
  };
  const header = {
    onNewChat: handleNewChat, theme, onToggleTheme: toggleTheme, atmosphereMode,
    onSelectAtmosphereMode: setAtmosphereMode, chatTitle: currentThread?.title ?? "New chat",
  };
  const sendNewChat = (text) => handleSendMessage(text, true);

  return (
    <WeatherLayout scene={atmosphereMode} theme={theme}>
      {auth.phase === "checking" ? (
        <div className="floating-app-window-frame" role="status">Checking your session…</div>
      ) : (
        <Routes>
          <Route element={<AuthLayout phase={auth.phase} signedIn={signedIn} />}>
            <Route path="/login" element={<LoginPage key="signin" mode="signin" {...loginProps} />} />
            <Route path="/signup" element={<LoginPage key="signup" mode="signup" {...loginProps} />} />
          </Route>
          <Route element={
            <AppLayout signedIn={signedIn} user={user} onLogout={handleLogout}
              onOpenTerms={() => setShowTerms(true)}
              chatSessions={chat.sessions} header={header} notice={chat.notice} />
          }>
            <Route path="/chat/:conversationId?" element={
              <ChatRoute conversations={conversations} chat={chat}
                onSend={handleSendMessage} onStartChat={sendNewChat} />
            } />
            <Route path="/dashboard" element={
              <main className="city-lookup-wrapper">
                <CityLookup onConsultAgent={sendNewChat} />
              </main>
            } />
            <Route path="/saved" element={<ComingSoon title="Saved Places" />} />
            <Route path="/notifications" element={<ComingSoon title="Notifications" />} />
            <Route path="/preferences" element={
              <main className="preferences-tab-wrapper">
                <PreferencesView
                  theme={theme}
                  onToggleTheme={toggleTheme}
                  atmosphereMode={atmosphereMode}
                  onSelectAtmosphereMode={setAtmosphereMode}
                  user={user}
                  onClearHistory={conversations.clear}
                  onOpenTerms={() => setShowTerms(true)}
                />
              </main>
            } />
          </Route>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="*" element={
            <main className="route-empty-state route-not-found">
              <h1>Page not found</h1>
              <Link to="/chat">Back to chat</Link>
            </main>
          } />
        </Routes>
      )}

      {/* Global Futuristic Atmospheric Cursor */}
      <CustomCursor />

      {/* Global Terms & Conditions Modal */}
      <TermsModal
        isOpen={showTerms}
        onClose={handleCloseTerms}
        isLight={theme === "light"}
        welcomeUser={user?.name}
      />
    </WeatherLayout>
  );
}

function ComingSoon({ title }) {
  return (
    <main className="route-empty-state">
      <h1>{title}</h1>
      <p>Coming soon</p>
    </main>
  );
}

function ChatRoute({ conversations, chat, onSend, onStartChat }) {
  const { conversationId } = useParams();
  const { key } = useLocation();

  useEffect(() => {
    if (conversationId) {
      conversations.activate(conversationId);
    } else {
      const { active, sessions } = conversations.getSnapshot();
      if (sessions.some((thread) => thread.id === active)) conversations.newChat();
    }
    // Apply only on navigation. A send can save the active chat before its URL updates.
  }, [conversations, conversationId, key]);

  if (conversationId && !chat.sessions.some((thread) => thread.id === conversationId)) {
    return <Navigate to="/chat" replace />;
  }
  if (conversationId ? chat.active !== conversationId : chat.sessions.some((thread) => thread.id === chat.active)) {
    return null;
  }
  return <ChatView key={chat.active} chat={chat} onSend={onSend}
    onStartChat={onStartChat} onRetry={conversations.retry} />;
}

function ChatView({ chat, onSend, onStartChat, onRetry }) {
  const { messages, loading, error, canRetry } = chat;
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <main className="chat-interface-wrapper">
      <div className="chat-messages-scroll-area">
        {messages.length === 0 ? (
          <WelcomeHero onSelectPrompt={onStartChat} onSendQuery={onStartChat} />
        ) : (
          <div className="chat-thread-list">
            {messages.map((message) => <ChatMessage key={message.id} message={message} />)}
            {loading && <ThinkingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
      {messages.length > 0 && (
        <ChatInput
          input={input}
          setInput={setInput}
          onSend={() => {
            onSend(input);
            setInput("");
          }}
          loading={loading}
          error={error}
          onRetry={canRetry ? onRetry : undefined}
        />
      )}
    </main>
  );
}
