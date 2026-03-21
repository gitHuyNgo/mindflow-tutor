import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, Loader2, Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

type State = "loading" | "success" | "error";

// ── Floating particle ─────────────────────────────────────────────────────────

const Particle = ({ delay, x, y }: { delay: number; x: string; y: string }) => (
  <motion.div
    className="absolute w-1 h-1 rounded-full bg-primary/40"
    style={{ left: x, top: y }}
    initial={{ opacity: 0, scale: 0, y: 0 }}
    animate={{ opacity: [0, 1, 0], scale: [0, 1, 0], y: -40 }}
    transition={{ duration: 2.4, delay, repeat: Infinity, repeatDelay: 1.6, ease: "easeOut" }}
  />
);

// ── Page ──────────────────────────────────────────────────────────────────────

const VerifyEmailPage = () => {
  const [searchParams] = useSearchParams();
  const navigate        = useNavigate();
  const [state, setState]   = useState<State>("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setState("error");
      setMessage("Invalid verification link.");
      return;
    }

    fetch(`/api/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
          setState("success");
          setMessage(data.message ?? "Email verified successfully.");
        } else {
          setState("error");
          setMessage(data.detail ?? "Verification failed.");
        }
      })
      .catch(() => {
        setState("error");
        setMessage("Network error. Please try again.");
      });
  }, [searchParams]);

  return (
    <div className="min-h-screen hero-arch flex flex-col">
      {/* Nav */}
      <header className="nav-glass sticky top-0 z-50">
        <div className="w-full px-4 md:px-6 flex items-center h-[3.4rem]">
          <button onClick={() => navigate("/")} className="flex items-center gap-2 cursor-pointer">
            <div className="gold-dot" />
            <span className="font-semibold text-lg tracking-tight text-white">Mind Tutor</span>
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center p-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={state}
            initial={{ opacity: 0, y: 20, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -12, filter: "blur(4px)" }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="w-full max-w-sm"
            style={{ zoom: 0.8 }}
          >

            {/* ── Loading ── */}
            {state === "loading" && (
              <div className="glass-card-strong rounded-3xl p-10 text-center space-y-4">
                <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto" />
                <p className="text-muted-foreground text-sm">Verifying your email…</p>
              </div>
            )}

            {/* ── Success ── */}
            {state === "success" && (
              <div className="glass-card-strong rounded-3xl p-8 space-y-7 text-center relative overflow-hidden">
                {/* Subtle top glow */}
                <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-48 h-48 rounded-full bg-primary/15 blur-3xl pointer-events-none" />

                {/* Particles */}
                <Particle delay={0.0} x="18%" y="22%" />
                <Particle delay={0.5} x="75%" y="18%" />
                <Particle delay={1.0} x="55%" y="30%" />
                <Particle delay={1.5} x="30%" y="40%" />
                <Particle delay={0.8} x="82%" y="35%" />

                {/* Icon */}
                <div className="relative flex items-center justify-center mx-auto w-20 h-20">
                  {/* Pulsing ring */}
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-primary/30"
                    animate={{ scale: [1, 1.35, 1], opacity: [0.6, 0, 0.6] }}
                    transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
                  />
                  <motion.div
                    className="absolute inset-0 rounded-full border border-primary/20"
                    animate={{ scale: [1, 1.6, 1], opacity: [0.4, 0, 0.4] }}
                    transition={{ duration: 2.5, delay: 0.4, repeat: Infinity, ease: "easeInOut" }}
                  />
                  <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                    <motion.div
                      initial={{ scale: 0, rotate: -20 }}
                      animate={{ scale: 1, rotate: 0 }}
                      transition={{ type: "spring", stiffness: 260, damping: 18, delay: 0.15 }}
                    >
                      <CheckCircle2 className="w-8 h-8 text-primary" strokeWidth={2} />
                    </motion.div>
                  </div>
                </div>

                {/* Copy */}
                <div className="space-y-2 relative">
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 }}
                    className="flex items-center justify-center gap-2 text-xs font-medium text-primary uppercase tracking-widest"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Account activated
                  </motion.div>

                  <motion.h1
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.32 }}
                    className="text-3xl font-bold text-foreground"
                  >
                    You're all set!
                  </motion.h1>

                  <motion.p
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="text-sm text-muted-foreground leading-relaxed"
                  >
                    Your email has been verified. Sign in to start your learning journey with Mind Tutor.
                  </motion.p>
                </div>

                {/* CTAs */}
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                  className="space-y-2.5"
                >
                  <Button
                    variant="hero"
                    className="w-full group"
                    onClick={() => navigate("/login")}
                  >
                    Sign in now
                    <ArrowRight className="w-4 h-4 ml-1.5 transition-transform group-hover:translate-x-0.5" />
                  </Button>
                  <button
                    onClick={() => navigate("/")}
                    className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors py-1"
                  >
                    Back to home
                  </button>
                </motion.div>
              </div>
            )}

            {/* ── Error ── */}
            {state === "error" && (
              <div className="glass-card-strong rounded-3xl p-8 space-y-6 text-center">
                <div className="w-16 h-16 rounded-2xl bg-destructive/10 flex items-center justify-center mx-auto">
                  <XCircle className="w-8 h-8 text-destructive" />
                </div>
                <div className="space-y-1.5">
                  <h1 className="text-2xl font-bold text-foreground">Verification failed</h1>
                  <p className="text-sm text-muted-foreground leading-relaxed">{message}</p>
                </div>
                <div className="space-y-2.5">
                  <Button variant="hero" className="w-full" onClick={() => navigate("/login")}>
                    Back to login
                  </Button>
                  <button
                    onClick={() => navigate("/")}
                    className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors py-1"
                  >
                    Back to home
                  </button>
                </div>
              </div>
            )}

          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

export default VerifyEmailPage;
