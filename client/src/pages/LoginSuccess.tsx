import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const HOLD_MS  = 3000;   // stay visible
const FADE_MS  = 700;    // fade-out duration

const LoginSuccessPage = () => {
  const navigate          = useNavigate();
  const { user }          = useAuth();
  const [leaving, setLeaving] = useState(false);

  const firstName = user?.full_name?.split(" ")[0] || "there";

  useEffect(() => {
    const holdTimer = setTimeout(() => setLeaving(true), HOLD_MS);
    const leaveTimer = setTimeout(() => navigate("/", { replace: true }), HOLD_MS + FADE_MS);
    return () => { clearTimeout(holdTimer); clearTimeout(leaveTimer); };
  }, [navigate]);

  return (
    <motion.div
      className="min-h-screen hero-arch flex flex-col"
      animate={leaving ? { opacity: 0, filter: "blur(6px)", scale: 0.98 } : { opacity: 1, filter: "blur(0px)", scale: 1 }}
      transition={{ duration: FADE_MS / 1000, ease: [0.4, 0, 1, 1] }}
    >
      {/* Nav */}
      <header className="nav-glass sticky top-0 z-50">
        <div className="w-full px-4 md:px-6 flex items-center h-[3.4rem]">
          <div className="flex items-center gap-2">
            <div className="gold-dot" />
            <span className="font-semibold text-lg tracking-tight text-white">Mind Tutor</span>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, y: 24, filter: "blur(10px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-sm text-center space-y-7"
          style={{ zoom: 0.8 }}
        >
          {/* Icon */}
          <div className="relative flex items-center justify-center mx-auto w-24 h-24">
            <motion.div
              className="absolute inset-0 rounded-full border-2 border-primary/25"
              animate={{ scale: [1, 1.4, 1], opacity: [0.5, 0, 0.5] }}
              transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
            />
            <motion.div
              className="absolute inset-0 rounded-full border border-primary/15"
              animate={{ scale: [1, 1.7, 1], opacity: [0.3, 0, 0.3] }}
              transition={{ duration: 2.4, delay: 0.5, repeat: Infinity, ease: "easeInOut" }}
            />
            <motion.div
              className="w-[4.5rem] h-[4.5rem] rounded-full bg-primary/10 flex items-center justify-center"
              initial={{ scale: 0, rotate: -15 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: "spring", stiffness: 240, damping: 18, delay: 0.1 }}
            >
              <Sparkles className="w-9 h-9 text-primary" strokeWidth={1.5} />
            </motion.div>
          </div>

          {/* Copy */}
          <div className="space-y-3">
            <motion.p
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.22 }}
              className="text-xs font-medium text-primary uppercase tracking-widest"
            >
              Login successful
            </motion.p>

            <motion.h1
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="text-4xl font-bold text-white leading-tight"
            >
              Welcome back,<br />
              <span className="text-primary">{firstName}</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.38 }}
              className="text-sm text-white/50 leading-relaxed"
            >
              Taking you to your workspace…
            </motion.p>
          </div>

          {/* Progress dots */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="flex items-center justify-center gap-1.5"
          >
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-primary/50"
                animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
                transition={{
                  duration: 1.2,
                  delay: i * 0.2,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
              />
            ))}
          </motion.div>
        </motion.div>
      </div>
    </motion.div>
  );
};

export default LoginSuccessPage;
