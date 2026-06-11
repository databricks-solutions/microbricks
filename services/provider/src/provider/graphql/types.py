from __future__ import annotations

from uuid import UUID

import strawberry


@strawberry.type
class ProviderType:
    id: UUID
    npi: str
    given_name: str
    family_name: str
    credential_suffix: str | None
    email: str
    is_active: bool
    organization_id: UUID


@strawberry.type
class ProviderPage:
    items: list[ProviderType]
    total: int
    limit: int
    offset: int
