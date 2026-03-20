import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Mail } from "lucide-react";
import { motion } from "framer-motion";

const LoginPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen hero-arch flex flex-col">
      {/* Header — synced with Navbar and StartLearning */}
      <header className="nav-glass sticky top-0 z-50">
        <div className="w-full px-4 md:px-6 relative flex items-center h-[3.4rem]">
          {/* Logo + Site Name — top-left, clickable → home */}
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 shrink-0 cursor-pointer"
          >
            <div className="gold-dot" />
            <span className="font-semibold text-lg tracking-tight text-white">Mind Tutor</span>
          </button>

          {/* Spacer */}
          <div className="flex-1" />

          {/* "Start Learning" — top-right */}
          <div className="nav-reduced flex items-center gap-3">
            <Button variant="hero" size="default" onClick={() => navigate("/start-learning")}>
              Start Learning
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, y: 20, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-sm"
          style={{ zoom: 0.8 }}
        >
          <div className="glass-card-strong rounded-3xl p-8 space-y-6">
            {/* Heading */}
            <div className="text-center space-y-2">
              <h1 className="text-2xl md:text-3xl font-bold leading-[1.2] text-foreground">
                Log in or sign up in seconds
              </h1>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Use your email or another service to continue with Mind Tutor (it's free)
              </p>
            </div>

            {/* Social buttons */}
            <div className="space-y-3">
              <button
                className="w-full flex items-center gap-3 h-12 px-4 rounded-xl bg-foreground text-background font-medium text-sm hover:opacity-90 transition-opacity active:scale-[0.97]"
                onClick={() => {/* TODO: Google auth */}}
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
                onClick={() => {/* TODO: Facebook auth */}}
              >
                <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="#1877F2">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
                Continue with Facebook
              </button>

              <button
                className="w-full flex items-center gap-3 h-12 px-4 rounded-xl bg-foreground text-background font-medium text-sm hover:opacity-90 transition-opacity active:scale-[0.97]"
                onClick={() => {/* TODO: Email auth */}}
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
        </motion.div>
      </div>
    </div>
  );
};

export default LoginPage;
