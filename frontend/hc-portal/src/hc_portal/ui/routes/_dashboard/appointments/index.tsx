import { useEffect, useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@apollo/client/react";
import { ErrorBoundary } from "react-error-boundary";
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Search,
  X,
} from "lucide-react";

import { APPOINTMENTS_LIST_QUERY } from "@/lib/graphql/operations";
import type { AppointmentsListData, AppointmentsListVars } from "@/lib/graphql/operations";
import { formatDateTime } from "@/lib/formatters";
import { Pagination } from "@/components/pagination";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

export const Route = createFileRoute("/_dashboard/appointments/")({
  component: AppointmentsPage,
});

function AppointmentsPage() {
  return (
    <ErrorBoundary
      fallbackRender={({ resetErrorBoundary }) => (
        <div className="flex flex-col items-center justify-center gap-4 py-16">
          <p className="text-muted-foreground">Failed to load appointments.</p>
          <button onClick={resetErrorBoundary} className="text-sm text-primary underline">
            Try again
          </button>
        </div>
      )}
    >
      <AppointmentsContent />
    </ErrorBoundary>
  );
}

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "booked", label: "Booked" },
  { value: "arrived", label: "Arrived" },
  { value: "in_progress", label: "In progress" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "no_show", label: "No show" },
];

function AppointmentsContent() {
  const [weekOffset, setWeekOffset] = useState(0);
  const [patientSearch, setPatientSearch] = useState("");
  const [reasonSearch, setReasonSearch] = useState("");
  const [status, setStatus] = useState("");
  const [limit, setLimit] = useState(50);
  const [pageOffset, setPageOffset] = useState(0);

  const patientQ = useDebouncedValue(patientSearch, 300);
  const reasonQ = useDebouncedValue(reasonSearch, 300);

  const { fromDate, toDate, weekLabel } = useMemo(() => {
    const now = new Date();
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay() + weekOffset * 7);
    startOfWeek.setHours(0, 0, 0, 0);
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    return {
      fromDate: iso(startOfWeek),
      toDate: iso(endOfWeek),
      weekLabel: `${startOfWeek.toLocaleDateString("en-US", { month: "short", day: "numeric" })} – ${endOfWeek.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`,
    };
  }, [weekOffset]);

  useEffect(() => {
    setPageOffset(0);
  }, [patientQ, reasonQ, status, fromDate, toDate]);

  const { data, loading, previousData } = useQuery<AppointmentsListData, AppointmentsListVars>(
    APPOINTMENTS_LIST_QUERY,
    {
      variables: {
        patientQ: patientQ || undefined,
        status: status || undefined,
        fromDate,
        toDate,
        limit,
        offset: pageOffset,
      },
    },
  );

  const current = data ?? previousData;

  if (loading && !current) {
    return <Skeleton className="h-96 w-full" />;
  }

  const items = current?.appointments.items ?? [];
  const total = current?.appointments.total ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <h1 className="text-2xl font-bold">Appointments</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => setWeekOffset((w) => w - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium min-w-[180px] text-center">{weekLabel}</span>
          <Button variant="outline" size="icon" onClick={() => setWeekOffset((w) => w + 1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          {weekOffset !== 0 && (
            <Button variant="ghost" size="sm" onClick={() => setWeekOffset(0)}>
              Today
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardHeader className="space-y-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <CalendarDays className="h-4 w-4" />
            {total.toLocaleString()} appointment{total !== 1 ? "s" : ""} this week
          </CardTitle>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <SearchBox
              value={patientSearch}
              onChange={setPatientSearch}
              placeholder="Search patient..."
            />
            <SearchBox
              value={reasonSearch}
              onChange={setReasonSearch}
              placeholder="Search reason / visit type..."
            />
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
          </div>
        </CardHeader>
        <CardContent
          className={`transition-opacity ${loading ? "opacity-60" : "opacity-100"}`}
        >
          {items.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              No appointments match the current filter.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date & Time</TableHead>
                  <TableHead>Patient</TableHead>
                  <TableHead className="hidden md:table-cell">Provider</TableHead>
                  <TableHead className="hidden md:table-cell">Type</TableHead>
                  <TableHead className="hidden lg:table-cell">Reason</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="whitespace-nowrap">
                      {formatDateTime(a.scheduledStart)}
                    </TableCell>
                    <TableCell className="font-medium">
                      {a.patient
                        ? `${a.patient.givenName} ${a.patient.familyName}`
                        : "—"}
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      {a.provider
                        ? `${a.provider.givenName} ${a.provider.familyName}`
                        : "—"}
                    </TableCell>
                    <TableCell className="hidden md:table-cell">{a.visitTypeCode}</TableCell>
                    <TableCell className="hidden lg:table-cell text-muted-foreground">
                      {a.reason ?? "—"}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={a.status} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Pagination
        total={total}
        limit={limit}
        offset={pageOffset}
        onOffsetChange={setPageOffset}
        onLimitChange={setLimit}
      />
    </div>
  );
}

function SearchBox({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div className="relative">
      <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
      <Input
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pl-8 pr-8"
      />
      {value && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-0.5 top-0.5 h-8 w-8"
          onClick={() => onChange("")}
          aria-label="Clear"
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
