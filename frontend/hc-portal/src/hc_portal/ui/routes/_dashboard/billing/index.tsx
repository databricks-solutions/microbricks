import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@apollo/client/react";
import { ErrorBoundary } from "react-error-boundary";
import { Receipt, AlertTriangle, Clock, DollarSign, Search, X } from "lucide-react";

import { BILLING_OVERVIEW_QUERY } from "@/lib/graphql/operations";
import type { BillingOverviewData, BillingOverviewVars } from "@/lib/graphql/operations";
import { formatCurrency, formatDate } from "@/lib/formatters";
import { Pagination } from "@/components/pagination";
import { StatCard } from "@/components/stat-card";
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

export const Route = createFileRoute("/_dashboard/billing/")({
  component: BillingPage,
});

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "outstanding", label: "Outstanding" },
  { value: "paid", label: "Paid" },
  { value: "partially_paid", label: "Partially paid" },
  { value: "void", label: "Void" },
  { value: "draft", label: "Draft" },
];

function BillingPage() {
  return (
    <ErrorBoundary
      fallbackRender={({ resetErrorBoundary }) => (
        <div className="flex flex-col items-center justify-center gap-4 py-16">
          <p className="text-muted-foreground">Failed to load billing data.</p>
          <button onClick={resetErrorBoundary} className="text-sm text-primary underline">
            Try again
          </button>
        </div>
      )}
    >
      <BillingContent />
    </ErrorBoundary>
  );
}

function BillingContent() {
  const [patientSearch, setPatientSearch] = useState("");
  const [amountSearch, setAmountSearch] = useState("");
  const [status, setStatus] = useState("outstanding");
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);

  const patientQ = useDebouncedValue(patientSearch, 300);
  const amountQ = useDebouncedValue(amountSearch, 300);

  useEffect(() => {
    setOffset(0);
  }, [patientQ, amountQ, status]);

  const { data, loading, previousData } = useQuery<BillingOverviewData, BillingOverviewVars>(
    BILLING_OVERVIEW_QUERY,
    {
      variables: {
        patientQ: patientQ || undefined,
        q: amountQ || undefined,
        status: status || undefined,
        limit,
        offset,
      },
    },
  );

  const current = data ?? previousData;

  if (loading && !current) {
    return <Skeleton className="h-96 w-full" />;
  }

  const overview = current?.billingOverview;
  if (!overview) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Billing Overview</h1>

      <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
        <StatCard
          title="Total Outstanding"
          value={formatCurrency(overview.totalOutstandingCents)}
          icon={DollarSign}
          description="Across all patients"
        />
        <StatCard
          title="Overdue"
          value={overview.overdueCount}
          icon={AlertTriangle}
          description="Past due date"
        />
        <StatCard
          title="Due Soon"
          value={overview.dueSoonCount}
          icon={Clock}
          description="Due within 7 days"
        />
      </div>

      <Card>
        <CardHeader className="space-y-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Receipt className="h-4 w-4" />
            Invoices ({overview.total.toLocaleString()})
          </CardTitle>
          <div className="grid gap-3 sm:grid-cols-3">
            <SearchBox
              value={patientSearch}
              onChange={setPatientSearch}
              placeholder="Search patient..."
            />
            <SearchBox
              value={amountSearch}
              onChange={setAmountSearch}
              placeholder="Search amount / currency..."
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
          {overview.invoices.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              No invoices match the current filter.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Patient</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead className="hidden md:table-cell">Issued</TableHead>
                  <TableHead className="hidden md:table-cell">Due</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {overview.invoices.map((inv) => (
                  <TableRow key={inv.id}>
                    <TableCell className="font-medium">
                      {inv.patient
                        ? `${inv.patient.givenName} ${inv.patient.familyName}`
                        : "—"}
                    </TableCell>
                    <TableCell>{formatCurrency(inv.totalAmountCents, inv.currency)}</TableCell>
                    <TableCell className="hidden md:table-cell whitespace-nowrap">
                      {formatDate(inv.issuedAt)}
                    </TableCell>
                    <TableCell className="hidden md:table-cell whitespace-nowrap">
                      {inv.dueAt ? formatDate(inv.dueAt) : "—"}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={inv.status} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Pagination
        total={overview.total}
        limit={limit}
        offset={offset}
        onOffsetChange={setOffset}
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
