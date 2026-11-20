import { useState, useEffect, useRef } from "react";
import {
  Eye, EyeOff, Sparkles, Check, AlertCircle,
  Sun, Moon, ArrowRight, User, Mail, Lock,
} from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8000";

/* ─────────────────────────────────────────────────────────────────
   Animated Canvas Background — aurora / particle field
   ───────────────────────────────────────────────────────────────── */
function LoginCanvas({ theme }) {
  const canvasRef = useRef(null);
  const animRef  = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const isLight = theme === "light";

    // Particle data
    const PARTICLE_COUNT = 90;
    const particles = [];
    let W = 0, H = 0;

    const resize = () => {
      W = canvas.width  = canvas.offsetWidth;
      H = canvas.height = canvas.offsetHeight;
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    // Build particles
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x:    Math.random() * W,
        y:    Math.random() * H,
        r:    Math.random() * 2.2 + 0.4,
        vx:   (Math.random() - 0.5) * 0.35,
        vy:   (Math.random() - 0.5) * 0.35,
        alpha: Math.random() * 0.5 + 0.15,
        hue:  Math.random() * 60 + (isLight ? 20 : 200), // warm for light, cool-purple for dark
      });
    }

    // Aurora bands state
    const bands = [
      { y: 0.25, spread: 0.18, hue: isLight ? 35 : 270, speed: 0.0008 },
      { y: 0.55, spread: 0.14, hue: isLight ? 50 : 230, speed: 0.0012 },
      { y: 0.78, spread: 0.12, hue: isLight ? 25 : 300, speed: 0.0006 },
    ];
    let t = 0;

    const draw = () => {
      t += 1;

      // Background gradient
      const grad = ctx.createLinearGradient(0, 0, 0, H);
      if (isLight) {
        grad.addColorStop(0,   "#f0ebe2");
        grad.addColorStop(0.5, "#e4ddd3");
        grad.addColorStop(1,   "#d4ccbf");
      } else {
        grad.addColorStop(0,   "#0a0718");
        grad.addColorStop(0.5, "#0e0c22");
        grad.addColorStop(1,   "#07050f");
      }
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);

      // Aurora bands
      bands.forEach((b) => {
        const cy = H * (b.y + Math.sin(t * b.speed) * 0.06);
        const spread = H * b.spread;
        const ag = ctx.createRadialGradient(W * 0.5, cy, 0, W * 0.5, cy, spread * 3.5);
        if (isLight) {
          ag.addColorStop(0,   `hsla(${b.hue}, 55%, 68%, 0.28)`);
          ag.addColorStop(0.5, `hsla(${b.hue + 20}, 50%, 72%, 0.12)`);
          ag.addColorStop(1,   "transparent");
        } else {
          ag.addColorStop(0,   `hsla(${b.hue}, 70%, 55%, 0.22)`);
          ag.addColorStop(0.5, `hsla(${b.hue + 30}, 60%, 45%, 0.10)`);
          ag.addColorStop(1,   "transparent");
        }
        ctx.fillStyle = ag;
        ctx.fillRect(0, 0, W, H);
      });

      // Floating particles
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = W;
        if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H;
        if (p.y > H) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        if (isLight) {
          ctx.fillStyle = `hsla(${p.hue}, 50%, 55%, ${p.alpha * 0.5})`;
        } else {
          ctx.fillStyle = `hsla(${p.hue}, 80%, 75%, ${p.alpha})`;
        }
        ctx.fill();
      });

      // Soft bottom glow
      const glow = ctx.createLinearGradient(0, H * 0.6, 0, H);
      if (isLight) {
        glow.addColorStop(0, "transparent");
        glow.addColorStop(1, "rgba(200, 170, 120, 0.15)");
      } else {
        glow.addColorStop(0, "transparent");
        glow.addColorStop(1, "rgba(130, 60, 200, 0.18)");
      }
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, W, H);

      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animRef.current);
      ro.disconnect();
    };
  }, [theme]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 0,
      }}
    />
  );
}

/* ─────────────────────────────────────────────────────────────────
   Main Login Page
   ───────────────────────────────────────────────────────────────── */
