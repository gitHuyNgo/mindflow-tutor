import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Video, VideoOff, Scan, Send, LogOut } from "lucide-react";
import { sessionStore } from "@/lib/sessionStore";

type Message = {
  id: string;
  role: "user" | "ai";
  content: string;
};

const SESSION_DURATION = 30 * 60;

// Document PIP support detection
const supportsDocPiP = "documentPictureInPicture" in window;

const SessionPage = () => {
  const navigate = useNavigate();

  const [sessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [micOn, setMicOn] = useState(sessionStore.micOn);
  const [camOn, setCamOn] = useState(sessionStore.camOn);
  const [timeLeft, setTimeLeft] = useState(SESSION_DURATION);
  const [isPiP, setIsPiP] = useState(false);

  const camStreamRef = useRef<MediaStream | null>(sessionStore.camStream);
  const screenStreamRef = useRef<MediaStream | null>(sessionStore.screenStream);
  const pipWindowRef = useRef<Window | null>(null);

  // Camera video — ALWAYS in DOM, visibility via CSS (PIP requirement: must be playing)
  const camVideoRef = useRef<HTMLVideoElement>(null);
  // Screen video — offscreen, for canvas frame capture only
  const screenCaptureRef = useRef<HTMLVideoElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const addMessage = useCallback((role: "user" | "ai", content: string) => {
    setMessages(prev => [...prev, { id: crypto.randomUUID(), role, content }]);
  }, []);

  const analyzeScreen = useCallback(async (silent = false) => {
    const video = screenCaptureRef.current;
    if (!video || !screenStreamRef.current) return;
    if (!silent) addMessage("user", "Phân tích màn hình hiện tại giúp mình.");
    setIsLoading(true);
    try {
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      canvas.getContext("2d")!.drawImage(video, 0, 0);
      const base64 = canvas.toDataURL("image/jpeg", 0.7).split(",")[1];
      const res = await fetch("/api/v1/process-trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screen_capture: base64, session_id: sessionId }),
      });
      const data = await res.json();
      addMessage("ai", data.text_response);
    } catch {
      addMessage("ai", "Mình chưa đọc được màn hình lúc này, thử lại nhé.");
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, addMessage]);

  // Mount: attach streams, register PIP events, greet + auto-analyze
  useEffect(() => {
    const camVideo = camVideoRef.current;
    const screenVideo = screenCaptureRef.current;

    // Attach camera stream — video must be playing for PIP to work
    if (camVideo && camStreamRef.current) {
      camVideo.srcObject = camStreamRef.current;
      camVideo.play().catch(() => {});
    }
    if (screenVideo && screenStreamRef.current) {
      screenVideo.srcObject = screenStreamRef.current;
      screenVideo.play().catch(() => {});
    }

    // PIP state tracking via native events
    const onEnterPiP = () => setIsPiP(true);
    const onLeavePiP = () => { setIsPiP(false); };
    camVideo?.addEventListener("enterpictureinpicture", onEnterPiP);
    camVideo?.addEventListener("leavepictureinpicture", onLeavePiP);

    // Greeting + auto-analyze
    addMessage("ai", "Mình đã sẵn sàng! Đang phân tích màn hình của bạn...");
    setIsLoading(true);
    const t = setTimeout(() => analyzeScreen(true), 800);

    return () => {
      clearTimeout(t);
      camVideo?.removeEventListener("enterpictureinpicture", onEnterPiP);
      camVideo?.removeEventListener("leavepictureinpicture", onLeavePiP);
      camStreamRef.current?.getTracks().forEach(t => t.stop());
      screenStreamRef.current?.getTracks().forEach(t => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-attach camera stream when camOn toggles
  useEffect(() => {
    const video = camVideoRef.current;
    if (!video) return;
    if (camOn && camStreamRef.current) {
      video.srcObject = camStreamRef.current;
      video.play().catch(() => {});
    } else if (!camOn) {
      video.srcObject = null;
    }
  }, [camOn]);

  // visibilitychange → open/close Document PIP (or fallback to video PIP)
  useEffect(() => {
    const onChange = async () => {
      if (document.hidden) {
        await openPiP();
      } else {
        closePiP();
      }
    };
    document.addEventListener("visibilitychange", onChange);
    return () => document.removeEventListener("visibilitychange", onChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Countdown
  useEffect(() => {
    if (timeLeft <= 0) return;
    const id = setTimeout(() => setTimeLeft(t => t - 1), 1000);
    return () => clearTimeout(id);
  }, [timeLeft]);

  // Scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;
    addMessage("user", text);
    setInputText("");
    setIsLoading(true);
    try {
      const res = await fetch(
        `/api/v1/ask?question=${encodeURIComponent(text)}&session_id=${sessionId}`,
        { method: "POST" }
      );
      const data = await res.json();
      addMessage("ai", data.text_response);
    } catch {
      addMessage("ai", "Lỗi kết nối, thử lại nhé.");
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, sessionId, addMessage]);

  const endSession = useCallback(() => {
    closePiP();
    camStreamRef.current?.getTracks().forEach(t => t.stop());
    screenStreamRef.current?.getTracks().forEach(t => t.stop());
    navigate("/");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  // ── Document PIP (Chrome 116+) with vanilla HTML in PIP window ──
  // Avoids React cross-document portal issues. Event handlers close over React setters.
  const openPiP = useCallback(async () => {
    if (pipWindowRef.current) return; // already open

    if (supportsDocPiP) {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const pipWin: Window = await (window as any).documentPictureInPicture.requestWindow({
          width: 340,
          height: 280,
          disallowReturnToOpener: false,
        });
        pipWindowRef.current = pipWin;

        // Copy Tailwind / app styles into PIP document
        [...document.styleSheets].forEach(ss => {
          try {
            const css = [...ss.cssRules].map(r => r.cssText).join("");
            const el = pipWin.document.createElement("style");
            el.textContent = css;
            pipWin.document.head.appendChild(el);
          } catch {
            if ((ss as CSSStyleSheet).href) {
              const link = pipWin.document.createElement("link");
              link.rel = "stylesheet";
              link.href = (ss as CSSStyleSheet).href!;
              pipWin.document.head.appendChild(link);
            }
          }
        });

        // Build PIP UI — Google Meet style
        const body = pipWin.document.body;
        body.style.cssText = "margin:0;padding:0;background:#111827;overflow:hidden;font-family:system-ui,sans-serif";
        body.innerHTML = `
          <div style="display:flex;flex-direction:column;height:100dvh;position:relative;user-select:none">
            <video id="pip-cam" autoplay playsinline muted
              style="flex:1;width:100%;object-fit:cover;transform:scaleX(-1);background:#000;display:block">
            </video>
            <div style="
              position:absolute;bottom:0;left:0;right:0;
              padding:10px 12px 12px;
              background:linear-gradient(to top,rgba(0,0,0,0.75) 0%,transparent 100%);
              display:flex;align-items:center;gap:8px">
              <span style="font-size:11px;color:rgba(255,255,255,0.6);font-weight:500;flex:1">
                🤖 Mind Tutor
              </span>
              <button id="pip-mic"
                style="width:38px;height:38px;border-radius:50%;border:none;cursor:pointer;
                       font-size:15px;background:rgba(255,255,255,0.18);transition:background .15s"
                title="Mic">🎤</button>
              <button id="pip-cam-btn"
                style="width:38px;height:38px;border-radius:50%;border:none;cursor:pointer;
                       font-size:15px;background:rgba(255,255,255,0.18)"
                title="Camera">📹</button>
              <button id="pip-end"
                style="width:38px;height:38px;border-radius:50%;border:none;cursor:pointer;
                       font-size:15px;background:#ef4444;color:white;font-weight:bold"
                title="Kết thúc">✕</button>
            </div>
          </div>`;

        // Attach camera stream to PIP video element
        const pipVideo = pipWin.document.getElementById("pip-cam") as HTMLVideoElement;
        if (camStreamRef.current) {
          pipVideo.srcObject = camStreamRef.current;
          pipVideo.play().catch(() => {});
        }

        // Wire buttons — closures over stable React state setters
        pipWin.document.getElementById("pip-mic")?.addEventListener("click", () => setMicOn(p => !p));
        pipWin.document.getElementById("pip-cam-btn")?.addEventListener("click", () => setCamOn(p => !p));
        pipWin.document.getElementById("pip-end")?.addEventListener("click", () => {
          pipWindowRef.current?.close();
          pipWindowRef.current = null;
          setIsPiP(false);
          camStreamRef.current?.getTracks().forEach(t => t.stop());
          screenStreamRef.current?.getTracks().forEach(t => t.stop());
          navigate("/");
        });

        pipWin.addEventListener("pagehide", () => {
          pipWindowRef.current = null;
          setIsPiP(false);
        });

        setIsPiP(true);
        return;
      } catch (e) {
        console.warn("Document PiP failed, falling back to video PiP:", e);
      }
    }

    // Fallback: native video PIP (requires cam video to be playing)
    const video = camVideoRef.current;
    if (!video || !document.pictureInPictureEnabled) return;
    if (!video.srcObject && camStreamRef.current) {
      video.srcObject = camStreamRef.current;
      await video.play().catch(() => {});
    }
    if (video.readyState < 2) {
      await new Promise<void>(res => video.addEventListener("canplay", () => res(), { once: true }));
    }
    try {
      await video.requestPictureInPicture();
    } catch (e) {
      console.warn("Video PiP failed:", e);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  const closePiP = useCallback(() => {
    if (pipWindowRef.current) {
      pipWindowRef.current.close();
      pipWindowRef.current = null;
    }
    if (document.pictureInPictureElement) {
      document.exitPictureInPicture().catch(() => {});
    }
    setIsPiP(false);
  }, []);

  const formatTime = (s: number) =>
    `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;

  const isLowTime = timeLeft <= 5 * 60;

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">

      {/* Screen capture video — offscreen, only for canvas frame grab */}
      <video
        ref={screenCaptureRef}
        autoPlay
        playsInline
        muted
        style={{ position: "fixed", width: 1, height: 1, opacity: 0, pointerEvents: "none", top: -10, left: -10 }}
      />

      {/* ── Top bar ── */}
      <header className="nav-glass shrink-0 flex items-center gap-3 px-5 h-[3.4rem] z-10">
        <div className="gold-dot" />
        <span className="font-semibold text-white text-[15px]">Mind Tutor</span>

        {/* Live dot */}
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[11px] text-white/40">Live</span>
        </div>

        <div className="flex-1" />

        {/* Timer */}
        <span className={`text-[12px] font-mono tabular-nums transition-colors ${
          isLowTime ? "text-red-400" : "text-white/40"
        }`}>
          {isLowTime && "⚠ "}{formatTime(timeLeft)}
        </span>

        {/* PIP button — user gesture to open Document PIP (Chrome) */}
        {camOn && (
          <button
            onClick={isPiP ? closePiP : openPiP}
            title={isPiP ? "Quay lại phiên" : "Tách sang tab khác (PiP)"}
            className="text-[11px] text-white/35 hover:text-white/70 transition-colors px-2 py-1 rounded-lg hover:bg-white/8"
          >
            {isPiP ? "↩ Quay lại" : "⧉ Tách màn"}
          </button>
        )}

        {/* End session */}
        <button
          onClick={endSession}
          title="Kết thúc"
          className="flex items-center gap-1.5 text-[12px] text-white/35 hover:text-red-400 transition-colors px-2 py-1 rounded-lg hover:bg-red-500/8"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Rời phiên</span>
        </button>
      </header>

      {/* ── Chat area ── */}
      <div className="flex-1 relative overflow-hidden">
        <div className="h-full overflow-y-auto px-6 py-6">
          <div className="max-w-2xl mx-auto space-y-5">

            <AnimatePresence initial={false}>
              {messages.map(msg => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.22 }}
                  className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "ai" && (
                    <div className="w-7 h-7 rounded-full bg-primary/25 border border-primary/30 flex items-center justify-center shrink-0 mt-0.5">
                      <span className="text-[11px] leading-none">🤖</span>
                    </div>
                  )}
                  <div className={`max-w-[72%] rounded-2xl px-4 py-2.5 text-[13.5px] leading-relaxed ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground rounded-br-sm"
                      : "glass-card text-foreground rounded-bl-sm"
                  }`}>
                    {msg.content}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Typing dots */}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-3 justify-start"
              >
                <div className="w-7 h-7 rounded-full bg-primary/25 border border-primary/30 flex items-center justify-center shrink-0">
                  <span className="text-[11px] leading-none">🤖</span>
                </div>
                <div className="glass-card rounded-2xl rounded-bl-sm px-4 py-3 flex gap-1.5 items-center">
                  {[0, 130, 260].map(d => (
                    <div
                      key={d}
                      className="w-1.5 h-1.5 rounded-full bg-primary/50 animate-bounce"
                      style={{ animationDelay: `${d}ms` }}
                    />
                  ))}
                </div>
              </motion.div>
            )}

            <div ref={chatEndRef} />
          </div>
        </div>

        {/* Camera corner widget — ALWAYS in DOM (PIP requirement).
            Visibility controlled by CSS only, never unmounted. */}
        <div
          className={`absolute bottom-4 right-4 w-32 h-24 rounded-xl overflow-hidden shadow-lg border border-white/15 bg-black/40 transition-opacity duration-200 ${
            camOn && !isPiP ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
          }`}
        >
          <video
            ref={camVideoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover scale-x-[-1]"
          />
          {/* PIP trigger button */}
          <button
            onClick={isPiP ? closePiP : openPiP}
            title="Sang tab khác → camera nổi theo"
            className="absolute top-1 right-1 w-5 h-5 rounded bg-black/50 flex items-center justify-center text-white/60 hover:text-white/90 text-[9px] transition-colors"
          >
            ⧉
          </button>
        </div>
      </div>

      {/* ── Bottom input bar ── */}
      <div className="shrink-0 border-t border-border/25 bg-background/95 backdrop-blur-sm px-6 py-3">
        <div className="max-w-2xl mx-auto space-y-2">

          {/* Controls row */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setMicOn(p => !p)}
              title={micOn ? "Tắt mic" : "Bật mic"}
              className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all active:scale-90 ${
                micOn ? "bg-primary text-primary-foreground" : "glass-card text-muted-foreground hover:text-foreground"
              }`}
            >
              {micOn ? <Mic className="w-3.5 h-3.5" /> : <MicOff className="w-3.5 h-3.5" />}
            </button>

            <button
              onClick={() => setCamOn(p => !p)}
              title={camOn ? "Tắt camera" : "Bật camera"}
              className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all active:scale-90 ${
                camOn ? "bg-primary text-primary-foreground" : "glass-card text-muted-foreground hover:text-foreground"
              }`}
            >
              {camOn ? <Video className="w-3.5 h-3.5" /> : <VideoOff className="w-3.5 h-3.5" />}
            </button>

            <div className="w-px h-4 bg-border/50 mx-1" />

            <button
              onClick={() => analyzeScreen()}
              disabled={isLoading || !screenStreamRef.current}
              className="flex items-center gap-1.5 h-8 px-3 rounded-lg glass-card text-muted-foreground hover:text-foreground text-[12px] font-medium transition-all disabled:opacity-35 disabled:cursor-not-allowed"
            >
              <Scan className="w-3.5 h-3.5" />
              Phân tích màn hình
            </button>

            <div className="flex-1" />

            {/* Guest badge */}
            <span className="text-[11px] text-amber-400/50">⚠</span>
            <span className="text-[11px] text-muted-foreground/40">Khách ·</span>
            <button
              onClick={() => navigate("/login")}
              className="text-[11px] text-primary/50 hover:text-primary/80 transition-colors"
            >
              Đăng ký
            </button>
          </div>

          {/* Input row */}
          <div className="flex gap-2 items-center">
            <input
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter") { e.preventDefault(); sendMessage(inputText); }
              }}
              placeholder="Nhập câu hỏi... (Enter để gửi)"
              className="flex-1 h-10 rounded-xl bg-white/5 border border-border/40 px-4 text-[13px] text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/40 transition-colors"
            />
            <button
              onClick={() => sendMessage(inputText)}
              disabled={!inputText.trim() || isLoading}
              className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-primary-foreground disabled:opacity-35 disabled:cursor-not-allowed transition-all active:scale-95"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SessionPage;
