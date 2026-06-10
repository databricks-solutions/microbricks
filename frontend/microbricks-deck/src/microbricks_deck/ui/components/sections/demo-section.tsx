import { motion } from "motion/react";
import { SectionContainer, SectionTitle } from "./section-container";
import { Code2, BookOpen, Blocks } from "lucide-react";

const RESOURCES = [
  {
    icon: Code2,
    title: "Source Code",
    description: "Full monorepo: services, BFF, frontends, CI/CD workflows, DAB configs, and Lakebase scripts.",
    tag: "github.com",
  },
  {
    icon: BookOpen,
    title: "Architecture Docs",
    description: "ARCHITECTURE.md, CONTRIBUTING.md, data model, and per-service READMEs.",
    tag: "docs",
  },
  {
    icon: Blocks,
    title: "This Presentation",
    description: "Built with the same stack: React 19, FastAPI, APX toolkit, deployed as a Databricks App.",
    tag: "microbricks-deck",
  },
];

export function DemoSection() {
  return (
    <SectionContainer id="demo">
      <SectionTitle
        badge="Resources"
        title="Try it yourself"
        subtitle="Everything is open and reproducible. Clone the repo, follow the README, deploy in 30 minutes."
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {RESOURCES.map((item, i) => (
          <motion.div
            key={item.tag}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.15 }}
            className="group glow-card rounded-xl border border-border bg-card p-6 hover:border-primary/30 transition-colors"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <item.icon className="w-5 h-5 text-primary" />
              </div>
            </div>
            <h3 className="font-semibold mb-1">{item.title}</h3>
            <p className="text-sm text-muted-foreground mb-3">{item.description}</p>
            <span className="inline-block text-[10px] font-mono text-primary px-2 py-0.5 rounded bg-primary/10 border border-primary/20">
              {item.tag}
            </span>
          </motion.div>
        ))}
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.5 }}
        className="mt-16 text-center"
      >
        <p className="text-sm text-muted-foreground">
          Databricks Apps + Lakebase + OBO Auth + DABs + GitHub Actions
        </p>
        <p className="text-xs text-muted-foreground/60 mt-2">
          microbricks — microservices on Databricks, done right
        </p>
      </motion.div>
    </SectionContainer>
  );
}
