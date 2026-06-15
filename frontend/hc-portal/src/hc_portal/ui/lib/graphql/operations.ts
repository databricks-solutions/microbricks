import { gql } from "@apollo/client/core";

// --- Dashboard Stats ---

export const DASHBOARD_STATS_QUERY = gql`
  query DashboardStats {
    dashboardStats {
      totalPatients
      totalProviders
      totalAppointments
      todaysAppointments
      totalLabOrders
      pendingLabs
      totalPrescriptions
      activePrescriptions
      totalInvoices
      partial
    }
  }
`;

export interface DashboardStatsData {
  dashboardStats: {
    totalPatients: number;
    totalProviders: number | null;
    totalAppointments: number | null;
    todaysAppointments: number | null;
    totalLabOrders: number | null;
    pendingLabs: number | null;
    totalPrescriptions: number | null;
    activePrescriptions: number | null;
    totalInvoices: number | null;
    partial: boolean;
  };
}

// --- Patients List ---

export const PATIENTS_LIST_QUERY = gql`
  query PatientsList($q: String, $limit: Int! = 50, $offset: Int! = 0) {
    patients(q: $q, limit: $limit, offset: $offset) {
      items {
        id
        mrn
        givenName
        familyName
        birthDate
        sexAtBirth
      }
      total
      limit
      offset
    }
  }
`;

export interface PatientsListData {
  patients: {
    items: {
      id: string;
      mrn: string;
      givenName: string;
      familyName: string;
      birthDate: string;
      sexAtBirth: string;
    }[];
    total: number;
    limit: number;
    offset: number;
  };
}

export interface PatientsListVars {
  q?: string;
  limit?: number;
  offset?: number;
}

// --- Providers List ---

export const PROVIDERS_LIST_QUERY = gql`
  query ProvidersList($q: String, $isActive: Boolean, $limit: Int! = 50, $offset: Int! = 0) {
    providers(q: $q, isActive: $isActive, limit: $limit, offset: $offset) {
      items {
        id
        npi
        givenName
        familyName
        credentialSuffix
        email
        isActive
      }
      total
      limit
      offset
    }
  }
`;

export interface ProvidersListData {
  providers: {
    items: {
      id: string;
      npi: string;
      givenName: string;
      familyName: string;
      credentialSuffix: string | null;
      email: string;
      isActive: boolean;
    }[];
    total: number;
    limit: number;
    offset: number;
  };
}

export interface ProvidersListVars {
  q?: string;
  isActive?: boolean;
  limit?: number;
  offset?: number;
}

// --- Appointments List ---

export const APPOINTMENTS_LIST_QUERY = gql`
  query AppointmentsList(
    $status: String
    $visitTypeCode: String
    $fromDate: Date
    $toDate: Date
    $patientQ: String
    $limit: Int! = 50
    $offset: Int! = 0
  ) {
    appointments(
      status: $status
      visitTypeCode: $visitTypeCode
      fromDate: $fromDate
      toDate: $toDate
      patientQ: $patientQ
      limit: $limit
      offset: $offset
    ) {
      items {
        id
        patientId
        providerId
        visitTypeCode
        scheduledStart
        scheduledEnd
        status
        reason
        patient {
          id
          givenName
          familyName
        }
        provider {
          id
          givenName
          familyName
          credentialSuffix
        }
      }
      total
      limit
      offset
    }
  }
`;

export interface AppointmentItem {
  id: string;
  patientId: string;
  providerId: string;
  visitTypeCode: string;
  scheduledStart: string;
  scheduledEnd: string;
  status: string;
  reason: string | null;
  patient: { id: string; givenName: string; familyName: string } | null;
  provider: { id: string; givenName: string; familyName: string; credentialSuffix: string | null } | null;
}

export interface AppointmentsListData {
  appointments: {
    items: AppointmentItem[];
    total: number;
    limit: number;
    offset: number;
  };
}

export interface AppointmentsListVars {
  status?: string;
  visitTypeCode?: string;
  fromDate?: string;
  toDate?: string;
  patientQ?: string;
  limit?: number;
  offset?: number;
}

// --- Labs List ---

export const LABS_LIST_QUERY = gql`
  query LabsList($status: [String!], $patientQ: String, $limit: Int! = 50, $offset: Int! = 0) {
    labOrders(status: $status, patientQ: $patientQ, limit: $limit, offset: $offset) {
      items {
        id
        patientId
        orderingProviderId
        appointmentId
        panelCode
        status
        orderedAt
        collectedAt
        resultedAt
        patient {
          id
          givenName
          familyName
        }
        provider {
          id
          givenName
          familyName
        }
      }
      total
      limit
      offset
    }
  }
`;

export interface LabOrderItem {
  id: string;
  patientId: string;
  orderingProviderId: string;
  appointmentId: string | null;
  panelCode: string;
  status: string;
  orderedAt: string;
  collectedAt: string | null;
  resultedAt: string | null;
  patient: { id: string; givenName: string; familyName: string } | null;
  provider: { id: string; givenName: string; familyName: string } | null;
}

