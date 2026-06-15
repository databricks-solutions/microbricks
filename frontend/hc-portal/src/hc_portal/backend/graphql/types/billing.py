from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.types import Info

from .patient import PatientGQL


@strawberry.type
class InvoiceGQL:
    id: UUID
    patient_id: UUID
    appointment_id: Optional[UUID]
    total_amount_cents: int
    currency: str
    status: str
    issued_at: datetime
    due_at: Optional[datetime]

    @strawberry.field
    async def patient(self, info: Info) -> Optional[PatientGQL]:
        p = await info.context.patient_loader.load(self.patient_id)
        if not p:
            return None
        return PatientGQL(
            id=p.id, mrn=p.mrn, given_name=p.given_name,
            family_name=p.family_name, birth_date=p.birth_date,
            sex_at_birth=p.sex_at_birth,
        )


@strawberry.type
class InvoicePageGQL:
    items: list[InvoiceGQL]
    total: int
    limit: int
    offset: int
