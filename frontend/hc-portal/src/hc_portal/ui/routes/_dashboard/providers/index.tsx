import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@apollo/client/react";
import { ErrorBoundary } from "react-error-boundary";
import { Search, Stethoscope, X } from "lucide-react";

import { PROVIDERS_LIST_QUERY } from "@/lib/graphql/operations";
import type { ProvidersListData, ProvidersListVars } from "@/lib/graphql/operations";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/pagination";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

export const Route = createFileRoute("/_dashboard/providers/")({
  component: ProvidersPage,
});

type ActiveFilter = "all" | "active" | "inactive";

function ProvidersPage() {
  return (
    <ErrorBoundary
      fallbackRender={({ resetErrorBoundary }) => (
        <div className="flex flex-col items-center justify-center gap-4 py-16">
          <p className="text-muted-foreground">Failed to load providers.</p>
          <button onClick={resetErrorBoundary} className="text-sm text-primary underline">
            Try again
          </button>
        </div>
      )}
    >
      <ProvidersContent />
    </ErrorBoundary>
  );
}

function ProvidersContent() {
  const [searchInput, setSearchInput] = useState("");
  const q = useDebouncedValue(searchInput, 250);
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>("all");
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    setOffset(0);
  }, [q, activeFilter]);

  const isActive = activeFilter === "all" ? undefined : activeFilter === "active";

  const { data, loading, previousData } = useQuery<ProvidersListData, ProvidersListVars>(
    PROVIDERS_LIST_QUERY,
    { variables: { q: q || undefined, isActive: isActive, limit, offset } },
  );

  const current = data ?? previousData;

  if (loading && !current) {
    return <Skeleton className="h-96 w-full" />;
  }

  const providers = current?.providers.items ?? [];
  const total = current?.providers.total ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Provider Directory</h1>

      <Card>
        <CardHeader className="space-y-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Stethoscope className="h-4 w-4" />
            {total.toLocaleString()} provider{total !== 1 ? "s" : ""}
          </CardTitle>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name, NPI, or email..."
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
            <Select
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value as ActiveFilter)}
              className="sm:w-[180px]"
            >
              <option value="all">All providers</option>
              <option value="active">Active only</option>
              <option value="inactive">Inactive only</option>
            </Select>
          </div>
        </CardHeader>
        <CardContent
          className={`transition-opacity ${loading ? "opacity-60" : "opacity-100"}`}
        >
          {providers.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              {q || activeFilter !== "all"
                ? "No providers match the current filter."
                : "No providers found."}
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead className="hidden md:table-cell">NPI</TableHead>
                  <TableHead className="hidden md:table-cell">Email</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {providers.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">
                      {p.givenName} {p.familyName}
                      {p.credentialSuffix && (
                        <span className="text-muted-foreground ml-1">, {p.credentialSuffix}</span>
                      )}
                    </TableCell>
                    <TableCell className="hidden md:table-cell font-mono text-sm">
                      {p.npi}
                    </TableCell>
                    <TableCell className="hidden md:table-cell text-muted-foreground">
                      {p.email}
                    </TableCell>
                    <TableCell>
                      <Badge variant={p.isActive ? "default" : "secondary"}>
                        {p.isActive ? "Active" : "Inactive"}
                      </Badge>
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
