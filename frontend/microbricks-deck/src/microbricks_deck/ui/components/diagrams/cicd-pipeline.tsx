import { motion } from "motion/react";
import { ENVIRONMENTS, WORKFLOWS, KEY_PRACTICES, SERVICES } from "@/lib/content";

export function CicdPipelineDiagram() {
  return (
    <div className="w-full max-w-5xl mx-auto space-y-10">
      {/* ─── Deployment Flow Overview ─── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="rounded-xl border border-border bg-card p-6"
      >
        <h3 className="text-sm font-semibold mb-1">Continuous Deployment Flow</h3>
        <p className="text-sm text-muted-foreground mb-6">
          Code flows through three environments. Each environment has its own workspace, its own Lakebase branch strategy, and its own deployment trigger. No manual steps between merge and deploy.
        </p>

        {/* Git branch flow → environments */}
        <svg viewBox="0 0 800 80" className="w-full h-auto mb-6" fill="none">
          {/* Flow line */}
          <motion.line
            x1="60" y1="40" x2="740" y2="40"
            stroke="var(--border)" strokeWidth="2"
            initial={{ pathLength: 0 }}
            whileInView={{ pathLength: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          />
          {/* Nodes */}
          {[
            { x: 100, label: "feature/*", sublabel: "PR preview" },
            { x: 280, label: "develop", sublabel: "→ DEV" },
            { x: 460, label: "release/*", sublabel: "→ TEST" },
            { x: 640, label: "tag v*", sublabel: "→ PROD" },
          ].map((node, i) => (
            <motion.g
              key={node.label}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3 + i * 0.15 }}
            >
              <circle cx={node.x} cy="40" r="8" fill="var(--primary)" opacity="0.8" />
              <text x={node.x} y="20" textAnchor="middle" fill="var(--foreground)" className="text-sm font-medium">{node.label}</text>
              <text x={node.x} y="65" textAnchor="middle" fill="var(--muted-foreground)" className="text-[9px]">{node.sublabel}</text>
            </motion.g>
          ))}
          {/* Arrows between nodes */}
          {[180, 360, 540].map((x, i) => (
            <motion.polygon
              key={i}
              points={`${x},36 ${x + 12},40 ${x},44`}
              fill="var(--muted-foreground)"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.6 + i * 0.15 }}
            />
          ))}
        </svg>

        {/* Environment detail cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {ENVIRONMENTS.map((env, i) => (
            <motion.div
              key={env.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.5 + i * 0.15 }}
              className="rounded-lg border border-border p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: env.color }} />
                <span className="font-bold text-sm">{env.name}</span>
              </div>
              <p className="text-sm text-muted-foreground mb-3">{env.purpose}</p>
              <div className="space-y-2 text-sm">
                <div className="flex flex-col gap-0.5">
                  <span className="text-muted-foreground uppercase tracking-wider text-[9px]">Deploy trigger</span>
                  <span className="text-foreground">{env.deploy}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-muted-foreground uppercase tracking-wider text-[9px]">Lakebase strategy</span>
                  <span className="text-foreground">{env.lakebase}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ─── Lakebase Branching Strategy ─── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.2 }}
        className="rounded-xl border border-border bg-card p-6"
      >
        <h3 className="text-sm font-semibold mb-1">Lakebase Branching — One Project per Service</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Each service owns a dedicated Lakebase project with its own protected production branch.
          For PRs and E2E verification, isolated branches are created within each project (copy-on-write from production).
          No shared schemas — services are fully independent at the data layer.
        </p>

        {/* Per-service project diagram */}
        <svg viewBox="0 0 750 300" className="w-full h-auto" fill="none">
          <defs>
            {/* Animated pulse traveling along production branch */}
            {SERVICES.map((_, i) => {
              const y = 50 + i * 65;
              return (
                <motion.circle
                  key={`pulse-${i}`}
                  r="3"
                  fill="oklch(0.72 0.16 145)"
                  filter="url(#glow-green)"
                  animate={{ cx: [140, 480], cy: [y, y] }}
                  transition={{ duration: 3, delay: i * 0.7, repeat: Infinity, repeatDelay: 1, ease: "linear" }}
                />
              );
            })}
            <filter id="glow-green" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="glow-primary" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="1.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Service project rows */}
          {SERVICES.map((svc, i) => {
            const y = 50 + i * 65;
            return (
              <motion.g
                key={svc.name}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.4 + i * 0.12 }}
              >
                {/* Project label */}
                <motion.rect
                  x="30" y={y - 10} width="90" height="22" rx="4"
                  fill={`${svc.color}20`} stroke={svc.color} strokeWidth="1"
                  animate={{ opacity: [0.6, 1, 0.6] }}
                  transition={{ duration: 3, delay: i * 0.5, repeat: Infinity, ease: "easeInOut" }}
                />
                <text x="75" y={y + 5} textAnchor="middle" fill={svc.color} className="text-[9px] font-semibold">{svc.name}</text>

                {/* Production branch line */}
                <line x1="140" y1={y} x2="480" y2={y} stroke="oklch(0.72 0.16 145)" strokeWidth="2" />
                <motion.circle
                  cx="150" cy={y} r="4" fill="oklch(0.72 0.16 145)"
                  animate={{ scale: [1, 1.3, 1] }}
                  transition={{ duration: 2, delay: i * 0.3, repeat: Infinity, ease: "easeInOut" }}
                />
                <text x="165" y={y - 8} fill="oklch(0.72 0.16 145)" className="text-[8px]">production</text>

                {/* Feature branch forking off — animated draw */}
                <motion.path
                  d={`M 300 ${y} C 310 ${y} 315 ${y + 20} 325 ${y + 20} L 420 ${y + 20}`}
                  stroke="var(--primary)" strokeWidth="1.5" strokeDasharray="3 2" fill="none"
                  initial={{ pathLength: 0, opacity: 0 }}
                  whileInView={{ pathLength: 1, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 1.2, delay: 0.8 + i * 0.15, ease: "easeOut" }}
                />
                <motion.circle
                  cx="420" cy={y + 20} r="3" fill="var(--primary)"
                  filter="url(#glow-primary)"
                  initial={{ scale: 0, opacity: 0 }}
                  whileInView={{ scale: 1, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: 1.8 + i * 0.15 }}
                  style={{ transformOrigin: `420px ${y + 20}px` }}
                />
                <motion.text
                  x="430" y={y + 24} fill="var(--primary)" className="text-[8px]"
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 2.0 + i * 0.15 }}
                >feat-hc-42</motion.text>

                {/* E2E branch forking off — animated draw */}
                <motion.path
                  d={`M 390 ${y} C 400 ${y} 405 ${y - 18} 415 ${y - 18} L 480 ${y - 18}`}
                  stroke="oklch(0.78 0.16 75)" strokeWidth="1.5" strokeDasharray="3 2" fill="none"
                  initial={{ pathLength: 0, opacity: 0 }}
                  whileInView={{ pathLength: 1, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 1.2, delay: 1.2 + i * 0.15, ease: "easeOut" }}
                />
                <motion.circle
                  cx="480" cy={y - 18} r="3" fill="oklch(0.78 0.16 75)"
                  initial={{ scale: 0, opacity: 0 }}
                  whileInView={{ scale: 1, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: 2.2 + i * 0.15 }}
                  style={{ transformOrigin: `480px ${y - 18}px` }}
                />
                <motion.text
                  x="490" y={y - 14} fill="oklch(0.78 0.16 75)" className="text-[8px]"
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 2.4 + i * 0.15 }}
                >e2e-1-2-0</motion.text>

                {/* Animated pulse on production line */}
                <motion.circle
                  r="3"
                  fill="oklch(0.72 0.16 145)"
                  filter="url(#glow-green)"
                  animate={{ cx: [140, 480], cy: [y, y], opacity: [0, 1, 1, 0] }}
                  transition={{ duration: 3, delay: i * 0.7, repeat: Infinity, repeatDelay: 1.5, ease: "linear" }}
                />
              </motion.g>
            );
          })}

          {/* Legend */}
          <motion.g
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 1.0 }}
          >
            <rect x="550" y="50" width="170" height="90" rx="6" fill="var(--card)" stroke="var(--border)" strokeWidth="1" />
            <text x="565" y="68" fill="var(--foreground)" className="text-[9px] font-semibold">Legend</text>
            <line x1="565" y1="80" x2="590" y2="80" stroke="oklch(0.72 0.16 145)" strokeWidth="2" />
            <text x="598" y="84" fill="var(--muted-foreground)" className="text-[8px]">production (protected)</text>
            <line x1="565" y1="100" x2="590" y2="100" stroke="var(--primary)" strokeWidth="1.5" strokeDasharray="3 2" />
            <text x="598" y="104" fill="var(--muted-foreground)" className="text-[8px]">feat-* (PR isolation)</text>
            <line x1="565" y1="120" x2="590" y2="120" stroke="oklch(0.78 0.16 75)" strokeWidth="1.5" strokeDasharray="3 2" />
            <text x="598" y="124" fill="var(--muted-foreground)" className="text-[8px]">e2e-* (deploy verification)</text>
          </motion.g>

          {/* Footer */}
          <motion.g
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 1.2 }}
          >
            <rect x="50" y="280" width="650" height="1" fill="var(--border)" />
            <text x="375" y="296" textAnchor="middle" fill="var(--muted-foreground)" className="text-[10px]">
              Each service = dedicated Lakebase project → isolated branches for PRs and E2E verification → auto-destroyed on completion
            </text>
          </motion.g>
        </svg>

        {/* Why this matters */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
          {[
            { title: "Domain ownership", detail: "Each service owns its Lakebase project. No shared schemas, no cross-service migration conflicts." },
            { title: "Isolated testing", detail: "Feature and E2E branches are copy-on-write per project — tests run against real schema state independently." },
            { title: "Zero cleanup debt", detail: "Branches are auto-destroyed (24h TTL + explicit teardown). No orphaned test databases accumulating." },
          ].map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 1.4 + i * 0.1 }}
              className="flex items-start gap-2 p-3 rounded-lg border border-border bg-card/50"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0 mt-1.5" />
              <div>
                <span className="text-sm font-medium text-foreground">{item.title}</span>
                <p className="text-sm text-muted-foreground mt-0.5">{item.detail}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ─── Two-Phase E2E Deploy (TEST/PROD) ─── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.2 }}
        className="rounded-xl border border-border bg-card p-6"
      >
        <h3 className="text-sm font-semibold mb-1">Two-Phase E2E Verification (TEST & PROD)</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Before deploying permanently, an ephemeral verification phase proves migrations and app startup work in isolation.
          Schema evolution scripts run in both phases — first on ephemeral branches (gate), then on the real production branch (deployment).
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Phase 1 */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.4 }}
            className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4"
          >
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-full bg-amber-500/20 text-amber-600 text-sm font-bold flex items-center justify-center">1</div>
              <span className="text-sm font-semibold text-foreground">E2E Verify (ephemeral gate)</span>
            </div>
            <div className="space-y-2">
              {[
                "Create ephemeral Lakebase branches (e2e-*)",
                "Run Alembic migrations against isolated data",
                "Deploy temporary apps with suffix (-e2e-<slug>)",
                "Smoke-test all /healthz endpoints",
                "Tear down ephemeral apps + branches (always)",
              ].map((step, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="w-1 h-1 rounded-full bg-amber-500 shrink-0 mt-1.5" />
                  <span className="text-sm text-muted-foreground">{step}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Phase 2 */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
            className="rounded-lg border border-green-500/30 bg-green-500/5 p-4"
          >
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-full bg-green-500/20 text-green-600 text-sm font-bold flex items-center justify-center">2</div>
              <span className="text-sm font-semibold text-foreground">Permanent Deploy (only if Phase 1 passes)</span>
            </div>
            <div className="space-y-2">
              {[
                "Run migrations against production Lakebase branch",
                "Deploy stable apps (no suffix)",
                "Wait for RUNNING state",
                "Smoke-test all /healthz endpoints",
                "Resolve portal URL for environment link",
              ].map((step, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="w-1 h-1 rounded-full bg-green-500 shrink-0 mt-1.5" />
                  <span className="text-sm text-muted-foreground">{step}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Flow arrow between phases */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.6 }}
          className="flex items-center justify-center my-3 md:hidden"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M12 5v14M5 12l7 7 7-7" stroke="var(--muted-foreground)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.7 }}
          className="text-sm text-muted-foreground text-center mt-4 border-t border-border pt-3"
        >
          Ephemeral branches use isolated DAB targets (e2e-test / e2e-prod) with separate root_paths — <code className="text-primary">bundle destroy</code> only touches the ephemeral state.
        </motion.p>
      </motion.div>

      {/* ─── PR Preview Environments ─── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.3 }}
        className="rounded-xl border border-primary/20 bg-primary/5 p-6"
      >
        <h3 className="text-sm font-semibold mb-1">PR Preview Environments</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Every pull request gets a fully functional preview — apps deployed, databases branched, health-checked.
          Reviewers can test the feature end-to-end before it hits develop.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          {[
            { step: "1", label: "PR opens", detail: "CI detects changed services" },
            { step: "2", label: "Provision", detail: "Lakebase branches + preview apps per service" },
            { step: "3", label: "Validate", detail: "Deploy, run migrations, smoke-check health endpoints" },
            { step: "4", label: "PR closes", detail: "Destroy preview apps + Lakebase branches" },
          ].map((item, i) => (
            <motion.div
              key={item.step}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.5 + i * 0.1 }}
              className="text-center p-3 rounded-lg border border-primary/20 bg-background/50"
            >
              <div className="w-7 h-7 rounded-full bg-primary/10 text-primary text-sm font-bold flex items-center justify-center mx-auto mb-2">
                {item.step}
              </div>
              <span className="text-sm font-medium text-foreground block">{item.label}</span>
              <span className="text-sm text-muted-foreground">{item.detail}</span>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ─── GitHub Actions Workflows Table ─── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.3 }}
        className="rounded-xl border border-border bg-card overflow-hidden"
      >
        <div className="px-6 py-4 border-b border-border">
          <h3 className="text-sm font-semibold">GitHub Actions Workflows</h3>
          <p className="text-sm text-muted-foreground">Six workflows cover the full lifecycle — from PR validation to nightly cleanup.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Workflow</th>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Trigger</th>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">What it does</th>
              </tr>
            </thead>
            <tbody>
              {WORKFLOWS.map((wf, i) => (
                <motion.tr
                  key={wf.name}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.4 + i * 0.06 }}
                  className="border-b border-border/50 hover:bg-muted/20 transition-colors"
                >
                  <td className="px-4 py-2.5 font-mono text-primary">{wf.name}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">{wf.trigger}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">{wf.purpose}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* ─── Key Practices ─── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.5 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-3"
      >
        {KEY_PRACTICES.map((practice, i) => (
          <motion.div
            key={practice}
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.6 + i * 0.08 }}
            className="flex items-center gap-2 p-3 rounded-lg border border-border bg-card/50"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
            <span className="text-sm text-muted-foreground">{practice}</span>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}

export function LakebaseBranchDiagram() {
  return null;
}
