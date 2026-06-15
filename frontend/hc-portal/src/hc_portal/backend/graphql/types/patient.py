from datetime import date
from uuid import UUID

import strawberry


@strawberry.type
class PatientGQL:
    id: UUID
    mrn: str
    given_name: str
    family_name: str
    birth_date: date
    sex_at_birth: str


@strawberry.type
class PatientPageGQL:
    items: list[PatientGQL]
    total: int
    limit: int
    offset: int
