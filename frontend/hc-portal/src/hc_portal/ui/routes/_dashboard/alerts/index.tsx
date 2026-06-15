import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@apollo/client/react";
import { ErrorBoundary } from "react-error-boundary";
import { AlertTriangle, Bell, Clock, Search, UserX, X } from "lucide-react";

import { ALERTS_QUERY } from "@/lib/graphql/operations";
import type { AlertsData, AlertsVars } from "@/lib/graphql/operations";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

export const Route = createFileRoute("/_dashboard/alerts/")({
  component: AlertsPage,
});

function AlertsPage() {
  return (
    <ErrorBoundary
      fallbackRender={({ resetErrorBoundary }) => (
        <div className="flex flex-col items-center justify-center gap-4 py-16">
          <p className="text-muted-foreground">Failed to load alerts.</p>
          <button onClick={resetErrorBoundary} className="text-sm text-primary underline">
            Try again
          </button>
        </div>
      )}
    >
      <AlertsContent />
    </ErrorBoundary>
  );
}

const severityColor: Record<string, "destructive" | "default" | "secondary"> = {
  warning: "destructive",
  high: "destructive",
  medium: "default",
  info: "secondary",
  low: "secondary",
};

const typeIcon: Record<string, typeof AlertTriangle> = {
  overdue_invoice: AlertTriangle,
  stale_lab: Clock,
  no_followup: UserX,
};

const SEVERITY_OPTIONS = [
  { value: "", label: "All severities" },
  { value: "warning", label: "Warning" },
  { value: "info", label: "Info" },
];

const TYPE_OPTIONS = [
  { value: "", label: "All types" },
  { value: "overdue_invoice", label: "Overdue invoice" },
  { value: "stale_lab", label: "Stale lab" },
  { value: "no_followup", label: "No follow-up" },
];

function AlertsContent() {
  const [searchInput, setSearchInput] = useState("");
  const [severity, setSeverity] = useState("");
  const [type, setType] = useState("");
  const q = useDebouncedValue(searchInput, 250);

  const { data, loading, previousData } = useQuery<AlertsData, AlertsVars>(
    ALERTS_QUERY,
    {
      variables: {
        q: q || undefined,
        severity: severity || undefined,
        type: type || undefined,
      },
    },
  );

  const current = data ?? previousData;

  if (loading && !current) {
    return <Skeleton className="h-96 w-full" />;
  }

  const alerts = current?.alerts.alerts ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Alerts & Notifications</h1>

      <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search alerts..."
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
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="sm:w-[160px]"
        >
          {SEVERITY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="sm:w-[200px]"
        >
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
      </div>

      <p className="text-xs text-muted-foreground">
        {alerts.length === 0
          ? "No alerts."
          : `${alerts.length.toLocaleString()} alert${alerts.length !== 1 ? "s" : ""}`}
      </p>

      <div
        className={`transition-opacity ${loading ? "opacity-60" : "opacity-100"}`}
      >
        {alerts.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Bell className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-muted-foreground">
                {q || severity || type
                  ? "No alerts match the current filter."
                  : "No active alerts — everything looks good."}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert, idx) => {
              const Icon = typeIcon[alert.type] ?? Bell;
              return (
                <Card key={idx}>
                  <CardContent className="flex items-start gap-4 py-4">
                    <div className="mt-0.5">
                      <Icon className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{alert.title}</span>
                        <Badge variant={severityColor[alert.severity] ?? "secondary"}>
                          {alert.severity}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{alert.detail}</p>
                      {alert.patientName && (
                        <p className="text-xs text-muted-foreground">Patient: {alert.patientName}</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
