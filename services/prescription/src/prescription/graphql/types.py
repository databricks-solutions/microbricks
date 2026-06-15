from __future__ import annotations

from datetime import datetime
from uuid import UUID

import strawberry


@strawberry.type
class PrescriptionType:
    id: UUID
    patient_id: UUID
    prescribing_provider_id: UUID
    medication_code: str
    dose_text: str
    quantity: int
    refills_remaining: int
    status: str
    start_at: datetime
    end_at: datetime | None


@strawberry.type
class PrescriptionPage:
    items: list[PrescriptionType]
    total: int
    limit: int
    offset: int


@strawberry.input
class PrescriptionCreateInput:
    patient_id: UUID
    prescribing_provider_id: UUID
    medication_code: str
    dose_text: str
    quantity: int
    refills_remaining: int = 0
    start_at: datetime | None = None
    end_at: datetime | None = None