export default function LoginPage({ onLoginSuccess, onBackToApp, theme = "dark", onToggleTheme }) {
  const [email,        setEmail]        = useState("");
  const [password,     setPassword]     = useState("");
  const [name,         setName]         = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [staySignedIn, setStaySignedIn] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess,    setIsSuccess]    = useState(false);
  const [authError,    setAuthError]    = useState("");
  const [mode,         setMode]         = useState("signin"); // "signin" | "signup"

  const isLight = theme === "light";

  const handleFillDemo = () => {
    setEmail("explorer@skyreader.ai");
    setPassword("weather123");
    setMode("signin");
    setAuthError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");
    setIsSubmitting(true);

    const endpoint =
      mode === "signin"
        ? `${API_BASE_URL}/api/auth/login`
        : `${API_BASE_URL}/api/auth/register`;

    const payload =
      mode === "signin"
        ? { email, password }
        : { email, password, name: name.trim() || email.split("@")[0] };

    try {
      const res  = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Authentication request failed.");

      if (staySignedIn && data.token) {
        localStorage.setItem("skyreader_token", data.token);
      }
      setIsSuccess(true);
      setTimeout(() => onLoginSuccess(data.user), 700);
    } catch (err) {
      setAuthError(err.message || "Failed to communicate with authentication server.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleLogin = () => {
    setIsSubmitting(true);
    setAuthError("");
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSuccess(true);
      setTimeout(() =>
        onLoginSuccess({
          id:         999,
          email:      "google.user@skyreader.ai",
          name:       "Meteorology Pro",
          created_at: new Date().toISOString(),
          saved_cities: ["Tokyo", "Zurich"],
        }), 600);
    }, 500);
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
      cursor:         isSubmitting || isSuccess ? "not-allowed" : "pointer",
      background:     isSuccess
        ? "linear-gradient(135deg,#34d399 0%,#059669 100%)"
        : "linear-gradient(135deg,#f59e0b 0%,#ea580c 100%)",
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

    // Demo pill
    demoPill: {
      display:        "flex",
      alignItems:     "center",
      justifyContent: "center",
      marginTop:      6,
    },
    demoBtn: {
      display:        "inline-flex",
      alignItems:     "center",
      gap:            8,
      padding:        "5px 14px",
      borderRadius:   999,
      border:         isLight
        ? "1px dashed rgba(175,155,120,0.5)"
        : "1px dashed rgba(192,132,252,0.4)",
      background:     "transparent",
      color:          isLight ? "#7a6e62" : "rgba(220,195,255,0.75)",
      fontSize:       11.5,
      cursor:         "pointer",
      fontFamily:     "inherit",
      transition:     "all 0.18s ease",
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
      {/* Animated canvas background */}
      <LoginCanvas theme={theme} />

      {/* Top bar: back button + theme toggle */}
      <div style={styles.topBar}>
        {onBackToApp ? (
          <button type="button" style={styles.backBtn} onClick={onBackToApp}>
            <ArrowRight size={14} style={{ transform: "rotate(180deg)" }} />
            Back to App
          </button>
        ) : <div />}

        {onToggleTheme && (
          <button type="button" style={styles.themeBtn} onClick={onToggleTheme} title="Toggle theme">
            {isLight ? <Moon size={17} /> : <Sun size={17} />}
          </button>
        )}
      </div>

      {/* Glass card */}
      <div style={styles.card}>
        {/* Brand */}
        <div style={styles.brandRow}>
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
                onClick={() => alert("Password reset link will be sent to your email.")}
              >
                Forgot password?
              </button>
            )}
          </div>

          {/* Submit */}
          <button type="submit" style={styles.submitBtn} disabled={isSubmitting || isSuccess}>
            {isSuccess ? (
              <><Check size={16} /> Authenticated! Entering...</>
            ) : isSubmitting ? (
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
            onClick={handleGoogleLogin}
            disabled={isSubmitting || isSuccess}
          >
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
            </svg>
            Continue with Google
          </button>
        </form>

        {/* Demo pill */}
        <div style={styles.demoPill}>
          <button type="button" style={styles.demoBtn} onClick={handleFillDemo}>
            <Sparkles size={12} />
            Quick Demo — Click to fill credentials
          </button>
        </div>

        {/* Footer switch */}
        <div style={styles.footer}>
          <span>{mode === "signin" ? "New to Sky Reader?" : "Already have an account?"}</span>
          <button
            type="button"
            style={styles.footerAction}
            onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setAuthError(""); }}
          >
            {mode === "signin" ? "Join Now" : "Sign In"}
          </button>
        </div>

        {/* Security tag */}
        <div style={styles.secTag}>
          <Sparkles size={10} color={isLight ? "#c17a2a" : "#f59e0b"} />
          <span>Encrypted SQLite • Zero-hallucination AI Sessions</span>
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
