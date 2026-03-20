import { Zap, Brain, Clock, Shield } from "lucide-react";
import { motion } from "framer-motion";

const benefits = [
  { icon: Brain, title: "Adaptive Learning", desc: "AI adjusts difficulty and pace based on your real-time performance." },
  { icon: Zap, title: "Instant Feedback", desc: "Get corrections and explanations the moment you need them." },
  { icon: Clock, title: "Study Anytime", desc: "24/7 access — learn at your own schedule, at your own speed." },
  { icon: Shield, title: "Private & Secure", desc: "Your data stays yours. End-to-end encrypted sessions." },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 16, filter: "blur(4px)" },
  show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] as const } },
};

const BenefitsSection = () => {
  return (
    <section id="benefits" className="arch-to-dark min-h-screen flex items-center py-32">
      <div className="container">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false, amount: 0.3 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-xl mx-auto mb-28"
        >
          <span className="inline-flex items-center gap-2 text-sm font-semibold text-white/70 tracking-wide uppercase mb-6">
            <div className="w-8 h-px bg-white/40" />
            Benefits
            <div className="w-8 h-px bg-white/40" />
          </span>
          <h2 className="text-3xl md:text-5xl font-bold leading-[1.2] bg-gradient-to-b from-white to-white/60 bg-clip-text text-transparent">
            Why learners choose Mind Tutor
          </h2>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: false, amount: 0.2 }}
          className="grid sm:grid-cols-2 gap-5 max-w-3xl mx-auto"
        >
          {benefits.map((b) => (
            <motion.div
              key={b.title}
              variants={item}
              className="group glass-card rounded-2xl p-6 flex gap-4 hover:shadow-lg hover:shadow-primary/5 transition-shadow duration-500"
            >
              <div className="w-11 h-11 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-300">
                <b.icon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-white mb-1">{b.title}</h3>
                <p className="text-sm text-white/65 leading-relaxed">{b.desc}</p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

export default BenefitsSection;
