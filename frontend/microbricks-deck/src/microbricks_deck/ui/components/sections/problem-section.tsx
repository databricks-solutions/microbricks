import { motion } from "motion/react";
import { SectionContainer, SectionTitle } from "./section-container";
import {
  Database,
  GitMerge,
  Users,
  AlertTriangle,
  Lock,
  GitBranch,
} from "lucide-react";

type PainPoint = {
  icon: typeof Database;
  category: string;
  title: string;
  description: string;
  cost: string;
};

const PAIN_POINTS: PainPoint[] = [
  {
    icon: Database,
    category: "Data",
    title: "The database becomes the coupling point",
    description:
      "All apps reading and writing the same tables creates invisible dependencies. A column rename for App A breaks App B's queries. Table growth from one app degrades performance for all others.",
    cost: "Every app is tied to every other app's release schedule.",
  },
  {
    icon: GitMerge,
    category: "Releases",
    title: "Schema changes require coordination",
    description:
      "A migration for one app can break another app's assumptions. Teams start negotiating database changes instead of shipping features. Rollbacks become dangerous when multiple apps depend on the same schema.",
    cost: "Independent apps still deploy at the speed of the slowest team.",
  },
  {
    icon: Users,
    category: "Ownership",
    title: "No clear owner for shared tables",
    description:
      "When multiple apps write to the same schema, ownership is ambiguous. New teams inherit tables they didn't design. Conventions drift. Nobody can confidently evolve the data model.",
    cost: "More apps means more negotiation, not more autonomy.",
  },
  {
    icon: AlertTriangle,
    category: "Blast radius",
    title: "One bad deploy affects everything",
    description:
      "A poorly tested migration or a runaway query from one app can take down the shared database for all apps. There's no isolation between workloads — one team's mistake is everyone's outage.",
    cost: "Risk grows linearly with each new app on the shared database.",
  },
  {
    icon: Lock,
    category: "Security",
    title: "Access control becomes all-or-nothing",
    description:
      "Granting one app access to the database often means granting access to all tables. Fine-grained permissions are hard to maintain across many apps. Audit trails blur across service boundaries.",
    cost: "Least-privilege gets harder as the app portfolio grows.",
  },
  {
    icon: GitBranch,
    category: "Dev loop",
    title: "Testing without collision is impossible",
    description:
      "Multiple developers working on different apps share the same dev database. Feature branches overwrite each other's test data. There's no way to get a clean, isolated environment per feature without manual setup.",
    cost: "Teams choose between fast iteration and reliable testing.",
  },
];

export function ProblemSection() {
  return (
    <SectionContainer id="problem">
      <SectionTitle
        badge="The Challenge"
        title="Multiple Apps, One Database — What Breaks at Scale?"
        subtitle="Your first app on Lakebase is simple. But as the app portfolio grows, the shared database becomes the coupling point slowing releases, blurring ownership, and expanding blast radius."
      />

      {/* The starting scenario */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="mb-10 p-6 sm:p-8 rounded-xl border border-border bg-card/40"
      >
        <h3 className="text-lg font-semibold text-foreground mb-3">You've been here</h3>
        <p className="text-base leading-relaxed text-muted-foreground">
          The first app connects, works perfectly. Then a second team needs their
          own tables. Then a third app with different access patterns. Before long
          every migration requires cross-team coordination, every deploy carries
          shared risk, and dev environments are stepping on each other.{" "}
          <span className="text-foreground font-medium">
            The database that made the first app easy now makes the fifth app hard.
          </span>
        </p>
      </motion.div>

      {/* Visual: before state */}
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.2 }}
        className="mb-10"
      >
        <svg viewBox="0 0 800 220" className="w-full max-w-3xl mx-auto h-auto" fill="none">
          {/* Central DB */}
          <motion.g
            initial={{ scale: 0.9, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <ellipse cx="400" cy="130" rx="70" ry="18" fill="oklch(0.65 0.2 25 / 0.12)" stroke="oklch(0.65 0.2 25 / 0.7)" strokeWidth="2" />
            <rect x="330" y="130" width="140" height="40" fill="oklch(0.65 0.2 25 / 0.12)" stroke="none" />
            <line x1="330" y1="130" x2="330" y2="170" stroke="oklch(0.65 0.2 25 / 0.7)" strokeWidth="2" />
            <line x1="470" y1="130" x2="470" y2="170" stroke="oklch(0.65 0.2 25 / 0.7)" strokeWidth="2" />
            <ellipse cx="400" cy="170" rx="70" ry="18" fill="oklch(0.65 0.2 25 / 0.12)" stroke="oklch(0.65 0.2 25 / 0.7)" strokeWidth="2" />
            <text x="400" y="155" textAnchor="middle" fill="oklch(0.65 0.2 25)" className="text-[12px] font-semibold">Shared Database</text>
          </motion.g>

          {/* Apps pointing to it — octagonal shape */}
          {["App A", "App B", "App C", "App D", "App E"].map((app, i) => {
            const cx = 120 + i * 140;
            const cy = 48;
            const w = 40;
            const h = 18;
            const c = 10;
            const points = `${cx - w + c},${cy - h} ${cx + w - c},${cy - h} ${cx + w},${cy - h + c} ${cx + w},${cy + h - c} ${cx + w - c},${cy + h} ${cx - w + c},${cy + h} ${cx - w},${cy + h - c} ${cx - w},${cy - h + c}`;
            return (
              <motion.g
                key={app}
                initial={{ opacity: 0, y: -20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.5 + i * 0.1 }}
              >
                <polygon points={points} fill="var(--card)" stroke="var(--border)" strokeWidth="1.5" />
                <text x={cx} y={cy + 4} textAnchor="middle" fill="var(--foreground)" className="text-sm font-medium">{app}</text>
                <line x1={cx} y1={cy + h} x2="400" y2="112" stroke="oklch(0.65 0.2 25 / 0.5)" strokeWidth="1.5" strokeDasharray="4 3" />
              </motion.g>
            );
          })}

          {/* Danger label */}
          <motion.text
            x="400" y="210"
            textAnchor="middle"
            fill="oklch(0.65 0.2 25 / 0.85)"
            className="text-sm"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 1 }}
          >
            Every app coupled to the same schema, same release cycle, same blast radius
          </motion.text>
        </svg>
      </motion.div>

      {/* Pain points grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {PAIN_POINTS.map((point, i) => (
          <motion.div
            key={point.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.08, duration: 0.5 }}
            className="glow-card rounded-xl border border-border bg-card p-6 flex flex-col h-full"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="shrink-0 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <point.icon className="w-5 h-5 text-primary" />
              </div>
              <span className="text-sm uppercase tracking-wider text-muted-foreground">
                {point.category}
              </span>
            </div>
            <h3 className="font-semibold text-lg leading-snug">{point.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              {point.description}
            </p>
            <div className="mt-auto pt-4">
              <div className="pt-4 border-t border-border/60">
                <p className="text-sm leading-relaxed">
                  <span className="text-muted-foreground uppercase tracking-wider">
                    Impact:{" "}
                  </span>
                  <span className="text-foreground">{point.cost}</span>
                </p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Closing statement */}
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.5 }}
        className="mt-12 p-8 rounded-xl border border-primary/20 bg-primary/5 text-center"
      >
        <p className="text-xl font-semibold text-foreground">
          The question isn't whether to grow your app portfolio — it's how to do it without the shared database becoming the bottleneck.
        </p>
        <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
          Each app needs to move independently — own its schema, own its release cycle, own its blast radius — while sharing the same governance and identity model.
        </p>
      </motion.div>
    </SectionContainer>
  );
}
