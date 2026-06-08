"""Per-service typed BFF clients for the simulator.

Each client extends `_BaseSvcClient` and forwards the user's OBO token to
its downstream service. Unlike `hc_portal.clients` (which is read-mostly),
these support the write methods the simulator needs.
"""
from .appointment import (
    Appointment,
    AppointmentClient,
    AppointmentCreatePayload,
)
from .billing import BillingClient, Invoice, InvoiceCreatePayload
from .lab import LabClient, LabOrder, LabOrderCreatePayload
from .patient import Patient, PatientClient, PatientCreatePayload
from .prescription import (
    Prescription,
    PrescriptionClient,
    PrescriptionCreatePayload,
)
from .provider import Provider, ProviderClient

__all__ = [
    "Appointment",
    "AppointmentClient",
    "AppointmentCreatePayload",
    "BillingClient",
    "Invoice",
    "InvoiceCreatePayload",
    "LabClient",
    "LabOrder",
    "LabOrderCreatePayload",
    "Patient",
    "PatientClient",
    "PatientCreatePayload",
    "Prescription",
    "PrescriptionClient",
    "PrescriptionCreatePayload",
    "Provider",
    "ProviderClient",
]
