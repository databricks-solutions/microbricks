"""BFF GraphQL context — user token forwarding + per-request DataLoaders."""
from __future__ import annotations

import os
from functools import cached_property
from uuid import UUID

from fastapi import Request
from strawberry.dataloader import DataLoader
from strawberry.fastapi.context import BaseContext

from ...clients import (
    Appointment,
    AppointmentClient,
    BillingClient,
    Invoice,
    LabClient,
    LabOrder,
    Patient,
    PatientClient,
    Prescription,
    PrescriptionClient,
    Provider,
    ProviderClient,
)


class BFFGraphQLContext(BaseContext):
    def __init__(self, *, user_token: str, branch: str | None, request: Request):
        super().__init__()
        self.user_token = user_token
        self.branch = branch
        self.request = request

    @cached_property
    def patient_loader(self) -> DataLoader[UUID, Patient | None]:
        return DataLoader(load_fn=self._batch_patients)

    @cached_property
    def provider_loader(self) -> DataLoader[UUID, Provider | None]:
        return DataLoader(load_fn=self._batch_providers)

    async def _batch_patients(self, ids: list[UUID]) -> list[Patient | None]:
        async with PatientClient(self.user_token, self.branch) as client:
            results = await client.list_by_ids(list(ids))
        lookup = {p.id: p for p in results}
        return [lookup.get(uid) for uid in ids]

    async def _batch_providers(self, ids: list[UUID]) -> list[Provider | None]:
        async with ProviderClient(self.user_token, self.branch) as client:
            results = await client.list_by_ids(list(ids))
        lookup = {p.id: p for p in results}
        return [lookup.get(uid) for uid in ids]


async def get_bff_context(request: Request) -> BFFGraphQLContext:
    token_header = request.headers.get("X-Forwarded-Access-Token")
    auth_header = request.headers.get("Authorization")

    if token_header:
        token = token_header
    elif auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]
    else:
        local = os.environ.get("LOCAL_DEV_TOKEN", "")
        if not local:
            from fastapi import HTTPException

            raise HTTPException(401, "Missing user token")
        token = local

    branch = request.query_params.get("branch_name") or os.environ.get(
        "LAKEBASE_BRANCH"
    )
    return BFFGraphQLContext(user_token=token, branch=branch, request=request)
