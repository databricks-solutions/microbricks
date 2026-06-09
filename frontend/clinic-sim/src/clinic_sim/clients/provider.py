"""Typed BFF client for provider-svc (read-only)."""
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


class ProviderClient(_BaseSvcClient):
    def __init__(self, user_token: str):
        super().__init__(user_token, service_slug="provider")

    async def list(self, *, limit: int = 200) -> list[Provider]:
        """All providers (up to one page) for the simulator's directory cache.

        provider-svc returns the paginated envelope
        `{items, total, limit, offset}` — caps `limit` at 200 (the svc max).
        The simulator only needs the directory snapshot, not pagination state.
        """
        r = await self._client.get(
            "/api/v1/providers", params={"limit": limit}
        )
        r.raise_for_status()
        return [Provider.model_validate(x) for x in r.json()["items"]]
