"""BFF aggregation routes.

This is the *only* place in the architecture where data from multiple services
is combined. Backend services never call each other — see
`.claude/skills/hc-bff-pattern/SKILL.md` for the rules.

Canonical pattern from the skill:

  - Per-request clients constructed inside the handler (not at module scope).
  - Concurrent fan-out via `asyncio.gather(..., return_exceptions=True)`.
  - Both `Authorization: Bearer <token>` AND `X-Forwarded-Access-Token`
    forwarded by `_BaseSvcClient`.
  - Partial-failure handling: peripheral failures degrade gracefully with a
    `partial: true` flag; a failure on the *required* call (the patient itself)
    propagates as a 502.
"""
from __future__ import annotations

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...auth import user_token
from ...clients import (
    AppointmentClient,
    BillingClient,
    LabClient,
    PatientClient,
    PrescriptionClient,
)

router = APIRouter(prefix="/bff", tags=["aggregations"])


class PatientSummaryOut(BaseModel):
    patient: dict
    last_appointments: list[dict]
    active_prescriptions: list[dict]
    recent_lab_orders: list[dict]
    outstanding_invoices: list[dict]
    partial: bool = False


@router.get(
    "/patient-summary/{patient_id}",
    response_model=PatientSummaryOut,
    operation_id="getPatientSummary",
)
async def patient_summary(
    patient_id: UUID,
    token: Annotated[str, Depends(user_token)],
) -> PatientSummaryOut:
    """Compose a single patient view from five backend services concurrently.

    Wall-clock latency = max(per-call), not sum. If any *peripheral* call fails
    the response still 200s with `partial: true` and an empty list for that
    section. If the patient lookup itself fails the response is a 502.
    """
    async with (
        PatientClient(token) as patient,
        AppointmentClient(token) as appointment,
        LabClient(token) as lab,
        PrescriptionClient(token) as rx,
        BillingClient(token) as billing,
    ):
        results = await asyncio.gather(
            patient.get(patient_id),
            appointment.list_for_patient(patient_id, limit=3, order="desc"),
            lab.list_orders_for_patient(patient_id, status="resulted", limit=5),
            rx.list_active_for_patient(patient_id),
            billing.list_outstanding_for_patient(patient_id),
            return_exceptions=True,
        )

    p, appts, labs, rxs, bills = results
    if isinstance(p, BaseException):
        raise HTTPException(502, "patient-svc unavailable") from p

    def _safe(value, default):
        return default if isinstance(value, BaseException) else value

    partial = any(isinstance(r, BaseException) for r in (appts, labs, rxs, bills))

    return PatientSummaryOut(
        patient=p.model_dump(mode="json"),
        last_appointments=[a.model_dump(mode="json") for a in _safe(appts, [])],
        recent_lab_orders=[lo.model_dump(mode="json") for lo in _safe(labs, [])],
        active_prescriptions=[r.model_dump(mode="json") for r in _safe(rxs, [])],
        outstanding_invoices=[b.model_dump(mode="json") for b in _safe(bills, [])],
        partial=partial,
    )


@router.get("/healthz", operation_id="bffHealthz")
async def healthz() -> dict[str, bool]:
    """BFF liveness probe. Does NOT touch downstream services."""
    return {"ok": True}


class PatientListItem(BaseModel):
    """Light shape returned by the BFF list view — fewer fields than the
    full patient record, no per-patient fan-out."""

    id: UUID
    mrn: str
    given_name: str
    family_name: str


@router.get(
    "/patients",
    response_model=list[PatientListItem],
    operation_id="listPatientsBff",
)
async def list_patients(
    token: Annotated[str, Depends(user_token)],
) -> list[PatientListItem]:
    """List patients for the index page. Simple proxy — no aggregation.

    A read-only proxy is acceptable here because the patient list page on the
    frontend doesn't render any other service's data; we keep it on the BFF
    only so the React app talks to a single origin.
    """
    async with PatientClient(token) as patient:
        patients = await patient.list()
    return [
        PatientListItem(
            id=p.id, mrn=p.mrn, given_name=p.given_name, family_name=p.family_name
        )
        for p in patients
    ]
