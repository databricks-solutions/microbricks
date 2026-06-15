from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.types import Info

from .patient import PatientGQL
from .provider import ProviderGQL


@strawberry.type
class LabOrderGQL:
    id: UUID
    patient_id: UUID
    ordering_provider_id: UUID
    appointment_id: Optional[UUID]
    panel_code: str
    status: str
    ordered_at: datetime
    collected_at: Optional[datetime]
    resulted_at: Optional[datetime]

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
        p = await info.context.provider_loader.load(self.ordering_provider_id)
        if not p:
            return None
        return ProviderGQL(
            id=p.id, npi=p.npi, given_name=p.given_name,
            family_name=p.family_name, credential_suffix=p.credential_suffix,
            email=p.email, is_active=p.is_active, organization_id=p.organization_id,
        )


@strawberry.type
class LabOrderPageGQL:
    items: list[LabOrderGQL]
    total: int
    limit: int
    offset: int
