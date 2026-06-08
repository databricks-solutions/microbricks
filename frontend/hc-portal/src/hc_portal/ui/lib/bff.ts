/**
 * Typed fetch helpers for the BFF aggregation routes.
 *
 * The apx scaffold doesn't ship Orval out of the box, so for this reference
 * repo we hand-write the type definitions that mirror the Pydantic shapes in
 * `src/hc_portal/backend/routers/aggregations.py`. When Orval lands in a
 * follow-up these can be replaced by generated hooks (`useGetPatientSummarySuspense`).
 *
 * The frontend talks to its own origin — Databricks Apps serves the React
 * bundle and the FastAPI BFF from the same host — so calls are relative.
 */
import axios from "axios";

const http = axios.create({
  baseURL: "/api/bff",
  timeout: 10_000,
  // FastAPI reads list query params as repeated keys (`?status=a&status=b`),
  // so we emit arrays the same way. URLSearchParams natively appends a new
  // key per value when given an array of [key, value] tuples.
  paramsSerializer: {
    serialize(params) {
      const sp = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v === undefined || v === null || v === "") continue;
        if (Array.isArray(v)) {
          for (const item of v) {
            if (item === undefined || item === null || item === "") continue;
            sp.append(k, String(item));
          }
        } else {
          sp.append(k, String(v));
        }
      }
      return sp.toString();
    },
  },
});

/**
 * Paginated list envelope returned by every BFF list route. Mirrors the
 * Pydantic `PageOut` shapes — `total` is the unfiltered row count for the
 * current search+filter predicate, NOT the size of `items`, so callers can
 * drive a "page N of M" control off a single response.
 */
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  partial?: boolean;
}

/** Common shape passed to every list helper for paginated + searchable queries. */
export interface ListParams {
  q?: string;
  limit?: number;
  offset?: number;
}

export interface PatientListItem {
  id: string;
  mrn: string;
  given_name: string;
  family_name: string;
}

export interface Patient extends PatientListItem {
  birth_date: string;
  sex_at_birth: string;
}

export interface Appointment {
  id: string;
  patient_id: string;
  provider_id: string;
  provider_name?: string;
  visit_type_code: string;
  scheduled_start: string;
  scheduled_end: string;
  status: string;
  reason: string | null;
}

export interface LabOrder {
  id: string;
  patient_id: string;
  ordering_provider_id: string;
  appointment_id: string | null;
  panel_code: string;
  status: string;
  ordered_at: string;
  collected_at: string | null;
  resulted_at: string | null;
}

export interface Prescription {
  id: string;
  patient_id: string;
  prescribing_provider_id: string;
  medication_code: string;
  dose_text: string;
  quantity: number;
  refills_remaining: number;
  status: string;
  start_at: string;
  end_at: string | null;
}

export interface Invoice {
  id: string;
  patient_id: string;
  appointment_id: string | null;
  total_amount_cents: number;
  currency: string;
  status: string;
  issued_at: string;
  due_at: string | null;
}

export interface PatientSummary {
  patient: Patient;
  last_appointments: Appointment[];
  active_prescriptions: Prescription[];
  recent_lab_orders: LabOrder[];
  outstanding_invoices: Invoice[];
  partial: boolean;
}

export interface ListPatientsParams extends ListParams {}

export async function listPatients(
  params: ListPatientsParams = {},
): Promise<Page<PatientListItem>> {
  const r = await http.get<Page<PatientListItem>>("/patients", { params });
  return r.data;
}

export async function getPatientSummary(
  patientId: string,
): Promise<PatientSummary> {
  const r = await http.get<PatientSummary>(`/patient-summary/${patientId}`);
  return r.data;
}

export interface DashboardStats {
  total_patients: number;
  total_providers: number;
  total_appointments: number;
  todays_appointments: number;
  total_prescriptions: number;
  active_prescriptions: number;
  total_lab_orders: number;
  pending_labs: number;
  total_invoices: number;
  partial: boolean;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const r = await http.get<DashboardStats>("/dashboard-stats");
  return r.data;
}

export async function bffHealthz(): Promise<{ ok: boolean }> {
  const r = await http.get<{ ok: boolean }>("/healthz");
  return r.data;
}

export interface AppointmentWithNames {
  id: string;
  patient_id: string;
  provider_id: string;
  patient_name: string;
  provider_name: string;
  visit_type_code: string;
  scheduled_start: string;
  scheduled_end: string;
  status: string;
  reason: string | null;
}

export interface ListAppointmentsParams extends ListParams {
  status?: string;
  visit_type_code?: string;
  from_date?: string;
  to_date?: string;
  patient_q?: string;
}

export async function listAppointments(
  params: ListAppointmentsParams = {},
): Promise<Page<AppointmentWithNames>> {
  const r = await http.get<Page<AppointmentWithNames>>("/appointments", { params });
  return r.data;
}

export interface ProviderListItem {
  id: string;
  npi: string;
  given_name: string;
  family_name: string;
  credential_suffix: string | null;
  email: string;
  is_active: boolean;
}

export interface ListProvidersParams extends ListParams {
  is_active?: boolean;
}

export async function listProviders(
  params: ListProvidersParams = {},
): Promise<Page<ProviderListItem>> {
  const r = await http.get<Page<ProviderListItem>>("/providers", { params });
  return r.data;
}

export interface BillingOverview {
  invoices: (Invoice & { patient_name: string })[];
  total: number;
  limit: number;
  offset: number;
  total_outstanding_cents: number;
  overdue_count: number;
  due_soon_count: number;
  partial: boolean;
}

export interface BillingOverviewParams extends ListParams {
  status?: string;
  patient_q?: string;
}

export async function getBillingOverview(
  params: BillingOverviewParams = {},
): Promise<BillingOverview> {
  const r = await http.get<BillingOverview>("/billing-overview", { params });
  return r.data;
}

export interface LabOrderWithNames {
  id: string;
  patient_id: string;
  patient_name: string;
  ordering_provider_id: string;
  provider_name: string;
  panel_code: string;
  status: string;
  ordered_at: string;
  collected_at: string | null;
  resulted_at: string | null;
}

export interface ListLabsParams extends ListParams {
  status?: string[];
  patient_q?: string;
}

export async function listLabs(
  params: ListLabsParams = {},
): Promise<Page<LabOrderWithNames>> {
  const r = await http.get<Page<LabOrderWithNames>>("/labs", { params });
  return r.data;
}

export interface AlertItem {
  type: string;
  severity: string;
  title: string;
  detail: string;
  patient_id: string | null;
  patient_name: string | null;
}

export interface AlertsOut {
  alerts: AlertItem[];
  total: number;
  partial?: boolean;
}

export interface GetAlertsParams {
  q?: string;
  severity?: string;
  type?: string;
}

export async function getAlerts(params: GetAlertsParams = {}): Promise<AlertsOut> {
  const r = await http.get<AlertsOut>("/alerts", { params });
  return r.data;
}

export interface TimelineEvent {
  timestamp: string;
  event_type: string;
  title: string;
  detail: string | null;
  status: string | null;
}

export async function getPatientTimeline(
  patientId: string,
): Promise<TimelineEvent[]> {
  const r = await http.get<TimelineEvent[]>(`/patient-timeline/${patientId}`);
  return r.data;
}
