import { motion } from "motion/react";
import { SectionContainer, SectionTitle } from "./section-container";
import { Target, Layers, Lightbulb, ArrowRight } from "lucide-react";

const PRINCIPLES = [
  {
    icon: Target,
    title: "Domain Ownership",
    description: "Each app gets its own Lakebase project independent schemas, independent migrations, independent release cycles. No cross-team coordination on data changes.",
  },
  {
    icon: Lightbulb,
    title: "Minimal Blast Radius",
    description: "A bad deploy or runaway migration affects one service only. The rest of the portfolio keeps running without intervention.",
  },
  {
    icon: Layers,
    title: "Automated Lifecycle",
    description: "Provisioning, branching, deployment, teardown all codified in CI/CD. New apps inherit the operating model, not rebuild it.",
  },
];

const BEFORE_AFTER = [
  { before: "All apps share one database", after: "Each service app owns its Lakebase project" },
  { before: "Schema changes require coordination", after: "Teams migrate independently" },
  { before: "One bad deploy risks all apps", after: "Blast radius = one service only" },
  { before: "Security is broad grants", after: "User identity flows end-to-end (OBO)" },
  { before: "Dev environments collide", after: "Every PR gets isolated data branches" },
  { before: "Deployment is manual and fragile", after: "Asset Bundles deploy N apps atomically" },
];

export function VisionSection() {
  return (
    <SectionContainer id="vision">
      <SectionTitle
        badge="The Solution"
        title="Give each app the right boundary"
        subtitle="MicroBricks is a reference architecture that scales your app portfolio by giving each domain its own data boundary, release cycle, and operating model with patterns you adopt incrementally."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
        {PRINCIPLES.map((p, i) => (
          <motion.div
            key={p.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.15 }}
            className="rounded-xl border border-border bg-card p-6 text-center"
          >
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-accent/10 mb-4">
              <p.icon className="w-6 h-6 text-accent" />
            </div>
            <h3 className="font-semibold text-lg mb-2">{p.title}</h3>
            <p className="text-sm text-muted-foreground">{p.description}</p>
          </motion.div>
        ))}
      </div>

      {/* Before → After comparison */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.3 }}
        className="rounded-xl border border-border bg-card overflow-hidden"
      >
        <div className="px-6 py-4 border-b border-border">
          <h3 className="font-semibold text-lg">Before → After</h3>
          <p className="text-sm text-muted-foreground mt-1">How each challenge maps to a concrete solution</p>
        </div>
        <div className="divide-y divide-border/50">
          {BEFORE_AFTER.map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.4 + i * 0.06 }}
              className="grid grid-cols-[1fr_auto_1fr] gap-4 items-center px-6 py-4"
            >
              <span className="text-sm text-muted-foreground">{item.before}</span>
              <ArrowRight className="w-4 h-4 text-primary shrink-0" />
              <span className="text-sm text-foreground font-medium">{item.after}</span>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Key message */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.6 }}
        className="mt-10 p-6 rounded-xl border border-accent/30 bg-accent/5 text-center"
      >
        <p className="text-lg font-semibold text-foreground">
          Each new app should make the platform stronger, not more fragile.
        </p>
        <p className="mt-3 text-sm text-muted-foreground max-w-2xl mx-auto">
          Add the right boundaries and automation so that scaling from 2 apps to 20 is an operational non-event
          with same patterns, same governance, same developer experience.
        </p>
      </motion.div>
    </SectionContainer>
  );
}
