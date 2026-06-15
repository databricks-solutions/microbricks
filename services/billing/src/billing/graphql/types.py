from __future__ import annotations

from datetime import datetime
from uuid import UUID

import strawberry


@strawberry.type
class InvoiceType:
    id: UUID
    patient_id: UUID
    appointment_id: UUID | None
    total_amount_cents: int
    currency: str
    status: str
    issued_at: datetime
    due_at: datetime | None


@strawberry.type
class InvoicePage:
    items: list[InvoiceType]
    total: int
    limit: int
    offset: int


@strawberry.input
class InvoiceCreateInput:
    patient_id: UUID
    total_amount_cents: int
    appointment_id: UUID | None = None
    currency: str = "USD"
    status: str = "draft"
    issued_at: datetime | None = None
    due_at: datetime | None = None
