import { BookOpen, BarChart3, Mic, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";

const steps = [
  {
    icon: Mic,
    num: "01",
    title: "Enable Audio & Video",
    description: "Grant microphone and camera access so Mind Tutor can listen and respond in real time.",
  },
  {
    icon: BookOpen,
    num: "02",
    title: "Stream Your Documents",
    description: "Upload or share your study materials and we'll present them in an interactive learning view.",
  },
  {
    icon: BarChart3,
    num: "03",
    title: "Track Your Progress",
    description: "Get insights on comprehension, retention, and areas needing attention.",
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
};

const item = {
  hidden: { opacity: 0, y: 20, filter: "blur(6px)" },
  show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] as const } },
};

const HowItWorks = () => {
  return (
    <section id="how-it-works" className="section-from-hero min-h-screen flex items-center py-32">
      <div className="container">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false, amount: 0.3 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-xl mx-auto mb-28"
        >
          <span className="inline-flex items-center gap-2 text-sm font-semibold text-primary tracking-wide uppercase mb-6">
            <div className="w-8 h-px bg-primary/40" />
            How It Works
            <div className="w-8 h-px bg-primary/40" />
          </span>
          <h2 className="text-3xl md:text-5xl font-bold leading-[1.2] text-foreground">
            Three steps to start learning
          </h2>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: false, amount: 0.2 }}
          className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto"
        >
          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              variants={item}
              className="group relative glass-card rounded-3xl p-8 hover:shadow-lg hover:shadow-primary/5 transition-shadow duration-500"
            >
              <div className="flex items-center justify-between mb-6">
                <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-300">
                  <step.icon className="w-5 h-5" />
                </div>
                <span className="text-4xl font-bold text-foreground/5 group-hover:text-primary/10 transition-colors">{step.num}</span>
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">{step.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>

              {i < steps.length - 1 && (
                <div className="hidden md:flex absolute -right-3 top-1/2 -translate-y-1/2 z-10 w-6 h-6 rounded-full bg-secondary items-center justify-center">
                  <ArrowRight className="w-3 h-3 text-muted-foreground" />
                </div>
              )}
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

export default HowItWorks;
