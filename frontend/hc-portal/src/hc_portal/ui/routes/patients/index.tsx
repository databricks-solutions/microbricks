import { Suspense } from "react";
import { Link, createFileRoute } from "@tanstack/react-router";
import {
  QueryErrorResetBoundary,
  useSuspenseQuery,
} from "@tanstack/react-query";
import { ErrorBoundary } from "react-error-boundary";

import Navbar from "@/components/apx/navbar";
import { Button } from "@/components/ui/button";
import { listPatients } from "@/lib/bff";

export const Route = createFileRoute("/patients/")({
  component: PatientsPage,
});

function PatientsPage() {
  return (
    <div className="flex h-screen flex-col">
      <Navbar />
      <main className="container mx-auto flex-1 p-8">
        <h1 className="mb-6 text-3xl font-bold">Patients</h1>
        <QueryErrorResetBoundary>
          {({ reset }) => (
            <ErrorBoundary
              onReset={reset}
              fallbackRender={({ error, resetErrorBoundary }) => (
                <div className="rounded-md border border-destructive/50 p-4">
                  <p className="font-medium text-destructive">
                    Failed to load patients
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
              <Suspense fallback={<PatientsSkeleton />}>
                <PatientsList />
              </Suspense>
            </ErrorBoundary>
          )}
        </QueryErrorResetBoundary>
      </main>
    </div>
  );
}

function PatientsList() {
  const { data: patients } = useSuspenseQuery({
    queryKey: ["bff", "patients"],
    queryFn: listPatients,
  });

  if (patients.length === 0) {
    return (
      <p className="text-muted-foreground">
        No patients yet. Run the dev seed (Phase 4) to populate sample data.
      </p>
    );
  }

  return (
    <ul className="divide-y rounded-md border">
      {patients.map((p) => (
        <li key={p.id}>
          <Link
            to="/patients/$id"
            params={{ id: p.id }}
            className="flex items-baseline justify-between p-4 hover:bg-accent"
          >
            <span className="font-medium">
              {p.family_name}, {p.given_name}
            </span>
            <span className="text-sm text-muted-foreground">MRN {p.mrn}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function PatientsSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="h-14 animate-pulse rounded-md bg-muted/40"
          aria-hidden
        />
      ))}
    </div>
  );
}
