import { Suspense, useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@apollo/client/react";
import { ErrorBoundary } from "react-error-boundary";
import { Users, CalendarDays, Pill, FlaskConical, Bug } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

import {
  DASHBOARD_STATS_QUERY,
  PATIENTS_LIST_QUERY,
  APPOINTMENTS_LIST_QUERY,
  ALERTS_QUERY,
} from "@/lib/graphql/operations";
import type {
  DashboardStatsData,
  PatientsListData,
  PatientsListVars,
  AppointmentsListData,
  AppointmentsListVars,
  AlertsData,
  AlertsVars,
} from "@/lib/graphql/operations";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/stat-card";
import { PatientAvatar } from "@/components/patient-avatar";
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

export const Route = createFileRoute("/_dashboard/")({
  component: DashboardPage,
});

function DashboardPage() {
  return (
    <ErrorBoundary
      fallbackRender={({ resetErrorBoundary }) => (
        <div className="flex flex-col items-center justify-center gap-4 py-16">
          <p className="text-muted-foreground">Failed to load dashboard data.</p>
          <button
            onClick={resetErrorBoundary}
            className="text-sm text-primary underline"
          >
            Try again
          </button>
        </div>
      )}
    >
      <Suspense fallback={<DashboardSkeleton />}>
        <DashboardContent />
      </Suspense>
    </ErrorBoundary>
  );
}

function DashboardContent() {
  const [showDebug, setShowDebug] = useState(false);

  const { data: statsData } = useSuspenseQuery<DashboardStatsData>(DASHBOARD_STATS_QUERY);
  const stats = statsData.dashboardStats;

  const { data: patientsData } = useSuspenseQuery<PatientsListData, PatientsListVars>(
    PATIENTS_LIST_QUERY,
    { variables: { limit: 5, offset: 0 } },
  );
  const patients = patientsData.patients.items;

  const { fromDate, toDate } = useMemo(() => {
    const now = new Date();
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay());
    startOfWeek.setHours(0, 0, 0, 0);
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    return { fromDate: iso(startOfWeek), toDate: iso(endOfWeek) };
  }, []);

  const { data: appointmentsData } = useSuspenseQuery<AppointmentsListData, AppointmentsListVars>(
    APPOINTMENTS_LIST_QUERY,
    { variables: { fromDate, toDate, limit: 200, offset: 0 } },
  );
  const appointments = appointmentsData.appointments.items;

  const { data: alertsData } = useSuspenseQuery<AlertsData, AlertsVars>(ALERTS_QUERY);
  const alerts = alertsData.alerts;

  const chartData = useMemo(() => {
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const now = new Date();
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay());
    startOfWeek.setHours(0, 0, 0, 0);

    return days.map((label, i) => {
      const dayStart = new Date(startOfWeek);
      dayStart.setDate(startOfWeek.getDate() + i);
      const dayEnd = new Date(dayStart);
      dayEnd.setDate(dayStart.getDate() + 1);

      const count = appointments.filter((a) => {
        const d = new Date(a.scheduledStart);
        return d >= dayStart && d < dayEnd;
      }).length;

      return { day: label, appointments: count };
    });
  }, [appointments]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <button
          onClick={() => setShowDebug((v) => !v)}
          className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          title="Toggle debug counts"
        >
          <Bug className="h-3 w-3" />
          Debug
        </button>
      </div>

      {showDebug && (
        <div className="rounded-md border border-dashed border-amber-500/50 bg-amber-50/50 dark:bg-amber-950/20 p-3">
          <p className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-2">Entity Counts (all domains)</p>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="text-xs">Patients: {stats.totalPatients}</Badge>
            <Badge variant="outline" className="text-xs">Appointments: {stats.totalAppointments ?? 0}</Badge>
            <Badge variant="outline" className="text-xs">Providers: {stats.totalProviders ?? 0}</Badge>
            <Badge variant="outline" className="text-xs">Invoices: {stats.totalInvoices ?? 0}</Badge>
            <Badge variant="outline" className="text-xs">Lab Orders: {stats.totalLabOrders ?? 0}</Badge>
            <Badge variant="outline" className="text-xs">Alerts: {alerts.total ?? alerts.alerts.length}</Badge>
            <Badge variant="outline" className="text-xs">Active Rx: {stats.activePrescriptions ?? 0}</Badge>
          </div>
        </div>
      )}

      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Patients"
          value={stats.totalPatients}
          icon={Users}
          description="Registered patients"
        />
        <StatCard
          title="Appointments"
          value={stats.todaysAppointments ?? 0}
          icon={CalendarDays}
          description="Scheduled today"
        />
        <StatCard
          title="Active Prescriptions"
          value={stats.activePrescriptions ?? 0}
          icon={Pill}
          description="Currently active"
        />
        <StatCard
          title="Pending Labs"
          value={stats.pendingLabs ?? 0}
          icon={FlaskConical}
          description="Ordered or collected"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Appointments This Week</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="day" className="text-xs" />
              <YAxis allowDecimals={false} className="text-xs" />
              <Tooltip />
              <Bar dataKey="appointments" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Patients</h2>
          <Link
            to="/patients"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
          </Link>
        </div>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12"></TableHead>
                <TableHead>Name</TableHead>
                <TableHead className="hidden md:table-cell">MRN</TableHead>
                <TableHead className="w-20"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {patients.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>
                    <PatientAvatar
                      givenName={p.givenName}
                      familyName={p.familyName}
                      className="h-8 w-8 text-xs"
                    />
                  </TableCell>
                  <TableCell className="font-medium">
                    {p.givenName} {p.familyName}
                  </TableCell>
                  <TableCell className="hidden md:table-cell text-muted-foreground">
                    {p.mrn}
                  </TableCell>
                  <TableCell>
                    <Link
                      to="/patients/$id"
                      params={{ id: p.id }}
                      className="text-sm text-primary hover:underline"
                    >
                      View
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-40" />
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}
