import { motion } from "motion/react";
import { ChevronDown } from "lucide-react";

export function HeroSection() {
  return (
    <section
      id="hero"
      className="relative min-h-screen flex flex-col items-center justify-center px-4 overflow-hidden"
    >
      <div className="absolute inset-0 grid-bg opacity-30" />

      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="relative z-10 text-center"
      >
        <motion.img
          src="/logo-full.png"
          alt="microbricks — powered by databricks"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="max-w-lg sm:max-w-2xl lg:max-w-4xl mx-auto mb-10"
        />

        <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto">
          A scalable app architecture pattern<p>from shared database to independent domains</p>
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3 text-sm text-muted-foreground">
          <span className="px-3 py-1 rounded-full border border-border bg-card/50">
            Domain Boundaries
          </span>
          <span className="px-3 py-1 rounded-full border border-border bg-card/50">
            Independent Releases
          </span>
          <span className="px-3 py-1 rounded-full border border-border bg-card/50">
            Isolated Data
          </span>
          <span className="px-3 py-1 rounded-full border border-border bg-card/50">
            Automated Lifecycle
          </span>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
        className="absolute bottom-8 flex flex-col items-center gap-2 text-muted-foreground"
      >
        <span className="text-xs">Scroll to explore</span>
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          <ChevronDown className="w-5 h-5" />
        </motion.div>
      </motion.div>
    </section>
  );
}
