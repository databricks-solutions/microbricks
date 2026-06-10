import { motion } from "motion/react";
import { SectionContainer, SectionTitle } from "./section-container";
import { ServiceTopologyDiagram } from "@/components/diagrams/service-topology";
import { Shield, Database, Workflow, Ban } from "lucide-react";

const PRINCIPLES = [
  {
    icon: Database,
    title: "Database per Service",
    description: "Each microservice owns a Lakebase Postgres project. No shared schemas, no cross-service foreign keys — full isolation.",
  },
  {
    icon: Workflow,
    title: "BFF Orchestration",
    description: "A Backend-for-Frontend fans out to services. All joins happen in-memory at the BFF layer.",
  },
  {
    icon: Shield,
    title: "OBO Identity Passthrough",
    description: "The user's OAuth token travels from browser to database. Unity Catalog enforces row-level access. No service accounts.",
  },
  {
    icon: Ban,
    title: "No Backend-to-Backend",
    description: "Services never call each other. Cross-service references are UUIDs only. No distributed transactions needed.",
  },
];

const RECOMMENDATIONS = [
  { label: "Scale-to-zero", detail: "Independent scaling per service. Small blast radius — a change in one service won't break the others." },
  { label: "Independent deployability", detail: "Each service has its own compute, its own release cycle. No noisy neighbors, no coordinated deploys." },
  { label: "Fast API composition", detail: "BFF calls service APIs concurrently (~50-60ms) and joins results in-memory. No cross-database queries." },
];

export function ArchitectureSection() {
  return (
    <SectionContainer id="architecture" fullHeight={false}>
      <SectionTitle
        badge="Architecture"
        title="BFF / Microservices Network View"
        subtitle="Front-end apps call domain services APIs through the BFF. Each service owns its Lakebase project. Cross-domain views are composed in the BFF. No cross database joins and no backend-to-backend calls."
      />

      <ServiceTopologyDiagram />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-12">
        {PRINCIPLES.map((p, i) => (
          <motion.div
            key={p.title}
            initial={{ opacity: 0, x: i % 2 === 0 ? -20 : 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
            className="flex items-start gap-3 p-4 rounded-lg border border-border bg-card/50"
          >
            <p.icon className="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-sm">{p.title}</h4>
              <p className="text-sm text-muted-foreground mt-1">{p.description}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Recommendation box */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.5 }}
        className="mt-8 rounded-xl border border-accent/30 bg-accent/5 p-6"
      >
        <h3 className="text-sm font-semibold text-accent mb-4">Why this pattern scales</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {RECOMMENDATIONS.map((rec, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0 mt-1.5" />
              <div>
                <span className="text-sm font-medium text-foreground">{rec.label}</span>
                <p className="text-sm text-muted-foreground mt-0.5">{rec.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </SectionContainer>
  );
}
