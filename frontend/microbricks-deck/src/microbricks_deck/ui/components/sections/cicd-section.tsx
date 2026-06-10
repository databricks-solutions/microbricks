import { SectionContainer, SectionTitle } from "./section-container";
import { CicdPipelineDiagram } from "@/components/diagrams/cicd-pipeline";

export function CicdSection() {
  return (
    <SectionContainer id="cicd" fullHeight={false}>
      <SectionTitle
        badge="CI/CD & Deployment"
        title="Continuous Deployment + Lakebase Branching"
        subtitle="Every merge deploys automatically. Every PR gets isolated data. The operating model scales with the app portfolio — adding a new service doesn't require new CI/CD work."
      />

      <CicdPipelineDiagram />
    </SectionContainer>
  );
}
