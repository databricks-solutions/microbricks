from typing import Optional

import strawberry

from .appointment import AppointmentGQL
from .billing import InvoiceGQL
from .lab import LabOrderGQL
from .patient import PatientGQL
from .prescription import PrescriptionGQL


@strawberry.type
class PatientSummaryGQL:
    patient: PatientGQL
    last_appointments: list[AppointmentGQL]
    active_prescriptions: list[PrescriptionGQL]
    recent_lab_orders: list[LabOrderGQL]
    outstanding_invoices: list[InvoiceGQL]
    partial: bool
