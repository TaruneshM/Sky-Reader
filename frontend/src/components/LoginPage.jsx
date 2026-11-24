import { useState, useEffect, useRef, lazy, Suspense, useCallback } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Eye, EyeOff, Sparkles, AlertCircle,
  Sun, Moon, ArrowRight, User, Mail, Lock,
} from "lucide-react";
import { hasIntroPlayed, markIntroPlayed } from "../utils/introState.js";

// Lazy-load SkyReaderIntro so it is not in bundle path for signed-in users
const SkyReaderIntro = lazy(() => import("./SkyReaderIntro.jsx"));

/* ─────────────────────────────────────────────────────────────────
   Main Login Page
   ───────────────────────────────────────────────────────────────── */
export default function LoginPage({
  onAuthenticate, onContinueAsGuest, onRetrySession, authError = "",
  mode, isSubmitting = false, theme = "dark", onToggleTheme,
  authPhase = "signin",
}) {
  const [email,        setEmail]        = useState("");
  const [password,     setPassword]     = useState("");
  const [name,         setName]         = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [staySignedIn, setStaySignedIn] = useState(true);
  const [introActive,  setIntroActive]  = useState(false);
  const brandRef = useRef(null);
  const { state } = useLocation();

  const isLight = theme === "light";

  // Check intro eligibility
  useEffect(() => {
    // 1. Play once per page load (in-memory flag)
    if (hasIntroPlayed()) return;
    // 2. Never while auth.phase is checking
    if (authPhase === "checking") return;
    // 3. Skip if auth.phase is unavailable or an error notice is already showing
    if (authPhase === "unavailable" || Boolean(authError)) {
      markIntroPlayed();
      return;
    }
    // 4. prefers-reduced-motion: skip intro entirely
    const prefersReducedMotion = typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    if (prefersReducedMotion) {
      markIntroPlayed();
      return;
    }

    // Start intro on next frame to avoid synchronous setState inside effect
    const frame = requestAnimationFrame(() => {
      setIntroActive(true);
    });
    return () => cancelAnimationFrame(frame);
  }, [authPhase, authError]);

  const handleIntroComplete = useCallback(() => {
    markIntroPlayed();
    setIntroActive(false);
    requestAnimationFrame(() => {
      document.getElementById("login-email")?.focus();
    });
  }, []);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (isSubmitting) return;
    const credentials = mode === "signin" ? { email, password } : { email, password, name: name.trim() };
    void onAuthenticate(mode, credentials, staySignedIn);
  };

  /* ── Inline styles so the login page works independently of App.css theming ── */
  const styles = {
    wrapper: {
      position:       "relative",
      width:          "100vw",
      height:         "100vh",
      display:        "flex",
      alignItems:     "center",
      justifyContent: "center",
      overflow:       "hidden",
      fontFamily:     "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif",
    },
    topBar: {
      position:       "absolute",
      top:            20,
      left:           20,
      right:          20,
      display:        "flex",
      alignItems:     "center",
      justifyContent: "space-between",
      zIndex:         40,
    },
    backBtn: {
      display:        "inline-flex",
      alignItems:     "center",
      gap:            8,
      padding:        "8px 18px",
      borderRadius:   999,
      border:         isLight
        ? "1px solid rgba(160,140,110,0.4)"
        : "1px solid rgba(255,255,255,0.18)",
      background:     isLight
        ? "rgba(255,250,242,0.55)"
        : "rgba(255,255,255,0.08)",
      backdropFilter: "blur(12px)",
      WebkitBackdropFilter: "blur(12px)",
      color:          isLight ? "#3a3028" : "#ffffff",
      fontSize:       12.5,
      fontWeight:     600,
      cursor:         "pointer",
      transition:     "all 0.18s ease",
    },
    themeBtn: {
      width:          40,
      height:         40,
      borderRadius:   "50%",
      border:         isLight
        ? "1px solid rgba(160,140,110,0.4)"
        : "1px solid rgba(255,255,255,0.18)",
      background:     isLight
        ? "rgba(255,250,242,0.55)"
        : "rgba(255,255,255,0.08)",
      backdropFilter: "blur(12px)",
      WebkitBackdropFilter: "blur(12px)",
      color:          isLight ? "#c17a2a" : "#f8d77a",
      display:        "flex",
      alignItems:     "center",
      justifyContent: "center",
      cursor:         "pointer",
      transition:     "all 0.18s ease",
      flexShrink:     0,
    },
    card: {
      position:       "relative",
      zIndex:         20,
      width:          "100%",
      maxWidth:       420,
      margin:         "0 16px",
      padding:        "36px 32px 28px",
      borderRadius:   28,
      border:         isLight
        ? "1px solid rgba(200,180,150,0.45)"
        : "1px solid rgba(255,255,255,0.18)",
      background:     isLight
        ? "rgba(255,252,246,0.60)"
        : "rgba(10,6,30,0.42)",
      backdropFilter: "blur(32px)",
      WebkitBackdropFilter: "blur(32px)",
      boxShadow:      isLight
        ? "0 24px 60px -10px rgba(100,70,30,0.22), inset 0 1px 1px rgba(255,250,235,0.6)"
        : "0 24px 60px -10px rgba(0,0,0,0.65), inset 0 1px 0 rgba(255,255,255,0.1)",
      animation:      "loginFadeUp 0.4s cubic-bezier(0.16,1,0.3,1)",
    },

    // Brand
    brandRow: {
      display:        "flex",
      alignItems:     "center",
      justifyContent: "center",
      gap:            10,
      marginBottom:   6,
    },
    brandBadge: {
      width:          42,
      height:         42,
      borderRadius:   14,
      background:     "linear-gradient(135deg,#f59e0b 0%,#ea580c 100%)",
      boxShadow:      "0 6px 20px rgba(234,88,12,0.4)",
      display:        "flex",
      alignItems:     "center",
      justifyContent: "center",
      flexShrink:     0,
    },
    brandName: {
      fontSize:   22,
      fontWeight: 800,
      letterSpacing: "-0.3px",
      color:      isLight ? "#2c2520" : "#ffffff",
    },
    headline: {
      fontSize:      26,
      fontWeight:    700,
      letterSpacing: "-0.5px",
      color:         isLight ? "#2c2520" : "#ffffff",
      textAlign:     "center",
      margin:        "14px 0 6px",
    },
    subline: {
      fontSize:   13,
      color:      isLight ? "#7a6e62" : "rgba(220,210,255,0.75)",
      textAlign:  "center",
      lineHeight: 1.55,
      marginBottom: 22,
    },

    // Error
    errorBanner: {
      display:      "flex",
      alignItems:   "center",
      gap:          8,
      padding:      "9px 13px",
      borderRadius: 12,
      background:   "rgba(220,50,50,0.12)",
      border:       "1px solid rgba(220,50,50,0.3)",
      color:        "#fca5a5",
      fontSize:     12.5,
      marginBottom: 14,
    },

    // Form
    form:        { display: "flex", flexDirection: "column", gap: 14 },
    fieldGroup:  { display: "flex", flexDirection: "column", gap: 5 },
    label: {
      fontSize:   11.5,
      fontWeight: 600,
      color:      isLight ? "#7a6e62" : "rgba(210,195,255,0.85)",
      display:    "flex",
      alignItems: "center",
      gap:        5,
    },
    inputWrap:   { position: "relative", display: "flex", alignItems: "center" },
    input: {
      width:        "100%",
      padding:      "11px 14px 11px 38px",
      borderRadius: 12,
      border:       isLight
        ? "1px solid rgba(175,155,120,0.4)"
        : "1px solid rgba(255,255,255,0.14)",
      background:   isLight
        ? "rgba(250,245,235,0.70)"
        : "rgba(255,255,255,0.07)",
      color:        isLight ? "#2c2520" : "#ffffff",
      fontSize:     13.5,
      outline:      "none",
      boxSizing:    "border-box",
      fontFamily:   "inherit",
      transition:   "border-color 0.18s, box-shadow 0.18s",
    },
    inputIcon: {
      position: "absolute",
      left:     12,
      color:    isLight ? "#a09488" : "rgba(200,180,255,0.5)",
      pointerEvents: "none",
    },
    eyeBtn: {
      position:   "absolute",
      right:      11,
      background: "none",
      border:     "none",
      cursor:     "pointer",
      color:      isLight ? "#a09488" : "rgba(200,180,255,0.6)",
      display:    "flex",
      alignItems: "center",
      padding:    4,
    },

    // Options row
    optionsRow: {
      display:        "flex",
      alignItems:     "center",
      justifyContent: "space-between",
      fontSize:       12,
      marginTop:      -4,
    },
    stayLabel: {
      display:    "flex",
      alignItems: "center",
      gap:        6,
      cursor:     "pointer",
      color:      isLight ? "#7a6e62" : "rgba(210,195,255,0.8)",
    },
    forgotBtn: {
      background:     "none",
      border:         "none",
      cursor:         "pointer",
      color:          isLight ? "#c17a2a" : "#c084fc",
      fontSize:       12,
      textDecoration: "underline",
      fontFamily:     "inherit",
    },

    // Primary submit
    submitBtn: {
      width:          "100%",
      padding:        "13px 20px",
      borderRadius:   999,
      border:         "none",
      cursor:         isSubmitting ? "not-allowed" : "pointer",
      background:     "linear-gradient(135deg,#f59e0b 0%,#ea580c 100%)",
      color:          "#ffffff",
      fontSize:       14,
      fontWeight:     700,
      boxShadow:      "0 6px 20px rgba(234,88,12,0.35)",
      display:        "flex",
      alignItems:     "center",
      justifyContent: "center",
      gap:            8,
      transition:     "all 0.18s ease",
      fontFamily:     "inherit",
      opacity:        isSubmitting ? 0.7 : 1,
    },

    // Google btn
    googleBtn: {
      width:          "100%",
      padding:        "11px 20px",
      borderRadius:   999,
      border:         isLight
        ? "1px solid rgba(175,155,120,0.4)"
        : "1px solid rgba(255,255,255,0.15)",
      background:     isLight
        ? "rgba(250,245,235,0.55)"
        : "rgba(255,255,255,0.06)",
      color:          isLight ? "#2c2520" : "#ffffff",
      fontSize:       13,
      fontWeight:     600,
      display:        "flex",
      alignItems:     "center",
      justifyContent: "center",
      gap:            10,
      cursor:         "pointer",
      transition:     "all 0.18s ease",
      fontFamily:     "inherit",
    },

    divider: {
      display:        "flex",
      alignItems:     "center",
      gap:            10,
      color:          isLight ? "#a09488" : "rgba(200,180,255,0.4)",
      fontSize:       11,
    },
    dividerLine: {
      flex:       1,
      height:     1,
      background: isLight ? "rgba(175,155,120,0.3)" : "rgba(255,255,255,0.1)",
    },

    // Footer
    footer: {
      marginTop:      18,
      display:        "flex",
      alignItems:     "center",
      justifyContent: "center",
      gap:            6,
      fontSize:       12.5,
      color:          isLight ? "#a09488" : "rgba(200,180,255,0.6)",
    },
    footerAction: {
      background:     "none",
      border:         "none",
      cursor:         "pointer",
      fontWeight:     700,
      color:          isLight ? "#c17a2a" : "#c084fc",
      fontSize:       12.5,
      fontFamily:     "inherit",
      textDecoration: "underline",
    },

    secTag: {
      display:        "flex",
      alignItems:     "center",
      justifyContent: "center",
      gap:            5,
      marginTop:      12,
      fontSize:       10.5,
      color:          isLight ? "#b0a090" : "rgba(200,180,255,0.4)",
    },
  };

  return (
    <div style={styles.wrapper}>
      {/* One-time Sky Reader Intro (only when signed out, lazy-loaded) */}
      {introActive && (
        <Suspense fallback={null}>
          <SkyReaderIntro
            onComplete={handleIntroComplete}
            onSkip={handleIntroComplete}
            cardBrandRef={brandRef}
          />
        </Suspense>
      )}

      {/* Top bar: back button + theme toggle */}
      <div
        style={{
          ...styles.topBar,
          opacity: introActive ? 0 : 1,
          pointerEvents: introActive ? "none" : "auto",
          transition: introActive ? "none" : "opacity 0.5s ease",
        }}
        aria-hidden={introActive ? "true" : undefined}
      >
        {onContinueAsGuest ? (
          <button type="button" style={styles.backBtn} onClick={onContinueAsGuest}>
            <ArrowRight size={14} style={{ transform: "rotate(180deg)" }} />
            Continue as guest
          </button>
        ) : <div />}

        {onToggleTheme && (
          <button type="button" style={styles.themeBtn} onClick={onToggleTheme} title="Toggle theme">
            {isLight ? <Moon size={17} /> : <Sun size={17} />}
          </button>
        )}
      </div>

      {/* Glass card: hidden during intro, then fades and rises in */}
      <div
        style={{
          ...styles.card,
          opacity: introActive ? 0 : 1,
          pointerEvents: introActive ? "none" : "auto",
          transform: introActive ? "translateY(24px)" : "translateY(0)",
          transition: introActive
            ? "none"
            : "opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1), transform 0.5s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
        inert={introActive ? true : undefined}
        aria-hidden={introActive ? "true" : undefined}
      >
        {/* Brand */}
        <div ref={brandRef} style={styles.brandRow}>
          <div style={styles.brandBadge}>
            <Sparkles size={20} color="#fff" />
          </div>
          <span style={styles.brandName}>Sky Reader</span>
        </div>

        <h1 style={styles.headline}>
          {mode === "signin" ? "Welcome back ✦" : "Create account"}
        </h1>
        <p style={styles.subline}>
          {mode === "signin"
            ? "Sign in to continue your meteorological AI sessions."
            : "Join Sky Reader for real-time weather intelligence."}
        </p>

        {/* Error */}
        {authError && (
          <div style={styles.errorBanner} role="alert">
            <AlertCircle size={14} />
            <span>{authError}</span>
          </div>
        )}

        {onRetrySession && (
          <button type="button" onClick={onRetrySession} style={styles.footerAction}>
            Retry session verification
          </button>
        )}

        {/* Form */}
        <form style={styles.form} onSubmit={handleSubmit}>
          {/* Name (signup only) */}
          {mode === "signup" && (
            <div style={styles.fieldGroup}>
              <label style={styles.label} htmlFor="login-name">
                <User size={12} /> Full Name
              </label>
              <div style={styles.inputWrap}>
                <User size={15} style={styles.inputIcon} />
                <input
                  id="login-name"
                  type="text"
                  style={styles.input}
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
            </div>
          )}

          {/* Email */}
          <div style={styles.fieldGroup}>
            <label style={styles.label} htmlFor="login-email">
              <Mail size={12} /> Email
            </label>
            <div style={styles.inputWrap}>
              <Mail size={15} style={styles.inputIcon} />
              <input
                id="login-email"
                type="email"
                style={styles.input}
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Password */}
          <div style={styles.fieldGroup}>
            <label style={styles.label} htmlFor="login-password">
              <Lock size={12} /> Password
            </label>
            <div style={styles.inputWrap}>
              <Lock size={15} style={styles.inputIcon} />
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                style={{ ...styles.input, paddingRight: 42 }}
                placeholder={mode === "signup" ? "At least 6 characters" : "Your password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={mode === "signup" ? 6 : 1}
                required
              />
              <button
                type="button"
                style={styles.eyeBtn}
                onClick={() => setShowPassword((p) => !p)}
                title={showPassword ? "Hide" : "Show"}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {/* Options */}
          <div style={styles.optionsRow}>
            <label style={styles.stayLabel}>
              <input
                type="checkbox"
                checked={staySignedIn}
                onChange={(e) => setStaySignedIn(e.target.checked)}
                style={{ accentColor: isLight ? "#c17a2a" : "#c084fc" }}
              />
              <span>Stay signed in</span>
            </label>
            {mode === "signin" && (
              <button
                type="button"
                style={styles.forgotBtn}
                disabled
              >
                Password reset unavailable
              </button>
            )}
          </div>

          {/* Submit */}
          <button type="submit" style={styles.submitBtn} disabled={isSubmitting}>
            {isSubmitting ? (
              <span>{mode === "signin" ? "Signing in…" : "Creating account…"}</span>
            ) : (
              <span>{mode === "signin" ? "Sign In" : "Sign Up"}</span>
            )}
          </button>

          {/* Divider */}
          <div style={styles.divider}>
            <div style={styles.dividerLine} />
            <span>or</span>
            <div style={styles.dividerLine} />
          </div>

          {/* Google */}
          <button
            type="button"
            style={styles.googleBtn}
            disabled
          >
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
            </svg>
            Google sign-in unavailable
          </button>
        </form>

        {/* Footer switch */}
        <div style={styles.footer}>
          <span>{mode === "signin" ? "New to Sky Reader?" : "Already have an account?"}</span>
          <Link
            to={mode === "signin" ? "/signup" : "/login"}
            state={state}
            style={styles.footerAction}
            aria-disabled={isSubmitting || undefined}
            tabIndex={isSubmitting ? -1 : undefined}
            onClick={(event) => { if (isSubmitting) event.preventDefault(); }}
          >
            {mode === "signin" ? "Join Now" : "Sign In"}
          </Link>
        </div>

        {/* Security tag */}
        <div style={styles.secTag}>
          <Sparkles size={10} color={isLight ? "#c17a2a" : "#f59e0b"} />
          <span>Chat history stays in this browser</span>
        </div>
      </div>

      {/* Keyframe injection */}
      <style>{`
        @keyframes loginFadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
