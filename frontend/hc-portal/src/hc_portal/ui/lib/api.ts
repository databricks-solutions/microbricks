import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import type { UseQueryOptions, UseSuspenseQueryOptions } from "@tanstack/react-query";
export class ApiError extends Error {
    status: number;
    statusText: string;
    body: unknown;
    constructor(status: number, statusText: string, body: unknown){
        super(`HTTP ${status}: ${statusText}`);
        this.name = "ApiError";
        this.status = status;
        this.statusText = statusText;
        this.body = body;
    }
}
export interface AlertItem {
    detail: string;
    patient_id?: string | null;
    patient_name?: string | null;
    severity: string;
    title: string;
    type: string;
}
export interface AlertsOut {
    alerts: AlertItem[];
    partial?: boolean;
    total: number;
}
export interface AppointmentWithNames {
    id: string;
    patient_id: string;
    patient_name: string;
    provider_id: string;
    provider_name: string;
    reason?: string | null;
    scheduled_end: string;
    scheduled_start: string;
    status: string;
    visit_type_code: string;
}
export interface AppointmentsPageOut {
    items: AppointmentWithNames[];
    limit: number;
    offset: number;
    partial?: boolean;
    total: number;
}
export interface BillingOverviewOut {
    due_soon_count: number;
    invoices: Record<string, unknown>[];
    limit: number;
    offset: number;
    overdue_count: number;
    partial?: boolean;
    total: number;
    total_outstanding_cents: number;
}
export interface ComplexValue {
    display?: string | null;
    primary?: boolean | null;
    ref?: string | null;
    type?: string | null;
    value?: string | null;
}
export interface DashboardStatsOut {
    active_prescriptions: number;
    partial?: boolean;
    pending_labs: number;
    todays_appointments: number;
    total_appointments: number;
    total_invoices: number;
    total_lab_orders: number;
    total_patients: number;
    total_prescriptions: number;
    total_providers: number;
}
export interface HTTPValidationError {
    detail?: ValidationError[];
}
export interface LabOrderWithNames {
    collected_at?: string | null;
    id: string;
    ordered_at: string;
    ordering_provider_id: string;
    panel_code: string;
    patient_id: string;
    patient_name: string;
    provider_name: string;
    resulted_at?: string | null;
    status: string;
}
export interface LabsPageOut {
    items: LabOrderWithNames[];
    limit: number;
    offset: number;
    partial?: boolean;
    total: number;
}
export interface Name {
    family_name?: string | null;
    given_name?: string | null;
}
export interface PatientListItem {
    family_name: string;
    given_name: string;
    id: string;
    mrn: string;
}
export interface PatientSummaryOut {
    active_prescriptions: Record<string, unknown>[];
    last_appointments: Record<string, unknown>[];
    outstanding_invoices: Record<string, unknown>[];
    partial?: boolean;
    patient: Record<string, unknown>;
    recent_lab_orders: Record<string, unknown>[];
}
export interface PatientsPageOut {
    items: PatientListItem[];
    limit: number;
    offset: number;
    total: number;
}
export interface ProviderListItem {
    credential_suffix?: string | null;
    email: string;
    family_name: string;
    given_name: string;
    id: string;
    is_active: boolean;
    npi: string;
}
export interface ProvidersPageOut {
    items: ProviderListItem[];
    limit: number;
    offset: number;
    total: number;
}
export interface TimelineEvent {
    detail?: string | null;
    event_type: string;
    status?: string | null;
    timestamp: string;
    title: string;
}
export interface User {
    active?: boolean | null;
    display_name?: string | null;
    emails?: ComplexValue[] | null;
    entitlements?: ComplexValue[] | null;
    external_id?: string | null;
    groups?: ComplexValue[] | null;
    id?: string | null;
    name?: Name | null;
    roles?: ComplexValue[] | null;
    schemas?: UserSchema[] | null;
    user_name?: string | null;
}
export const UserSchema = {
    "urn:ietf:params:scim:schemas:core:2.0:User": "urn:ietf:params:scim:schemas:core:2.0:User",
    "urn:ietf:params:scim:schemas:extension:workspace:2.0:User": "urn:ietf:params:scim:schemas:extension:workspace:2.0:User"
} as const;
export type UserSchema = typeof UserSchema[keyof typeof UserSchema];
export interface ValidationError {
    ctx?: Record<string, unknown>;
    input?: unknown;
    loc: (string | number)[];
    msg: string;
    type: string;
}
export interface VersionOut {
    version: string;
}
export interface GetAlertsParams {
    q?: string | null;
    severity?: string | null;
    type?: string | null;
    "X-Forwarded-Access-Token"?: string | null;
    authorization?: string | null;
}
export const getAlerts = async (params?: GetAlertsParams, options?: RequestInit): Promise<{
    data: AlertsOut;
}> =>{
    const searchParams = new URLSearchParams();
    if (params?.q != null) searchParams.set("q", String(params?.q));
    if (params?.severity != null) searchParams.set("severity", String(params?.severity));
    if (params?.type != null) searchParams.set("type", String(params?.type));
    const queryString = searchParams.toString();
    const url = queryString ? `/api/bff/alerts?${queryString}` : "/api/bff/alerts";
    const res = await fetch(url, {
        ...options,
        method: "GET",
        headers: {
            ...(params?.["X-Forwarded-Access-Token"] != null && {
                "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"]
            }),
            ...(params?.authorization != null && {
                "authorization": params.authorization
            }),
            ...options?.headers
        }
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getAlertsKey = (params?: GetAlertsParams)=>{
    return [
        "/api/bff/alerts",
        params
    ] as const;
};
export function useGetAlerts<TData = {
    data: AlertsOut;
}>(options?: {
    params?: GetAlertsParams;
    query?: Omit<UseQueryOptions<{
        data: AlertsOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getAlertsKey(options?.params),
        queryFn: ()=>getAlerts(options?.params),
        ...options?.query
    });
}
export function useGetAlertsSuspense<TData = {
    data: AlertsOut;
}>(options?: {
    params?: GetAlertsParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: AlertsOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getAlertsKey(options?.params),
        queryFn: ()=>getAlerts(options?.params),
        ...options?.query
    });
}
export interface ListAppointmentsBffParams {
    q?: string | null;
    status?: string | null;
    visit_type_code?: string | null;
    from_date?: string | null;
    to_date?: string | null;
    patient_q?: string | null;
    limit?: number;
    offset?: number;
    "X-Forwarded-Access-Token"?: string | null;
    authorization?: string | null;
}
export const listAppointmentsBff = async (params?: ListAppointmentsBffParams, options?: RequestInit): Promise<{
    data: AppointmentsPageOut;
}> =>{
    const searchParams = new URLSearchParams();
    if (params?.q != null) searchParams.set("q", String(params?.q));
    if (params?.status != null) searchParams.set("status", String(params?.status));
    if (params?.visit_type_code != null) searchParams.set("visit_type_code", String(params?.visit_type_code));
    if (params?.from_date != null) searchParams.set("from_date", String(params?.from_date));
    if (params?.to_date != null) searchParams.set("to_date", String(params?.to_date));
    if (params?.patient_q != null) searchParams.set("patient_q", String(params?.patient_q));
    if (params?.limit != null) searchParams.set("limit", String(params?.limit));
    if (params?.offset != null) searchParams.set("offset", String(params?.offset));
    const queryString = searchParams.toString();
    const url = queryString ? `/api/bff/appointments?${queryString}` : "/api/bff/appointments";
    const res = await fetch(url, {
        ...options,
        method: "GET",
        headers: {
            ...(params?.["X-Forwarded-Access-Token"] != null && {
                "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"]
            }),
            ...(params?.authorization != null && {
                "authorization": params.authorization
            }),
            ...options?.headers
        }
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const listAppointmentsBffKey = (params?: ListAppointmentsBffParams)=>{
    return [
        "/api/bff/appointments",
        params
    ] as const;
};
export function useListAppointmentsBff<TData = {
    data: AppointmentsPageOut;
}>(options?: {
    params?: ListAppointmentsBffParams;
    query?: Omit<UseQueryOptions<{
        data: AppointmentsPageOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: listAppointmentsBffKey(options?.params),
        queryFn: ()=>listAppointmentsBff(options?.params),
        ...options?.query
    });
}
export function useListAppointmentsBffSuspense<TData = {
    data: AppointmentsPageOut;
}>(options?: {
    params?: ListAppointmentsBffParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: AppointmentsPageOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: listAppointmentsBffKey(options?.params),
        queryFn: ()=>listAppointmentsBff(options?.params),
        ...options?.query
    });
}
export interface GetBillingOverviewParams {
    q?: string | null;
    status?: string | null;
    patient_q?: string | null;
    limit?: number;
    offset?: number;
    "X-Forwarded-Access-Token"?: string | null;
    authorization?: string | null;
}
export const getBillingOverview = async (params?: GetBillingOverviewParams, options?: RequestInit): Promise<{
    data: BillingOverviewOut;
}> =>{
    const searchParams = new URLSearchParams();
    if (params?.q != null) searchParams.set("q", String(params?.q));
    if (params?.status != null) searchParams.set("status", String(params?.status));
    if (params?.patient_q != null) searchParams.set("patient_q", String(params?.patient_q));
    if (params?.limit != null) searchParams.set("limit", String(params?.limit));
    if (params?.offset != null) searchParams.set("offset", String(params?.offset));
    const queryString = searchParams.toString();
    const url = queryString ? `/api/bff/billing-overview?${queryString}` : "/api/bff/billing-overview";
    const res = await fetch(url, {
        ...options,
        method: "GET",
        headers: {
            ...(params?.["X-Forwarded-Access-Token"] != null && {
                "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"]
            }),
            ...(params?.authorization != null && {
                "authorization": params.authorization
            }),
            ...options?.headers
        }
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getBillingOverviewKey = (params?: GetBillingOverviewParams)=>{
    return [
        "/api/bff/billing-overview",
        params
    ] as const;
};
export function useGetBillingOverview<TData = {
    data: BillingOverviewOut;
}>(options?: {
    params?: GetBillingOverviewParams;
    query?: Omit<UseQueryOptions<{
        data: BillingOverviewOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getBillingOverviewKey(options?.params),
        queryFn: ()=>getBillingOverview(options?.params),
        ...options?.query
    });
}
export function useGetBillingOverviewSuspense<TData = {
    data: BillingOverviewOut;
}>(options?: {
    params?: GetBillingOverviewParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: BillingOverviewOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getBillingOverviewKey(options?.params),
        queryFn: ()=>getBillingOverview(options?.params),
        ...options?.query
    });
}
export interface GetDashboardStatsParams {
    "X-Forwarded-Access-Token"?: string | null;
    authorization?: string | null;
}
export const getDashboardStats = async (params?: GetDashboardStatsParams, options?: RequestInit): Promise<{
    data: DashboardStatsOut;
}> =>{
    const res = await fetch("/api/bff/dashboard-stats", {
        ...options,
        method: "GET",
        headers: {
            ...(params?.["X-Forwarded-Access-Token"] != null && {
                "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"]
            }),
            ...(params?.authorization != null && {
                "authorization": params.authorization
            }),
            ...options?.headers
        }
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getDashboardStatsKey = (params?: GetDashboardStatsParams)=>{
    return [
        "/api/bff/dashboard-stats",
        params
    ] as const;
};
export function useGetDashboardStats<TData = {
    data: DashboardStatsOut;
}>(options?: {
    params?: GetDashboardStatsParams;
    query?: Omit<UseQueryOptions<{
        data: DashboardStatsOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getDashboardStatsKey(options?.params),
        queryFn: ()=>getDashboardStats(options?.params),
        ...options?.query
    });
}
export function useGetDashboardStatsSuspense<TData = {
    data: DashboardStatsOut;
}>(options?: {
    params?: GetDashboardStatsParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: DashboardStatsOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getDashboardStatsKey(options?.params),
        queryFn: ()=>getDashboardStats(options?.params),
        ...options?.query
    });
}
export const bffHealthz = async (options?: RequestInit): Promise<{
    data: Record<string, boolean>;
}> =>{
    const res = await fetch("/api/bff/healthz", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const bffHealthzKey = ()=>{
    return [
        "/api/bff/healthz"
    ] as const;
};
export function useBffHealthz<TData = {
    data: Record<string, boolean>;
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: Record<string, boolean>;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: bffHealthzKey(),
        queryFn: ()=>bffHealthz(),
        ...options?.query
    });
}
export function useBffHealthzSuspense<TData = {
    data: Record<string, boolean>;
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: Record<string, boolean>;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: bffHealthzKey(),
        queryFn: ()=>bffHealthz(),
        ...options?.query
    });
}
export interface ListLabsBffParams {
    q?: string | null;
    status?: string[] | null;
    patient_q?: string | null;
    limit?: number;
    offset?: number;
    "X-Forwarded-Access-Token"?: string | null;
    authorization?: string | null;
}
export const listLabsBff = async (params?: ListLabsBffParams, options?: RequestInit): Promise<{
    data: LabsPageOut;
}> =>{
    const searchParams = new URLSearchParams();
    if (params?.q != null) searchParams.set("q", String(params?.q));
    if (params?.status != null) params?.status.forEach((v)=>searchParams.append("status", String(v)));
    if (params?.patient_q != null) searchParams.set("patient_q", String(params?.patient_q));
    if (params?.limit != null) searchParams.set("limit", String(params?.limit));
    if (params?.offset != null) searchParams.set("offset", String(params?.offset));
    const queryString = searchParams.toString();
    const url = queryString ? `/api/bff/labs?${queryString}` : "/api/bff/labs";
    const res = await fetch(url, {
        ...options,
        method: "GET",
        headers: {
            ...(params?.["X-Forwarded-Access-Token"] != null && {
                "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"]
            }),
            ...(params?.authorization != null && {
                "authorization": params.authorization
            }),
            ...options?.headers
        }
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const listLabsBffKey = (params?: ListLabsBffParams)=>{
    return [
        "/api/bff/labs",
        params
    ] as const;
};
export function useListLabsBff<TData = {
    data: LabsPageOut;
}>(options?: {
    params?: ListLabsBffParams;
    query?: Omit<UseQueryOptions<{
        data: LabsPageOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: listLabsBffKey(options?.params),
        queryFn: ()=>listLabsBff(options?.params),
        ...options?.query
    });
}
export function useListLabsBffSuspense<TData = {
    data: LabsPageOut;
}>(options?: {
    params?: ListLabsBffParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: LabsPageOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: listLabsBffKey(options?.params),
        queryFn: ()=>listLabsBff(options?.params),
        ...options?.query
    });
}
export interface GetPatientSummaryParams {
    patient_id: string;
    "X-Forwarded-Access-Token"?: string | null;
    authorization?: string | null;
}
export const getPatientSummary = async (params: GetPatientSummaryParams, options?: RequestInit): Promise<{
    data: PatientSummaryOut;
}> =>{
    const res = await fetch(`/api/bff/patient-summary/${params.patient_id}`, {
        ...options,
        method: "GET",
        headers: {
            ...(params?.["X-Forwarded-Access-Token"] != null && {
                "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"]
            }),
            ...(params?.authorization != null && {
                "authorization": params.authorization
            }),
            ...options?.headers
        }
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getPatientSummaryKey = (params?: GetPatientSummaryParams)=>{
    return [
        "/api/bff/patient-summary/{patient_id}",
        params
    ] as const;
};
export function useGetPatientSummary<TData = {
    data: PatientSummaryOut;
}>(options: {
    params: GetPatientSummaryParams;
    query?: Omit<UseQueryOptions<{
        data: PatientSummaryOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getPatientSummaryKey(options.params),
        queryFn: ()=>getPatientSummary(options.params),
        ...options?.query
    });
}
export function useGetPatientSummarySuspense<TData = {
    data: PatientSummaryOut;
}>(options: {
    params: GetPatientSummaryParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: PatientSummaryOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getPatientSummaryKey(options.params),
        queryFn: ()=>getPatientSummary(options.params),
        ...options?.query
    });
}
export interface GetPatientTimelineParams {
    patient_id: string;
    "X-Forwarded-Access-Token"?: string | null;
    authorization?: string | null;
}
export const getPatientTimeline = async (params: GetPatientTimelineParams, options?: RequestInit): Promise<{
    data: TimelineEvent[];
}> =>{
    const res = await fetch(`/api/bff/patient-timeline/${params.patient_id}`, {
        ...options,
        method: "GET",
        headers: {
            ...(params?.["X-Forwarded-Access-Token"] != null && {
                "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"]
            }),
            ...(params?.authorization != null && {
                "authorization": params.authorization
            }),
            ...options?.headers
        }
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getPatientTimelineKey = (params?: GetPatientTimelineParams)=>{
    return [
        "/api/bff/patient-timeline/{patient_id}",
        params
    ] as const;
};
export function useGetPatientTimeline<TData = {
    data: TimelineEvent[];
}>(options: {
    params: GetPatientTimelineParams;
    query?: Omit<UseQueryOptions<{
        data: TimelineEvent[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getPatientTimelineKey(options.params),
        queryFn: ()=>getPatientTimeline(options.params),
        ...options?.query
    });
}
export function useGetPatientTimelineSuspense<TData = {
    data: TimelineEvent[];
}>(options: {
    params: GetPatientTimelineParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: TimelineEvent[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getPatientTimelineKey(options.params),
        queryFn: ()=>getPatientTimeline(options.params),
        ...options?.query
    });
}
export interface ListPatientsBffParams {
    q?: string | null;
    limit?: number;
    offset?: number;
    "X-Forwarded-Access-Token"?: string | null;
    authorization?: string | null;
}
export const listPatientsBff = async (params?: ListPatientsBffParams, options?: RequestInit): Promise<{
    data: PatientsPageOut;
}> =>{
    const searchParams = new URLSearchParams();
    if (params?.q != null) searchParams.set("q", String(params?.q));
    if (params?.limit != null) searchParams.set("limit", String(params?.limit));
    if (params?.offset != null) searchParams.set("offset", String(params?.offset));
    const queryString = searchParams.toString();
    const url = queryString ? `/api/bff/patients?${queryString}` : "/api/bff/patients";
    const res = await fetch(url, {
        ...options,
        method: "GET",
        headers: {
            ...(params?.["X-Forwarded-Access-Token"] != null && {
                "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"]
            }),
            ...(params?.authorization != null && {
                "authorization": params.authorization
            }),
            ...options?.headers
        }
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const listPatientsBffKey = (params?: ListPatientsBffParams)=>{
    return [
        "/api/bff/patients",
        params
    ] as const;
};
export function useListPatientsBff<TData = {
    data: PatientsPageOut;
}>(options?: {
    params?: ListPatientsBffParams;
    query?: Omit<UseQueryOptions<{
        data: PatientsPageOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: listPatientsBffKey(options?.params),
        queryFn: ()=>listPatientsBff(options?.params),
        ...options?.query
    });
}
export function useListPatientsBffSuspense<TData = {
    data: PatientsPageOut;
}>(options?: {
    params?: ListPatientsBffParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: PatientsPageOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: listPatientsBffKey(options?.params),
        queryFn: ()=>listPatientsBff(options?.params),
        ...options?.query
    });
}
export interface ListProvidersBffParams {
    q?: string | null;
    is_active?: boolean | null;
    limit?: number;
    offset?: number;
    "X-Forwarded-Access-Token"?: string | null;
    authorization?: string | null;
}
export const listProvidersBff = async (params?: ListProvidersBffParams, options?: RequestInit): Promise<{
    data: ProvidersPageOut;
}> =>{
    const searchParams = new URLSearchParams();
    if (params?.q != null) searchParams.set("q", String(params?.q));
    if (params?.is_active != null) searchParams.set("is_active", String(params?.is_active));
    if (params?.limit != null) searchParams.set("limit", String(params?.limit));
    if (params?.offset != null) searchParams.set("offset", String(params?.offset));
    const queryString = searchParams.toString();
    const url = queryString ? `/api/bff/providers?${queryString}` : "/api/bff/providers";
    const res = await fetch(url, {
        ...options,
        method: "GET",
        headers: {
            ...(params?.["X-Forwarded-Access-Token"] != null && {
                "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"]
            }),
            ...(params?.authorization != null && {
                "authorization": params.authorization
            }),
            ...options?.headers
        }
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const listProvidersBffKey = (params?: ListProvidersBffParams)=>{
    return [
        "/api/bff/providers",
        params
    ] as const;
};
export function useListProvidersBff<TData = {
    data: ProvidersPageOut;
}>(options?: {
    params?: ListProvidersBffParams;
    query?: Omit<UseQueryOptions<{
        data: ProvidersPageOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: listProvidersBffKey(options?.params),
        queryFn: ()=>listProvidersBff(options?.params),
        ...options?.query
    });
}
export function useListProvidersBffSuspense<TData = {
    data: ProvidersPageOut;
}>(options?: {
    params?: ListProvidersBffParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: ProvidersPageOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: listProvidersBffKey(options?.params),
        queryFn: ()=>listProvidersBff(options?.params),
        ...options?.query
    });
}
export interface CurrentUserParams {
    "X-Forwarded-Host"?: string | null;
    "X-Forwarded-Preferred-Username"?: string | null;
    "X-Forwarded-User"?: string | null;
    "X-Forwarded-Email"?: string | null;
    "X-Request-Id"?: string | null;
    "X-Forwarded-Access-Token"?: string | null;
}
export const currentUser = async (params?: CurrentUserParams, options?: RequestInit): Promise<{
    data: User;
}> =>{
    const res = await fetch("/api/current-user", {
        ...options,
        method: "GET",
        headers: {
            ...(params?.["X-Forwarded-Host"] != null && {
                "X-Forwarded-Host": params["X-Forwarded-Host"]
            }),
            ...(params?.["X-Forwarded-Preferred-Username"] != null && {
                "X-Forwarded-Preferred-Username": params["X-Forwarded-Preferred-Username"]
            }),
            ...(params?.["X-Forwarded-User"] != null && {
                "X-Forwarded-User": params["X-Forwarded-User"]
            }),
            ...(params?.["X-Forwarded-Email"] != null && {
                "X-Forwarded-Email": params["X-Forwarded-Email"]
            }),
            ...(params?.["X-Request-Id"] != null && {
                "X-Request-Id": params["X-Request-Id"]
            }),
            ...(params?.["X-Forwarded-Access-Token"] != null && {
                "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"]
            }),
            ...options?.headers
        }
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const currentUserKey = (params?: CurrentUserParams)=>{
    return [
        "/api/current-user",
        params
    ] as const;
};
export function useCurrentUser<TData = {
    data: User;
}>(options?: {
    params?: CurrentUserParams;
    query?: Omit<UseQueryOptions<{
        data: User;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: currentUserKey(options?.params),
        queryFn: ()=>currentUser(options?.params),
        ...options?.query
    });
}
export function useCurrentUserSuspense<TData = {
    data: User;
}>(options?: {
    params?: CurrentUserParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: User;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: currentUserKey(options?.params),
        queryFn: ()=>currentUser(options?.params),
        ...options?.query
    });
}
export const version = async (options?: RequestInit): Promise<{
    data: VersionOut;
}> =>{
    const res = await fetch("/api/version", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const versionKey = ()=>{
    return [
        "/api/version"
    ] as const;
};
export function useVersion<TData = {
    data: VersionOut;
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: VersionOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: versionKey(),
        queryFn: ()=>version(),
        ...options?.query
    });
}
export function useVersionSuspense<TData = {
    data: VersionOut;
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: VersionOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: versionKey(),
        queryFn: ()=>version(),
        ...options?.query
    });
}
