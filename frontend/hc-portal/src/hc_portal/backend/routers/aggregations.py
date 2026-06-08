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

Pagination/search/filter contract on the list endpoints:

  - Every list endpoint accepts `q` (search), domain filters, `limit`
    (default 50, max 200) and `offset` (default 0).
  - Every list endpoint returns `{items, total, limit, offset, partial?}`
    where `total` is the unfiltered count *under the current predicate* so
    the UI can render a pagination control without a second round-trip.
  - Patient/provider name joins are resolved per-page via the `ids` batch
    on `patient.list_by_ids` / `provider.list_by_ids` — we don't pull the
    whole directory just to enrich 50 rows.
"""
from __future__ import annotations

import asyncio
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...auth import user_token
from ...clients import (
    AppointmentClient,
    BillingClient,
    LabClient,
    PatientClient,
    PrescriptionClient,
    ProviderClient,
)

router = APIRouter(prefix="/bff", tags=["aggregations"])


def _clamp(limit: int, offset: int) -> tuple[int, int]:
    """Normalise paging args — caps `limit` at 200 and clamps `offset` to
    non-negative. The per-service handlers do the same; we duplicate here
    so the BFF response reports the actual values the user will see."""
    return max(1, min(limit, 200)), max(0, offset)


def _provider_label(given: str, family: str, suffix: str | None) -> str:
    """Display label for a provider — e.g. "Sarah Lee, MD"."""
    return f"{given} {family}" + (f", {suffix}" if suffix else "")


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
        ProviderClient(token) as provider,
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

        # Resolve provider names *only* for the appointments we're returning
        # — no longer pulls the full provider directory.
        appt_provider_ids: list[UUID] = []
        if not isinstance(appts, BaseException):
            appt_provider_ids = list({a.provider_id for a in appts})
        try:
            providers_raw = await provider.list_by_ids(appt_provider_ids)
        except Exception:
            providers_raw = []

    def _safe(value, default):
        return default if isinstance(value, BaseException) else value

    provider_map: dict[str, str] = {
        str(pv.id): _provider_label(pv.given_name, pv.family_name, pv.credential_suffix)
        for pv in providers_raw
    }

    partial = any(isinstance(r, BaseException) for r in (appts, labs, rxs, bills))

    enriched_appts = []
    for a in _safe(appts, []):
        d = a.model_dump(mode="json")
        d["provider_name"] = provider_map.get(str(a.provider_id), "Unknown")
        enriched_appts.append(d)

    return PatientSummaryOut(
        patient=p.model_dump(mode="json"),
        last_appointments=enriched_appts,
        recent_lab_orders=[lo.model_dump(mode="json") for lo in _safe(labs, [])],
        active_prescriptions=[r.model_dump(mode="json") for r in _safe(rxs, [])],
        outstanding_invoices=[b.model_dump(mode="json") for b in _safe(bills, [])],
        partial=partial,
    )


class DashboardStatsOut(BaseModel):
    total_patients: int
    total_providers: int
    total_appointments: int
    todays_appointments: int
    total_prescriptions: int
    active_prescriptions: int
    total_lab_orders: int
    pending_labs: int
    total_invoices: int
    partial: bool = False


@router.get(
    "/dashboard-stats",
    response_model=DashboardStatsOut,
    operation_id="getDashboardStats",
)
async def dashboard_stats(
    token: Annotated[str, Depends(user_token)],
) -> DashboardStatsOut:
    """Return aggregate counts for the dashboard overview cards.

    Each count is computed server-side by the owning service via a dedicated
    `/count` endpoint — we never `len()` a truncated list (which would silently
    cap at the per-service `LIMIT`). Fan-out is concurrent so wall-clock is
    `max(per-call)`, not the sum. Partial failures degrade to 0 for that
    individual count rather than breaking the page (`partial: true`).
    """
    today = date.today()

    async with (
        PatientClient(token) as patient,
        ProviderClient(token) as provider,
        AppointmentClient(token) as appointment,
        PrescriptionClient(token) as rx,
        LabClient(token) as lab,
        BillingClient(token) as billing,
    ):
        results = await asyncio.gather(
            patient.count(),
            provider.count(),
            appointment.count(),
            appointment.count(on_date=today),
            rx.count(),
            rx.count(status="active"),
            lab.count(),
            lab.count(status=["ordered", "collected"]),
            billing.count(),
            return_exceptions=True,
        )

    def _safe(value: object) -> int:
        return 0 if isinstance(value, BaseException) else int(value)  # type: ignore[arg-type]

    (
        total_patients,
        total_providers,
        total_appointments,
        todays_appointments,
        total_prescriptions,
        active_prescriptions,
        total_lab_orders,
        pending_labs,
        total_invoices,
    ) = (_safe(r) for r in results)

    return DashboardStatsOut(
        total_patients=total_patients,
        total_providers=total_providers,
        total_appointments=total_appointments,
        todays_appointments=todays_appointments,
        total_prescriptions=total_prescriptions,
        active_prescriptions=active_prescriptions,
        total_lab_orders=total_lab_orders,
        pending_labs=pending_labs,
        total_invoices=total_invoices,
        partial=any(isinstance(r, BaseException) for r in results),
    )


class AppointmentWithNames(BaseModel):
    id: UUID
    patient_id: UUID
    provider_id: UUID
    patient_name: str
    provider_name: str
    visit_type_code: str
    scheduled_start: str
    scheduled_end: str
    status: str
    reason: str | None = None


class AppointmentsPageOut(BaseModel):
    """Paginated appointments page enriched with patient + provider names."""

    items: list[AppointmentWithNames]
    total: int
    limit: int
    offset: int
    partial: bool = False


@router.get(
    "/appointments",
    response_model=AppointmentsPageOut,
    operation_id="listAppointmentsBff",
)
async def list_appointments(
    token: Annotated[str, Depends(user_token)],
    q: str | None = None,
    status: str | None = None,
    visit_type_code: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    patient_q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AppointmentsPageOut:
    """Paginated appointments with patient + provider names resolved.

    Server-side search & filter:

      - `q` matches `reason` / `visit_type_code` on the appointment row.
      - `status`, `visit_type_code`, `from_date`, `to_date` are exact filters
        forwarded to appointment-svc.
      - `patient_q` filters by patient *name*. Because that field lives in
        patient-svc, we first resolve the matching patient IDs there, then
        push `patient_id IN (...)` down via appointment-svc's `patient_id`
        filter — degrading to "no rows" if the search has no matches.

    Name joins resolve only the IDs in the current page (`patient.list_by_ids`,
    `provider.list_by_ids`) — never a "fetch all patients" sweep.
    """
    safe_limit, safe_offset = _clamp(limit, offset)

    async with (
        AppointmentClient(token) as appointment,
        PatientClient(token) as patient,
        ProviderClient(token) as provider,
    ):
        # Cross-service filter: if the user searched by patient name, resolve
        # the matching patient IDs first so the appointment-svc page is
        # narrowed correctly.
        patient_id_filter: UUID | None = None
        partial = False
        if patient_q:
            try:
                page = await patient.list(q=patient_q, limit=200, offset=0)
            except Exception:
                partial = True
                page = None
            if page is not None:
                matched = [p.id for p in page.items]
                if not matched:
                    return AppointmentsPageOut(
                        items=[], total=0, limit=safe_limit, offset=safe_offset
                    )
                # appointment-svc only accepts a single patient_id; if more
                # than one matched, fall back to client-side filter on the
                # page result. Common case: exact-match prefix → single hit.
                if len(matched) == 1:
                    patient_id_filter = matched[0]

        appts_page = await appointment.list(
            q=q,
            status=status,
            visit_type_code=visit_type_code,
            from_date=from_date,
            to_date=to_date,
            patient_id=patient_id_filter,
            limit=safe_limit,
            offset=safe_offset,
        )

        # Page-scoped batch resolution of names.
        patient_ids = list({a.patient_id for a in appts_page.items})
        provider_ids = list({a.provider_id for a in appts_page.items})
        patients_raw, providers_raw = await asyncio.gather(
            patient.list_by_ids(patient_ids),
            provider.list_by_ids(provider_ids),
            return_exceptions=True,
        )

    if isinstance(patients_raw, BaseException):
        partial = True
        patient_map: dict[str, str] = {}
    else:
        patient_map = {
            str(p.id): f"{p.given_name} {p.family_name}" for p in patients_raw
        }

    if isinstance(providers_raw, BaseException):
        partial = True
        provider_map: dict[str, str] = {}
    else:
        provider_map = {
            str(pv.id): _provider_label(pv.given_name, pv.family_name, pv.credential_suffix)
            for pv in providers_raw
        }

    items = [
        AppointmentWithNames(
            id=a.id,
            patient_id=a.patient_id,
            provider_id=a.provider_id,
            patient_name=patient_map.get(str(a.patient_id), "Unknown"),
            provider_name=provider_map.get(str(a.provider_id), "Unknown"),
            visit_type_code=a.visit_type_code,
            scheduled_start=a.scheduled_start.isoformat(),
            scheduled_end=a.scheduled_end.isoformat(),
            status=a.status,
            reason=a.reason,
        )
        for a in appts_page.items
    ]

    # If patient_q matched many patients we couldn't push down server-side;
    # apply the rest as a client-side filter on the page. Note this can
    # under-fill the page — the caller should treat this as best-effort
    # when patient_q is set.
    if patient_q and patient_id_filter is None:
        needle = patient_q.lower()
        items = [it for it in items if needle in it.patient_name.lower()]

    return AppointmentsPageOut(
        items=items,
        total=appts_page.total,
        limit=safe_limit,
        offset=safe_offset,
        partial=partial,
    )


class ProviderListItem(BaseModel):
    id: UUID
    npi: str
    given_name: str
    family_name: str
    credential_suffix: str | None = None
    email: str
    is_active: bool


class ProvidersPageOut(BaseModel):
    items: list[ProviderListItem]
    total: int
    limit: int
    offset: int


@router.get(
    "/providers",
    response_model=ProvidersPageOut,
    operation_id="listProvidersBff",
)
async def list_providers(
    token: Annotated[str, Depends(user_token)],
    q: str | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ProvidersPageOut:
    """Paginated provider directory with name/NPI/email search and an
    active-only toggle."""
    safe_limit, safe_offset = _clamp(limit, offset)
    async with ProviderClient(token) as provider:
        page = await provider.list(
            q=q, is_active=is_active, limit=safe_limit, offset=safe_offset
        )
    return ProvidersPageOut(
        items=[
            ProviderListItem(
                id=p.id,
                npi=p.npi,
                given_name=p.given_name,
                family_name=p.family_name,
                credential_suffix=p.credential_suffix,
                email=p.email,
                is_active=p.is_active,
            )
            for p in page.items
        ],
        total=page.total,
        limit=safe_limit,
        offset=safe_offset,
    )


class BillingOverviewOut(BaseModel):
    """Paginated invoice list + aggregate aging stats.

    The aging stats (`total_outstanding_cents`, `overdue_count`,
    `due_soon_count`) come from a separate `billing.count(...)` + targeted
    queries — they are *not* derived from `len(invoices)` (which is a single
    page).
    """

    invoices: list[dict]
    total: int
    limit: int
    offset: int
    total_outstanding_cents: int
    overdue_count: int
    due_soon_count: int
    partial: bool = False


@router.get(
    "/billing-overview",
    response_model=BillingOverviewOut,
    operation_id="getBillingOverview",
)
async def billing_overview(
    token: Annotated[str, Depends(user_token)],
    q: str | None = None,
    status: str | None = None,
    patient_q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> BillingOverviewOut:
    """Paginated billing list with patient-name search and aging tiles.

    The aging tiles need the *full* outstanding ledger, so we compute them
    server-side via a streaming aggregate (paginating internally up to a
    sensible safety cap). This avoids the "len(list) is wrong" trap when
    there are more invoices than fit in one page.
    """
    safe_limit, safe_offset = _clamp(limit, offset)

    async with (
        BillingClient(token) as billing,
        PatientClient(token) as patient,
    ):
        # Cross-service filter: patient_q → patient ID set.
        patient_id_filter: UUID | None = None
        partial = False
        if patient_q:
            try:
                page = await patient.list(q=patient_q, limit=200, offset=0)
                matched_ids = [p.id for p in page.items]
                if not matched_ids:
                    return BillingOverviewOut(
                        invoices=[],
                        total=0,
                        limit=safe_limit,
                        offset=safe_offset,
                        total_outstanding_cents=0,
                        overdue_count=0,
                        due_soon_count=0,
                        partial=False,
                    )
                if len(matched_ids) == 1:
                    patient_id_filter = matched_ids[0]
            except Exception:
                partial = True

        # Page of invoices + server-side aging aggregate (only for
        # `outstanding` invoices — that's all aging cares about).
        page_task = billing.list_invoices(
            q=q,
            status=status,
            patient_id=patient_id_filter,
            limit=safe_limit,
            offset=safe_offset,
        )
        aging_task = _aging_aggregate(billing)
        invoice_page, aging = await asyncio.gather(
            page_task, aging_task, return_exceptions=True
        )

        if isinstance(invoice_page, BaseException):
            raise HTTPException(502, "billing-svc unavailable") from invoice_page

        # Resolve patient names only for the IDs on this page.
        patient_ids = list({inv.patient_id for inv in invoice_page.items})
        try:
            patients = await patient.list_by_ids(patient_ids)
            patient_map = {
                str(p.id): f"{p.given_name} {p.family_name}" for p in patients
            }
        except Exception:
            patient_map = {}
            partial = True

    if isinstance(aging, BaseException):
        total_outstanding, overdue, due_soon = 0, 0, 0
        partial = True
    else:
        total_outstanding, overdue, due_soon = aging

    enriched: list[dict] = []
    for inv in invoice_page.items:
        d = inv.model_dump(mode="json")
        d["patient_name"] = patient_map.get(str(inv.patient_id), "Unknown")
        enriched.append(d)

    if patient_q and patient_id_filter is None:
        needle = patient_q.lower()
        enriched = [d for d in enriched if needle in d.get("patient_name", "").lower()]

    return BillingOverviewOut(
        invoices=enriched,
        total=invoice_page.total,
        limit=safe_limit,
        offset=safe_offset,
        total_outstanding_cents=total_outstanding,
        overdue_count=overdue,
        due_soon_count=due_soon,
        partial=partial,
    )


# Aging-aggregate hard cap so a runaway billing-svc can't make this BFF call
# pull megabytes of invoice rows. 5 pages × 200 rows = 1000 outstanding
# invoices; way more than any realistic clinic.
_AGING_MAX_PAGES = 5
_AGING_PAGE_SIZE = 200


async def _aging_aggregate(billing: BillingClient) -> tuple[int, int, int]:
    """Walk the `status=outstanding` invoice list to compute aging totals.

    Returns `(total_outstanding_cents, overdue_count, due_soon_count)`.
    Iterates up to `_AGING_MAX_PAGES` pages — beyond that we degrade
    (the dashboard tile would be stale by then anyway).
    """
    today = date.today()
    total_outstanding = 0
    overdue = 0
    due_soon = 0
    for page_idx in range(_AGING_MAX_PAGES):
        page = await billing.list_invoices(
            status="outstanding",
            limit=_AGING_PAGE_SIZE,
            offset=page_idx * _AGING_PAGE_SIZE,
        )
        for inv in page.items:
            total_outstanding += inv.total_amount_cents
            if inv.due_at and inv.due_at.date() < today:
                overdue += 1
            elif inv.due_at and (inv.due_at.date() - today).days <= 7:
                due_soon += 1
        if len(page.items) < _AGING_PAGE_SIZE:
            break
    return total_outstanding, overdue, due_soon


class LabOrderWithNames(BaseModel):
    id: UUID
    patient_id: UUID
    patient_name: str
    ordering_provider_id: UUID
    provider_name: str
    panel_code: str
    status: str
    ordered_at: str
    collected_at: str | None = None
    resulted_at: str | None = None


class LabsPageOut(BaseModel):
    """Paginated lab-order page enriched with patient + provider names."""

    items: list[LabOrderWithNames]
    total: int
    limit: int
    offset: int
    partial: bool = False


@router.get(
    "/labs",
    response_model=LabsPageOut,
    operation_id="listLabsBff",
)
async def list_labs(
    token: Annotated[str, Depends(user_token)],
    q: str | None = None,
    status: Annotated[list[str] | None, Query()] = None,
    patient_q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> LabsPageOut:
    """Paginated lab orders with filter + search + name joins.

    - `q` matches `panel_code` server-side.
    - `status` is repeatable (e.g. the "pending" tab maps to
      `status=ordered&status=collected`).
    - `patient_q` resolves to a `patient_id` filter via patient-svc first
      (single-match fast-path; multi-match falls back to a page-scoped
      client-side filter — best-effort).
    """
    safe_limit, safe_offset = _clamp(limit, offset)

    async with (
        LabClient(token) as lab,
        PatientClient(token) as patient,
        ProviderClient(token) as provider,
    ):
        patient_id_filter: UUID | None = None
        partial = False
        if patient_q:
            try:
                p_page = await patient.list(q=patient_q, limit=200, offset=0)
                matched = [p.id for p in p_page.items]
                if not matched:
                    return LabsPageOut(items=[], total=0, limit=safe_limit, offset=safe_offset)
                if len(matched) == 1:
                    patient_id_filter = matched[0]
            except Exception:
                partial = True

        labs_page = await lab.list_orders(
            q=q,
            status=status,
            patient_id=patient_id_filter,
            limit=safe_limit,
            offset=safe_offset,
        )

        patient_ids = list({lo.patient_id for lo in labs_page.items})
        provider_ids = list({lo.ordering_provider_id for lo in labs_page.items})
        patients_raw, providers_raw = await asyncio.gather(
            patient.list_by_ids(patient_ids),
            provider.list_by_ids(provider_ids),
            return_exceptions=True,
        )

    if isinstance(patients_raw, BaseException):
        partial = True
        patient_map: dict[str, str] = {}
    else:
        patient_map = {
            str(p.id): f"{p.given_name} {p.family_name}" for p in patients_raw
        }

    if isinstance(providers_raw, BaseException):
        partial = True
        provider_map: dict[str, str] = {}
    else:
        provider_map = {
            str(pv.id): f"{pv.given_name} {pv.family_name}" for pv in providers_raw
        }

    items = [
        LabOrderWithNames(
            id=lo.id,
            patient_id=lo.patient_id,
            patient_name=patient_map.get(str(lo.patient_id), "Unknown"),
            ordering_provider_id=lo.ordering_provider_id,
            provider_name=provider_map.get(str(lo.ordering_provider_id), "Unknown"),
            panel_code=lo.panel_code,
            status=lo.status,
            ordered_at=lo.ordered_at.isoformat(),
            collected_at=lo.collected_at.isoformat() if lo.collected_at else None,
            resulted_at=lo.resulted_at.isoformat() if lo.resulted_at else None,
        )
        for lo in labs_page.items
    ]

    if patient_q and patient_id_filter is None:
        needle = patient_q.lower()
        items = [it for it in items if needle in it.patient_name.lower()]

    return LabsPageOut(
        items=items,
        total=labs_page.total,
        limit=safe_limit,
        offset=safe_offset,
        partial=partial,
    )


class AlertItem(BaseModel):
    type: str
    severity: str
    title: str
    detail: str
    patient_id: UUID | None = None
    patient_name: str | None = None


class AlertsOut(BaseModel):
    """Server-built alert list. Pagination/search/filter happen *server-side*
    so the UI doesn't need to know about underlying invoice/lab/patient page
    boundaries. The page itself is small (typically dozens of alerts), so we
    return the full filtered list rather than a paged envelope."""

    alerts: list[AlertItem]
    total: int
    partial: bool = False


# Safety cap when scanning all invoices/labs/patients for alert candidates.
# Beyond this the alerts page degrades (`partial: true`) rather than holding
# the whole DB in memory.
_ALERTS_SCAN_PAGES = 5
_ALERTS_PAGE_SIZE = 200


async def _scan_all(fetch_page) -> tuple[list, bool]:
    """Iterate up to `_ALERTS_SCAN_PAGES` pages of a list endpoint and
    return `(items, truncated_flag)`.

    `fetch_page` is `(limit, offset) -> awaitable Page[T]`; the caller knows
    the row type. (We deliberately don't use a PEP-695 generic parameter
    list here so this stays Python 3.11-compatible.)
    """
    out: list = []
    for idx in range(_ALERTS_SCAN_PAGES):
        page = await fetch_page(_ALERTS_PAGE_SIZE, idx * _ALERTS_PAGE_SIZE)
        out.extend(page.items)
        if len(page.items) < _ALERTS_PAGE_SIZE:
            return out, False
    return out, True


@router.get(
    "/alerts",
    response_model=AlertsOut,
    operation_id="getAlerts",
)
async def get_alerts(
    token: Annotated[str, Depends(user_token)],
    q: str | None = None,
    severity: str | None = None,
    type: Annotated[str | None, Query(alias="type")] = None,
) -> AlertsOut:
    """Clinical alerts: overdue invoices, stale labs, no follow-up.

    Server-side filters:
      - `q` matches the alert title/detail/patient_name (case-insensitive).
      - `severity` exact-match (`warning` / `info`).
      - `type` exact-match (`overdue_invoice` / `stale_lab` / `no_followup`).

    Underlying lists are scanned with a hard page cap so a runaway DB can't
    OOM the BFF; the response flags `partial: true` if any source was truncated.
    """
    from datetime import datetime, timezone

    async with (
        BillingClient(token) as billing,
        LabClient(token) as lab,
        AppointmentClient(token) as appointment,
        PatientClient(token) as patient,
    ):
        results = await asyncio.gather(
            _scan_all(lambda L, O: billing.list_invoices(limit=L, offset=O)),
            _scan_all(lambda L, O: lab.list_orders(limit=L, offset=O)),
            _scan_all(lambda L, O: appointment.list(limit=L, offset=O)),
            _scan_all(lambda L, O: patient.list(limit=L, offset=O)),
            return_exceptions=True,
        )

    invoices_res, labs_res, appts_res, patients_res = results
    partial = False

    def _unpack(r):
        nonlocal partial
        if isinstance(r, BaseException):
            partial = True
            return [], False
        items, truncated = r
        if truncated:
            partial = True
        return items, truncated

    invoices, _ = _unpack(invoices_res)
    labs, _ = _unpack(labs_res)
    appts, _ = _unpack(appts_res)
    patients, _ = _unpack(patients_res)

    patient_map = {str(p.id): f"{p.given_name} {p.family_name}" for p in patients}

    now = datetime.now(timezone.utc)
    today = date.today()
    alerts: list[AlertItem] = []

    for inv in invoices:
        if inv.status == "outstanding" and inv.due_at and inv.due_at.date() < today:
            alerts.append(
                AlertItem(
                    type="overdue_invoice",
                    severity="warning",
                    title="Overdue invoice",
                    detail=f"${inv.total_amount_cents / 100:.2f} due {inv.due_at.date()}",
                    patient_id=inv.patient_id,
                    patient_name=patient_map.get(str(inv.patient_id)),
                )
            )

    for lo in labs:
        if lo.status in ("ordered", "collected"):
            hours_waiting = (now - lo.ordered_at).total_seconds() / 3600
            if hours_waiting > 48:
                alerts.append(
                    AlertItem(
                        type="stale_lab",
                        severity="info",
                        title="Lab pending > 48h",
                        detail=f"{lo.panel_code} ordered {lo.ordered_at.date()}",
                        patient_id=lo.patient_id,
                        patient_name=patient_map.get(str(lo.patient_id)),
                    )
                )

    if appts and patients:
        patients_with_future_appts = {
            str(a.patient_id)
            for a in appts
            if a.scheduled_start > now
        }
        for p in patients:
            if str(p.id) not in patients_with_future_appts:
                alerts.append(
                    AlertItem(
                        type="no_followup",
                        severity="info",
                        title="No upcoming appointment",
                        detail="Consider scheduling a follow-up",
                        patient_id=p.id,
                        patient_name=f"{p.given_name} {p.family_name}",
                    )
                )

    # Apply server-side filter/search after composing the candidate list so
    # the same data set powers all UI filters.
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    if type:
        alerts = [a for a in alerts if a.type == type]
    if q:
        needle = q.lower()
        alerts = [
            a for a in alerts
            if needle in a.title.lower()
            or needle in a.detail.lower()
            or (a.patient_name or "").lower().find(needle) >= 0
        ]

    alerts.sort(key=lambda a: (0 if a.severity == "warning" else 1, a.title))
    return AlertsOut(alerts=alerts, total=len(alerts), partial=partial)


class TimelineEvent(BaseModel):
    timestamp: str
    event_type: str
    title: str
    detail: str | None = None
    status: str | None = None


@router.get(
    "/patient-timeline/{patient_id}",
    response_model=list[TimelineEvent],
    operation_id="getPatientTimeline",
)
async def patient_timeline(
    patient_id: UUID,
    token: Annotated[str, Depends(user_token)],
) -> list[TimelineEvent]:
    """Unified chronological timeline for a patient."""
    async with (
        AppointmentClient(token) as appointment,
        PrescriptionClient(token) as rx,
        LabClient(token) as lab,
        BillingClient(token) as billing,
    ):
        results = await asyncio.gather(
            appointment.list_for_patient(patient_id, limit=20, order="desc"),
            rx.list_active_for_patient(patient_id),
            lab.list_orders_for_patient(patient_id, limit=20),
            billing.list_outstanding_for_patient(patient_id),
            return_exceptions=True,
        )

    appts, rxs, labs, bills = results
    events: list[TimelineEvent] = []

    if not isinstance(appts, BaseException):
        for a in appts:
            events.append(
                TimelineEvent(
                    timestamp=a.scheduled_start.isoformat(),
                    event_type="appointment",
                    title=f"{a.visit_type_code} visit",
                    detail=a.reason,
                    status=a.status,
                )
            )

    if not isinstance(rxs, BaseException):
        for r in rxs:
            events.append(
                TimelineEvent(
                    timestamp=r.start_at.isoformat(),
                    event_type="prescription",
                    title=f"Rx: {r.medication_code}",
                    detail=r.dose_text,
                    status=r.status,
                )
            )

    if not isinstance(labs, BaseException):
        for lo in labs:
            events.append(
                TimelineEvent(
                    timestamp=lo.ordered_at.isoformat(),
                    event_type="lab",
                    title=f"Lab: {lo.panel_code}",
                    status=lo.status,
                )
            )

    if not isinstance(bills, BaseException):
        for b in bills:
            events.append(
                TimelineEvent(
                    timestamp=b.issued_at.isoformat(),
                    event_type="billing",
                    title=f"Invoice: ${b.total_amount_cents / 100:.2f}",
                    status=b.status,
                )
            )

    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events


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


class PatientsPageOut(BaseModel):
    items: list[PatientListItem]
    total: int
    limit: int
    offset: int


@router.get(
    "/patients",
    response_model=PatientsPageOut,
    operation_id="listPatientsBff",
)
async def list_patients(
    token: Annotated[str, Depends(user_token)],
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PatientsPageOut:
    """Paginated patient index with name/MRN search.

    A read-only proxy is acceptable here because the patient list page on the
    frontend doesn't render any other service's data; we keep it on the BFF
    only so the React app talks to a single origin.
    """
    safe_limit, safe_offset = _clamp(limit, offset)
    async with PatientClient(token) as patient:
        page = await patient.list(q=q, limit=safe_limit, offset=safe_offset)
    return PatientsPageOut(
        items=[
            PatientListItem(
                id=p.id, mrn=p.mrn, given_name=p.given_name, family_name=p.family_name
            )
            for p in page.items
        ],
        total=page.total,
        limit=safe_limit,
        offset=safe_offset,
    )
