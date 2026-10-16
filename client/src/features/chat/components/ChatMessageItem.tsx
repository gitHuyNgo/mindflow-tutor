import React from "react";
import { motion } from "framer-motion";
import { Bot, User, Volume2 } from "lucide-react";
import type { Message } from "@/features/chat/types";

interface ChatMessageItemProps {
  message: Message;
  onPlayAudio?: (text: string) => void;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({ message, onPlayAudio }) => {
  const isAI = message.role === "ai";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex gap-3 max-w-[85%] ${isAI ? "self-start" : "self-end flex-row-reverse"}`}
    >
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${
          isAI
            ? "bg-gradient-to-br from-violet-600 to-indigo-600 text-white"
            : "bg-muted text-foreground border border-border"
        }`}
      >
        {isAI ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
      </div>

      <div
        className={`group relative rounded-2xl p-4 text-sm leading-relaxed shadow-sm transition-all ${
          isAI
            ? "bg-card/80 backdrop-blur-md border border-border/60 text-card-foreground rounded-tl-sm"
            : "bg-primary text-primary-foreground rounded-tr-sm shadow-primary/20"
        }`}
      >
        {message.imageBase64 && (
          <div className="mb-3 rounded-lg overflow-hidden border border-border/40">
            <img
              src={`data:image/jpeg;base64,${message.imageBase64}`}
              alt="Screen snapshot attached"
              className="max-h-60 w-auto object-contain rounded"
            />
          </div>
        )}

        <div className="whitespace-pre-wrap select-text">{message.content}</div>

        {isAI && onPlayAudio && (
          <button
            type="button"
            onClick={() => onPlayAudio(message.content)}
            title="Read aloud"
            className="mt-2.5 inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors opacity-70 group-hover:opacity-100"
          >
            <Volume2 className="w-3.5 h-3.5" />
            <span>Listen</span>
          </button>
        )}
      </div>
    </motion.div>
  );
};

export default ChatMessageItem;
