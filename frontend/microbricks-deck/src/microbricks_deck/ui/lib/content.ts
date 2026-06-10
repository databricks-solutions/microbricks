export const SECTIONS = [
  { id: "hero", label: "Start" },
  { id: "problem", label: "Problem" },
  { id: "vision", label: "Vision" },
  { id: "architecture", label: "Architecture" },
  { id: "cicd", label: "CI/CD" },
  { id: "implementation", label: "Implementation" },
  { id: "demo", label: "Resources" },
] as const;

export type SectionId = (typeof SECTIONS)[number]["id"];

export const SERVICES = [
  { name: "Service A", color: "oklch(0.7 0.18 250)", description: "Domain boundary A" },
  { name: "Service B", color: "oklch(0.7 0.15 175)", description: "Domain boundary B" },
  { name: "Service C", color: "oklch(0.7 0.16 145)", description: "Domain boundary C" },
  { name: "Service D", color: "oklch(0.7 0.16 300)", description: "Domain boundary D" },
] as const;

export const CLIENTS = [
  { name: "API", icon: "terminal" },
  { name: "Portal", icon: "layout" },
  { name: "Web App", icon: "globe" },
] as const;

export const TECH_STACK = {
  compute: [
    { name: "Databricks Apps", category: "Platform" },
    { name: "FastAPI", category: "Backend" },
    { name: "React 19", category: "Frontend" },
    { name: "TypeScript", category: "Language" },
  ],
  data: [
    { name: "Lakebase Postgres", category: "Database" },
    { name: "Unity Catalog", category: "Governance" },
    { name: "OBO Auth", category: "Security" },
    { name: "Alembic", category: "Migrations" },
  ],
  deploy: [
    { name: "DABs", category: "IaC" },
    { name: "GitHub Actions", category: "CI/CD" },
    { name: "GitFlow", category: "Branching" },
    { name: "APX Toolkit", category: "Scaffold" },
  ],
} as const;

export const ENVIRONMENTS = [
  {
    name: "DEV",
    trigger: "Push to develop",
    color: "oklch(0.7 0.18 250)",
    purpose: "Integration testing. Every merged PR lands here first. Lakebase branches allow parallel feature work without collision.",
    lakebase: "Protected production branch + ephemeral feature branches per PR",
    deploy: "Automatic on merge to develop",
  },
  {
    name: "TEST",
    trigger: "Push to release/* or main",
    color: "oklch(0.78 0.16 75)",
    purpose: "Pre-production validation. Two-phase deploy: ephemeral E2E verification gates the permanent deploy. Migrations tested in isolation first.",
    lakebase: "Ephemeral e2e-* branches for verification, then production branch for real deploy",
    deploy: "Automatic: E2E verify → permanent deploy",
  },
  {
    name: "PROD",
    trigger: "Tag v* + manual approval",
    color: "oklch(0.72 0.16 145)",
    purpose: "Live traffic. Same two-phase pipeline: ephemeral E2E proves compatibility before the real deploy. Manual approval gate.",
    lakebase: "Ephemeral e2e-* branches for verification, then production branch + read replicas",
    deploy: "Tag-triggered: E2E verify → manual approval → permanent deploy",
  },
] as const;

export const WORKFLOWS = [
  { name: "pr-validate", trigger: "PR open/sync", purpose: "Run required CI + tests for changed services, provision per-PR Lakebase feature branches, deploy preview apps, healthy-check." },
  { name: "pr-cleanup", trigger: "PR close (merged or not)", purpose: "Bundle destroy the preview + tear down the per-service Lakebase feature branches." },
  { name: "deploy-dev", trigger: "Push to develop", purpose: "Atomic CI + prod-bundle build; deploy + dev-bundle bundle deploy, run actual bundle only for RUNNING errors." },
  { name: "deploy-test", trigger: "Push to release/* or main", purpose: "Two-phase: ephemeral E2E verify (isolated Lakebase branches + temp apps) → permanent deploy (production branch + stable apps)." },
  { name: "deploy-prod", trigger: "Push tag v* on main", purpose: "Two-phase: ephemeral E2E verify → manual approval gate → permanent deploy. Schema evolution tested in isolation first." },
  { name: "nightly-orphan-cleanup", trigger: "Daily cron + manual", purpose: "Garbage-collect Lakebase feature branches whose PR is already closed." },
] as const;

export const BRANCH_FLOW = {
  featureBranches: "Feature branches (ephemeral)",
  develop: "develop",
  release: "release/*",
  main: "main",
  tags: "v* tags",
} as const;

export const KEY_PRACTICES = [
  "Scale-to-zero deploys",
  "Ephemeral Lakebase branches",
  "Two-phase E2E verification",
  "Targeted migrations per service",
  "Zero-downtime deploys",
  "Strict smoke-check URLs",
  "DABs + bundle CLI as IaC",
] as const;

export const ARCHITECTURE_HIGHLIGHTS = [
  { title: "Lakebase / Unity Catalog", description: "Row-level security via OBO token, end-to-end audit trail" },
  { title: "Lakebase Project / Domain", description: "Each service owns a project, no shared schemas" },
  { title: "Domain Service = Databricks App", description: "FastAPI, per-user connection pool, schema migrations" },
  { title: "BFF / API composition ", description: "Fan-out, in-memory joins" },
] as const;
