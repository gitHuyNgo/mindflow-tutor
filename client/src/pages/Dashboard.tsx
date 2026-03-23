import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mic, Video, VideoOff, Scan, Send, AlertTriangle,
  Volume2, VolumeX, ScreenShare, ScreenShareOff,
  Upload, X, FileText, Loader2,
  ChevronDown, User, LogOut, BookOpen, Info, Plus,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { saveSession } from "./SessionUser";
import ProfilePanel from "@/components/ProfilePanel";
import { captureScreenFrame } from "@/lib/captureScreen";

/* ────────── types ────────── */
type Message = {
  id: string;
  role: "user" | "ai";
  content: string;
  imageBase64?: string;
};
type FileStatus = "uploading" | "processing" | "ready" | "error";
type DocFile    = { id: string; docId?: string; name: string; size: number; status: FileStatus; error?: string };

const SESSION_DURATION = 30 * 60;
const supportsDocPiP   = "documentPictureInPicture" in window;

type PipBridge = {
  updateMessages:  (msgs: Message[], loading: boolean) => void;
  updateControls:  (cam: boolean) => void;
  updateAudio:     (on: boolean) => void;
  updateScreen:    (on: boolean) => void;
  updateRecording: (rec: boolean) => void;
};

/* ────────── StatusBadge ────────── */
const STATUS_CFG: Record<FileStatus, { label: string; color: string; bg: string; ring: string }> = {
  uploading:  { label: "Uploading",  color: "rgba(96,165,250,.95)",  bg: "rgba(96,165,250,.1)",  ring: "rgba(96,165,250,.28)"  },
  processing: { label: "Processing", color: "rgba(251,191,36,.95)",  bg: "rgba(251,191,36,.1)",  ring: "rgba(251,191,36,.28)"  },
  ready:      { label: "Ready",      color: "rgba(52,211,153,.95)",  bg: "rgba(52,211,153,.1)",  ring: "rgba(52,211,153,.28)"  },
  error:      { label: "Error",      color: "rgba(248,113,113,.95)", bg: "rgba(248,113,113,.1)", ring: "rgba(248,113,113,.28)" },
};
const StatusBadge = ({ status }: { status: FileStatus }) => {
  const { label, color, bg, ring } = STATUS_CFG[status];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 8px", borderRadius: 20, flexShrink: 0,
      background: bg, border: `1px solid ${ring}`,
      color, fontSize: 10, fontWeight: 600, letterSpacing: "0.03em", whiteSpace: "nowrap",
    }}>
      {status !== "ready"
        ? <Loader2 style={{ width: 9, height: 9, animation: "spin 1s linear infinite" }} />
        : <span style={{ width: 6, height: 6, borderRadius: "50%", background: color, display: "inline-block" }} />}
      {label}
    </span>
  );
};

