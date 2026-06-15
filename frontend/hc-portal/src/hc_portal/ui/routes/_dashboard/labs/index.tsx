import { useEffect, useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@apollo/client/react";
import { ErrorBoundary } from "react-error-boundary";
import { FlaskConical, Search, X } from "lucide-react";

import { LABS_LIST_QUERY } from "@/lib/graphql/operations";
import type { LabsListData, LabsListVars } from "@/lib/graphql/operations";
import { formatDate } from "@/lib/formatters";
import { Pagination } from "@/components/pagination";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

export const Route = createFileRoute("/_dashboard/labs/")({
  component: LabsPage,
});

type LabTab = "pending" | "resulted" | "all";

const TAB_STATUSES: Record<LabTab, string[] | undefined> = {
  pending: ["ordered", "collected"],
  resulted: ["resulted"],
  all: undefined,
};

function LabsPage() {
  return (
    <ErrorBoundary
      fallbackRender={({ resetErrorBoundary }) => (
        <div className="flex flex-col items-center justify-center gap-4 py-16">
          <p className="text-muted-foreground">Failed to load lab data.</p>
          <button onClick={resetErrorBoundary} className="text-sm text-primary underline">
            Try again
          </button>
        </div>
      )}
    >
      <LabsContent />
    </ErrorBoundary>
  );
}

function LabsContent() {
  const [tab, setTab] = useState<LabTab>("pending");
  const [patientSearch, setPatientSearch] = useState("");
  const [panelSearch, setPanelSearch] = useState("");
  const patientQ = useDebouncedValue(patientSearch, 300);
  const panelQ = useDebouncedValue(panelSearch, 300);
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);

  const status = useMemo(() => TAB_STATUSES[tab], [tab]);

  useEffect(() => {
    setOffset(0);
  }, [tab, patientQ, panelQ]);

  const { data, loading, previousData } = useQuery<LabsListData, LabsListVars>(
    LABS_LIST_QUERY,
    {
      variables: {
        status: status,
        patientQ: patientQ || undefined,
        limit,
        offset,
      },
    },
  );

  const current = data ?? previousData;

  if (loading && !current) {
    return <Skeleton className="h-96 w-full" />;
  }

  const labs = current?.labOrders.items ?? [];
  const total = current?.labOrders.total ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Lab Results Tracker</h1>

      <Tabs value={tab} onValueChange={(v) => setTab(v as LabTab)}>
        <TabsList>
          <TabsTrigger value="pending">Pending</TabsTrigger>
          <TabsTrigger value="resulted">Resulted</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardHeader className="space-y-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <FlaskConical className="h-4 w-4" />
            {tab === "pending"
              ? "Pending Labs"
              : tab === "resulted"
                ? "Resulted Labs"
                : "All Lab Orders"}{" "}
            ({total.toLocaleString()})
          </CardTitle>
          <div className="grid gap-3 sm:grid-cols-2">
            <SearchBox
              value={patientSearch}
              onChange={setPatientSearch}
              placeholder="Search patient..."
            />
            <SearchBox
              value={panelSearch}
              onChange={setPanelSearch}
              placeholder="Search panel code..."
            />
          </div>
        </CardHeader>
        <CardContent
          className={`transition-opacity ${loading ? "opacity-60" : "opacity-100"}`}
        >
          {labs.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              No lab orders match the current filter.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Panel</TableHead>
                  <TableHead>Patient</TableHead>
                  <TableHead className="hidden md:table-cell">Ordered By</TableHead>
                  <TableHead className="hidden md:table-cell">Ordered</TableHead>
                  <TableHead className="hidden lg:table-cell">Collected</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {labs.map((lab) => (
                  <TableRow key={lab.id}>
                    <TableCell className="font-medium">{lab.panelCode}</TableCell>
                    <TableCell>
                      {lab.patient
                        ? `${lab.patient.givenName} ${lab.patient.familyName}`
                        : "—"}
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      {lab.provider
                        ? `${lab.provider.givenName} ${lab.provider.familyName}`
                        : "—"}
                    </TableCell>
                    <TableCell className="hidden md:table-cell whitespace-nowrap">
                      {formatDate(lab.orderedAt)}
                    </TableCell>
                    <TableCell className="hidden lg:table-cell whitespace-nowrap">
                      {lab.collectedAt ? formatDate(lab.collectedAt) : "—"}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={lab.status} />
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
