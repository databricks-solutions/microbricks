"""Typed BFF client for provider-svc via GraphQL (read-only)."""
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


_LIST_QUERY = """
query ListProviders($limit: Int!) {
    providers(limit: $limit) {
        items {
            id
            npi
            givenName
            familyName
            credentialSuffix
            email
            isActive
        }
    }
}
"""


def _to_provider(d: dict) -> Provider:
    return Provider(
        id=d["id"],
        npi=d["npi"],
        given_name=d["givenName"],
        family_name=d["familyName"],
        credential_suffix=d["credentialSuffix"],
        email=d["email"],
        is_active=d["isActive"],
    )


class ProviderClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="provider", branch=branch)

    async def list(self, *, limit: int = 200) -> list[Provider]:
        data = await self._graphql(_LIST_QUERY, {"limit": limit})
        return [_to_provider(p) for p in data["providers"]["items"]]