/* ────────── Dashboard ────────── */
const DashboardPage = () => {
  const { user, isLoading: authLoading, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const locState = (location.state || {}) as { sessionId?: string; subject?: string; title?: string };

  /* ── Auth guard ── */
  useEffect(() => {
    if (!authLoading && !isAuthenticated) navigate("/login", { replace: true });
  }, [authLoading, isAuthenticated, navigate]);

  /* ── State (mirrors Session.tsx) ── */
  const [sessionId] = useState(() => locState.sessionId ?? crypto.randomUUID());
  const [messages, setMessages]       = useState<Message[]>([]);
  const [inputText, setInputText]     = useState("");
  const [isLoading, setIsLoading]     = useState(false);
  const [camOn, setCamOn]             = useState(false);
  const [audioOn, setAudioOn]         = useState(true);
  const [screenOn, setScreenOn]       = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [detectorState, setDetectorState] = useState<null | "confused" | "distracted">(null);
  const [timeLeft, setTimeLeft]       = useState(SESSION_DURATION);
  const [isPiP, setIsPiP]             = useState(false);
  const [menuOpen, setMenuOpen]       = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [sessionStarted, setSessionStarted] = useState(false);

  /* ── Document state ── */
  const [primaryFile, setPrimary]  = useState<DocFile | null>(null);
  const [supportFiles, setSupport] = useState<DocFile[]>([]);
  const [dragOver, setDragOver]    = useState<"primary" | "supporting" | null>(null);

  /* ── Refs (mirrors Session.tsx) ── */
  const camStreamRef    = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const pipWindowRef    = useRef<Window | null>(null);
  const pipBridgeRef    = useRef<PipBridge | null>(null);

  const sendMessageRef  = useRef<(text: string) => void>(() => {});
  const endSessionRef   = useRef<() => void>(() => {});
  const messagesRef     = useRef<Message[]>([]);
  const isLoadingRef    = useRef(false);
  const audioOnRef      = useRef(true);
  messagesRef.current   = messages;
  isLoadingRef.current  = isLoading;
  audioOnRef.current    = audioOn;
  const screenOnRef     = useRef(false);
  screenOnRef.current   = screenOn;
  const isRecordingRef  = useRef(false);
  isRecordingRef.current = isRecording;

  const camVideoRef       = useRef<HTMLVideoElement>(null);
  const screenCaptureRef  = useRef<HTMLVideoElement>(null);
  const setupCamPipRef    = useRef<HTMLVideoElement>(null);
  const chatEndRef        = useRef<HTMLDivElement>(null);
  const currentAudioRef   = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef  = useRef<MediaRecorder | null>(null);
  const audioChunksRef    = useRef<Blob[]>([]);
  const primaryInpRef     = useRef<HTMLInputElement>(null);
  const supportInpRef     = useRef<HTMLInputElement>(null);

  /* ── playAudio (same as Session.tsx) ── */
  const playAudio = useCallback((base64: string) => {
    if (!audioOnRef.current) return;
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    const audio = new Audio(`data:audio/mpeg;base64,${base64}`);
    currentAudioRef.current = audio;
    audio.play().catch(() => {});
    audio.onended = () => { currentAudioRef.current = null; };
  }, []);

  /* ── switchScreen (same as Session.tsx) ── */
  const switchScreen = useCallback(async () => {
    try {
      screenStreamRef.current?.getTracks().forEach(t => t.stop());
      const newStream = await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 15 }, audio: false });
      screenStreamRef.current = newStream;
      const screenVideo = screenCaptureRef.current;
      if (screenVideo) {
        screenVideo.srcObject = newStream;
        screenVideo.play().catch(() => {});
      }
      setScreenOn(true);
      newStream.getVideoTracks()[0].addEventListener("ended", () => {
        screenStreamRef.current = null;
        setScreenOn(false);
      });
    } catch { /* user cancelled */ }
  }, []);
  const switchScreenRef = useRef<() => Promise<void>>(async () => {});
  switchScreenRef.current = switchScreen;

  /* ── toggleRecording / STT (same as Session.tsx) ── */
  const toggleRecording = useCallback(async () => {
    if (isRecordingRef.current) {
      mediaRecorderRef.current?.stop();
      return;
    }
    try {
      const stream   = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4";
      const recorder = new MediaRecorder(stream, { mimeType });
      audioChunksRef.current = [];
      recorder.ondataavailable = e => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        setIsRecording(false);
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
        if (blob.size < 500) return;
        const fd = new FormData();
        fd.append("audio", blob, mimeType === "audio/webm" ? "audio.webm" : "audio.mp4");
        try {
          const res  = await fetch("/api/v1/stt", { method: "POST", body: fd });
          const data = await res.json();
          if (data.text?.trim()) sendMessageRef.current(data.text.trim());
        } catch { /* silent */ }
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch { /* permission denied */ }
  }, []);
  const toggleRecordingRef = useRef<() => void>(() => {});
  toggleRecordingRef.current = toggleRecording;

  /* ── Load DM Sans + Material Symbols Rounded (same as Session.tsx) ── */
  useEffect(() => {
    const link = document.createElement("link");
    link.rel  = "stylesheet";
    link.href = "https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20,400,1,0&display=swap";
    document.head.appendChild(link);
    return () => { document.head.removeChild(link); };
  }, []);

  /* ── addMessage (same as Session.tsx) ── */
  const addMessage = useCallback((role: "user" | "ai", content: string, imageBase64?: string) => {
    setMessages(prev => {
      const next = [...prev, { id: crypto.randomUUID(), role, content, imageBase64 }];
      pipBridgeRef.current?.updateMessages(next, false);
      return next;
    });
  }, []);

  /* ── analyzeScreen (same as Session.tsx) ── */
  const analyzeScreen = useCallback(async (silent = false) => {
    const video = screenCaptureRef.current;
    if (!video || !screenStreamRef.current) return;
    if (!silent) addMessage("user", "Analyze my current screen.");
    setIsLoading(true);
    pipBridgeRef.current?.updateMessages(messagesRef.current, true);
    try {
      const canvas = document.createElement("canvas");
      canvas.width  = video.videoWidth  || 1280;
      canvas.height = video.videoHeight || 720;
      canvas.getContext("2d")!.drawImage(video, 0, 0);
      const base64 = canvas.toDataURL("image/jpeg", 0.7).split(",")[1];
      const res  = await fetch("/api/v1/process-trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screen_capture: base64, session_id: sessionId }),
      });
      const data = await res.json();
      addMessage("ai", data.text_response);
      if (data.audio_base64) playAudio(data.audio_base64);
    } catch {
      addMessage("ai", "Couldn't read the screen right now. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, addMessage, playAudio]);

  /* ── sendMessage (same as Session.tsx, with detector ack) ── */
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;
    setInputText("");
    addMessage("user", text);

    if (detectionAckTypeRef.current) {
      const ackType = detectionAckTypeRef.current;
      detectionAckTypeRef.current = null;
      const capturedFrame = pendingConfusionFrameRef.current;
      pendingConfusionFrameRef.current = null;

      if (ackType === "explained") {
        // AI already explained — check if user fully understands now
        let fullyUnderstood = false;
        try {
          const r = await fetch("/api/v1/utils/classify-intent", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, intent: "the user fully understands the topic now and has no more questions" }),
          });
          fullyUnderstood = (await r.json()).match === true;
        } catch { }
        if (fullyUnderstood) {
          // Resume detector
          if (detectorResumeTimerRef.current) clearTimeout(detectorResumeTimerRef.current);
          detectorPausedRef.current = false;
          setDetectorState(null);
          const ackMsg = "Nice, we figured it out together 🙌";
          addMessage("ai", ackMsg);
          fetch(`/api/v1/tts/generate?text=${encodeURIComponent(ackMsg)}`, { method: "POST" })
            .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});
          return;
        }
        // Not fully understood yet → keep detector paused, answer normally (with RAG)
        detectionAckTypeRef.current = "explained";

      } else if (ackType === "distraction") {
        // Resume detector after a delay
        if (detectorResumeTimerRef.current) clearTimeout(detectorResumeTimerRef.current);
        detectorResumeTimerRef.current = setTimeout(() => {
          detectorPausedRef.current = false;
          setDetectorState(null);
          detectorResumeTimerRef.current = null;
        }, 4000);
        let isAck = false;
        try {
          const r = await fetch("/api/v1/utils/classify-intent", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, intent: "the user is acknowledging they were distracted and will refocus on studying" }),
          });
          isAck = (await r.json()).match === true;
        } catch { }
        if (isAck) {
          const ackMsg = "That's the spirit! Let's keep going 💪";
          addMessage("ai", ackMsg);
          fetch(`/api/v1/tts/generate?text=${encodeURIComponent(ackMsg)}`, { method: "POST" })
            .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});
          return;
        }
        // Not ack → fall through to normal ask (with RAG)

      } else {
        // confusion: send captured frame + user message → AI explains
        if (capturedFrame) {
          setIsLoading(true);
          try {
            const res = await fetch("/api/v1/process-trigger", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ screen_capture: capturedFrame, session_id: sessionId, user_query: text }),
            });
            const data = await res.json();
            addMessage("ai", data.text_response);
            if (data.audio_base64) playAudio(data.audio_base64);
            // Keep detector paused — wait to see if user fully understands
            detectionAckTypeRef.current = "explained";
          } catch {
            addMessage("ai", "Connection error. Please try again.");
            detectorPausedRef.current = false;
            setDetectorState(null);
          } finally {
            setIsLoading(false);
          }
          return;
        }
        // No frame → resume detector and fall through to normal ask (with RAG)
        if (detectorResumeTimerRef.current) clearTimeout(detectorResumeTimerRef.current);
        detectorResumeTimerRef.current = setTimeout(() => {
          detectorPausedRef.current = false;
          setDetectorState(null);
          detectorResumeTimerRef.current = null;
        }, 4000);
      }
    }

    setIsLoading(true);
    try {
      const res  = await fetch(`/api/v1/ask?question=${encodeURIComponent(text)}&session_id=${sessionId}`, { method: "POST" });
      const data = await res.json();
      addMessage("ai", data.text_response);
      if (data.audio_base64) playAudio(data.audio_base64);
    } catch {
      addMessage("ai", "Connection error. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, sessionId, addMessage, playAudio]);
  sendMessageRef.current = sendMessage;

  /* ── closePiP (same as Session.tsx) ── */
  const closePiP = useCallback(() => {
    pipWindowRef.current?.close();
    pipWindowRef.current = null;
    pipBridgeRef.current = null;
    if (document.pictureInPictureElement) document.exitPictureInPicture().catch(() => {});
    setIsPiP(false);
  }, []);

  /* ── Persist session to localStorage ── */
  useEffect(() => {
    saveSession({
      id: sessionId,
      title: locState.title || locState.subject || "Study Session",
      subject: locState.subject || "",
      createdAt: new Date().toISOString(),
      messageCount: messages.filter(m => m.role === "user").length,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length]);

  /* ── Register session in MongoDB when session starts ── */
  useEffect(() => {
    if (!sessionStarted) return;
    fetch("/api/v1/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        title: locState.title || locState.subject || "Study Session",
        subject: locState.subject || "",
      }),
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionStarted]);

  /* ── endSession — goes to home, stops streams ── */
  const endSession = useCallback(() => {
    currentAudioRef.current?.pause();
    if (detectorResumeTimerRef.current) clearTimeout(detectorResumeTimerRef.current);
    closePiP();
    camStreamRef.current?.getTracks().forEach(t => t.stop());
    screenStreamRef.current?.getTracks().forEach(t => t.stop());
    navigate("/");
  }, [navigate, closePiP]);
  endSessionRef.current = endSession;

  /* ── Auto-start: latch sessionStarted when cam + screen both ready ── */
  useEffect(() => {
    if (!sessionStarted && camOn && screenOn) {
      setSessionStarted(true);
    }
  }, [camOn, screenOn, sessionStarted]);

  /* ── Re-wire streams to hidden video elements when dashboard mounts ── */
  useEffect(() => {
    if (!sessionStarted) return;
    const camVideo = camVideoRef.current;
    if (camVideo && camStreamRef.current) {
      camVideo.srcObject = camStreamRef.current;
      camVideo.play().catch(() => {});
    }
    const screenVideo = screenCaptureRef.current;
    if (screenVideo && screenStreamRef.current) {
      screenVideo.srcObject = screenStreamRef.current;
      screenVideo.play().catch(() => {});
    }
  }, [sessionStarted]);

  /* ── Wire PiP cam preview in setup screen ── */
  useEffect(() => {
    const pip = setupCamPipRef.current;
    if (pip && camStreamRef.current) {
      pip.srcObject = camStreamRef.current;
      pip.play().catch(() => {});
    }
  }, [camOn, screenOn]);

  /* ── Mount: initial greeting — fires once when session starts ── */
  useEffect(() => {
    if (!sessionStarted || !user) return;
    const name     = user.full_name?.split(" ")[0] || "there";
    const subject  = locState.subject ? ` Let's dive into ${locState.subject}!` : "";
    const greeting = `Hey ${name}! I'm your AI Tutor. Ask me anything!${subject}`;
    addMessage("ai", greeting);
    fetch(`/api/v1/tts/generate?text=${encodeURIComponent(greeting)}`, { method: "POST" })
      .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});
    const countdown = "In 3 seconds I'll start monitoring to help you stay focused. Let's do this! 🚀";
    const cdTimer = setTimeout(() => {
      addMessage("ai", countdown);
      fetch(`/api/v1/tts/generate?text=${encodeURIComponent(countdown)}`, { method: "POST" })
        .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});
    }, 1500);
    setTimeout(() => openPiPRef.current().catch(() => {}), 300);
    return () => {
      clearTimeout(cdTimer);
      currentAudioRef.current?.pause();
      camStreamRef.current?.getTracks().forEach(t => t.stop());
      screenStreamRef.current?.getTracks().forEach(t => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionStarted, user]);

  /* ── Camera toggle: acquire stream when turned on ── */
  useEffect(() => {
    const video = camVideoRef.current;
    if (!video) return;
    if (camOn) {
      if (!camStreamRef.current) {
        navigator.mediaDevices.getUserMedia({ video: true, audio: false })
          .then(stream => {
            camStreamRef.current = stream;
            video.srcObject = stream;
            video.play().catch(() => {});
          })
          .catch(() => setCamOn(false));
      } else {
        video.srcObject = camStreamRef.current;
        video.play().catch(() => {});
      }
    } else {
      video.srcObject = null;
      camStreamRef.current?.getTracks().forEach(t => t.stop());
      camStreamRef.current = null;
    }
  }, [camOn]);

  /* ── Sync to PiP (same as Session.tsx) ── */
  useEffect(() => { pipBridgeRef.current?.updateMessages(messages, isLoading); }, [messages, isLoading]);
  useEffect(() => { pipBridgeRef.current?.updateControls(camOn); }, [camOn]);
  useEffect(() => {
    if (!audioOn) { currentAudioRef.current?.pause(); currentAudioRef.current = null; }
    pipBridgeRef.current?.updateAudio(audioOn);
  }, [audioOn]);
  useEffect(() => { pipBridgeRef.current?.updateScreen(screenOn); }, [screenOn]);
  useEffect(() => { pipBridgeRef.current?.updateRecording(isRecording); }, [isRecording]);

  /* ── Detector (same as Session.tsx) ── */
  const detectorPausedRef       = useRef(false);
  const detectorResumeTimerRef  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingConfusionFrameRef = useRef<string | null>(null);
  const detectionAckTypeRef     = useRef<"confusion" | "distraction" | "explained" | null>(null);

  useEffect(() => {
    if (!camOn) { setDetectorState(null); return; }
    const poll = async () => {
      if (detectorPausedRef.current) return;
      const video = camVideoRef.current;
      if (!video || !camStreamRef.current || video.videoWidth === 0) return;
      try {
        const canvas = document.createElement("canvas");
        canvas.width  = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d")!.drawImage(video, 0, 0);
        const base64 = canvas.toDataURL("image/jpeg", 0.5).split(",")[1];
        const res = await fetch("/api/v1/detector/frame", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image_base64: base64 }),
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data.confused) {
          setDetectorState("confused");
          detectorPausedRef.current    = true;
          detectionAckTypeRef.current  = "confusion";
          if (screenStreamRef.current) {
            pendingConfusionFrameRef.current = await captureScreenFrame(screenStreamRef.current);
          } else {
            pendingConfusionFrameRef.current = null;
          }
          const checkIn = "Hey, it looks like something might be confusing here 👀 Feel free to ask me anything!";
          addMessage("ai", checkIn);
          fetch(`/api/v1/tts/generate?text=${encodeURIComponent(checkIn)}`, { method: "POST" })
            .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});
        } else if (data.distracted) {
          setDetectorState("distracted");
          detectorPausedRef.current   = true;
          detectionAckTypeRef.current = "distraction";
          const msg = "Hey my friend, let's focus again, we can do this together 💪";
          addMessage("ai", msg);
          fetch(`/api/v1/tts/generate?text=${encodeURIComponent(msg)}`, { method: "POST" })
            .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});
        } else { setDetectorState(null); }
      } catch { /* silent */ }
    };
    const id = setInterval(poll, 2500);
    return () => { clearInterval(id); setDetectorState(null); };
  }, [camOn, addMessage, playAudio]);

  /* ── Session timer — only ticks after session started ── */
  useEffect(() => {
    if (!sessionStarted || timeLeft <= 0) return;
    const id = setTimeout(() => setTimeLeft(t => t - 1), 1000);
    return () => clearTimeout(id);
  }, [sessionStarted, timeLeft]);

  /* ── Scroll to bottom ── */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  /* ── Close user menu on outside click ── */
  useEffect(() => {
    if (!menuOpen) return;
    const h = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest("[data-user-menu]")) setMenuOpen(false);
    };
    document.addEventListener("click", h);
    return () => document.removeEventListener("click", h);
  }, [menuOpen]);

  /* ── openPiP — 100% identical to Session.tsx ── */
  const openPiP = useCallback(async () => {
    if (pipWindowRef.current) { closePiP(); return; }

    if (supportsDocPiP) {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const pipWin: Window = await (window as any).documentPictureInPicture.requestWindow({
          width: 360,
          height: 660,
          disallowReturnToOpener: false,
        });
        pipWindowRef.current = pipWin;

        [...document.styleSheets].forEach(ss => {
          try {
            const css = [...ss.cssRules].map(r => r.cssText).join("");
            const el  = pipWin.document.createElement("style");
            el.textContent = css;
            pipWin.document.head.appendChild(el);
          } catch {
            if ((ss as CSSStyleSheet).href) {
              const link = pipWin.document.createElement("link");
              link.rel   = "stylesheet";
              link.href  = (ss as CSSStyleSheet).href!;
              pipWin.document.head.appendChild(link);
            }
          }
        });

        const gFonts = pipWin.document.createElement("link");
        gFonts.rel  = "stylesheet";
        gFonts.href = "https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20,400,1,0&display=swap";
        pipWin.document.head.appendChild(gFonts);

        const style = pipWin.document.createElement("style");
        style.textContent = `
          @keyframes pip-recording {
            0%   { box-shadow:0 0 0 0 rgba(239,68,68,.6) }
            70%  { box-shadow:0 0 0 7px rgba(239,68,68,0) }
            100% { box-shadow:0 0 0 0 rgba(239,68,68,0) }
          }
          @keyframes pip-bounce {
            0%,80%,100% { transform:translateY(0);opacity:.4 }
            40%          { transform:translateY(-5px);opacity:1 }
          }
          @keyframes pip-pulse-ring {
            0%   { box-shadow:0 0 0 0 rgba(52,211,153,.4) }
            70%  { box-shadow:0 0 0 5px rgba(52,211,153,0) }
            100% { box-shadow:0 0 0 0 rgba(52,211,153,0) }
          }
          * { box-sizing:border-box }
          #pip-chat::-webkit-scrollbar { width:3px }
          #pip-chat::-webkit-scrollbar-thumb { background:rgba(255,255,255,.12);border-radius:2px }
          #pip-input::placeholder { color:rgba(255,255,255,.25) }
          #pip-input:focus { outline:none;border-color:rgba(138,180,248,.5);background:rgba(255,255,255,.09) }
          .pip-btn { transition:background .15s,transform .1s,filter .1s;display:flex;align-items:center;justify-content:center;cursor:pointer }
          .pip-btn:hover { filter:brightness(1.2) }
          .pip-btn:active { transform:scale(.88) }
          .ms { font-family:'Material Symbols Rounded';font-weight:normal;font-style:normal;
                font-size:18px;line-height:1;letter-spacing:normal;text-transform:none;
                display:inline-block;white-space:nowrap;word-wrap:normal;direction:ltr;
                -webkit-font-feature-settings:'liga';font-feature-settings:'liga';
                -webkit-font-smoothing:antialiased }
          .pip-live-dot { animation:pip-pulse-ring 2s ease infinite }
        `;
        pipWin.document.head.appendChild(style);

        const body = pipWin.document.body;
        body.style.cssText = [
          "margin:0;padding:0;overflow:hidden;color:white",
          "background:linear-gradient(160deg,#030D1A 0%,#071830 50%,#030D1A 100%)",
          "font-family:'DM Sans',system-ui,sans-serif",
        ].join(";");

        /* ── PiP HTML — identical to Session.tsx ── */
        body.innerHTML = `
          <div id="pip-root" style="display:flex;flex-direction:column;height:100dvh;overflow:hidden">

            <!-- Camera preview -->
            <div style="height:240px;position:relative;flex-shrink:0;background:#000;overflow:hidden">
              <video id="pip-cam" autoplay playsinline muted
                style="width:100%;height:100%;object-fit:cover;object-position:center top;transform:scaleX(-1);display:block">
              </video>
              <div style="position:absolute;inset:0;background:linear-gradient(to top,rgba(3,13,26,.9) 0%,rgba(3,13,26,.2) 35%,transparent 60%)"></div>
              <div style="position:absolute;inset:0;background:radial-gradient(ellipse at center,transparent 60%,rgba(3,13,26,.35) 100%)"></div>
              <div style="position:absolute;bottom:10px;left:10px;display:flex;align-items:center;gap:5px;background:rgba(3,13,26,.55);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);border-radius:20px;padding:4px 9px 4px 7px;border:1px solid rgba(255,255,255,.1)">
                <div class="pip-live-dot" style="width:6px;height:6px;border-radius:50%;background:#34d399;flex-shrink:0"></div>
                <span style="font-size:9.5px;color:rgba(255,255,255,.75);font-weight:600;letter-spacing:.06em;font-family:'DM Sans',sans-serif">LIVE</span>
              </div>
            </div>

            <!-- Chat messages -->
            <div id="pip-chat"
              style="flex:1;overflow-y:auto;padding:10px 11px 6px;display:flex;flex-direction:column;gap:8px;min-height:0">
            </div>

            <!-- Input row -->
            <div style="padding:7px 10px;display:flex;gap:6px;align-items:center;border-top:1px solid rgba(255,255,255,.06)">
              <input id="pip-input" type="text" placeholder="Ask anything..."
                style="flex:1;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);transition:border-color .15s,background .15s;
                       border-radius:24px;padding:7px 14px;color:white;font-size:12px;font-family:'DM Sans',sans-serif">
              <button id="pip-stt" class="pip-btn"
                style="width:32px;height:32px;border-radius:50%;border:none;
                       background:rgba(255,255,255,.07);color:rgba(255,255,255,.5)">
                <span class="ms" style="font-size:17px">mic</span>
              </button>
              <button id="pip-send" class="pip-btn"
                style="width:32px;height:32px;border-radius:50%;border:none;
                       background:rgba(138,180,248,.85);color:#030D1A;
                       box-shadow:0 0 12px rgba(138,180,248,.2)">
                <span class="ms" style="font-size:17px">send</span>
              </button>
            </div>

            <!-- Controls footer -->
            <div style="padding:8px 12px 13px;display:flex;align-items:center;gap:8px;border-top:1px solid rgba(255,255,255,.06);flex-shrink:0">
              <button id="pip-cam-btn" class="pip-btn" style="width:38px;height:38px;border-radius:50%;border:none"></button>
              <button id="pip-audio"   class="pip-btn" style="width:38px;height:38px;border-radius:50%;border:none"></button>
              <button id="pip-screen"  class="pip-btn" style="width:38px;height:38px;border-radius:50%;border:none"></button>
              <div style="flex:1"></div>
              <button id="pip-end" class="pip-btn"
                style="width:38px;height:38px;border-radius:50%;border:none;
                       background:rgba(239,68,68,.85);color:white;
                       box-shadow:0 0 12px rgba(239,68,68,.25)">
                <span class="ms" style="font-size:18px">call_end</span>
              </button>
            </div>
          </div>`;

        /* Attach camera stream */
        const pipCamVideo = pipWin.document.getElementById("pip-cam") as HTMLVideoElement;
        if (camStreamRef.current) {
          pipCamVideo.srcObject = camStreamRef.current;
          pipCamVideo.play().catch(() => {});
        }

        /* Bridge: messages */
        const chatEl    = pipWin.document.getElementById("pip-chat")!;
        const renderMsg = (m: Message) => {
          const isUser  = m.role === "user";
          const imgHtml = m.imageBase64
            ? `<img src="data:image/jpeg;base64,${m.imageBase64}" style="width:100%;border-radius:8px;margin-bottom:6px;object-fit:contain;max-height:120px;border:1px solid rgba(255,255,255,.1);background:rgba(0,0,0,.3);display:block">`
            : "";
          return `<div style="display:flex;gap:6px;justify-content:${isUser ? "flex-end" : "flex-start"};align-items:flex-end">
            ${!isUser ? `<div style="width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,rgba(138,180,248,.35),rgba(138,180,248,.12));border:1px solid rgba(138,180,248,.35);display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 0 10px rgba(138,180,248,.15)"><span class="ms" style="font-size:14px;color:rgba(138,180,248,.9)">smart_toy</span></div>` : ""}
            <div style="max-width:83%;
              background:${isUser ? "rgba(138,180,248,.2)" : "rgba(138,180,248,.07)"};
              border:1px solid ${isUser ? "rgba(138,180,248,.32)" : "rgba(138,180,248,.18)"};
              color:rgba(255,255,255,${isUser ? ".95" : ".9"});
              border-radius:18px;padding:6px 11px;font-size:14.5px;line-height:1.55;
              font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;letter-spacing:0.01em;
              border-bottom-${isUser ? "right" : "left"}-radius:4px${isUser ? ";box-shadow:0 2px 10px rgba(138,180,248,.1)" : ""}">
              ${imgHtml}${m.content}
            </div>
          </div>`;
        };

        const updateMessages = (msgs: Message[], loading: boolean) => {
          const last3 = msgs.slice(-3);
          chatEl.innerHTML = last3.map(renderMsg).join("") + (loading ? `
            <div style="display:flex;gap:6px;align-items:flex-end">
              <div style="width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,rgba(138,180,248,.35),rgba(138,180,248,.12));border:1px solid rgba(138,180,248,.35);display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 0 10px rgba(138,180,248,.15)"><span class="ms" style="font-size:14px;color:rgba(138,180,248,.9)">smart_toy</span></div>
              <div style="background:rgba(138,180,248,.07);border:1px solid rgba(138,180,248,.18);border-radius:18px;border-bottom-left-radius:4px;padding:9px 13px;display:flex;gap:4px;align-items:center">
                ${[0, 160, 320].map(d => `<span style="width:5px;height:5px;border-radius:50%;background:rgba(138,180,248,.7);display:inline-block;animation:pip-bounce 1.2s ${d}ms infinite"></span>`).join("")}
              </div>
            </div>` : "");
          chatEl.scrollTop = chatEl.scrollHeight;
        };

        /* Bridge: controls */
        const camBtn   = pipWin.document.getElementById("pip-cam-btn")!;
        const audioBtn = pipWin.document.getElementById("pip-audio")!;
        const screenBtn = pipWin.document.getElementById("pip-screen")!;
        const sttBtn   = pipWin.document.getElementById("pip-stt")!;
        const pipInput = pipWin.document.getElementById("pip-input") as HTMLInputElement;

        const updateControls = (cam: boolean) => {
          camBtn.style.background = cam ? "rgba(138,180,248,.85)" : "rgba(239,68,68,.75)";
          camBtn.style.color      = cam ? "#030D1A" : "white";
          camBtn.innerHTML        = `<span class="ms">${cam ? "videocam" : "videocam_off"}</span>`;
        };
        const updateAudio = (on: boolean) => {
          audioBtn.style.background = on ? "rgba(138,180,248,.85)" : "rgba(239,68,68,.75)";
          audioBtn.style.color      = on ? "#030D1A" : "white";
          audioBtn.innerHTML        = `<span class="ms">${on ? "volume_up" : "volume_off"}</span>`;
        };
        const updateScreen = (on: boolean) => {
          screenBtn.style.background = on ? "rgba(138,180,248,.85)" : "rgba(255,255,255,.07)";
          screenBtn.style.color      = on ? "#030D1A" : "rgba(255,255,255,.5)";
          screenBtn.innerHTML        = `<span class="ms">${on ? "screen_share" : "stop_screen_share"}</span>`;
        };
        const updateRecording = (rec: boolean) => {
          sttBtn.style.background = rec ? "rgba(239,68,68,.85)" : "rgba(255,255,255,.07)";
          sttBtn.style.color      = rec ? "white" : "rgba(255,255,255,.5)";
          sttBtn.style.animation  = rec ? "pip-recording 1s ease infinite" : "none";
          pipInput.placeholder    = rec ? "Listening..." : "Ask anything...";
          pipInput.disabled       = rec;
        };

        pipBridgeRef.current = { updateMessages, updateControls, updateAudio, updateScreen, updateRecording };

        updateMessages(messagesRef.current, isLoadingRef.current);
        updateControls(camOn);
        updateAudio(audioOnRef.current);
        updateScreen(screenOnRef.current);
        updateRecording(isRecordingRef.current);

        /* Wire buttons */
        camBtn.addEventListener("click", () => setCamOn(p => !p));
        audioBtn.addEventListener("click", () => setAudioOn(p => !p));
        screenBtn.addEventListener("click", () => switchScreenRef.current());
        sttBtn.addEventListener("click", () => toggleRecordingRef.current());
        const doSend = () => {
          const text = pipInput.value.trim();
          if (!text) return;
          pipInput.value = "";
          sendMessageRef.current(text);
        };
        pipWin.document.getElementById("pip-send")?.addEventListener("click", doSend);
        pipInput.addEventListener("keydown", e => { if (e.key === "Enter") doSend(); });
        pipWin.document.getElementById("pip-end")?.addEventListener("click", () => endSessionRef.current());

        pipWin.addEventListener("pagehide", () => {
          pipWindowRef.current = null;
          pipBridgeRef.current = null;
          setIsPiP(false);
        });

        setIsPiP(true);
        return;
      } catch (e) {
        console.warn("Document PiP failed, fallback to video PiP:", e);
      }
    }

    /* Fallback: native video PiP */
    const video = camVideoRef.current;
    if (!video || !document.pictureInPictureEnabled) return;
    if (!video.srcObject && camStreamRef.current) {
      video.srcObject = camStreamRef.current;
      await video.play().catch(() => {});
    }
    if (video.readyState < 2) {
      await new Promise<void>(res => video.addEventListener("canplay", () => res(), { once: true }));
    }
    try { await video.requestPictureInPicture(); } catch (e) { console.warn("Video PiP:", e); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [closePiP, camOn]);

  const openPiPRef = useRef<() => Promise<void>>(async () => {});
  openPiPRef.current = openPiP;

  /* ── Helpers ── */
  const formatTime = (s: number) =>
    `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;
  const isLowTime  = timeLeft <= 5 * 60;
  const isGrounded = primaryFile?.status === "ready" || supportFiles.some(f => f.status === "ready");
  const firstName  = user?.full_name?.split(" ")[0] ?? "there";
  const fmt        = (b: number) => b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`;

  /* ── processFile — real upload to /api/v1/documents/upload ── */
  const processFile = useCallback(async (file: File, type: "primary" | "supporting") => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      addMessage("ai", `⚠️ Only PDF files are supported. "${file.name}" was skipped.`);
      return;
    }

    const localId = crypto.randomUUID();
    const entry: DocFile = { id: localId, name: file.name, size: file.size, status: "uploading" };

    const setEntry = (patch: Partial<DocFile>) => {
      if (type === "primary")
        setPrimary(p => p?.id === localId ? { ...p, ...patch } : p);
      else
        setSupport(p => p.map(f => f.id === localId ? { ...f, ...patch } : f));
    };

    if (type === "primary") setPrimary(entry);
    else setSupport(prev => [...prev, entry]);

    try {
      setEntry({ status: "processing" });

      const fd = new FormData();
      fd.append("file", file);

      const res  = await fetch("/api/v1/documents/upload", { method: "POST", body: fd });
      const data = await res.json();

      if (!res.ok) {
        setEntry({ status: "error", error: data?.detail ?? "Upload failed" });
        addMessage("ai", `❌ Failed to index "${file.name}": ${data?.detail ?? "Unknown error"}`);
        return;
      }

      setEntry({ status: "ready", docId: data.document_id });

      if (type === "primary") {
        const pages = data.pages ? ` (${data.pages} page${data.pages !== 1 ? "s" : ""})` : "";
        addMessage("ai", `✅ "${file.name}"${pages} indexed — I'll use it to give you more accurate answers!`);
      }
    } catch (err) {
      setEntry({ status: "error", error: "Network error" });
      addMessage("ai", `❌ Could not upload "${file.name}". Please check your connection and try again.`);
    }
  }, [addMessage]);

  /* ── deleteDoc — remove from ChromaDB + MongoDB then clear local state ── */
  const deleteDoc = useCallback(async (docId: string | undefined, localId: string, type: "primary" | "supporting") => {
    if (type === "primary") setPrimary(null);
    else setSupport(p => p.filter(f => f.id !== localId));
    if (!docId) return;
    try {
      await fetch(`/api/v1/documents/${docId}`, { method: "DELETE" });
    } catch { /* silent — document still de-listed locally */ }
  }, []);

  if (authLoading) return (
    <div style={{ minHeight: "100vh", background: "#030D1A", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Loader2 className="w-7 h-7 animate-spin" style={{ color: "rgba(138,180,248,0.5)" }} />
    </div>
  );

  /* ════════════ SETUP SCREEN (before session starts) ════════════ */
  if (!sessionStarted) return (
    <div className="h-screen flex flex-col overflow-hidden"
      style={{ background: "linear-gradient(160deg,#030D1A 0%,#071830 50%,#030D1A 100%)", fontFamily: "'DM Sans', sans-serif" }}>

      {/* Navbar */}
      <header className="nav-glass shrink-0 flex items-center gap-3 px-4 md:px-6 h-[3.4rem] z-10 border-b border-white/[0.06]">
        <button onClick={endSession} className="flex items-center gap-2 cursor-pointer" style={{ background: "none", border: "none" }}>
          <div className="gold-dot" />
          <span className="font-semibold text-lg tracking-tight text-white">Mind Tutor</span>
        </button>
      </header>

      {/* Setup content */}
      <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-3xl space-y-6"
        >
          {/* Header */}
          <div className="text-center space-y-1">
            <p className="text-xs font-medium text-primary/70 uppercase tracking-widest">Setup</p>
            <h1 className="text-2xl font-semibold text-white">Before we start</h1>
            <p className="text-[13px] text-white/40">Enable camera and share screen to begin your session</p>
          </div>

          {/* 2-column preview grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            {/* ── Camera preview ── */}
            <div className="space-y-3">
              <div className="relative w-full rounded-2xl overflow-hidden"
                style={{ aspectRatio: "16/9", background: "rgba(0,0,0,0.4)", border: `1px solid ${camOn ? "rgba(52,211,153,0.3)" : "rgba(255,255,255,0.08)"}` }}>
                {camOn ? (
                  <video ref={camVideoRef} autoPlay playsInline muted
                    className="w-full h-full object-cover" style={{ transform: "scaleX(-1)" }} />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center gap-3">
                    <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
                      style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}>
                      <VideoOff className="w-6 h-6 text-white/25" />
                    </div>
                    <p className="text-[12px] text-white/30">Camera is off</p>
                  </div>
                )}
                {camOn && (
                  <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5 px-2.5 py-1 rounded-full"
                    style={{ background: "rgba(4,16,32,0.7)", backdropFilter: "blur(8px)", border: "1px solid rgba(52,211,153,0.25)" }}>
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-[10px] text-emerald-400 font-medium">Camera on</span>
                  </div>
                )}
              </div>
              <button
                onClick={() => setCamOn(p => !p)}
                className="w-full h-10 rounded-xl flex items-center justify-center gap-2 text-[13px] font-medium transition-all cursor-pointer active:scale-[0.98]"
                style={{
                  background: camOn ? "rgba(52,211,153,0.12)" : "rgba(255,255,255,0.05)",
                  border: camOn ? "1px solid rgba(52,211,153,0.28)" : "1px solid rgba(255,255,255,0.1)",
                  color: camOn ? "#34d399" : "rgba(255,255,255,0.55)",
                }}
              >
                {camOn ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
                {camOn ? "Turn off camera" : "Turn on camera"}
              </button>
            </div>

            {/* ── Screen share preview ── */}
            <div className="space-y-3">
              <div
                className="relative w-full rounded-2xl overflow-hidden cursor-pointer"
                style={{ aspectRatio: "16/9", background: "rgba(0,0,0,0.4)", border: `1px solid ${screenOn ? "rgba(52,211,153,0.3)" : "rgba(255,255,255,0.08)"}` }}
                onClick={() => !screenOn && switchScreen()}
              >
                {screenOn ? (
                  <video ref={screenCaptureRef} autoPlay playsInline muted
                    className="w-full h-full object-contain" />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center gap-3 group">
                    <div className="w-14 h-14 rounded-2xl flex items-center justify-center transition-all"
                      style={{ background: "rgba(138,180,248,0.08)", border: "1px solid rgba(138,180,248,0.15)" }}
                      onMouseEnter={e => { e.currentTarget.style.background = "rgba(138,180,248,0.18)"; }}
                      onMouseLeave={e => { e.currentTarget.style.background = "rgba(138,180,248,0.08)"; }}>
                      <ScreenShare className="w-6 h-6" style={{ color: "rgba(138,180,248,0.6)" }} />
                    </div>
                    <div className="text-center">
                      <p className="text-[13px] font-medium text-white/55">Click to share screen</p>
                      <p className="text-[11px] text-white/25 mt-0.5">Window, tab, or entire screen</p>
                    </div>
                  </div>
                )}

                {/* PiP cam overlay */}
                {screenOn && camOn && (
                  <div className="absolute bottom-2.5 right-2.5 rounded-xl overflow-hidden shadow-lg"
                    style={{ width: 96, height: 72, border: "2px solid rgba(255,255,255,0.15)" }}>
                    <video ref={setupCamPipRef} autoPlay playsInline muted
                      className="w-full h-full object-cover" style={{ transform: "scaleX(-1)" }} />
                  </div>
                )}

                {screenOn && (
                  <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5 px-2.5 py-1 rounded-full"
                    style={{ background: "rgba(4,16,32,0.7)", backdropFilter: "blur(8px)", border: "1px solid rgba(239,68,68,0.3)" }}>
                    <div className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
                    <span className="text-[10px] text-red-400 font-medium">Sharing</span>
                  </div>
                )}
              </div>
              <button
                onClick={() => screenOn ? null : switchScreen()}
                disabled={screenOn}
                className="w-full h-10 rounded-xl flex items-center justify-center gap-2 text-[13px] font-medium transition-all cursor-pointer active:scale-[0.98] disabled:cursor-default"
                style={{
                  background: screenOn ? "rgba(52,211,153,0.12)" : "rgba(255,255,255,0.05)",
                  border: screenOn ? "1px solid rgba(52,211,153,0.28)" : "1px solid rgba(255,255,255,0.1)",
                  color: screenOn ? "#34d399" : "rgba(255,255,255,0.55)",
                }}
              >
                {screenOn ? <ScreenShare className="w-4 h-4" /> : <ScreenShareOff className="w-4 h-4" />}
                {screenOn ? "Screen is shared" : "Share screen"}
              </button>
            </div>
          </div>

          {/* Progress hint */}
          <p className="text-center text-[12px] text-white/25">
            {!camOn && !screenOn && "Enable camera and share screen to begin"}
            {camOn && !screenOn && "Now share your screen to continue →"}
            {!camOn && screenOn && "Now enable your camera to continue →"}
            {camOn && screenOn && "Starting session..."}
          </p>
        </motion.div>
      </div>
    </div>
  );

  /* ════════════════════ RENDER ════════════════════ */
  return (
    <div className="h-screen flex flex-col overflow-hidden"
      style={{ background: "linear-gradient(160deg,#030D1A 0%,#071830 50%,#030D1A 100%)" }}>

      {/* Hidden video elements */}
      <video ref={screenCaptureRef} autoPlay playsInline muted
        style={{ position: "fixed", width: 1, height: 1, opacity: 0, pointerEvents: "none", top: -10, left: -10 }} />
      <video ref={camVideoRef} autoPlay playsInline muted
        style={{ position: "fixed", width: 1, height: 1, opacity: 0, pointerEvents: "none", top: -10, left: -20 }} />

      {/* ── Navbar — identical to Session.tsx + user dropdown ── */}
      <header className="nav-glass shrink-0 flex items-center gap-3 px-4 md:px-6 h-[3.4rem] z-10 border-b border-white/[0.06]">
        <button onClick={endSession} className="flex items-center gap-2 cursor-pointer" style={{ background: "none", border: "none" }}>
          <div className="gold-dot" />
          <span className="font-semibold text-lg tracking-tight text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>Mind Tutor</span>
        </button>

        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-400/10 border border-emerald-400/20">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_6px_#34d399]" />
          <span className="text-[10px] text-emerald-400/90 font-medium tracking-wide" style={{ fontFamily: "'DM Sans', sans-serif" }}>LIVE</span>
        </div>

        {detectorState && (
          <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-medium tracking-wide transition-all ${
            detectorState === "confused"
              ? "bg-amber-400/10 border-amber-400/25 text-amber-400/90"
              : "bg-red-400/10 border-red-400/25 text-red-400/80"
          }`} style={{ fontFamily: "'DM Sans', sans-serif" }}>
            <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${detectorState === "confused" ? "bg-amber-400" : "bg-red-400"}`} />
            {detectorState === "confused" ? "CONFUSED" : "DISTRACTED"}
          </div>
        )}

        <div className="flex-1" />

        {/* Timer */}
        <span className={`text-[12px] font-mono tabular-nums transition-colors px-2 py-0.5 rounded-md ${
          isLowTime ? "text-red-400 bg-red-500/10 border border-red-500/20" : "text-white/40"
        }`}>
          {isLowTime && <AlertTriangle className="w-3 h-3 inline mr-1" />}{formatTime(timeLeft)}
        </span>

        {/* Float button */}
        <button
          onClick={isPiP ? closePiP : openPiP}
          title={isPiP ? "Close float panel" : "Open float panel"}
          className={`flex items-center gap-1.5 text-[11px] px-2.5 py-1.5 rounded-lg transition-all cursor-pointer ${
            isPiP
              ? "bg-primary/20 text-primary hover:bg-primary/30 border border-primary/20"
              : "text-white/40 hover:text-white/75 hover:bg-white/8 border border-transparent"
          }`}
          style={{ fontFamily: "'DM Sans', sans-serif" }}
        >
          {isPiP ? "↩ Return" : "⧉ Float"}
        </button>

        {/* User dropdown */}
        <div data-user-menu className="relative">
          <button
            onClick={() => setMenuOpen(p => !p)}
            className="flex items-center gap-2 h-8 px-2.5 rounded-xl border border-white/[0.1] bg-white/[0.04] hover:bg-white/[0.07] transition-colors cursor-pointer"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            {/* Avatar */}
            <div className="w-6 h-6 rounded-full overflow-hidden flex items-center justify-center text-[10px] font-bold shrink-0"
              style={{
                background: user?.avatar_url ? "transparent" : "linear-gradient(135deg,rgba(138,180,248,0.3),rgba(138,180,248,0.1))",
                border: "1px solid rgba(138,180,248,0.3)",
                color: "rgba(138,180,248,0.9)",
              }}>
              {user?.avatar_url
                ? <img src={user.avatar_url} alt="avatar" className="w-full h-full object-cover" />
                : firstName[0]?.toUpperCase()}
            </div>
            <span className="text-[12px] text-white/70">{firstName}</span>
            <ChevronDown className={`w-3 h-3 text-white/30 transition-transform ${menuOpen ? "rotate-180" : ""}`} />
          </button>
          <AnimatePresence>
            {menuOpen && (
              <motion.div
                initial={{ opacity: 0, y: 6, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 4, scale: 0.96 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-1.5 w-48 rounded-2xl overflow-hidden z-50"
                style={{ background: "rgba(4,16,32,0.96)", backdropFilter: "blur(24px)", border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 16px 48px rgba(0,0,0,0.5)" }}
              >
                {/* User info header */}
                <div className="px-3.5 pt-3 pb-2 border-b border-white/[0.06]">
                  <p className="text-[12px] font-medium text-white/80 truncate">{user?.full_name || firstName}</p>
                  <p className="text-[11px] text-white/35 truncate mt-0.5">{user?.email}</p>
                </div>
                <div className="p-1.5">
                  <button
                    onClick={() => { setMenuOpen(false); setProfileOpen(true); }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[12px] text-white/65 hover:bg-white/[0.07] transition-colors cursor-pointer"
                    style={{ fontFamily: "'DM Sans', sans-serif", background: "none", border: "none" }}
                  >
                    <User className="w-3.5 h-3.5 text-white/35" /> Edit Profile
                  </button>
                  <div style={{ height: 1, background: "rgba(255,255,255,0.05)", margin: "4px 8px" }} />
                  <button
                    onClick={() => { endSession(); logout(); }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[12px] text-red-400/80 hover:bg-red-500/10 transition-colors cursor-pointer"
                    style={{ fontFamily: "'DM Sans', sans-serif", background: "none", border: "none" }}
                  >
                    <LogOut className="w-3.5 h-3.5" /> Log out
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </header>

      <ProfilePanel open={profileOpen} onClose={() => setProfileOpen(false)} />

      {/* ── Main 2-column layout ── */}
      <div className="flex-1 flex overflow-hidden px-4 py-4 gap-4" style={{ minHeight: 0 }}>

        {/* ─── LEFT: Knowledge Workspace ─── */}
        <div className="flex flex-col gap-4 overflow-y-auto" style={{ width: "34%", minWidth: 272 }}>

          {/* Primary Document */}
          <div className="rounded-[1.25rem] flex flex-col gap-3.5 p-5"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 2px 16px rgba(0,0,0,0.2)" }}>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg flex items-center justify-center"
                style={{ background: "rgba(138,180,248,0.12)", border: "1px solid rgba(138,180,248,0.22)" }}>
                <BookOpen className="w-3.5 h-3.5" style={{ color: "rgba(138,180,248,0.8)" }} />
              </div>
              <span className="text-[12px] font-semibold text-white/80" style={{ fontFamily: "'DM Sans', sans-serif" }}>Context Document <span className="text-white/30 font-normal">(optional)</span></span>
              <div title="Main context for AI understanding" className="ml-auto text-white/25 hover:text-white/50 transition-colors cursor-help">
                <Info className="w-3.5 h-3.5" />
              </div>
            </div>

            {!primaryFile ? (
              <>
                <div
                  onDragOver={e => { e.preventDefault(); setDragOver("primary"); }}
                  onDragLeave={() => setDragOver(null)}
                  onDrop={e => { e.preventDefault(); setDragOver(null); const f = e.dataTransfer.files[0]; if (f) processFile(f, "primary"); }}
                  onClick={() => primaryInpRef.current?.click()}
                  className="flex flex-col items-center justify-center gap-3 cursor-pointer transition-all rounded-[0.875rem]"
                  style={{
                    height: 132,
                    border: `2px dashed ${dragOver === "primary" ? "rgba(138,180,248,0.55)" : "rgba(255,255,255,0.13)"}`,
                    background: dragOver === "primary" ? "rgba(138,180,248,0.06)" : "transparent",
                    transform: dragOver === "primary" ? "scale(1.01)" : "scale(1)",
                  }}
                >
                  <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
                    style={{ background: "rgba(138,180,248,0.1)", border: "1px solid rgba(138,180,248,0.22)" }}>
                    <Upload className="w-5 h-5" style={{ color: "rgba(138,180,248,0.75)" }} />
                  </div>
                  <div className="text-center">
                    <p className="text-[12px] font-medium text-white/60" style={{ fontFamily: "'DM Sans', sans-serif" }}>Upload a Document</p>
                    <p className="text-[11px] text-white/28 mt-0.5" style={{ fontFamily: "'DM Sans', sans-serif" }}>PDF only · up to 50 MB · optional</p>
                  </div>
                  <input ref={primaryInpRef} type="file" accept=".pdf" className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) processFile(f, "primary"); e.target.value = ""; }} />
                </div>
                <p className="text-[10px] text-center text-white/20" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                  Uploading a document helps the AI avoid hallucinations on your topic
                </p>
              </>
            ) : (
              <div className="rounded-[0.875rem] p-3.5 flex items-center gap-3"
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                  style={{ background: "rgba(138,180,248,0.1)", border: "1px solid rgba(138,180,248,0.2)" }}>
                  <FileText className="w-5 h-5" style={{ color: "rgba(138,180,248,0.7)" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[12px] font-medium text-white/80 truncate" style={{ fontFamily: "'DM Sans', sans-serif" }}>{primaryFile.name}</p>
                  <p className="text-[10px] text-white/30 mt-0.5" style={{ fontFamily: "'DM Sans', sans-serif" }}>{fmt(primaryFile.size)}</p>
                </div>
                <StatusBadge status={primaryFile.status} />
                {(primaryFile.status === "ready" || primaryFile.status === "error") && (
                  <button onClick={() => deleteDoc(primaryFile.docId, primaryFile.id, "primary")}
                    className="w-6 h-6 rounded-lg flex items-center justify-center cursor-pointer transition-colors text-white/30 hover:text-white/65"
                    style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Supporting Materials */}
          <div className="rounded-[1.25rem] flex flex-col gap-3 p-5 flex-1"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 2px 16px rgba(0,0,0,0.2)" }}>
            <div className="flex items-center gap-2">
              <span className="text-[12px] font-semibold text-white/80" style={{ fontFamily: "'DM Sans', sans-serif" }}>Supporting Materials</span>
              <div title="Used for retrieval (RAG)" className="text-white/25 hover:text-white/50 transition-colors cursor-help">
                <Info className="w-3.5 h-3.5" />
              </div>
              <div className="flex-1" />
              <button onClick={() => supportInpRef.current?.click()}
                className="flex items-center gap-1 text-[11px] font-medium cursor-pointer transition-colors text-[rgba(138,180,248,0.75)] hover:text-[rgba(138,180,248,1)]"
                style={{ background: "none", border: "none", fontFamily: "'DM Sans', sans-serif" }}>
                <Plus className="w-3.5 h-3.5" /> Add
              </button>
              <input ref={supportInpRef} type="file" accept=".pdf" multiple className="hidden"
                onChange={e => { Array.from(e.target.files || []).forEach(f => processFile(f, "supporting")); e.target.value = ""; }} />
            </div>

            {supportFiles.length === 0 ? (
              <div
                onDragOver={e => { e.preventDefault(); setDragOver("supporting"); }}
                onDragLeave={() => setDragOver(null)}
                onDrop={e => { e.preventDefault(); setDragOver(null); Array.from(e.dataTransfer.files).forEach(f => processFile(f, "supporting")); }}
                onClick={() => supportInpRef.current?.click()}
                className="flex flex-col items-center justify-center gap-2 cursor-pointer transition-all rounded-[0.875rem]"
                style={{
                  height: 82,
                  border: `2px dashed ${dragOver === "supporting" ? "rgba(138,180,248,0.5)" : "rgba(255,255,255,0.1)"}`,
                  background: dragOver === "supporting" ? "rgba(138,180,248,0.05)" : "transparent",
                }}
              >
                <Plus className="w-4 h-4 text-white/22" />
                <p className="text-[11px] text-white/28" style={{ fontFamily: "'DM Sans', sans-serif" }}>Add Supporting Materials</p>
              </div>
            ) : (
              <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight: 280 }}>
                {supportFiles.map(f => (
                  <div key={f.id} className="rounded-[0.75rem] p-3 flex items-center gap-2.5"
                    style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.065)" }}>
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0" style={{ background: "rgba(255,255,255,0.05)" }}>
                      <FileText className="w-4 h-4 text-white/30" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] font-medium text-white/65 truncate" style={{ fontFamily: "'DM Sans', sans-serif" }}>{f.name}</p>
                      <p className="text-[10px] text-white/25" style={{ fontFamily: "'DM Sans', sans-serif" }}>{fmt(f.size)}</p>
                    </div>
                    <StatusBadge status={f.status} />
                    {(f.status === "ready" || f.status === "error") && (
                      <button onClick={() => deleteDoc(f.docId, f.id, "supporting")}
                        className="w-6 h-6 rounded-md flex items-center justify-center cursor-pointer transition-colors text-white/25 hover:text-white/60"
                        style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                        <X className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                ))}
                <button
                  onDragOver={e => { e.preventDefault(); setDragOver("supporting"); }}
                  onDragLeave={() => setDragOver(null)}
                  onDrop={e => { e.preventDefault(); setDragOver(null); Array.from(e.dataTransfer.files).forEach(f => processFile(f, "supporting")); }}
                  onClick={() => supportInpRef.current?.click()}
                  className="flex items-center justify-center gap-2 h-9 rounded-[0.75rem] cursor-pointer transition-all text-[11px] text-white/30 hover:text-[rgba(138,180,248,0.7)]"
                  style={{ border: `1px dashed ${dragOver === "supporting" ? "rgba(138,180,248,0.4)" : "rgba(255,255,255,0.1)"}`, background: "transparent", fontFamily: "'DM Sans', sans-serif" }}
                >
                  <Plus className="w-3.5 h-3.5" /> Add more files
                </button>
              </div>
            )}

            {isGrounded && (
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl mt-auto"
                style={{ background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.18)" }}>
                <div className="w-1.5 h-1.5 rounded-full" style={{ background: "#34d399", boxShadow: "0 0 5px #34d399" }} />
                <span className="text-[10px] text-emerald-400/85 font-medium" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                  AI is grounded on your documents
                </span>
              </div>
            )}
          </div>
        </div>

        {/* ─── RIGHT: Chat — EXACT copy from Session.tsx ─── */}
        <div className="flex-1 flex flex-col overflow-hidden" style={{ minHeight: 0 }}>

          {/* ── Chat area — identical to Session.tsx ── */}
          <div className="flex-1 relative overflow-hidden">
            <div className="h-full overflow-y-auto px-6 py-6">
              <div className="max-w-2xl mx-auto space-y-4">
                <AnimatePresence initial={false}>
                  {messages.map(msg => (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2 }}
                      className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      {msg.role === "ai" && (
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/35 to-primary/10 border border-primary/35 flex items-center justify-center shrink-0 mt-0.5 shadow-[0_0_14px_rgba(138,180,248,0.18)]">
                          <span style={{ fontFamily: "'Material Symbols Rounded'", fontSize: 16, lineHeight: 1, color: "rgba(138,180,248,0.9)", fontWeight: "normal" }}>smart_toy</span>
                        </div>
                      )}
                      <div
                        className={`max-w-[72%] rounded-[18px] px-4 py-2.5 text-[16px] leading-relaxed shadow-sm ${
                          msg.role === "user"
                            ? "bg-[rgba(138,180,248,0.16)] border border-[rgba(138,180,248,0.28)] text-white/95 rounded-br-[4px] shadow-[0_2px_12px_rgba(138,180,248,0.1)]"
                            : "bg-[rgba(138,180,248,0.06)] border border-[rgba(138,180,248,0.15)] text-white/90 rounded-bl-[4px]"
                        }`}
                        style={{ fontFamily: "'Helvetica Neue', Helvetica, Arial, sans-serif" }}
                      >
                        {msg.imageBase64 && (
                          <img src={`data:image/jpeg;base64,${msg.imageBase64}`} alt="Captured screen"
                            className="w-full rounded-lg mb-2 border border-white/10"
                            style={{ maxHeight: 220, objectFit: "contain", background: "rgba(0,0,0,0.3)" }} />
                        )}
                        {msg.content}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>

                {isLoading && (
                  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3 justify-start">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/35 to-primary/10 border border-primary/35 flex items-center justify-center shrink-0 shadow-[0_0_14px_rgba(138,180,248,0.18)]">
                      <span style={{ fontFamily: "'Material Symbols Rounded'", fontSize: 16, lineHeight: 1, color: "rgba(138,180,248,0.9)", fontWeight: "normal" }}>smart_toy</span>
                    </div>
                    <div className="bg-[rgba(138,180,248,0.06)] border border-[rgba(138,180,248,0.15)] rounded-[18px] rounded-bl-[4px] px-5 py-3.5 flex gap-1.5 items-center">
                      {[0, 130, 260].map(d => (
                        <div key={d} className="w-1.5 h-1.5 rounded-full bg-primary/70 animate-bounce" style={{ animationDelay: `${d}ms` }} />
                      ))}
                    </div>
                  </motion.div>
                )}
                <div ref={chatEndRef} />
              </div>
            </div>
          </div>

          {/* ── Input bar — identical to Session.tsx ── */}
          <div className="shrink-0 border-t border-white/[0.07] bg-[#030D1A]/96 backdrop-blur-md px-6 py-3">
            <div className="max-w-2xl mx-auto space-y-2.5">

              {/* Controls row — identical to Session.tsx */}
              <div className="flex items-center gap-2">
                <button onClick={() => setCamOn(p => !p)} title={camOn ? "Turn off camera" : "Turn on camera"}
                  className={`w-9 h-9 rounded-full flex items-center justify-center transition-all active:scale-90 cursor-pointer ${
                    camOn
                      ? "bg-[rgba(138,180,248,0.85)] text-[#030D1A] shadow-[0_0_12px_rgba(138,180,248,0.25)]"
                      : "bg-red-500/12 text-red-400 hover:bg-red-500/22 border border-red-500/20"
                  }`}>
                  {camOn ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
                </button>

                <button onClick={() => setAudioOn(p => !p)} title={audioOn ? "Mute AI voice" : "Unmute AI voice"}
                  className={`w-9 h-9 rounded-full flex items-center justify-center transition-all active:scale-90 cursor-pointer ${
                    audioOn
                      ? "bg-[rgba(138,180,248,0.85)] text-[#030D1A] shadow-[0_0_12px_rgba(138,180,248,0.25)]"
                      : "bg-red-500/12 text-red-400 hover:bg-red-500/22 border border-red-500/20"
                  }`}>
                  {audioOn ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
                </button>

                <button onClick={switchScreen} title={screenOn ? "Switch screen" : "Share screen"}
                  className={`w-9 h-9 rounded-full flex items-center justify-center transition-all active:scale-90 cursor-pointer ${
                    screenOn
                      ? "bg-[rgba(138,180,248,0.85)] text-[#030D1A] shadow-[0_0_12px_rgba(138,180,248,0.25)]"
                      : "bg-white/[0.06] text-white/50 hover:text-white/80 hover:bg-white/[0.09] border border-white/[0.09]"
                  }`}>
                  {screenOn ? <ScreenShare className="w-4 h-4" /> : <ScreenShareOff className="w-4 h-4" />}
                </button>

                <div className="w-px h-4 bg-white/10 mx-1" />

                <button onClick={() => analyzeScreen()} disabled={isLoading || !screenStreamRef.current}
                  className="flex items-center gap-1.5 h-9 px-3.5 rounded-full bg-white/[0.05] border border-white/[0.09] text-white/50 hover:text-white/80 hover:bg-white/[0.09] hover:border-white/[0.15] text-[12px] font-medium transition-all disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                  style={{ fontFamily: "'DM Sans', sans-serif" }}>
                  <Scan className="w-3.5 h-3.5" />
                  Analyze Screen
                </button>

                <div className="flex-1" />

                {isGrounded && (
                  <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-400/10 border border-emerald-400/20">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" style={{ boxShadow: "0 0 5px #34d399" }} />
                    <span className="text-[10px] text-emerald-400/85 font-medium" style={{ fontFamily: "'DM Sans', sans-serif" }}>Grounded</span>
                  </div>
                )}
              </div>

              {/* Input row — identical to Session.tsx */}
              <div className="flex gap-2 items-center">
                <input
                  value={isRecording ? "" : inputText}
                  onChange={e => setInputText(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); sendMessage(inputText); } }}
                  placeholder={isRecording ? "Listening..." : isGrounded ? "Ask about your documents..." : "Ask your AI Tutor..."}
                  disabled={isRecording}
                  className="flex-1 h-11 rounded-3xl bg-white/[0.05] border border-white/[0.1] px-5 text-[14px] text-white/90 placeholder:text-white/30 focus:outline-none focus:border-[rgba(138,180,248,0.4)] focus:bg-white/[0.07] transition-all disabled:cursor-not-allowed"
                  style={{ fontFamily: "'DM Sans', sans-serif" }}
                />
                <button onClick={toggleRecording} title={isRecording ? "Stop recording" : "Speak to AI"}
                  className={`w-11 h-11 rounded-full flex items-center justify-center transition-all active:scale-95 cursor-pointer ${
                    isRecording
                      ? "bg-red-500 text-white shadow-[0_0_0_4px_rgba(239,68,68,0.25)] animate-pulse"
                      : "bg-white/[0.07] border border-white/[0.1] text-white/55 hover:text-white/85 hover:bg-white/[0.12]"
                  }`}>
                  <Mic className="w-4 h-4" />
                </button>
                <button onClick={() => sendMessage(inputText)} disabled={!inputText.trim() || isLoading || isRecording}
                  className="w-11 h-11 rounded-full bg-[rgba(138,180,248,0.85)] flex items-center justify-center text-[#030D1A] disabled:opacity-30 disabled:cursor-not-allowed transition-all active:scale-95 hover:bg-[rgba(138,180,248,0.95)] shadow-[0_0_16px_rgba(138,180,248,0.2)] cursor-pointer">
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
