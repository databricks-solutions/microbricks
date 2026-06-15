from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.types import Info

from .patient import PatientGQL
from .provider import ProviderGQL


@strawberry.type
class AppointmentGQL:
    id: UUID
    patient_id: UUID
    provider_id: UUID
    visit_type_code: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    reason: Optional[str]

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

    @strawberry.field
    async def provider(self, info: Info) -> Optional[ProviderGQL]:
        p = await info.context.provider_loader.load(self.provider_id)
        if not p:
            return None
        return ProviderGQL(
            id=p.id, npi=p.npi, given_name=p.given_name,
            family_name=p.family_name, credential_suffix=p.credential_suffix,
            email=p.email, is_active=p.is_active, organization_id=p.organization_id,
        )


@strawberry.type
class AppointmentPageGQL:
    items: list[AppointmentGQL]
    total: int
    limit: int
    offset: int
