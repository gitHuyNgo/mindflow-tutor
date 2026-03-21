import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Mail, ArrowLeft, Eye, EyeOff, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { authApi } from "@/lib/auth";
import { useAuth } from "@/contexts/AuthContext";

type View = "social" | "login" | "register" | "check-email";

// ── Client-side validation (mirrors backend rules) ───────────────────────────

const BLOCKED_TLDS = new Set([
  "test","invalid","example","localhost","local","fake","demo","null","undefined",
]);
const SUSPICIOUS_TLDS = new Set(["con","cmo","ocm","cpm","vom","cok"]);

function validateFullName(name: string): string {
  if (!name) return "";
  if (name.length > 50) return "Full name must be at most 50 characters";
  if (/[0-9!@#$%^&*()_+=\[\]{};:'",<>?/\\|`~]/.test(name))
    return "Full name must not contain numbers or special characters";
  return "";
}

function validateEmail(email: string): string {
  if (!email) return "";
  const tld = email.split(".").pop()?.toLowerCase() ?? "";
  if (tld.length < 2) return "Email has an invalid domain extension";
  if (BLOCKED_TLDS.has(tld)) return `Email extension '.${tld}' is not allowed`;
  if (SUSPICIOUS_TLDS.has(tld)) return `'.${tld}' looks like a typo — did you mean '.com'?`;
  return "";
}

function validatePassword(password: string, email: string, fullName: string): string {
  if (!password) return "";
  if (password.length < 8) return "At least 8 characters required";
  if (!/[A-Z]/.test(password)) return "Add at least one uppercase letter";
  if (!/\d/.test(password)) return "Add at least one number";
  if (!/[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]/.test(password))
    return "Add at least one special character";
  const pw = password.toLowerCase();
  const emailLocal = email.split("@")[0].toLowerCase();
  if (emailLocal.length >= 4 && pw.includes(emailLocal))
    return "Password is too similar to your email";
  for (const part of fullName.toLowerCase().split(/\s+/))
    if (part.length >= 3 && pw.includes(part))
      return "Password is too similar to your name";
  return "";
}

// ── Component ────────────────────────────────────────────────────────────────

type View = "social" | "login" | "register" | "check-email" | "resend-prompt";

const LoginPage = () => {
  const navigate  = useNavigate();
  const { login } = useAuth();

  const [view, setView]           = useState<View>("social");
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");
  const [showPass, setShowPass]   = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState("");

  // Form fields
  const [fullName,  setFullName]  = useState("");
  const [email,     setEmail]     = useState("");
  const [password,  setPassword]  = useState("");

  // Register field-level errors
  const [fieldErrors, setFieldErrors] = useState({ fullName: "", email: "", password: "" });

  // Resend cooldown
  const [cooldown, setCooldown] = useState(0);
  const startCooldown = () => {
    setCooldown(60);
    const t = setInterval(() => {
      setCooldown((s) => {
        if (s <= 1) { clearInterval(t); return 0; }
        return s - 1;
      });
    }, 1000);
  };

  const clearError = () => {
    setError("");
    setFieldErrors({ fullName: "", email: "", password: "" });
  };

  const setFieldError = (field: keyof typeof fieldErrors, msg: string) =>
    setFieldErrors((prev) => ({ ...prev, [field]: msg }));

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setLoading(true);
    try {
      const res = await authApi.login(email, password);
      login(res.access_token, res.user);
      navigate("/login-success");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    // Run all validators before hitting the server
    const nameErr  = validateFullName(fullName);
    const emailErr = validateEmail(email);
    const passErr  = validatePassword(password, email, fullName);
    setFieldErrors({ fullName: nameErr, email: emailErr, password: passErr });
    if (nameErr || emailErr || passErr) return;

    setLoading(true);
    try {
      const res = await authApi.register(email, password, fullName);
      setRegisteredEmail(email);
      setView(res.pending_verification ? "resend-prompt" : "check-email");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen hero-arch flex flex-col">
      {/* Header */}
      <header className="nav-glass sticky top-0 z-50">
        <div className="w-full px-4 md:px-6 relative flex items-center h-[3.4rem]">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 shrink-0 cursor-pointer"
          >
            <div className="gold-dot" />
            <span className="font-semibold text-lg tracking-tight text-white">Mind Tutor</span>
          </button>
          <div className="flex-1" />
          <div className="nav-reduced flex items-center gap-3">
            <Button variant="hero" size="default" onClick={() => navigate("/start-learning")}>
              Start Learning
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center p-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={view}
            initial={{ opacity: 0, y: 16, filter: "blur(6px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -12, filter: "blur(4px)" }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="w-full max-w-sm"
            style={{ zoom: 0.8 }}
          >
            {/* ── Social buttons ── */}
            {view === "social" && (
              <div className="glass-card-strong rounded-3xl p-8 space-y-6">
                <div className="text-center space-y-2">
                  <h1 className="text-2xl md:text-3xl font-bold leading-[1.2] text-foreground">
                    Log in or sign up in seconds
                  </h1>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    Use your email or another service to continue with Mind Tutor (it's free)
                  </p>
                </div>

                <div className="space-y-3">
                  <button
                    className="w-full flex items-center gap-3 h-12 px-4 rounded-xl bg-foreground text-background font-medium text-sm hover:opacity-90 transition-opacity active:scale-[0.97]"
                    onClick={() => {/* TODO: Google OAuth */}}
                  >
                    <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                    </svg>
                    Continue with Google
                  </button>

                  <button
                    className="w-full flex items-center gap-3 h-12 px-4 rounded-xl bg-foreground text-background font-medium text-sm hover:opacity-90 transition-opacity active:scale-[0.97]"
                    onClick={() => {/* TODO: Facebook OAuth */}}
                  >
                    <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="#1877F2">
                      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                    </svg>
                    Continue with Facebook
                  </button>

                  <button
                    className="w-full flex items-center gap-3 h-12 px-4 rounded-xl bg-foreground text-background font-medium text-sm hover:opacity-90 transition-opacity active:scale-[0.97]"
                    onClick={() => setView("login")}
                  >
                    <Mail className="w-5 h-5 shrink-0" />
                    Continue with email
                  </button>
                </div>

                <p className="text-xs text-center text-muted-foreground leading-relaxed">
                  By continuing, you agree to our{" "}
                  <a href="#" className="underline hover:text-foreground transition-colors">Terms of Service</a>
                  {" "}and{" "}
                  <a href="#" className="underline hover:text-foreground transition-colors">Privacy Policy</a>
                </p>
              </div>
            )}

            {/* ── Login form ── */}
            {view === "login" && (
              <div className="glass-card-strong rounded-3xl p-8 space-y-6">
                <button
                  onClick={() => { setView("social"); clearError(); }}
                  className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors text-sm"
                >
                  <ArrowLeft className="w-4 h-4" /> Back
                </button>

                <div className="text-center space-y-1">
                  <h1 className="text-2xl font-bold text-foreground">Welcome back</h1>
                  <p className="text-sm text-muted-foreground">Sign in to your Mind Tutor account</p>
                </div>

                <form onSubmit={handleLogin} className="space-y-3">
                  <input
                    type="email"
                    placeholder="Email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full h-11 px-4 rounded-xl bg-foreground/5 border border-border text-foreground placeholder:text-muted-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                  <div className="relative">
                    <input
                      type={showPass ? "text" : "password"}
                      placeholder="Password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full h-11 px-4 pr-11 rounded-xl bg-foreground/5 border border-border text-foreground placeholder:text-muted-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPass((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>

                  {error && (
                    <p className="text-xs text-destructive text-center">{error}</p>
                  )}

                  <Button type="submit" variant="hero" className="w-full" disabled={loading}>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Sign in"}
                  </Button>
                </form>

                <p className="text-xs text-center text-muted-foreground">
                  Don't have an account?{" "}
                  <button
                    onClick={() => { setView("register"); clearError(); }}
                    className="underline hover:text-foreground transition-colors"
                  >
                    Sign up
                  </button>
                </p>
              </div>
            )}

            {/* ── Register form ── */}
            {view === "register" && (
              <div className="glass-card-strong rounded-3xl p-8 space-y-6">
                <button
                  onClick={() => { setView("social"); clearError(); }}
                  className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors text-sm"
                >
                  <ArrowLeft className="w-4 h-4" /> Back
                </button>

                <div className="text-center space-y-1">
                  <h1 className="text-2xl font-bold text-foreground">Create account</h1>
                  <p className="text-sm text-muted-foreground">Start learning for free today</p>
                </div>

                <form onSubmit={handleRegister} className="space-y-3">
                  <div>
                    <input
                      type="text"
                      placeholder="Full name"
                      value={fullName}
                      onChange={(e) => { setFullName(e.target.value); setFieldError("fullName", validateFullName(e.target.value)); }}
                      className="w-full h-11 px-4 rounded-xl bg-foreground/5 border border-border text-foreground placeholder:text-muted-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                    {fieldErrors.fullName && <p className="mt-1 text-xs text-destructive">{fieldErrors.fullName}</p>}
                  </div>
                  <div>
                    <input
                      type="email"
                      placeholder="Email"
                      required
                      value={email}
                      onChange={(e) => { setEmail(e.target.value); setFieldError("email", validateEmail(e.target.value)); }}
                      className="w-full h-11 px-4 rounded-xl bg-foreground/5 border border-border text-foreground placeholder:text-muted-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                    {fieldErrors.email && <p className="mt-1 text-xs text-destructive">{fieldErrors.email}</p>}
                  </div>
                  <div>
                    <div className="relative">
                      <input
                        type={showPass ? "text" : "password"}
                        placeholder="Password (min. 8 characters)"
                        required
                        minLength={8}
                        value={password}
                        onChange={(e) => { setPassword(e.target.value); setFieldError("password", validatePassword(e.target.value, email, fullName)); }}
                        className="w-full h-11 px-4 pr-11 rounded-xl bg-foreground/5 border border-border text-foreground placeholder:text-muted-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPass((v) => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    {fieldErrors.password && <p className="mt-1 text-xs text-destructive">{fieldErrors.password}</p>}
                  </div>

                  {error && (
                    <p className="text-xs text-destructive text-center">{error}</p>
                  )}

                  <Button type="submit" variant="hero" className="w-full" disabled={loading}>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create account"}
                  </Button>
                </form>

                <p className="text-xs text-center text-muted-foreground">
                  Already have an account?{" "}
                  <button
                    onClick={() => { setView("login"); clearError(); }}
                    className="underline hover:text-foreground transition-colors"
                  >
                    Sign in
                  </button>
                </p>
              </div>
            )}

            {/* ── Check email ── */}
            {view === "check-email" && (
              <div className="glass-card-strong rounded-3xl p-8 space-y-6 text-center">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mx-auto">
                  <Mail className="w-8 h-8" />
                </div>
                <div className="space-y-2">
                  <h1 className="text-2xl font-bold text-foreground">Check your email</h1>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    We sent a verification link to{" "}
                    <span className="text-foreground font-medium">{registeredEmail}</span>.
                    Click it to activate your account.
                  </p>
                </div>
                <Button
                  variant="hero"
                  className="w-full"
                  onClick={() => { setView("login"); clearError(); }}
                >
                  Go to sign in
                </Button>
                <p className="text-xs text-muted-foreground">
                  Didn't receive it?{" "}
                  <button
                    disabled={cooldown > 0}
                    className="underline hover:text-foreground transition-colors disabled:opacity-40 disabled:no-underline disabled:cursor-not-allowed"
                    onClick={async () => {
                      try {
                        await authApi.resendVerification(registeredEmail);
                        startCooldown();
                      } catch {
                        // silent
                      }
                    }}
                  >
                    {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend"}
                  </button>
                </p>
              </div>
            )}

            {/* ── Resend prompt (registered but not verified) ── */}
            {view === "resend-prompt" && (
              <div className="glass-card-strong rounded-3xl p-8 space-y-6 text-center">
                <div className="w-16 h-16 rounded-2xl bg-amber-500/10 text-amber-500 flex items-center justify-center mx-auto">
                  <Mail className="w-8 h-8" />
                </div>
                <div className="space-y-2">
                  <h1 className="text-2xl font-bold text-foreground">Account pending</h1>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    <span className="text-foreground font-medium">{registeredEmail}</span> is already
                    registered but not verified yet.
                    <br />Did you receive the confirmation email?
                  </p>
                </div>

                <div className="space-y-2.5">
                  <Button
                    variant="hero"
                    className="w-full"
                    onClick={() => { setView("login"); clearError(); }}
                  >
                    Yes, go to sign in
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full"
                    disabled={loading || cooldown > 0}
                    onClick={async () => {
                      setLoading(true);
                      try {
                        await authApi.resendVerification(registeredEmail);
                        startCooldown();
                        setView("check-email");
                      } catch {
                        setView("check-email");
                      } finally {
                        setLoading(false);
                      }
                    }}
                  >
                    {loading
                      ? <Loader2 className="w-4 h-4 animate-spin" />
                      : cooldown > 0 ? `Resend in ${cooldown}s` : "No, resend email"
                    }
                  </Button>
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

export default LoginPage;
