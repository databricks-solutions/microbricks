from .appointment import AppointmentGQL
from .billing import InvoiceGQL
from .common import PageInfo
from .dashboard import DashboardStatsGQL
from .lab import LabOrderGQL
from .patient import PatientGQL
from .prescription import PrescriptionGQL
from .provider import ProviderGQL

__all__ = [
    "AppointmentGQL",
    "DashboardStatsGQL",
    "InvoiceGQL",
    "LabOrderGQL",
    "PageInfo",
    "PatientGQL",
    "PrescriptionGQL",
    "ProviderGQL",
]
