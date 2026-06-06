"""Per-service typed BFF clients.

Every concrete client extends `_BaseSvcClient` and forwards the user's OBO
token to its downstream service. The BFF is the only place in this
architecture that combines data from multiple services — see
`.claude/skills/hc-bff-pattern/SKILL.md`.
"""
from .appointment import Appointment, AppointmentClient
from .billing import BillingClient, Invoice
from .lab import LabClient, LabOrder
from .patient import Patient, PatientClient
from .prescription import Prescription, PrescriptionClient
from .provider import Provider, ProviderClient

__all__ = [
    "Appointment",
    "AppointmentClient",
    "BillingClient",
    "Invoice",
    "LabClient",
    "LabOrder",
    "Patient",
    "PatientClient",
    "Prescription",
    "PrescriptionClient",
    "Provider",
    "ProviderClient",
]
