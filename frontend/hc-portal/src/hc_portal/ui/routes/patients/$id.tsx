import { Suspense } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  QueryErrorResetBoundary,
  useSuspenseQuery,
} from "@tanstack/react-query";
import { ErrorBoundary } from "react-error-boundary";

import Navbar from "@/components/apx/navbar";
import { Button } from "@/components/ui/button";
import { PatientSummary, getPatientSummary } from "@/lib/bff";

export const Route = createFileRoute("/patients/$id")({
  component: PatientDetailPage,
});

function PatientDetailPage() {
  const { id } = Route.useParams();
  return (
    <div className="flex h-screen flex-col">
      <Navbar />
      <main className="container mx-auto flex-1 space-y-6 p-8">
        <QueryErrorResetBoundary>
          {({ reset }) => (
            <ErrorBoundary
              onReset={reset}
              fallbackRender={({ error, resetErrorBoundary }) => (
                <div className="rounded-md border border-destructive/50 p-4">
                  <p className="font-medium text-destructive">
                    Failed to load patient summary
                  </p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {String(error)}
                  </p>
                  <Button
                    onClick={resetErrorBoundary}
                    variant="outline"
                    className="mt-4"
                  >
                    Try again
                  </Button>
                </div>
              )}
            >
              <Suspense fallback={<DetailSkeleton />}>
                <PatientDetail patientId={id} />
              </Suspense>
            </ErrorBoundary>
          )}
        </QueryErrorResetBoundary>
      </main>
    </div>
  );
}

function PatientDetail({ patientId }: { patientId: string }) {
  const { data: summary } = useSuspenseQuery<PatientSummary>({
    queryKey: ["bff", "patient-summary", patientId],
    queryFn: () => getPatientSummary(patientId),
  });

  const { patient } = summary;

  return (
    <>
      <header className="space-y-1">
        <h1 className="text-3xl font-bold">
          {patient.family_name}, {patient.given_name}
        </h1>
        <p className="text-sm text-muted-foreground">
          MRN {patient.mrn} · DOB {patient.birth_date} · {patient.sex_at_birth}
        </p>
        {summary.partial && (
          <p className="text-xs text-yellow-600 dark:text-yellow-400">
            Partial response — one or more downstream services were unavailable.
          </p>
        )}
      </header>

      <SummarySection
        title={`Last ${summary.last_appointments.length} appointments`}
        empty="No recent appointments."
        count={summary.last_appointments.length}
      >
        <ul className="divide-y rounded-md border text-sm">
          {summary.last_appointments.map((a) => (
            <li key={a.id} className="flex justify-between p-3">
              <span>
                {a.visit_type_code} · {a.scheduled_start.slice(0, 16).replace("T", " ")}
              </span>
              <span className="text-muted-foreground">{a.status}</span>
            </li>
          ))}
        </ul>
      </SummarySection>

      <SummarySection
        title="Active prescriptions"
        empty="No active prescriptions."
        count={summary.active_prescriptions.length}
      >
        <ul className="divide-y rounded-md border text-sm">
          {summary.active_prescriptions.map((rx) => (
            <li key={rx.id} className="flex justify-between p-3">
              <span>
                {rx.medication_code} — {rx.dose_text}
              </span>
              <span className="text-muted-foreground">
                {rx.refills_remaining} refills left
              </span>
            </li>
          ))}
        </ul>
      </SummarySection>

      <SummarySection
        title="Recent lab orders"
        empty="No recent lab orders."
        count={summary.recent_lab_orders.length}
      >
        <ul className="divide-y rounded-md border text-sm">
          {summary.recent_lab_orders.map((lo) => (
            <li key={lo.id} className="flex justify-between p-3">
              <span>
                {lo.panel_code} · ordered {lo.ordered_at.slice(0, 10)}
              </span>
              <span className="text-muted-foreground">{lo.status}</span>
            </li>
          ))}
        </ul>
      </SummarySection>

      <SummarySection
        title="Outstanding invoices"
        empty="No outstanding invoices."
        count={summary.outstanding_invoices.length}
      >
        <ul className="divide-y rounded-md border text-sm">
          {summary.outstanding_invoices.map((inv) => (
            <li key={inv.id} className="flex justify-between p-3">
              <span>
                {(inv.total_amount_cents / 100).toFixed(2)} {inv.currency}
              </span>
              <span className="text-muted-foreground">{inv.status}</span>
            </li>
          ))}
        </ul>
      </SummarySection>
    </>
  );
}

interface SummarySectionProps {
  title: string;
  empty: string;
  count: number;
  children: React.ReactNode;
}

function SummarySection({ title, empty, count, children }: SummarySectionProps) {
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold">{title}</h2>
      {count === 0 ? (
        <p className="text-sm text-muted-foreground">{empty}</p>
      ) : (
        children
      )}
    </section>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-8 w-2/3 animate-pulse rounded bg-muted/40" />
      <div className="h-4 w-1/3 animate-pulse rounded bg-muted/40" />
      <div className="h-32 animate-pulse rounded bg-muted/40" />
      <div className="h-32 animate-pulse rounded bg-muted/40" />
    </div>
  );
}
