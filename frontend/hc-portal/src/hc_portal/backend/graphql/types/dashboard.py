from typing import Optional

import strawberry


@strawberry.type
class DashboardStatsGQL:
    total_patients: int
    total_providers: Optional[int]
    total_appointments: Optional[int]
    todays_appointments: Optional[int]
    total_lab_orders: Optional[int]
    pending_labs: Optional[int]
    total_prescriptions: Optional[int]
    active_prescriptions: Optional[int]
    total_invoices: Optional[int]
    partial: bool
