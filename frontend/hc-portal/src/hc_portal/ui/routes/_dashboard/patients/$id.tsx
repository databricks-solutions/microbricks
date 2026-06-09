import { Suspense } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { QueryErrorResetBoundary, useSuspenseQuery } from "@tanstack/react-query";
import { ErrorBoundary } from "react-error-boundary";
import {
  CalendarDays,
  Pill,
  FlaskConical,
  Receipt,
  AlertTriangle,
  ArrowLeft,
  Clock,
} from "lucide-react";

import { getPatientSummary, getPatientTimeline } from "@/lib/bff";
import type { TimelineEvent } from "@/lib/bff";
import { formatCurrency, formatDate, formatDateTime } from "@/lib/formatters";
import { PatientAvatar } from "@/components/patient-avatar";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const Route = createFileRoute("/_dashboard/patients/$id")({
  component: PatientDetailPage,
});

function PatientDetailPage() {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ErrorBoundary
          onReset={reset}
          fallbackRender={({ resetErrorBoundary }) => (
            <div className="flex flex-col items-center justify-center gap-4 py-16">
              <p className="text-muted-foreground">Failed to load patient.</p>
              <button
                onClick={resetErrorBoundary}
                className="text-sm text-primary underline"
              >
                Try again
              </button>
            </div>
          )}
        >
          <Suspense fallback={<DetailSkeleton />}>
            <PatientDetailContent />
          </Suspense>
        </ErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  );
}

