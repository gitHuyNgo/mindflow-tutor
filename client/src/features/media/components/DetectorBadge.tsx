import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Eye, Sparkles } from "lucide-react";
import type { DetectorState } from "@/features/chat/types";

interface DetectorBadgeProps {
  state: DetectorState;
  className?: string;
}

export const DetectorBadge: React.FC<DetectorBadgeProps> = ({ state, className = "" }) => {
  return (
    <AnimatePresence>
      {state && (
        <motion.div
          initial={{ opacity: 0, y: -8, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.95 }}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold backdrop-blur-md shadow-sm border ${
            state === "confused"
              ? "bg-amber-500/15 border-amber-500/30 text-amber-300"
              : "bg-rose-500/15 border-rose-500/30 text-rose-300"
          } ${className}`}
        >
          {state === "confused" ? (
            <>
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
              <span>Confusion Detected · AI Assistant Ready</span>
            </>
          ) : (
            <>
              <Eye className="w-3.5 h-3.5 text-rose-400" />
              <span>Distraction Detected · Stay Focused</span>
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default DetectorBadge;
