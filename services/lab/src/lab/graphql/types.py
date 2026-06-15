from __future__ import annotations

from datetime import datetime
from uuid import UUID

import strawberry


@strawberry.type
class LabOrderType:
    id: UUID
    patient_id: UUID
    ordering_provider_id: UUID
    appointment_id: UUID | None
    panel_code: str
    status: str
    ordered_at: datetime
    collected_at: datetime | None
    resulted_at: datetime | None


@strawberry.type
class LabOrderPage:
    items: list[LabOrderType]
    total: int
    limit: int
    offset: int


@strawberry.input
class LabOrderCreateInput:
    patient_id: UUID
    ordering_provider_id: UUID
    panel_code: str
    appointment_id: UUID | None = None
    ordered_at: datetime | None = None
