from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry


@strawberry.type
class PrescriptionGQL:
    id: UUID
    patient_id: UUID
    prescribing_provider_id: UUID
    medication_code: str
    dose_text: str
    quantity: int
    refills_remaining: int
    status: str
    start_at: datetime
    end_at: Optional[datetime]


@strawberry.type
class PrescriptionPageGQL:
    items: list[PrescriptionGQL]
    total: int
    limit: int
    offset: int
