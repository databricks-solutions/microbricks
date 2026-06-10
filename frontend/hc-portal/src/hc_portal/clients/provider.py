"""Typed BFF client for provider-svc."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from ._base import Page, _BaseSvcClient


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
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="provider", branch=branch)

    async def get(self, provider_id: UUID) -> Provider:
        r = await self._client.get(f"/api/v1/providers/{provider_id}")
        r.raise_for_status()
        return Provider.model_validate(r.json())

    async def list(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[Provider]:
        """Single page of providers with optional search/active filter."""
        params: dict[str, str | int | bool] = {"limit": limit, "offset": offset}
        if q:
            params["q"] = q
        if is_active is not None:
            params["is_active"] = "true" if is_active else "false"
        r = await self._client.get("/api/v1/providers", params=params)
        r.raise_for_status()
        payload = r.json()
        return Page[Provider](
            items=[Provider.model_validate(x) for x in payload["items"]],
            total=int(payload["total"]),
            limit=int(payload["limit"]),
            offset=int(payload["offset"]),
        )

    async def list_by_ids(self, ids: list[UUID]) -> list[Provider]:
        """Batch-resolve providers referenced by a paginated list elsewhere
        (e.g. an appointments page). Returns [] when `ids` is empty
        (no round-trip)."""
        if not ids:
            return []
        params: list[tuple[str, str]] = [("ids", str(i)) for i in ids]
        params.append(("limit", str(min(200, len(ids)))))
        r = await self._client.get("/api/v1/providers", params=params)
        r.raise_for_status()
        return [Provider.model_validate(x) for x in r.json()["items"]]

    async def count(self) -> int:
        r = await self._client.get("/api/v1/providers/count")
        r.raise_for_status()
        return int(r.json()["total"])