export interface LabsListData {
  labOrders: {
    items: LabOrderItem[];
    total: number;
    limit: number;
    offset: number;
  };
}

export interface LabsListVars {
  status?: string[];
  patientQ?: string;
  limit?: number;
  offset?: number;
}

// --- Billing Overview ---

export const BILLING_OVERVIEW_QUERY = gql`
  query BillingOverview($q: String, $status: String, $patientQ: String, $limit: Int! = 50, $offset: Int! = 0) {
    billingOverview(q: $q, status: $status, patientQ: $patientQ, limit: $limit, offset: $offset) {
      invoices {
        id
        patientId
        appointmentId
        totalAmountCents
        currency
        status
        issuedAt
        dueAt
        patient {
          id
          givenName
          familyName
        }
      }
      total
      limit
      offset
      totalOutstandingCents
      overdueCount
      dueSoonCount
      partial
    }
  }
`;

export interface BillingInvoiceItem {
  id: string;
  patientId: string;
  appointmentId: string | null;
  totalAmountCents: number;
  currency: string;
  status: string;
  issuedAt: string;
  dueAt: string | null;
  patient: { id: string; givenName: string; familyName: string } | null;
}

export interface BillingOverviewData {
  billingOverview: {
    invoices: BillingInvoiceItem[];
    total: number;
    limit: number;
    offset: number;
    totalOutstandingCents: number;
    overdueCount: number;
    dueSoonCount: number;
    partial: boolean;
  };
}

export interface BillingOverviewVars {
  q?: string;
  status?: string;
  patientQ?: string;
  limit?: number;
  offset?: number;
}

// --- Patient Summary ---

export const PATIENT_SUMMARY_QUERY = gql`
  query PatientSummary($id: UUID!) {
    patientSummary(id: $id) {
      patient {
        id
        mrn
        givenName
        familyName
        birthDate
        sexAtBirth
      }
      lastAppointments {
        id
        visitTypeCode
        scheduledStart
        scheduledEnd
        status
        reason
        provider {
          id
          givenName
          familyName
          credentialSuffix
        }
      }
      activePrescriptions {
        id
        medicationCode
        doseText
        quantity
        refillsRemaining
        status
        startAt
        endAt
      }
      recentLabOrders {
        id
        panelCode
        status
        orderedAt
        collectedAt
        resultedAt
      }
      outstandingInvoices {
        id
        totalAmountCents
        currency
        status
        issuedAt
        dueAt
      }
      partial
    }
  }
`;

export interface PatientSummaryData {
  patientSummary: {
    patient: {
      id: string;
      mrn: string;
      givenName: string;
      familyName: string;
      birthDate: string;
      sexAtBirth: string;
    };
    lastAppointments: {
      id: string;
      visitTypeCode: string;
      scheduledStart: string;
      scheduledEnd: string;
      status: string;
      reason: string | null;
      provider: { id: string; givenName: string; familyName: string; credentialSuffix: string | null } | null;
    }[];
    activePrescriptions: {
      id: string;
      medicationCode: string;
      doseText: string;
      quantity: number;
      refillsRemaining: number;
      status: string;
      startAt: string;
      endAt: string | null;
    }[];
    recentLabOrders: {
      id: string;
      panelCode: string;
      status: string;
      orderedAt: string;
      collectedAt: string | null;
      resultedAt: string | null;
    }[];
    outstandingInvoices: {
      id: string;
      totalAmountCents: number;
      currency: string;
      status: string;
      issuedAt: string;
      dueAt: string | null;
    }[];
    partial: boolean;
  };
}

export interface PatientSummaryVars {
  id: string;
}

// --- Patient Timeline ---

export const PATIENT_TIMELINE_QUERY = gql`
  query PatientTimeline($id: UUID!) {
    patientTimeline(id: $id) {
      timestamp
      eventType
      title
      detail
      status
    }
  }
`;

export interface TimelineEvent {
  timestamp: string;
  eventType: string;
  title: string;
  detail: string | null;
  status: string | null;
}

export interface PatientTimelineData {
  patientTimeline: TimelineEvent[];
}

export interface PatientTimelineVars {
  id: string;
}

// --- Alerts ---

export const ALERTS_QUERY = gql`
  query Alerts($q: String, $severity: String, $type: String) {
    alerts(q: $q, severity: $severity, type: $type) {
      alerts {
        type
        severity
        title
        detail
        patientId
        patientName
      }
      total
      partial
    }
  }
`;

export interface AlertItem {
  type: string;
  severity: string;
  title: string;
  detail: string;
  patientId: string | null;
  patientName: string | null;
}

export interface AlertsData {
  alerts: {
    alerts: AlertItem[];
    total: number;
    partial: boolean;
  };
}

export interface AlertsVars {
  q?: string;
  severity?: string;
  type?: string;
}
