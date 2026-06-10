import { motion } from "motion/react";
import { SectionContainer, SectionTitle } from "./section-container";
import { TECH_STACK } from "@/lib/content";
import { Cpu, HardDrive, Rocket } from "lucide-react";

const CATEGORY_META = {
  compute: { label: "Compute & Code", icon: Cpu },
  data: { label: "Data & Security", icon: HardDrive },
  deploy: { label: "Deploy & Operate", icon: Rocket },
} as const;

const CODE_SNIPPET = `# Every service follows the same pattern
services/<name>/
  src/<name>/
    app.py          # FastAPI + create_app()
    auth.py         # OBO token extraction
    db.py           # Per-user connection pool
    routers/        # CRUD endpoints
  migrations/       # Alembic schema
  tests/            # pytest + respx
  seed/             # Synthetic data`;

const MONOREPO_RULES = [
  "No backend-to-backend HTTP calls",
  "No shared Python libraries across services",
  "No cross-DB foreign keys — UUIDs only",
  "CODEOWNERS enforces per-service approval",
  "Path-filtered CI — only changed services build",
];

export function ImplementationSection() {
  return (
    <SectionContainer id="implementation" fullHeight={false}>
      <SectionTitle
        badge="Implementation"
        title="Tech stack & structure"
        subtitle="Production-grade tooling in a monorepo that stays manageable as services grow."
      />

      {/* Tech stack grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
        {(Object.keys(TECH_STACK) as Array<keyof typeof TECH_STACK>).map((key, catIdx) => {
          const meta = CATEGORY_META[key];
          const items = TECH_STACK[key];
          return (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: catIdx * 0.15 }}
              className="rounded-xl border border-border bg-card p-5"
            >
              <div className="flex items-center gap-2 mb-4">
                <meta.icon className="w-4 h-4 text-primary" />
                <span className="font-medium text-sm">{meta.label}</span>
              </div>
              <div className="space-y-2">
                {items.map((item) => (
                  <div key={item.name} className="flex items-center justify-between">
                    <span className="text-sm">{item.name}</span>
                    <span className="text-sm text-muted-foreground px-2 py-0.5 rounded bg-muted">
                      {item.category}
                    </span>
                  </div>
                ))}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Code structure */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          className="rounded-xl border border-border bg-card p-5"
        >
          <h3 className="font-medium text-sm mb-3">Service pattern</h3>
          <pre className="text-sm leading-relaxed text-muted-foreground overflow-x-auto font-mono bg-muted/30 rounded-lg p-4">
            {CODE_SNIPPET}
          </pre>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          className="rounded-xl border border-border bg-card p-5"
        >
          <h3 className="font-medium text-sm mb-3">Monorepo discipline</h3>
          <ul className="space-y-3">
            {MONOREPO_RULES.map((rule, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: 10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className="flex items-start gap-2 text-sm text-muted-foreground"
              >
                <span className="text-primary font-mono text-sm mt-0.5">{String(i + 1).padStart(2, "0")}</span>
                <span>{rule}</span>
              </motion.li>
            ))}
          </ul>
        </motion.div>
      </div>
    </SectionContainer>
  );
}
