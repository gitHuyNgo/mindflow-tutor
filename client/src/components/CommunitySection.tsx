import { Users, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

const CommunitySection = () => {
  return (
    <section id="community" className="relative flex flex-col min-h-screen overflow-hidden">
      {/* Background video */}
      <video
        className="absolute inset-0 w-full h-full object-cover"
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260306_074215_04640ca7-042c-45d6-bb56-58b1e8a42489.mp4"
        autoPlay
        loop
        muted
        playsInline
      />

      {/* Community content */}
      <div className="relative z-10 flex-1 flex items-center justify-center py-20">
        <div className="container flex flex-col items-center">
          <motion.div
            initial={{ opacity: 0, y: 20, filter: "blur(6px)" }}
            whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            viewport={{ once: false, amount: 0.3 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="max-w-2xl mx-auto text-center -translate-y-[10px]"
            style={{ paddingBottom: "250px" }}
          >
            <div className="w-16 h-16 rounded-2xl glass-card text-primary flex items-center justify-center mx-auto mb-6">
              <Users className="w-7 h-7" />
            </div>

            <h2 className="text-3xl md:text-5xl font-bold leading-[1.2] text-white mb-4">
              Join a growing community
            </h2>
            <p className="text-lg text-white/60 leading-relaxed max-w-lg mx-auto mb-10">
              Connect with fellow students, share study techniques, and learn together in a supportive environment.
            </p>

            <Button variant="hero" size="lg">
              Join the Community
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </motion.div>
        </div>
      </div>

      {/* Dark gradient at bottom for footer legibility */}
      <div className="absolute inset-x-0 bottom-0 h-32 z-[1]" style={{ background: "linear-gradient(to bottom, transparent, rgba(0,0,0,0.75))" }} />

      {/* Footer — gắn liền với section */}
      <footer className="relative z-10 border-t border-white/10 py-4" style={{ zoom: 0.7 }}>
        <div className="container flex flex-col items-center gap-6 text-sm text-white/30">
          <div className="flex items-center gap-2">
            <div className="gold-dot" />
            <span className="font-semibold text-white/40">Mind Tutor</span>
          </div>
          <div className="flex flex-wrap justify-center gap-8">
            {["Privacy Policy", "Terms of Service", "Help Center", "Contact Us"].map((link) => (
              <a key={link} href="#" className="text-white/30 hover:text-white/60 transition-colors">
                {link}
              </a>
            ))}
          </div>
          <p className="text-white/25">© 2026 Mind Tutor. All rights reserved.</p>
        </div>
      </footer>
    </section>
  );
};

export default CommunitySection;