function PatientDetailContent() {
  const { id } = Route.useParams();
  const { data: summary } = useSuspenseQuery({
    queryKey: ["patient-summary", id],
    queryFn: () => getPatientSummary(id),
  });

  const { data: timeline } = useSuspenseQuery({
    queryKey: ["patient-timeline", id],
    queryFn: () => getPatientTimeline(id),
  });

  const { patient, last_appointments, active_prescriptions, recent_lab_orders, outstanding_invoices, partial } = summary;

  const totalBalance = outstanding_invoices.reduce(
    (acc, inv) => acc + inv.total_amount_cents,
    0,
  );

  return (
    <div className="space-y-6">
      <Link
        to="/patients"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to patients
      </Link>

      <Card>
        <CardContent className="flex flex-col sm:flex-row items-start gap-4 pt-6">
          <PatientAvatar
            givenName={patient.given_name}
            familyName={patient.family_name}
            className="h-16 w-16 text-xl"
          />
          <div className="flex-1 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-2xl font-bold">
                {patient.given_name} {patient.family_name}
              </h1>
              {partial && (
                <Badge variant="destructive" className="gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Partial data
                </Badge>
              )}
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
              <span>MRN: {patient.mrn}</span>
              <span>DOB: {formatDate(patient.birth_date)}</span>
              <span>Sex: {patient.sex_at_birth}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Appointments"
          value={last_appointments.length}
          icon={CalendarDays}
        />
        <StatCard
          title="Active Meds"
          value={active_prescriptions.length}
          icon={Pill}
        />
        <StatCard
          title="Lab Orders"
          value={recent_lab_orders.length}
          icon={FlaskConical}
        />
        <StatCard
          title="Balance"
          value={formatCurrency(totalBalance)}
          icon={Receipt}
        />
      </div>

      <Tabs defaultValue="appointments">
        <TabsList>
          <TabsTrigger value="appointments">Appointments</TabsTrigger>
          <TabsTrigger value="prescriptions">Prescriptions</TabsTrigger>
          <TabsTrigger value="labs">Labs</TabsTrigger>
          <TabsTrigger value="invoices">Invoices</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
        </TabsList>

        <TabsContent value="appointments" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent Appointments</CardTitle>
            </CardHeader>
            <CardContent>
              {last_appointments.length === 0 ? (
                <p className="text-sm text-muted-foreground">No appointments.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead className="hidden md:table-cell">Provider</TableHead>
                      <TableHead className="hidden md:table-cell">Type</TableHead>
                      <TableHead className="hidden lg:table-cell">Reason</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {last_appointments.map((a) => (
                      <TableRow key={a.id}>
                        <TableCell className="whitespace-nowrap">
                          {formatDateTime(a.scheduled_start)}
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          {a.provider_name ?? "—"}
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          {a.visit_type_code}
                        </TableCell>
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
        </TabsContent>

        <TabsContent value="prescriptions" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Active Prescriptions</CardTitle>
            </CardHeader>
            <CardContent>
              {active_prescriptions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No active prescriptions.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Medication</TableHead>
                      <TableHead className="hidden md:table-cell">Dose</TableHead>
                      <TableHead className="hidden md:table-cell">Refills</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {active_prescriptions.map((rx) => (
                      <TableRow key={rx.id}>
                        <TableCell className="font-medium">
                          {rx.medication_code}
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          {rx.dose_text}
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          {rx.refills_remaining}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={rx.status} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="labs" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent Lab Orders</CardTitle>
            </CardHeader>
            <CardContent>
              {recent_lab_orders.length === 0 ? (
                <p className="text-sm text-muted-foreground">No lab orders.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Panel</TableHead>
                      <TableHead className="hidden md:table-cell">Ordered</TableHead>
                      <TableHead className="hidden md:table-cell">Collected</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recent_lab_orders.map((lab) => (
                      <TableRow key={lab.id}>
                        <TableCell className="font-medium">
                          {lab.panel_code}
                        </TableCell>
                        <TableCell className="hidden md:table-cell whitespace-nowrap">
                          {formatDate(lab.ordered_at)}
                        </TableCell>
                        <TableCell className="hidden md:table-cell whitespace-nowrap">
                          {lab.collected_at ? formatDate(lab.collected_at) : "—"}
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
        </TabsContent>

        <TabsContent value="invoices" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Outstanding Invoices</CardTitle>
            </CardHeader>
            <CardContent>
              {outstanding_invoices.length === 0 ? (
                <p className="text-sm text-muted-foreground">No invoices.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Amount</TableHead>
                      <TableHead className="hidden md:table-cell">Issued</TableHead>
                      <TableHead className="hidden md:table-cell">Due</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {outstanding_invoices.map((inv) => (
                      <TableRow key={inv.id}>
                        <TableCell className="font-medium">
                          {formatCurrency(inv.total_amount_cents, inv.currency)}
                        </TableCell>
                        <TableCell className="hidden md:table-cell whitespace-nowrap">
                          {formatDate(inv.issued_at)}
                        </TableCell>
                        <TableCell className="hidden md:table-cell whitespace-nowrap">
                          {inv.due_at ? formatDate(inv.due_at) : "—"}
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
        </TabsContent>

        <TabsContent value="timeline" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Patient Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              {timeline.length === 0 ? (
                <p className="text-sm text-muted-foreground">No events.</p>
              ) : (
                <div className="relative space-y-0">
                  {timeline.map((event, idx) => (
                    <TimelineItem key={idx} event={event} isLast={idx === timeline.length - 1} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

const eventTypeConfig: Record<string, { icon: typeof CalendarDays; color: string }> = {
  appointment: { icon: CalendarDays, color: "text-blue-500" },
  prescription: { icon: Pill, color: "text-green-500" },
  lab: { icon: FlaskConical, color: "text-purple-500" },
  billing: { icon: Receipt, color: "text-amber-500" },
};

function TimelineItem({ event, isLast }: { event: TimelineEvent; isLast: boolean }) {
  const config = eventTypeConfig[event.event_type] ?? { icon: Clock, color: "text-muted-foreground" };
  const Icon = config.icon;

  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <div className={`rounded-full border-2 border-background bg-muted p-1.5 ${config.color}`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
        {!isLast && <div className="w-px flex-1 bg-border" />}
      </div>
      <div className={`pb-6 ${isLast ? "pb-0" : ""}`}>
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{event.title}</span>
          {event.status && <StatusBadge status={event.status} />}
        </div>
        {event.detail && (
          <p className="text-xs text-muted-foreground mt-0.5">{event.detail}</p>
        )}
        <p className="text-xs text-muted-foreground mt-1">
          {formatDateTime(event.timestamp)}
        </p>
      </div>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-5 w-32" />
      <Skeleton className="h-28" />
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-72" />
    </div>
  );
}
