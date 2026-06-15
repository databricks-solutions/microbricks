from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from uuid import UUID

import strawberry


@strawberry.enum
class AppointmentStatus(Enum):
    BOOKED = "booked"
    ARRIVED = "arrived"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


@strawberry.type
class AppointmentType:
    id: UUID
    patient_id: UUID
    provider_id: UUID
    visit_type_code: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    reason: str | None


@strawberry.type
class AppointmentPage:
    items: list[AppointmentType]
    total: int
    limit: int
    offset: int


@strawberry.input
class AppointmentCreateInput:
    patient_id: UUID
    provider_id: UUID
    visit_type_code: str
    scheduled_start: datetime
    scheduled_end: datetime
    reason: str | None = None
    status: str = "booked"


@strawberry.input
class AppointmentFilterInput:
    patient_id: UUID | None = None
    provider_id: UUID | None = None
    status: str | None = None
    visit_type_code: str | None = None
    q: str | None = None
    from_date: date | None = None
    to_date: date | None = None
