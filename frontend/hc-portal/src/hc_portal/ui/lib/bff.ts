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
});

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

export async function listPatients(): Promise<PatientListItem[]> {
  const r = await http.get<PatientListItem[]>("/patients");
  return r.data;
}

export async function getPatientSummary(
  patientId: string,
): Promise<PatientSummary> {
  const r = await http.get<PatientSummary>(`/patient-summary/${patientId}`);
  return r.data;
}

export async function bffHealthz(): Promise<{ ok: boolean }> {
  const r = await http.get<{ ok: boolean }>("/healthz");
  return r.data;
}
