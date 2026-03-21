import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Mic, MicOff, Video, VideoOff, Monitor, ArrowRight, ArrowLeft, CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { sessionStore } from "@/lib/sessionStore";

const StartLearningPage = () => {
  const [step, setStep] = useState(1);
  const [camOn, setCamOn] = useState(false);
  const [micOn, setMicOn] = useState(false);
  const [isSharing, setIsSharing] = useState(false);

  const navigate = useNavigate();

  const camVideoRef = useRef<HTMLVideoElement>(null);
  const screenVideoRef = useRef<HTMLVideoElement>(null);
  const setPipRef = useCallback((el: HTMLVideoElement | null) => {
    if (el && camStreamRef.current) {
      el.srcObject = camStreamRef.current;
    }
  }, []);
  const camStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  // Flag: don't stop streams when navigating to session (Session.tsx takes ownership)
  const handedOffToSession = useRef(false);

  const handleBack = useCallback(() => {
    camStreamRef.current?.getTracks().forEach((t) => t.stop());
    screenStreamRef.current?.getTracks().forEach((t) => t.stop());
    navigate("/");
  }, [navigate]);

  const toggleCam = useCallback(async () => {
    if (camOn) {
      camStreamRef.current?.getVideoTracks().forEach((t) => t.stop());
      if (camVideoRef.current) camVideoRef.current.srcObject = null;
      setCamOn(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        camStreamRef.current = stream;
        if (camVideoRef.current) {
          camVideoRef.current.srcObject = stream;
        }
        setCamOn(true);
      } catch {
        // denied
      }
    }
  }, [camOn]);

  const toggleMic = useCallback(async () => {
    if (micOn) {
      camStreamRef.current?.getAudioTracks().forEach((t) => t.stop());
      setMicOn(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (camStreamRef.current) {
          stream.getAudioTracks().forEach((t) => camStreamRef.current!.addTrack(t));
        } else {
          camStreamRef.current = stream;
        }
        setMicOn(true);
      } catch {
        // denied
      }
    }
  }, [micOn]);

  const startScreenShare = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      screenStreamRef.current = stream;
      if (screenVideoRef.current) {
        screenVideoRef.current.srcObject = stream;
      }
      setIsSharing(true);
      stream.getVideoTracks()[0].addEventListener("ended", () => {
        setIsSharing(false);
        if (screenVideoRef.current) screenVideoRef.current.srcObject = null;
      });
    } catch {
      // cancelled
    }
  }, []);

  useEffect(() => {
    return () => {
      // Only stop streams if user backed out, not when handing off to session
      if (!handedOffToSession.current) {
        camStreamRef.current?.getTracks().forEach((t) => t.stop());
        screenStreamRef.current?.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  useEffect(() => {
    if (camOn && camVideoRef.current && camStreamRef.current) {
      camVideoRef.current.srcObject = camStreamRef.current;
    }
  }, [camOn]);

  useEffect(() => {
    if (isSharing && screenVideoRef.current && screenStreamRef.current) {
      screenVideoRef.current.srcObject = screenStreamRef.current;
    }
  }, [isSharing]);

  const hasAnyPermission = camOn || micOn;

  return (
    <div className="min-h-screen hero-arch flex flex-col">
      {/* Header — logo left, buttons right, synced with Navbar */}
      <header className="nav-glass sticky top-0 z-50">
        <div className="w-full px-4 md:px-6 relative flex items-center h-[3.4rem]">
          {/* Logo + Site Name — top-left, clickable → home with stream cleanup */}
          <button
            onClick={handleBack}
            className="flex items-center gap-2 shrink-0 cursor-pointer"
          >
            <div className="gold-dot" />
            <span className="font-semibold text-lg tracking-tight text-white">Mind Tutor</span>
          </button>

          {/* Spacer */}
          <div className="flex-1" />

          {/* "Log in" + "Start Learning" — top-right (same as Navbar) */}
          <div className="nav-reduced flex items-center gap-3">
            <Button variant="ghost" size="sm" className="text-white/70 hover:text-white" onClick={() => navigate("/login")}>
              Log in
            </Button>
            <Button variant="hero" size="default" onClick={() => navigate("/start-learning")}>
              Start Learning
            </Button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-3xl" style={{ zoom: 0.8 }}>

          {/* Back to home — near panel */}
          <button
            onClick={handleBack}
            className="flex items-center gap-1.5 text-white/55 hover:text-white transition-colors mb-6 text-sm font-medium cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </button>

          {/* Step indicators */}
          <div className="flex items-center justify-center gap-4 mb-10">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-base font-bold transition-all duration-500 ${
                step >= 1
                  ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                  : "glass-card text-muted-foreground"
              }`}>
                {step > 1 ? <CheckCircle2 className="w-5 h-5" /> : "1"}
              </div>
              <div className="flex flex-col">
                <span className={`text-sm font-semibold transition-colors ${step >= 1 ? "text-white" : "text-white/50"}`}>
                  Camera & Mic
                </span>
                <span className="text-xs text-white/50">Preview & toggle</span>
              </div>
            </div>

            <div className="w-12 h-px bg-white/20" />

            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-base font-bold transition-all duration-500 ${
                step >= 2
                  ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                  : "glass-card text-muted-foreground"
              }`}>
                2
              </div>
              <div className="flex flex-col">
                <span className={`text-sm font-semibold transition-colors ${step >= 2 ? "text-white" : "text-white/50"}`}>
                  Share Screen
                </span>
                <span className="text-xs text-white/50">Stream your document</span>
              </div>
            </div>
          </div>

          {/* Step content */}
          <AnimatePresence mode="wait">
            {step === 1 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, y: 16, filter: "blur(6px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -12, filter: "blur(4px)" }}
                transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
              >
                <div className="glass-card-strong rounded-3xl p-8 md:p-10 space-y-6">
                  <div className="text-center">
                    <h1 className="text-2xl md:text-3xl font-bold leading-[1.2] text-foreground mb-2">
                      Check your camera and microphone
                    </h1>
                    <p className="text-muted-foreground text-sm leading-relaxed max-w-md mx-auto">
                      Toggle your camera and mic on or off. You can change these anytime during the session.
                    </p>
                  </div>

                  {/* Camera preview */}
                  <div className="relative w-full aspect-video rounded-2xl overflow-hidden bg-foreground/5 border border-border/50">
                    {camOn ? (
                      <video
                        ref={camVideoRef}
                        autoPlay
                        playsInline
                        muted
                        className="w-full h-full object-cover scale-x-[-1]"
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center gap-3">
                        <div className="w-20 h-20 rounded-full bg-secondary flex items-center justify-center">
                          <VideoOff className="w-8 h-8 text-muted-foreground" />
                        </div>
                        <p className="text-sm text-muted-foreground">Camera is off</p>
                      </div>
                    )}

                    {micOn && (
                      <div className="absolute top-3 left-3 flex items-center gap-1.5 glass-card rounded-full px-3 py-1.5">
                        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                        <span className="text-xs font-medium text-foreground">Mic on</span>
                      </div>
                    )}
                  </div>

                  {/* Toggle controls */}
                  <div className="flex justify-center gap-4">
                    <button
                      onClick={toggleMic}
                      className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300 active:scale-95 ${
                        micOn
                          ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                          : "glass-card text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {micOn ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
                    </button>
                    <button
                      onClick={toggleCam}
                      className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300 active:scale-95 ${
                        camOn
                          ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                          : "glass-card text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {camOn ? <Video className="w-5 h-5" /> : <VideoOff className="w-5 h-5" />}
                    </button>
                  </div>

                  {/* Next */}
                  <div className="flex justify-center pt-2">
                    <Button variant="hero" size="lg" onClick={() => setStep(2)} disabled={!hasAnyPermission}>
                      Continue
                      <ArrowRight className="w-4 h-4 ml-1" />
                    </Button>
                  </div>
                  {!hasAnyPermission && (
                    <p className="text-xs text-muted-foreground text-center">Turn on at least the mic or camera to continue</p>
                  )}
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div
                key="step2"
                initial={{ opacity: 0, y: 16, filter: "blur(6px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -12, filter: "blur(4px)" }}
                transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
              >
                <div className="glass-card-strong rounded-3xl p-8 md:p-10 space-y-6">
                  <div className="text-center">
                    <h1 className="text-2xl md:text-3xl font-bold leading-[1.2] text-foreground mb-2">
                      Share your screen to start learning
                    </h1>
                    <p className="text-muted-foreground text-sm leading-relaxed max-w-md mx-auto">
                      Share the window with your study material — just like a Google Meet call.
                    </p>
                  </div>

                  {/* Screen preview */}
                  <div className="relative w-full aspect-video rounded-2xl overflow-hidden bg-foreground/5 border border-border/50">
                    {isSharing ? (
                      <video
                        ref={screenVideoRef}
                        autoPlay
                        playsInline
                        muted
                        className="w-full h-full object-contain bg-foreground/5"
                      />
                    ) : (
                      <div
                        onClick={startScreenShare}
                        className="w-full h-full flex flex-col items-center justify-center gap-4 cursor-pointer group"
                      >
                        <div className="w-20 h-20 rounded-3xl bg-primary/10 text-primary flex items-center justify-center group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-300">
                          <Monitor className="w-9 h-9" />
                        </div>
                        <div className="text-center">
                          <p className="font-semibold text-foreground mb-0.5">Click to share your screen</p>
                          <p className="text-xs text-muted-foreground">Choose a window, tab, or entire screen</p>
                        </div>
                      </div>
                    )}

                    {camOn && (
                      <div className="absolute bottom-3 right-3 w-32 h-24 rounded-xl overflow-hidden shadow-lg border-2 border-background/60">
                        <video
                          ref={setPipRef}
                          autoPlay
                          playsInline
                          muted
                          className="w-full h-full object-cover scale-x-[-1]"
                        />
                      </div>
                    )}

                    {isSharing && (
                      <div className="absolute top-3 left-3 flex items-center gap-1.5 glass-card rounded-full px-3 py-1.5">
                        <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                        <span className="text-xs font-medium text-foreground">Sharing</span>
                      </div>
                    )}
                  </div>

                  {/* Controls */}
                  <div className="flex justify-center gap-3">
                    <button
                      onClick={toggleMic}
                      className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 active:scale-95 ${
                        micOn
                          ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                          : "glass-card text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {micOn ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={toggleCam}
                      className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 active:scale-95 ${
                        camOn
                          ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                          : "glass-card text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {camOn ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={isSharing ? () => {
                        screenStreamRef.current?.getTracks().forEach((t) => t.stop());
                        setIsSharing(false);
                        if (screenVideoRef.current) screenVideoRef.current.srcObject = null;
                      } : startScreenShare}
                      className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 active:scale-95 ${
                        isSharing
                          ? "bg-red-500 text-white shadow-md shadow-red-500/20"
                          : "glass-card text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <Monitor className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="flex justify-center gap-4 pt-2">
                    <Button variant="outline" size="lg" onClick={() => setStep(1)}>
                      <ArrowLeft className="w-4 h-4 mr-1" />
                      Back
                    </Button>
                    <Button
                      variant="hero"
                      size="lg"
                      disabled={!isSharing}
                      onClick={() => {
                        handedOffToSession.current = true;
                        sessionStore.camStream = camStreamRef.current;
                        sessionStore.screenStream = screenStreamRef.current;
                        sessionStore.micOn = micOn;
                        sessionStore.camOn = camOn;
                        navigate("/session");
                      }}
                    >
                      Begin Session
                      <ArrowRight className="w-4 h-4 ml-1" />
                    </Button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default StartLearningPage;
