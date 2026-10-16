import React from "react";
import { Sparkles, HelpCircle, BookOpen, Calculator } from "lucide-react";

interface ChatEmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

const STARTER_PROMPTS = [
  {
    icon: HelpCircle,
    label: "Explain a concept",
    prompt: "Can you explain the main concept from my notes in simple terms with an analogy?",
  },
  {
    icon: Calculator,
    label: "Step-by-step problem",
    prompt: "Guide me step-by-step through solving a problem related to this topic.",
  },
  {
    icon: BookOpen,
    label: "Quiz my understanding",
    prompt: "Ask me 3 conceptual questions to test my understanding of this chapter.",
  },
];

export const ChatEmptyState: React.FC<ChatEmptyStateProps> = ({ onSelectPrompt }) => {
  return (
    <div className="flex flex-col items-center justify-center h-full max-w-lg mx-auto text-center px-4 py-8">
      <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500/20 to-indigo-500/20 border border-violet-500/30 flex items-center justify-center text-primary mb-4 shadow-sm">
        <Sparkles className="w-6 h-6 text-primary" />
      </div>

      <h3 className="text-lg font-semibold tracking-tight mb-2">How can I assist your study session?</h3>
      <p className="text-xs text-muted-foreground mb-6 leading-relaxed">
        Upload your study materials or share your screen. I monitor your focus and offer proactive guidance whenever you get stuck.
      </p>

      <div className="grid grid-cols-1 gap-2.5 w-full text-left">
        {STARTER_PROMPTS.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectPrompt(item.prompt)}
              className="group p-3 rounded-xl bg-card/60 hover:bg-card border border-border/50 hover:border-primary/40 transition-all duration-200 flex items-start gap-3 shadow-xs"
            >
              <div className="p-2 rounded-lg bg-muted text-muted-foreground group-hover:text-primary group-hover:bg-primary/10 transition-colors shrink-0">
                <Icon className="w-4 h-4" />
              </div>
              <div>
                <div className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors">
                  {item.label}
                </div>
                <div className="text-[11px] text-muted-foreground line-clamp-1 mt-0.5">
                  {item.prompt}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default ChatEmptyState;
