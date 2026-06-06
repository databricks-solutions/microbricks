"""Typed BFF client for provider-svc."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from ._base import _BaseSvcClient


class Provider(BaseModel):
    id: UUID
    npi: str
    given_name: str
    family_name: str
    credential_suffix: str | None = None
    email: str
    is_active: bool
    organization_id: UUID


class ProviderClient(_BaseSvcClient):
    def __init__(self, user_token: str):
        super().__init__(user_token, service_slug="provider")

    async def get(self, provider_id: UUID) -> Provider:
        r = await self._client.get(f"/api/v1/providers/{provider_id}")
        r.raise_for_status()
        return Provider.model_validate(r.json())

    async def list(self) -> list[Provider]:
        r = await self._client.get("/api/v1/providers")
        r.raise_for_status()
        return [Provider.model_validate(x) for x in r.json()]
