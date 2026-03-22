import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus, History, BookOpen, Clock, MessageSquare,
  ChevronDown, User, LogOut, Trash2, ArrowRight,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import ProfilePanel from "@/components/ProfilePanel";

/* ────────── types ────────── */
export type SessionRecord = {
  id: string;
  title: string;
  subject: string;
  createdAt: string;
  messageCount: number;
};

const LS_KEY = "mindtutor_sessions";

export function loadSessions(): SessionRecord[] {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || "[]"); }
  catch { return []; }
}
export function saveSession(s: SessionRecord) {
  const list = loadSessions().filter(x => x.id !== s.id);
  localStorage.setItem(LS_KEY, JSON.stringify([s, ...list].slice(0, 50)));
}
function deleteSession(id: string) {
  const list = loadSessions().filter(x => x.id !== id);
  localStorage.setItem(LS_KEY, JSON.stringify(list));
}

function fmt(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
  if (diff < 60)  return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/* ────────── Page ────────── */
const SessionUserPage = () => {
  const navigate = useNavigate();
  const { user, isLoading: authLoading, isAuthenticated, logout } = useAuth();

  const [tab, setTab]             = useState<"new" | "history">("new");
  const [sessionName, setSessionName] = useState("");
  const [subject, setSubject]     = useState("");
  const [sessions, setSessions]   = useState<SessionRecord[]>([]);
  const [menuOpen, setMenuOpen]   = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const firstName = user?.full_name?.split(" ")[0] || "there";

  useEffect(() => {
    if (!authLoading && !isAuthenticated) navigate("/login", { replace: true });
  }, [authLoading, isAuthenticated, navigate]);

  useEffect(() => {
    setSessions(loadSessions());
  }, [tab]);

  /* close menu on outside click */
  useEffect(() => {
    if (!menuOpen) return;
    const h = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest("[data-user-menu]")) setMenuOpen(false);
    };
    document.addEventListener("click", h);
    return () => document.removeEventListener("click", h);
  }, [menuOpen]);

  const startNewSession = () => {
    const id = crypto.randomUUID();
    const record: SessionRecord = {
      id,
      title: sessionName.trim() || subject.trim() || "Study Session",
      subject: subject.trim(),
      createdAt: new Date().toISOString(),
      messageCount: 0,
    };
    saveSession(record);
    navigate("/dashboard", { state: { sessionId: id, subject: subject.trim(), title: record.title } });
  };

  const resumeSession = (s: SessionRecord) => {
    navigate("/dashboard", { state: { sessionId: s.id, subject: s.subject } });
  };

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    deleteSession(id);
    setSessions(prev => prev.filter(x => x.id !== id));
  };

  if (authLoading) return (
    <div style={{ minHeight: "100vh", background: "#030D1A", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="w-6 h-6 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
    </div>
  );

  return (
    <div className="h-screen flex flex-col overflow-hidden"
      style={{ background: "linear-gradient(160deg,#030D1A 0%,#071830 50%,#030D1A 100%)", fontFamily: "'DM Sans', sans-serif" }}>

      {/* ── Navbar ── */}
      <header className="nav-glass shrink-0 flex items-center gap-3 px-4 md:px-6 h-[3.4rem] z-10 border-b border-white/[0.06]">
        <button onClick={() => navigate("/")} className="flex items-center gap-2 cursor-pointer" style={{ background: "none", border: "none" }}>
          <div className="gold-dot" />
          <span className="font-semibold text-lg tracking-tight text-white">Mind Tutor</span>
        </button>

        <div className="flex-1" />

        {/* User dropdown */}
        <div data-user-menu className="relative">
          <button
            onClick={() => setMenuOpen(p => !p)}
            className="flex items-center gap-2 h-8 px-2.5 rounded-xl border border-white/[0.1] bg-white/[0.04] hover:bg-white/[0.07] transition-colors cursor-pointer"
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
            <span className="text-[12px] text-white/70 max-w-[90px] truncate">{firstName}</span>
            <ChevronDown className={`w-3 h-3 text-white/40 transition-transform ${menuOpen ? "rotate-180" : ""}`} />
          </button>

          <AnimatePresence>
            {menuOpen && (
              <motion.div
                initial={{ opacity: 0, y: -6, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -6, scale: 0.97 }}
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
                    style={{ background: "none", border: "none" }}
                  >
                    <User className="w-3.5 h-3.5 text-white/35" /> Edit Profile
                  </button>
                  <div style={{ height: 1, background: "rgba(255,255,255,0.05)", margin: "4px 8px" }} />
                  <button
                    onClick={() => { logout(); navigate("/"); }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[12px] text-red-400/80 hover:bg-red-500/10 transition-colors cursor-pointer"
                    style={{ background: "none", border: "none" }}
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
      <div className="flex-1 overflow-y-auto px-4 py-8">
        <div className="max-w-2xl mx-auto space-y-6">

          {/* Greeting */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <p className="text-xs font-medium text-primary/80 uppercase tracking-widest mb-1">Welcome back</p>
            <h1 className="text-2xl font-semibold text-white">Hey, {firstName} 👋</h1>
          </motion.div>

          {/* Tabs */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.08 }}
            className="flex gap-1 p-1 rounded-2xl w-fit"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}
          >
            {([["new", Plus, "New Session"], ["history", History, "History"]] as const).map(([key, Icon, label]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-[13px] font-medium transition-all cursor-pointer"
                style={{
                  background: tab === key ? "rgba(138,180,248,0.15)" : "transparent",
                  border: tab === key ? "1px solid rgba(138,180,248,0.25)" : "1px solid transparent",
                  color: tab === key ? "rgba(138,180,248,0.95)" : "rgba(255,255,255,0.35)",
                }}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </button>
            ))}
          </motion.div>

          {/* Tab content */}
          <AnimatePresence mode="wait">

            {/* ── NEW SESSION ── */}
            {tab === "new" && (
              <motion.div
                key="new"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25 }}
                className="rounded-[1.5rem] p-7 space-y-6"
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 4px 32px rgba(0,0,0,0.25)" }}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
                    style={{ background: "rgba(138,180,248,0.1)", border: "1px solid rgba(138,180,248,0.2)" }}>
                    <BookOpen className="w-5 h-5" style={{ color: "rgba(138,180,248,0.8)" }} />
                  </div>
                  <div>
                    <p className="text-[15px] font-semibold text-white/90">Create Study Session</p>
                    <p className="text-[12px] text-white/35 mt-0.5">Start a new learning session with your AI Tutor</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-[11px] text-white/70 uppercase tracking-wider font-medium">
                      Session Name <span className="normal-case tracking-normal text-white/40">(optional)</span>
                    </label>
                    <input
                      value={sessionName}
                      onChange={e => setSessionName(e.target.value)}
                      onKeyDown={e => { if (e.key === "Enter") startNewSession(); }}
                      placeholder="e.g. Morning Study, Chapter 5 Review..."
                      className="w-full h-11 rounded-2xl px-4 text-[13px] text-white/90 placeholder:text-white/25 focus:outline-none transition-all"
                      style={{
                        background: "rgba(255,255,255,0.05)",
                        border: "1px solid rgba(255,255,255,0.1)",
                      }}
                      onFocus={e => { e.currentTarget.style.border = "1px solid rgba(138,180,248,0.4)"; e.currentTarget.style.background = "rgba(255,255,255,0.07)"; }}
                      onBlur={e => { e.currentTarget.style.border = "1px solid rgba(255,255,255,0.1)"; e.currentTarget.style.background = "rgba(255,255,255,0.05)"; }}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-[11px] text-white/70 uppercase tracking-wider font-medium">
                      Subject / Topic <span className="normal-case tracking-normal text-white/40">(optional)</span>
                    </label>
                    <input
                      value={subject}
                      onChange={e => setSubject(e.target.value)}
                      onKeyDown={e => { if (e.key === "Enter") startNewSession(); }}
                      placeholder="e.g. Calculus, Machine Learning, History..."
                      className="w-full h-11 rounded-2xl px-4 text-[13px] text-white/90 placeholder:text-white/25 focus:outline-none transition-all"
                      style={{
                        background: "rgba(255,255,255,0.05)",
                        border: "1px solid rgba(255,255,255,0.1)",
                      }}
                      onFocus={e => { e.currentTarget.style.border = "1px solid rgba(138,180,248,0.4)"; e.currentTarget.style.background = "rgba(255,255,255,0.07)"; }}
                      onBlur={e => { e.currentTarget.style.border = "1px solid rgba(255,255,255,0.1)"; e.currentTarget.style.background = "rgba(255,255,255,0.05)"; }}
                    />
                  </div>
                </div>

                <button
                  onClick={startNewSession}
                  className="w-full h-11 rounded-2xl flex items-center justify-center gap-2 text-[13px] font-semibold transition-all active:scale-[0.98] cursor-pointer"
                  style={{ background: "rgba(138,180,248,0.9)", color: "#030D1A", boxShadow: "0 0 24px rgba(138,180,248,0.2)" }}
                  onMouseEnter={e => { e.currentTarget.style.background = "rgba(138,180,248,1)"; }}
                  onMouseLeave={e => { e.currentTarget.style.background = "rgba(138,180,248,0.9)"; }}
                >
                  Start Session <ArrowRight className="w-4 h-4" />
                </button>
              </motion.div>
            )}

            {/* ── HISTORY ── */}
            {tab === "history" && (
              <motion.div
                key="history"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25 }}
                className="space-y-3"
              >
                {sessions.length === 0 ? (
                  <div className="rounded-[1.5rem] p-12 flex flex-col items-center gap-3"
                    style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
                      style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
                      <History className="w-5 h-5 text-white/25" />
                    </div>
                    <p className="text-[13px] text-white/50">No sessions yet</p>
                    <button
                      onClick={() => setTab("new")}
                      className="text-[12px] font-medium cursor-pointer transition-colors"
                      style={{ color: "rgba(138,180,248,0.7)", background: "none", border: "none" }}
                    >
                      Start your first session →
                    </button>
                  </div>
                ) : (
                  sessions.map((s, i) => (
                    <motion.div
                      key={s.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2, delay: i * 0.04 }}
                      onClick={() => resumeSession(s)}
                      className="group rounded-[1.25rem] p-4 flex items-center gap-4 cursor-pointer transition-all"
                      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}
                      onMouseEnter={e => { e.currentTarget.style.background = "rgba(138,180,248,0.06)"; e.currentTarget.style.border = "1px solid rgba(138,180,248,0.18)"; }}
                      onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.03)"; e.currentTarget.style.border = "1px solid rgba(255,255,255,0.07)"; }}
                    >
                      <div className="w-10 h-10 rounded-2xl flex items-center justify-center shrink-0"
                        style={{ background: "rgba(138,180,248,0.08)", border: "1px solid rgba(138,180,248,0.15)" }}>
                        <BookOpen className="w-4.5 h-4.5" style={{ color: "rgba(138,180,248,0.65)" }} />
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-medium text-white/90 truncate">{s.title}</p>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="flex items-center gap-1 text-[11px] text-white/45">
                            <Clock className="w-3 h-3" /> {fmt(s.createdAt)}
                          </span>
                          {s.messageCount > 0 && (
                            <span className="flex items-center gap-1 text-[11px] text-white/45">
                              <MessageSquare className="w-3 h-3" /> {s.messageCount} messages
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={e => handleDelete(e, s.id)}
                          className="w-7 h-7 rounded-lg flex items-center justify-center cursor-pointer transition-colors text-white/25 hover:text-red-400 hover:bg-red-500/10"
                          style={{ background: "transparent", border: "none" }}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                        <ArrowRight className="w-4 h-4 text-primary/50" />
                      </div>
                    </motion.div>
                  ))
                )}
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default SessionUserPage;
