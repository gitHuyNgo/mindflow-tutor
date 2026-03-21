import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, Video, VideoOff, Scan, Send, LogOut, AlertTriangle, Volume2, VolumeX, ScreenShare, ScreenShareOff } from "lucide-react";
import { sessionStore } from "@/lib/sessionStore";

type Message = {
  id: string;
  role: "user" | "ai";
  content: string;
  imageBase64?: string;
};

const SESSION_DURATION = 30 * 60;
const supportsDocPiP = "documentPictureInPicture" in window;

type PipBridge = {
  updateMessages: (msgs: Message[], loading: boolean) => void;
  updateControls: (cam: boolean) => void;
  updateAudio: (on: boolean) => void;
  updateScreen: (on: boolean) => void;
  updateRecording: (rec: boolean) => void;
};

const SessionPage = () => {
  const navigate = useNavigate();

  const [sessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [camOn, setCamOn] = useState(sessionStore.camOn);
  const [audioOn, setAudioOn] = useState(true);
  const [screenOn, setScreenOn] = useState(!!sessionStore.screenStream);
  const [isRecording, setIsRecording] = useState(false);
  const [detectorState, setDetectorState] = useState<null | "confused" | "distracted">(null);
  const [timeLeft, setTimeLeft] = useState(SESSION_DURATION);
  const [isPiP, setIsPiP] = useState(false);

  const camStreamRef = useRef<MediaStream | null>(sessionStore.camStream);
  const screenStreamRef = useRef<MediaStream | null>(sessionStore.screenStream);
  const pipWindowRef = useRef<Window | null>(null);
  const pipBridgeRef = useRef<PipBridge | null>(null);

  // Always-current refs — never go stale inside callbacks
  const sendMessageRef = useRef<(text: string) => void>(() => {});
  const endSessionRef = useRef<() => void>(() => {});
  const messagesRef = useRef<Message[]>([]);
  const isLoadingRef = useRef(false);
  const audioOnRef = useRef(true);
  messagesRef.current = messages;
  isLoadingRef.current = isLoading;
  audioOnRef.current = audioOn;
  const screenOnRef = useRef(!!sessionStore.screenStream);
  screenOnRef.current = screenOn;
  const isRecordingRef = useRef(false);
  isRecordingRef.current = isRecording;

  const camVideoRef = useRef<HTMLVideoElement>(null);
  const screenCaptureRef = useRef<HTMLVideoElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Play base64 audio from ElevenLabs — skipped if audio is muted
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

  // Switch/start screen share via getDisplayMedia
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
    } catch {
      // user cancelled or permission denied — no state change
    }
  }, []);
  const switchScreenRef = useRef<() => Promise<void>>(async () => {});
  switchScreenRef.current = switchScreen;

  // Push-to-talk: record mic → STT → send as message
  const toggleRecording = useCallback(async () => {
    if (isRecordingRef.current) {
      mediaRecorderRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
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
          const res = await fetch("/api/v1/stt", { method: "POST", body: fd });
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

  // Load DM Sans (UI font) + Material Symbols Rounded (icons, synced with float panel)
  useEffect(() => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20,400,1,0&display=swap";
    document.head.appendChild(link);
    return () => { document.head.removeChild(link); };
  }, []);

  // ── addMessage ──
  const addMessage = useCallback((role: "user" | "ai", content: string, imageBase64?: string) => {
    setMessages(prev => {
      const next = [...prev, { id: crypto.randomUUID(), role, content, imageBase64 }];
      pipBridgeRef.current?.updateMessages(next, false);
      return next;
    });
  }, []);

  // ── analyzeScreen ──
  const analyzeScreen = useCallback(async (silent = false) => {
    const video = screenCaptureRef.current;
    if (!video || !screenStreamRef.current) return;
    if (!silent) addMessage("user", "Analyze my current screen.");
    setIsLoading(true);
    pipBridgeRef.current?.updateMessages(messagesRef.current, true);
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
      if (data.audio_base64) playAudio(data.audio_base64);
    } catch {
      addMessage("ai", "Couldn't read the screen right now. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, addMessage, playAudio]);

  // ── sendMessage ──
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    const normalized = text.trim().toLowerCase();
    setInputText("");
    addMessage("user", text);

    // ── Acknowledgement for distraction reminder ──
    if (awaitingDistractionReplyRef.current) {
      awaitingDistractionReplyRef.current = false;
      let isAck = false;
      try {
        const r = await fetch("/api/v1/utils/classify-intent", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, intent: "the user is acknowledging they were distracted and will refocus on studying" }),
        });
        isAck = (await r.json()).match === true;
      } catch { /* fallback: treat as normal question */ }

      if (isAck) {
        if (detectorResumeTimerRef.current) clearTimeout(detectorResumeTimerRef.current);
        detectorResumeTimerRef.current = setTimeout(() => {
          detectorPausedRef.current = false;
          setDetectorState(null);
          detectorResumeTimerRef.current = null;
        }, 5000);
        const encourage = "That's the spirit! Let's keep going 💪";
        addMessage("ai", encourage);
        fetch(`/api/v1/tts/generate?text=${encodeURIComponent(encourage)}`, { method: "POST" })
          .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});
        return;
      }
      // Not an ack → resume detector, process as normal question
      detectorPausedRef.current = false;
      setDetectorState(null);
    }

    // ── Yes/No response to confusion check-in ──
    if (awaitingConfusionReplyRef.current) {
      awaitingConfusionReplyRef.current = false;

      if (normalized.startsWith("yes")) {
        const ack = "I captured this moment for us 👇\nWhat part feels unclear? Let's figure it out together.";
        addMessage("ai", ack, pendingConfusionFrameRef.current ?? undefined);
        fetch(`/api/v1/tts/generate?text=${encodeURIComponent(ack)}`, { method: "POST" })
          .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});
        confusionFrameReadyRef.current = true;
        return;
      }

      // "no" or anything else → discard frame, resume detector
      detectorPausedRef.current = false;
      setDetectorState(null);
      pendingConfusionFrameRef.current = null;
      if (normalized.startsWith("no")) return;
      // Other message: fall through to normal flow
    }

    // ── Understanding confirmation during interaction phase ──
    if (inConfusionInteractionRef.current) {
      let isUnderstanding = false;
      try {
        const r = await fetch("/api/v1/utils/classify-intent", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, intent: "the user understands the topic and has no more questions about it" }),
        });
        isUnderstanding = (await r.json()).match === true;
      } catch { /* fallback: treat as follow-up question */ }

      if (isUnderstanding) {
        inConfusionInteractionRef.current = false;
        pendingConfusionFrameRef.current = null;
        if (detectorResumeTimerRef.current) clearTimeout(detectorResumeTimerRef.current);
        detectorResumeTimerRef.current = setTimeout(() => {
          detectorPausedRef.current = false;
          setDetectorState(null);
          detectorResumeTimerRef.current = null;
        }, 5000);
        const wrap = "Nice, we figured it out together 🙌";
        addMessage("ai", wrap);
        fetch(`/api/v1/tts/generate?text=${encodeURIComponent(wrap)}`, { method: "POST" })
          .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});
        return;
      }
    }

    // ── Send to AI ──
    setIsLoading(true);
    try {
      let res: Response;
      if (confusionFrameReadyRef.current) {
        // First question after "yes" — send frame as context
        confusionFrameReadyRef.current = false;
        inConfusionInteractionRef.current = true;
        const frame = pendingConfusionFrameRef.current;
        if (frame) {
          res = await fetch("/api/v1/process-trigger", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ screen_capture: frame, session_id: sessionId, user_query: text }),
          });
        } else {
          res = await fetch(`/api/v1/ask?question=${encodeURIComponent(text)}&session_id=${sessionId}`, { method: "POST" });
        }
      } else {
        res = await fetch(`/api/v1/ask?question=${encodeURIComponent(text)}&session_id=${sessionId}`, { method: "POST" });
      }
      const data = await res.json();
      addMessage("ai", data.text_response);
      if (data.audio_base64) playAudio(data.audio_base64);
    } catch {
      addMessage("ai", "Connection error. Please try again.");
    } finally {
      setIsLoading(false);
      if (!inConfusionInteractionRef.current && detectorPausedRef.current) {
        detectorPausedRef.current = false;
        setDetectorState(null);
      }
    }
  }, [isLoading, sessionId, addMessage, playAudio]);

  sendMessageRef.current = sendMessage;

  // ── closePiP ──
  const closePiP = useCallback(() => {
    pipWindowRef.current?.close();
    pipWindowRef.current = null;
    pipBridgeRef.current = null;
    if (document.pictureInPictureElement) document.exitPictureInPicture().catch(() => {});
    setIsPiP(false);
  }, []);

  // ── endSession ──
  const endSession = useCallback(() => {
    currentAudioRef.current?.pause();
    if (detectorResumeTimerRef.current) clearTimeout(detectorResumeTimerRef.current);
    closePiP();
    camStreamRef.current?.getTracks().forEach(t => t.stop());
    screenStreamRef.current?.getTracks().forEach(t => t.stop());
    navigate("/");
  }, [navigate, closePiP]);

  endSessionRef.current = endSession;

  // ── Mount: attach streams + initial greeting ──
  useEffect(() => {
    const camVideo = camVideoRef.current;
    const screenVideo = screenCaptureRef.current;

    if (camVideo && camStreamRef.current) {
      camVideo.srcObject = camStreamRef.current;
      camVideo.play().catch(() => {});
    }
    if (screenVideo && screenStreamRef.current) {
      screenVideo.srcObject = screenStreamRef.current;
      screenVideo.play().catch(() => {});
    }

    const onEnterVideoPiP = () => setIsPiP(true);
    const onLeaveVideoPiP = () => setIsPiP(false);
    camVideo?.addEventListener("enterpictureinpicture", onEnterVideoPiP);
    camVideo?.addEventListener("leavepictureinpicture", onLeaveVideoPiP);

    const greeting = "Hey! I'm your learning companion. Let's learn together!";
    addMessage("ai", greeting);
    fetch(`/api/v1/tts/generate?text=${encodeURIComponent(greeting)}`, { method: "POST" })
      .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});
    // Auto-open float panel — user activation from navigation click is still valid
    setTimeout(() => openPiPRef.current().catch(() => {}), 300);

    return () => {
      camVideo?.removeEventListener("enterpictureinpicture", onEnterVideoPiP);
      camVideo?.removeEventListener("leavepictureinpicture", onLeaveVideoPiP);
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

  // Sync messages + loading to open PIP window
  useEffect(() => {
    pipBridgeRef.current?.updateMessages(messages, isLoading);
  }, [messages, isLoading]);

  // Sync cam control to PIP
  useEffect(() => {
    pipBridgeRef.current?.updateControls(camOn);
  }, [camOn]);

  // Sync audio state to PIP — stop current audio immediately when muted
  useEffect(() => {
    if (!audioOn) {
      currentAudioRef.current?.pause();
      currentAudioRef.current = null;
    }
    pipBridgeRef.current?.updateAudio(audioOn);
  }, [audioOn]);

  // Sync screen share state to PIP
  useEffect(() => {
    pipBridgeRef.current?.updateScreen(screenOn);
  }, [screenOn]);

  // Sync recording state to PIP
  useEffect(() => {
    pipBridgeRef.current?.updateRecording(isRecording);
  }, [isRecording]);

  // ── Camera detector polling — runs every 2.5 s when cam is on ──
  const detectorPausedRef = useRef(false);
  const detectorResumeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingConfusionFrameRef = useRef<string | null>(null);
  const awaitingConfusionReplyRef = useRef(false);
  const awaitingDistractionReplyRef = useRef(false);
  const confusionFrameReadyRef = useRef(false);
  const inConfusionInteractionRef = useRef(false);

  useEffect(() => {
    if (!camOn) { setDetectorState(null); return; }

    const poll = async () => {
      if (detectorPausedRef.current) return;
      const video = camVideoRef.current;
      if (!video || !camStreamRef.current || video.videoWidth === 0) return;
      try {
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth;
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
          // Pause detector immediately so it doesn't fire again
          detectorPausedRef.current = true;
          awaitingConfusionReplyRef.current = true;

          // Capture current screen frame (what the user is studying)
          const sv = screenCaptureRef.current;
          if (sv && screenStreamRef.current && sv.videoWidth > 0) {
            const sc = document.createElement("canvas");
            sc.width = sv.videoWidth || 1280;
            sc.height = sv.videoHeight || 720;
            sc.getContext("2d")!.drawImage(sv, 0, 0);
            pendingConfusionFrameRef.current = sc.toDataURL("image/jpeg", 0.7).split(",")[1];
          } else {
            pendingConfusionFrameRef.current = null;
          }

          const checkIn = "Hey, it looks like something might be confusing here 👀\nAm I right? (yes/no)";
          addMessage("ai", checkIn);
          fetch(`/api/v1/tts/generate?text=${encodeURIComponent(checkIn)}`, { method: "POST" })
            .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});

        } else if (data.distracted) {
          setDetectorState("distracted");
          detectorPausedRef.current = true;
          awaitingDistractionReplyRef.current = true;
          const msg = "Hey my friend, let's focus again, we can do this together 💪";
          addMessage("ai", msg);
          fetch(`/api/v1/tts/generate?text=${encodeURIComponent(msg)}`, { method: "POST" })
            .then(r => r.json()).then(d => { if (d.audio_base64) playAudio(d.audio_base64); }).catch(() => {});
        } else {
          setDetectorState(null);
        }
      } catch { /* silent — detector is optional */ }
    };

    const id = setInterval(poll, 2500);
    return () => { clearInterval(id); setDetectorState(null); };
  }, [camOn, addMessage, playAudio]);
  useEffect(() => {
    if (timeLeft <= 0) return;
    const id = setTimeout(() => setTimeLeft(t => t - 1), 1000);
    return () => clearTimeout(id);
  }, [timeLeft]);

  // Scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // ── openPiP ──
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

        // Copy app styles into PIP document
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

        // Load DM Sans + Material Symbols Rounded
        const gFonts = pipWin.document.createElement("link");
        gFonts.rel = "stylesheet";
        gFonts.href = "https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20,400,1,0&display=swap";
        pipWin.document.head.appendChild(gFonts);

        const style = pipWin.document.createElement("style");
        style.textContent = `
          @keyframes pip-recording {
            0% { box-shadow:0 0 0 0 rgba(239,68,68,.6) }
            70% { box-shadow:0 0 0 7px rgba(239,68,68,0) }
            100% { box-shadow:0 0 0 0 rgba(239,68,68,0) }
          }
          @keyframes pip-bounce {
            0%,80%,100% { transform:translateY(0);opacity:.4 }
            40%          { transform:translateY(-5px);opacity:1 }
          }
          @keyframes pip-pulse-ring {
            0% { box-shadow:0 0 0 0 rgba(52,211,153,.4) }
            70% { box-shadow:0 0 0 5px rgba(52,211,153,0) }
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

        body.innerHTML = `
          <div id="pip-root" style="display:flex;flex-direction:column;height:100dvh;overflow:hidden">

            <!-- Camera preview -->
            <div style="height:240px;position:relative;flex-shrink:0;background:#000;overflow:hidden">
              <video id="pip-cam" autoplay playsinline muted
                style="width:100%;height:100%;object-fit:cover;object-position:center top;transform:scaleX(-1);display:block">
              </video>
              <!-- Gradient overlay: strong at bottom, subtle vignette -->
              <div style="position:absolute;inset:0;background:linear-gradient(to top,rgba(3,13,26,.9) 0%,rgba(3,13,26,.2) 35%,transparent 60%)"></div>
              <div style="position:absolute;inset:0;background:radial-gradient(ellipse at center,transparent 60%,rgba(3,13,26,.35) 100%)"></div>
              <!-- Live badge -->
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
              <button id="pip-cam-btn" class="pip-btn"
                style="width:38px;height:38px;border-radius:50%;border:none">
              </button>
              <button id="pip-audio" class="pip-btn"
                style="width:38px;height:38px;border-radius:50%;border:none">
              </button>
              <button id="pip-screen" class="pip-btn"
                style="width:38px;height:38px;border-radius:50%;border:none">
              </button>
              <div style="flex:1"></div>
              <button id="pip-end" class="pip-btn"
                style="width:38px;height:38px;border-radius:50%;border:none;
                       background:rgba(239,68,68,.85);color:white;
                       box-shadow:0 0 12px rgba(239,68,68,.25)">
                <span class="ms" style="font-size:18px">call_end</span>
              </button>
            </div>
          </div>`;

        // ── Attach camera stream ──
        const pipCamVideo = pipWin.document.getElementById("pip-cam") as HTMLVideoElement;
        if (camStreamRef.current) {
          pipCamVideo.srcObject = camStreamRef.current;
          pipCamVideo.play().catch(() => {});
        }

        // ── Bridge: messages — synced style with main chat ──
        const chatEl = pipWin.document.getElementById("pip-chat")!;
        const renderMsg = (m: Message) => {
          const isUser = m.role === "user";
          const imgHtml = m.imageBase64
            ? `<img src="data:image/jpeg;base64,${m.imageBase64}" style="width:100%;border-radius:8px;margin-bottom:6px;object-fit:contain;max-height:120px;border:1px solid rgba(255,255,255,.1);background:rgba(0,0,0,.3);display:block">`
            : "";
          return `<div style="display:flex;gap:6px;justify-content:${isUser ? "flex-end" : "flex-start"};align-items:flex-end">
            ${!isUser ? `<div style="width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,rgba(138,180,248,.35),rgba(138,180,248,.12));border:1px solid rgba(138,180,248,.35);display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 0 10px rgba(138,180,248,.15)"><span class="ms" style="font-size:14px;color:rgba(138,180,248,.9)">smart_toy</span></div>` : ""}
            <div style="max-width:83%;
              background:${isUser ? "rgba(138,180,248,.2)" : "rgba(255,255,255,.07)"};
              border:1px solid ${isUser ? "rgba(138,180,248,.32)" : "rgba(255,255,255,.1)"};
              color:rgba(255,255,255,${isUser ? ".95" : ".85"});
              border-radius:18px;padding:6px 11px;font-size:13.5px;line-height:1.55;
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
              <div style="background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.1);border-radius:18px;border-bottom-left-radius:4px;padding:9px 13px;display:flex;gap:4px;align-items:center">
                ${[0, 160, 320].map(d => `<span style="width:5px;height:5px;border-radius:50%;background:rgba(138,180,248,.7);display:inline-block;animation:pip-bounce 1.2s ${d}ms infinite"></span>`).join("")}
              </div>
            </div>` : "");
          chatEl.scrollTop = chatEl.scrollHeight;
        };

        // ── Bridge: cam control ──
        const camBtn = pipWin.document.getElementById("pip-cam-btn")!;
        const audioBtn = pipWin.document.getElementById("pip-audio")!;
        const screenBtn = pipWin.document.getElementById("pip-screen")!;
        const sttBtn = pipWin.document.getElementById("pip-stt")!;
        const pipInput = pipWin.document.getElementById("pip-input") as HTMLInputElement;

        const updateControls = (cam: boolean) => {
          camBtn.style.background = cam ? "rgba(138,180,248,.85)" : "rgba(239,68,68,.75)";
          camBtn.style.color = cam ? "#030D1A" : "white";
          camBtn.innerHTML = `<span class="ms">${cam ? "videocam" : "videocam_off"}</span>`;
        };

        const updateAudio = (on: boolean) => {
          audioBtn.style.background = on ? "rgba(138,180,248,.85)" : "rgba(239,68,68,.75)";
          audioBtn.style.color = on ? "#030D1A" : "white";
          audioBtn.innerHTML = `<span class="ms">${on ? "volume_up" : "volume_off"}</span>`;
        };

        const updateScreen = (on: boolean) => {
          screenBtn.style.background = on ? "rgba(138,180,248,.85)" : "rgba(255,255,255,.07)";
          screenBtn.style.color = on ? "#030D1A" : "rgba(255,255,255,.5)";
          screenBtn.innerHTML = `<span class="ms">${on ? "screen_share" : "stop_screen_share"}</span>`;
        };

        const updateRecording = (rec: boolean) => {
          sttBtn.style.background = rec ? "rgba(239,68,68,.85)" : "rgba(255,255,255,.07)";
          sttBtn.style.color = rec ? "white" : "rgba(255,255,255,.5)";
          sttBtn.style.animation = rec ? "pip-recording 1s ease infinite" : "none";
          pipInput.placeholder = rec ? "Listening..." : "Ask anything...";
          pipInput.disabled = rec;
        };

        pipBridgeRef.current = { updateMessages, updateControls, updateAudio, updateScreen, updateRecording };

        // Seed with current state immediately
        updateMessages(messagesRef.current, isLoadingRef.current);
        updateControls(camOn);
        updateAudio(audioOnRef.current);
        updateScreen(screenOnRef.current);
        updateRecording(isRecordingRef.current);

        // ── Wire buttons ──
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

    // Fallback: native video PIP
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

  // openPiP ref — always current, safe inside callbacks
  const openPiPRef = useRef<() => Promise<void>>(async () => {});
  openPiPRef.current = openPiP;

  const formatTime = (s: number) =>
    `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;

  const isLowTime = timeLeft <= 5 * 60;

  return (
    <div className="h-screen flex flex-col overflow-hidden"
      style={{ background: "linear-gradient(160deg,#030D1A 0%,#071830 50%,#030D1A 100%)" }}>

      {/* Offscreen screen capture */}
      <video ref={screenCaptureRef} autoPlay playsInline muted
        style={{ position: "fixed", width: 1, height: 1, opacity: 0, pointerEvents: "none", top: -10, left: -10 }}
      />
      {/* Hidden camera video — kept in DOM for PIP stream */}
      <video ref={camVideoRef} autoPlay playsInline muted
        style={{ position: "fixed", width: 1, height: 1, opacity: 0, pointerEvents: "none", top: -10, left: -20 }}
      />

      {/* ── Top bar ── */}
      <header className="nav-glass shrink-0 flex items-center gap-3 px-4 md:px-6 h-[3.4rem] z-10 border-b border-white/[0.06]">
        <div className="gold-dot" />
        <span className="font-semibold text-lg tracking-tight text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>Mind Tutor</span>
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
            <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${
              detectorState === "confused" ? "bg-amber-400" : "bg-red-400"
            }`} />
            {detectorState === "confused" ? "CONFUSED" : "DISTRACTED"}
          </div>
        )}
        <div className="flex-1" />
        <span className={`text-[12px] font-mono tabular-nums transition-colors px-2 py-0.5 rounded-md ${
          isLowTime ? "text-red-400 bg-red-500/10 border border-red-500/20" : "text-white/40"
        }`}>
          {isLowTime && <AlertTriangle className="w-3 h-3 inline mr-1" />}{formatTime(timeLeft)}
        </span>

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

        <button
          onClick={endSession}
          className="flex items-center gap-1.5 text-[12px] text-white/35 hover:text-red-400 transition-colors px-2 py-1.5 rounded-lg hover:bg-red-500/8 cursor-pointer"
          style={{ fontFamily: "'DM Sans', sans-serif" }}
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Leave</span>
        </button>
      </header>

      {/* ── Chat area ── */}
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
                    className={`max-w-[72%] rounded-[18px] px-4 py-2.5 text-[15px] leading-relaxed shadow-sm ${
                      msg.role === "user"
                        ? "bg-[rgba(138,180,248,0.16)] border border-[rgba(138,180,248,0.28)] text-white/95 rounded-br-[4px] shadow-[0_2px_12px_rgba(138,180,248,0.1)]"
                        : "bg-white/[0.07] border border-white/[0.1] text-white/85 rounded-bl-[4px]"
                    }`}
                    style={{ fontFamily: "'Helvetica Neue', Helvetica, Arial, sans-serif" }}
                  >
                    {msg.imageBase64 && (
                      <img
                        src={`data:image/jpeg;base64,${msg.imageBase64}`}
                        alt="Captured screen"
                        className="w-full rounded-lg mb-2 border border-white/10"
                        style={{ maxHeight: 220, objectFit: "contain", background: "rgba(0,0,0,0.3)" }}
                      />
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
                <div className="bg-white/[0.07] border border-white/[0.1] rounded-[18px] rounded-bl-[4px] px-5 py-3.5 flex gap-1.5 items-center">
                  {[0, 130, 260].map(d => (
                    <div key={d} className="w-1.5 h-1.5 rounded-full bg-primary/70 animate-bounce"
                      style={{ animationDelay: `${d}ms` }} />
                  ))}
                </div>
              </motion.div>
            )}
            <div ref={chatEndRef} />
          </div>
        </div>
      </div>

      {/* ── Bottom input bar ── */}
      <div className="shrink-0 border-t border-white/[0.07] bg-[#030D1A]/96 backdrop-blur-md px-6 py-3">
        <div className="max-w-2xl mx-auto space-y-2.5">

          {/* Controls row */}
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
            <div className="flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 text-amber-400/45" />
              <span className="text-[11px] text-white/25" style={{ fontFamily: "'DM Sans', sans-serif" }}>Guest ·</span>
              <button onClick={() => navigate("/login")}
                className="text-[11px] text-primary/50 hover:text-primary/80 transition-colors cursor-pointer"
                style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Sign Up
              </button>
            </div>
          </div>

          {/* Input row */}
          <div className="flex gap-2 items-center">
            <input
              value={isRecording ? "" : inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); sendMessage(inputText); } }}
              placeholder={isRecording ? "Listening..." : "Type your question..."}
              disabled={isRecording}
              className="flex-1 h-11 rounded-3xl bg-white/[0.05] border border-white/[0.1] px-5 text-[13px] text-white/90 placeholder:text-white/22 focus:outline-none focus:border-[rgba(138,180,248,0.4)] focus:bg-white/[0.07] transition-all disabled:cursor-not-allowed"
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
  );
};

export default SessionPage;
