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
export interface ComplexValue {
    display?: string | null;
    primary?: boolean | null;
    ref?: string | null;
    type?: string | null;
    value?: string | null;
}
export interface HTTPValidationError {
    detail?: ValidationError[];
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
export interface ListPatientsBffParams {
    "X-Forwarded-Access-Token"?: string | null;
    authorization?: string | null;
}
export const listPatientsBff = async (params?: ListPatientsBffParams, options?: RequestInit): Promise<{
    data: PatientListItem[];
}> =>{
    const res = await fetch("/api/bff/patients", {
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
    data: PatientListItem[];
}>(options?: {
    params?: ListPatientsBffParams;
    query?: Omit<UseQueryOptions<{
        data: PatientListItem[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: listPatientsBffKey(options?.params),
        queryFn: ()=>listPatientsBff(options?.params),
        ...options?.query
    });
}
export function useListPatientsBffSuspense<TData = {
    data: PatientListItem[];
}>(options?: {
    params?: ListPatientsBffParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: PatientListItem[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: listPatientsBffKey(options?.params),
        queryFn: ()=>listPatientsBff(options?.params),
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
