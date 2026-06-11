from typing import Optional
from uuid import UUID

import strawberry


@strawberry.type
class AlertGQL:
    type: str
    severity: str
    title: str
    detail: str
    patient_id: Optional[UUID]
    patient_name: Optional[str]


@strawberry.type
class AlertsResultGQL:
    alerts: list[AlertGQL]
    total: int
    partial: bool
