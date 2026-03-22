import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Camera, Check, Loader2, AlertCircle } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { authApi } from "@/lib/auth";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function ProfilePanel({ open, onClose }: Props) {
  const { user, token, updateUser } = useAuth();

  const [name, setName]         = useState(user?.full_name ?? "");
  const [avatar, setAvatar]     = useState(user?.avatar_url ?? "");
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState("");
  const [saved, setSaved]       = useState(false);
  const fileRef                 = useRef<HTMLInputElement>(null);

  // Sync when panel opens
  useEffect(() => {
    if (open) {
      setName(user?.full_name ?? "");
      setAvatar(user?.avatar_url ?? "");
      setError("");
      setSaved(false);
    }
  }, [open, user]);

  const pickAvatar = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 500_000) { setError("Image too large — max 500 KB"); return; }
    const reader = new FileReader();
    reader.onload = ev => setAvatar(ev.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleSave = async () => {
    if (!token) return;
    setSaving(true);
    setError("");
    try {
      const updated = await authApi.updateProfile(token, {
        full_name: name.trim() || undefined,
        avatar_url: avatar || undefined,
      });
      updateUser({ full_name: updated.full_name, avatar_url: updated.avatar_url });
      setSaved(true);
      setTimeout(() => { setSaved(false); onClose(); }, 900);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const initials = (user?.full_name ?? "?")
    .split(" ").slice(0, 2).map(w => w[0]?.toUpperCase()).join("");

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="fixed inset-0 z-[60]"
            style={{ background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)" }}
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            key="panel"
            initial={{ opacity: 0, x: 40, scale: 0.97 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 40, scale: 0.97 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="fixed right-4 top-[3.8rem] z-[70] w-80 rounded-[1.5rem] overflow-hidden"
            style={{
              background: "rgba(4,16,32,0.97)",
              border: "1px solid rgba(138,180,248,0.15)",
              boxShadow: "0 24px 64px rgba(0,0,0,0.6), 0 0 0 1px rgba(138,180,248,0.08)",
              backdropFilter: "blur(32px)",
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 pt-5 pb-3">
              <span className="text-[13px] font-semibold text-white/80 uppercase tracking-widest">Profile</span>
              <button
                onClick={onClose}
                className="w-7 h-7 rounded-lg flex items-center justify-center text-white/30 hover:text-white/70 hover:bg-white/[0.07] transition-colors cursor-pointer"
                style={{ border: "none", background: "transparent" }}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="px-5 pb-5 space-y-5">
              {/* Avatar */}
              <div className="flex flex-col items-center gap-3">
                <div className="relative group">
                  <div
                    className="w-20 h-20 rounded-full overflow-hidden flex items-center justify-center text-xl font-bold cursor-pointer"
                    style={{
                      background: avatar
                        ? "transparent"
                        : "linear-gradient(135deg,rgba(138,180,248,0.25),rgba(138,180,248,0.08))",
                      border: "2px solid rgba(138,180,248,0.25)",
                      boxShadow: "0 0 24px rgba(138,180,248,0.12)",
                      color: "rgba(138,180,248,0.9)",
                    }}
                    onClick={() => fileRef.current?.click()}
                  >
                    {avatar
                      ? <img src={avatar} alt="avatar" className="w-full h-full object-cover" />
                      : initials}
                  </div>
                  <button
                    onClick={() => fileRef.current?.click()}
                    className="absolute bottom-0 right-0 w-7 h-7 rounded-full flex items-center justify-center cursor-pointer transition-all"
                    style={{
                      background: "rgba(138,180,248,0.9)",
                      border: "2px solid rgba(4,16,32,1)",
                      color: "#030D1A",
                    }}
                    title="Change avatar"
                  >
                    <Camera className="w-3.5 h-3.5" />
                  </button>
                </div>
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={pickAvatar}
                />
                <p className="text-[11px] text-white/30">Click to change · max 500 KB</p>
              </div>

              {/* Divider */}
              <div style={{ height: 1, background: "rgba(255,255,255,0.06)" }} />

              {/* Email (read-only) */}
              <div className="space-y-1.5">
                <label className="text-[11px] text-white/40 uppercase tracking-wider font-medium">Email</label>
                <div
                  className="h-10 rounded-xl px-3.5 flex items-center text-[13px] text-white/35"
                  style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
                >
                  {user?.email}
                </div>
              </div>

              {/* Full name */}
              <div className="space-y-1.5">
                <label className="text-[11px] text-white/60 uppercase tracking-wider font-medium">Display Name</label>
                <input
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="Your name"
                  maxLength={50}
                  className="w-full h-10 rounded-xl px-3.5 text-[13px] text-white/90 placeholder:text-white/25 focus:outline-none transition-all"
                  style={{
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    fontFamily: "'DM Sans', sans-serif",
                  }}
                  onFocus={e => {
                    e.currentTarget.style.border = "1px solid rgba(138,180,248,0.4)";
                    e.currentTarget.style.background = "rgba(255,255,255,0.07)";
                  }}
                  onBlur={e => {
                    e.currentTarget.style.border = "1px solid rgba(255,255,255,0.1)";
                    e.currentTarget.style.background = "rgba(255,255,255,0.05)";
                  }}
                />
              </div>

              {/* Error */}
              {error && (
                <div className="flex items-center gap-2 text-[12px] text-red-400/80 rounded-xl px-3 py-2"
                  style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.15)" }}>
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  {error}
                </div>
              )}

              {/* Save button */}
              <button
                onClick={handleSave}
                disabled={saving || saved}
                className="w-full h-10 rounded-xl flex items-center justify-center gap-2 text-[13px] font-semibold transition-all active:scale-[0.98] cursor-pointer disabled:cursor-not-allowed"
                style={{
                  background: saved ? "rgba(52,211,153,0.85)" : "rgba(138,180,248,0.9)",
                  color: "#030D1A",
                  boxShadow: saved
                    ? "0 0 20px rgba(52,211,153,0.25)"
                    : "0 0 20px rgba(138,180,248,0.2)",
                  opacity: saving ? 0.7 : 1,
                }}
              >
                {saving
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
                  : saved
                  ? <><Check className="w-4 h-4" /> Saved!</>
                  : "Save Changes"}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
