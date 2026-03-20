import { Button } from "@/components/ui/button";
import { ArrowRight, Play } from "lucide-react";
import { motion } from "framer-motion";

interface HeroSectionProps {
  onStartLearning: () => void;
}

const HeroSection = ({ onStartLearning }: HeroSectionProps) => {
  return (
    <section className="hero-arch relative min-h-screen flex items-center justify-center">
      {/* Decorative blobs — overflow-hidden scoped here only */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-32 right-[15%] w-[400px] h-[400px] rounded-full bg-primary/8 blur-[100px] animate-float" />
        <div className="absolute bottom-20 left-[10%] w-[300px] h-[300px] rounded-full bg-gold/10 blur-[80px] animate-float" style={{ animationDelay: "3s" }} />
      </div>

      <div className="container relative z-10">
        <div className="max-w-3xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 24, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="space-y-8"
          >
            <div className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium text-white/80"
              style={{
                background: "rgba(255,255,255,0.08)",
                backdropFilter: "blur(28px) saturate(180%)",
                WebkitBackdropFilter: "blur(28px) saturate(180%)",
                border: "1px solid rgba(255,255,255,0.18)",
                boxShadow: "inset 0 1px 0 rgba(255,255,255,0.15), 0 2px 12px rgba(0,0,0,0.25)",
              }}
            >
              <div className="gold-dot" />
              AI Companion Active
            </div>

            <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold leading-[1.3] text-white">
              Stay focused. Learn with
              <span className="block bg-gradient-to-r from-primary to-blue-vibrant bg-clip-text text-transparent pb-[0.25em]">
                an AI that understands you.
              </span>
            </h1>

            <p className="text-base md:text-lg text-white/40 font-medium italic">
              It doesn't interrupt. It appears when you need it.
            </p>

            <p className="text-base md:text-lg text-white/60 max-w-lg mx-auto leading-relaxed">
              Track your focus in real time, get gentle guidance when you're stuck, and stay in flow with voice-based support.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-wrap justify-center gap-4 mt-14"
          >
            <Button variant="hero-glass" size="lg">
              <Play className="w-4 h-4 mr-1" />
              How It Works
            </Button>
            <Button
              variant="hero-glass"
              size="lg"
              className="bg-primary/35 border-primary/55 hover:bg-primary/48 shadow-lg shadow-primary/25"
              onClick={onStartLearning}
            >
              Start Learning
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </motion.div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
