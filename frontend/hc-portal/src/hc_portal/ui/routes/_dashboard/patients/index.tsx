import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@apollo/client/react";
import { ErrorBoundary } from "react-error-boundary";
import { Search, X } from "lucide-react";

import { PATIENTS_LIST_QUERY } from "@/lib/graphql/operations";
import type { PatientsListData, PatientsListVars } from "@/lib/graphql/operations";
import { PatientAvatar } from "@/components/patient-avatar";
import { Pagination } from "@/components/pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

export const Route = createFileRoute("/_dashboard/patients/")({
  component: PatientsPage,
});

function PatientsPage() {
  return (
    <ErrorBoundary
      fallbackRender={({ resetErrorBoundary }) => (
        <div className="flex flex-col items-center justify-center gap-4 py-16">
          <p className="text-muted-foreground">Failed to load patients.</p>
          <button
            onClick={resetErrorBoundary}
            className="text-sm text-primary underline"
          >
            Try again
          </button>
        </div>
      )}
    >
      <PatientsContent />
    </ErrorBoundary>
  );
}

function PatientsContent() {
  const [searchInput, setSearchInput] = useState("");
  const q = useDebouncedValue(searchInput, 250);
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    setOffset(0);
  }, [q]);

  const { data, loading, previousData } = useQuery<PatientsListData, PatientsListVars>(
    PATIENTS_LIST_QUERY,
    { variables: { q: q || undefined, limit, offset } },
  );

  const current = data ?? previousData;

  if (loading && !current) {
    return <PatientsSkeleton />;
  }

  const patients = current?.patients.items ?? [];
  const total = current?.patients.total ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold">Patients</h1>
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name or MRN..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-8 pr-8"
          />
          {searchInput && (
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-0.5 top-0.5 h-8 w-8"
              onClick={() => setSearchInput("")}
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      <div
        className={`rounded-md border transition-opacity ${
          loading ? "opacity-60" : "opacity-100"
        }`}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12"></TableHead>
              <TableHead>Name</TableHead>
              <TableHead className="hidden md:table-cell">MRN</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {patients.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
                  {q ? `No patients match "${q}".` : "No patients found."}
                </TableCell>
              </TableRow>
            ) : (
              patients.map((p) => (
                <TableRow key={p.id} className="cursor-pointer">
                  <TableCell>
                    <PatientAvatar
                      givenName={p.givenName}
                      familyName={p.familyName}
                      className="h-8 w-8 text-xs"
                    />
                  </TableCell>
                  <TableCell className="font-medium">
                    <Link
                      to="/patients/$id"
                      params={{ id: p.id }}
                      className="hover:underline"
                    >
                      {p.givenName} {p.familyName}
                    </Link>
                  </TableCell>
                  <TableCell className="hidden md:table-cell text-muted-foreground">
                    {p.mrn}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Pagination
        total={total}
        limit={limit}
        offset={offset}
        onOffsetChange={setOffset}
        onLimitChange={setLimit}
      />
    </div>
  );
}

function PatientsSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-9 w-64" />
      </div>
      <Skeleton className="h-96" />
    </div>
  );
}
