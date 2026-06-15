from typing import Optional
from uuid import UUID

import strawberry


@strawberry.type
class ProviderGQL:
    id: UUID
    npi: str
    given_name: str
    family_name: str
    credential_suffix: Optional[str]
    email: str
    is_active: bool
    organization_id: UUID


@strawberry.type
class ProviderPageGQL:
    items: list[ProviderGQL]
    total: int
    limit: int
    offset: int
