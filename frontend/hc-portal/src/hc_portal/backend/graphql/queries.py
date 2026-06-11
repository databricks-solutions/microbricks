"""Root BFF GraphQL queries — fan out to downstream services."""
import asyncio
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.types import Info

from ...clients import (
    AppointmentClient,
    BillingClient,
    LabClient,
    PatientClient,
    PrescriptionClient,
    ProviderClient,
)
from .context import BFFGraphQLContext
from .types.alert import AlertGQL, AlertsResultGQL
from .types.appointment import AppointmentGQL, AppointmentPageGQL
from .types.billing import InvoiceGQL, InvoicePageGQL
from .types.billing_overview import BillingOverviewGQL
from .types.dashboard import DashboardStatsGQL
from .types.lab import LabOrderGQL, LabOrderPageGQL
from .types.patient import PatientGQL, PatientPageGQL
from .types.patient_summary import PatientSummaryGQL
from .types.prescription import PrescriptionGQL, PrescriptionPageGQL
from .types.provider import ProviderGQL, ProviderPageGQL
from .types.timeline import TimelineEventGQL


def _clamp(limit: int, offset: int) -> tuple[int, int]:
    return max(1, min(limit, 200)), max(0, offset)


_SCAN_MAX_PAGES = 5
_SCAN_PAGE_SIZE = 200


async def _scan_all(fetch_page) -> tuple[list, bool]:
    out: list = []
    for idx in range(_SCAN_MAX_PAGES):
        page = await fetch_page(_SCAN_PAGE_SIZE, idx * _SCAN_PAGE_SIZE)
        out.extend(page.items)
        if len(page.items) < _SCAN_PAGE_SIZE:
            return out, False
    return out, True


async def _aging_aggregate(billing: BillingClient) -> tuple[int, int, int]:
    today = date.today()
    total_outstanding = 0
    overdue = 0
    due_soon = 0
    for page_idx in range(_SCAN_MAX_PAGES):
        page = await billing.list_invoices(
            status="outstanding",
            limit=_SCAN_PAGE_SIZE,
            offset=page_idx * _SCAN_PAGE_SIZE,
        )
        for inv in page.items:
            total_outstanding += inv.total_amount_cents
            if inv.due_at and inv.due_at.date() < today:
                overdue += 1
            elif inv.due_at and (inv.due_at.date() - today).days <= 7:
                due_soon += 1
        if len(page.items) < _SCAN_PAGE_SIZE:
            break
    return total_outstanding, overdue, due_soon


async def _resolve_patient_ids(
    patient_client: PatientClient, patient_q: str
) -> list[UUID] | None:
    """Resolve patient name search to a list of patient IDs.
    Returns None if the lookup fails (degrade gracefully)."""
    try:
        page = await patient_client.list(q=patient_q, limit=200, offset=0)
        return [p.id for p in page.items]
    except Exception:
        return None


@strawberry.type
class Query:
    @strawberry.field
    async def patients(
        self,
        info: Info[BFFGraphQLContext, None],
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PatientPageGQL:
        ctx = info.context
        safe_limit, safe_offset = _clamp(limit, offset)
        async with PatientClient(ctx.user_token, ctx.branch) as client:
            page = await client.list(q=q, limit=safe_limit, offset=safe_offset)
        return PatientPageGQL(
            items=[
                PatientGQL(
                    id=p.id, mrn=p.mrn, given_name=p.given_name,
                    family_name=p.family_name, birth_date=p.birth_date,
                    sex_at_birth=p.sex_at_birth,
                )
                for p in page.items
            ],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    @strawberry.field
    async def patient(self, info: Info[BFFGraphQLContext, None], id: UUID) -> PatientGQL | None:
        ctx = info.context
        async with PatientClient(ctx.user_token, ctx.branch) as client:
            try:
                p = await client.get(id)
            except Exception:
                return None
        return PatientGQL(
            id=p.id, mrn=p.mrn, given_name=p.given_name,
            family_name=p.family_name, birth_date=p.birth_date,
            sex_at_birth=p.sex_at_birth,
        )

    @strawberry.field
    async def providers(
        self,
        info: Info[BFFGraphQLContext, None],
        q: str | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ProviderPageGQL:
        ctx = info.context
        safe_limit, safe_offset = _clamp(limit, offset)
        async with ProviderClient(ctx.user_token, ctx.branch) as client:
            page = await client.list(q=q, is_active=is_active, limit=safe_limit, offset=safe_offset)
        return ProviderPageGQL(
            items=[
                ProviderGQL(
                    id=p.id, npi=p.npi, given_name=p.given_name,
                    family_name=p.family_name, credential_suffix=p.credential_suffix,
                    email=p.email, is_active=p.is_active,
                    organization_id=p.organization_id,
                )
                for p in page.items
            ],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    @strawberry.field
    async def appointments(
        self,
        info: Info[BFFGraphQLContext, None],
        patient_id: UUID | None = None,
        provider_id: UUID | None = None,
        status: str | None = None,
        visit_type_code: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        patient_q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AppointmentPageGQL:
        ctx = info.context
        safe_limit, safe_offset = _clamp(limit, offset)

        async with (
            AppointmentClient(ctx.user_token, ctx.branch) as appointment,
            PatientClient(ctx.user_token, ctx.branch) as patient_client,
        ):
            resolved_patient_id = patient_id
            if patient_q and not patient_id:
                matched = await _resolve_patient_ids(patient_client, patient_q)
                if matched is not None:
                    if not matched:
                        return AppointmentPageGQL(
                            items=[], total=0, limit=safe_limit, offset=safe_offset
                        )
                    if len(matched) == 1:
                        resolved_patient_id = matched[0]

            page = await appointment.list(
                q=None,
                status=status,
                visit_type_code=visit_type_code,
                patient_id=resolved_patient_id,
                provider_id=provider_id,
                from_date=from_date,
                to_date=to_date,
                limit=safe_limit,
                offset=safe_offset,
            )

        return AppointmentPageGQL(
            items=[
                AppointmentGQL(
                    id=a.id, patient_id=a.patient_id, provider_id=a.provider_id,
                    visit_type_code=a.visit_type_code,
                    scheduled_start=a.scheduled_start,
                    scheduled_end=a.scheduled_end, status=a.status,
                    reason=a.reason,
                )
                for a in page.items
            ],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    @strawberry.field
    async def lab_orders(
        self,
        info: Info[BFFGraphQLContext, None],
        patient_id: UUID | None = None,
        status: list[str] | None = None,
        patient_q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> LabOrderPageGQL:
        ctx = info.context
        safe_limit, safe_offset = _clamp(limit, offset)

        async with (
            LabClient(ctx.user_token, ctx.branch) as lab,
            PatientClient(ctx.user_token, ctx.branch) as patient_client,
        ):
            resolved_patient_id = patient_id
            if patient_q and not patient_id:
                matched = await _resolve_patient_ids(patient_client, patient_q)
                if matched is not None:
                    if not matched:
                        return LabOrderPageGQL(
                            items=[], total=0, limit=safe_limit, offset=safe_offset
                        )
                    if len(matched) == 1:
                        resolved_patient_id = matched[0]

            page = await lab.list_orders(
                patient_id=resolved_patient_id, status=status,
                limit=safe_limit, offset=safe_offset,
            )

        return LabOrderPageGQL(
            items=[
                LabOrderGQL(
                    id=o.id, patient_id=o.patient_id,
                    ordering_provider_id=o.ordering_provider_id,
                    appointment_id=o.appointment_id, panel_code=o.panel_code,
                    status=o.status, ordered_at=o.ordered_at,
                    collected_at=o.collected_at, resulted_at=o.resulted_at,
                )
                for o in page.items
            ],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    @strawberry.field
    async def prescriptions(
        self,
        info: Info[BFFGraphQLContext, None],
        patient_id: UUID | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PrescriptionPageGQL:
        ctx = info.context
        safe_limit, safe_offset = _clamp(limit, offset)
        async with PrescriptionClient(ctx.user_token, ctx.branch) as client:
            page = await client.list(
                patient_id=patient_id, status=status,
                limit=safe_limit, offset=safe_offset,
            )
        return PrescriptionPageGQL(
            items=[
                PrescriptionGQL(
                    id=rx.id, patient_id=rx.patient_id,
                    prescribing_provider_id=rx.prescribing_provider_id,
                    medication_code=rx.medication_code, dose_text=rx.dose_text,
                    quantity=rx.quantity, refills_remaining=rx.refills_remaining,
                    status=rx.status, start_at=rx.start_at, end_at=rx.end_at,
                )
                for rx in page.items
            ],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    @strawberry.field
    async def invoices(
        self,
        info: Info[BFFGraphQLContext, None],
        patient_id: UUID | None = None,
        status: str | None = None,
        patient_q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> InvoicePageGQL:
        ctx = info.context
        safe_limit, safe_offset = _clamp(limit, offset)

        async with (
            BillingClient(ctx.user_token, ctx.branch) as billing,
            PatientClient(ctx.user_token, ctx.branch) as patient_client,
        ):
            resolved_patient_id = patient_id
            if patient_q and not patient_id:
                matched = await _resolve_patient_ids(patient_client, patient_q)
                if matched is not None:
                    if not matched:
                        return InvoicePageGQL(
                            items=[], total=0, limit=safe_limit, offset=safe_offset
                        )
                    if len(matched) == 1:
                        resolved_patient_id = matched[0]

            page = await billing.list_invoices(
                patient_id=resolved_patient_id, status=status,
                limit=safe_limit, offset=safe_offset,
            )

        return InvoicePageGQL(
            items=[
                InvoiceGQL(
                    id=inv.id, patient_id=inv.patient_id,
                    appointment_id=inv.appointment_id,
                    total_amount_cents=inv.total_amount_cents,
                    currency=inv.currency, status=inv.status,
                    issued_at=inv.issued_at, due_at=inv.due_at,
                )
                for inv in page.items
            ],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    @strawberry.field(description="Aggregate counts from all 6 services (concurrent fan-out).")
    async def dashboard_stats(self, info: Info[BFFGraphQLContext, None]) -> DashboardStatsGQL:
        ctx = info.context
        today = date.today()

        async with (
            PatientClient(ctx.user_token, ctx.branch) as patient,
            ProviderClient(ctx.user_token, ctx.branch) as provider,
            AppointmentClient(ctx.user_token, ctx.branch) as appointment,
            LabClient(ctx.user_token, ctx.branch) as lab,
            PrescriptionClient(ctx.user_token, ctx.branch) as rx,
            BillingClient(ctx.user_token, ctx.branch) as billing,
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

        def _safe(r: int | BaseException) -> int | None:
            return r if isinstance(r, int) else None

        partial = any(isinstance(r, BaseException) for r in results)
        return DashboardStatsGQL(
            total_patients=results[0] if isinstance(results[0], int) else 0,
            total_providers=_safe(results[1]),
            total_appointments=_safe(results[2]),
            todays_appointments=_safe(results[3]),
            total_prescriptions=_safe(results[4]),
            active_prescriptions=_safe(results[5]),
            total_lab_orders=_safe(results[6]),
            pending_labs=_safe(results[7]),
            total_invoices=_safe(results[8]),
            partial=partial,
        )

    @strawberry.field(description="Composite patient view from 5 services (concurrent fan-out).")
    async def patient_summary(
        self, info: Info[BFFGraphQLContext, None], id: UUID
    ) -> PatientSummaryGQL:
        ctx = info.context

        async with (
            PatientClient(ctx.user_token, ctx.branch) as patient,
            AppointmentClient(ctx.user_token, ctx.branch) as appointment,
            LabClient(ctx.user_token, ctx.branch) as lab,
            PrescriptionClient(ctx.user_token, ctx.branch) as rx,
            BillingClient(ctx.user_token, ctx.branch) as billing,
        ):
            results = await asyncio.gather(
                patient.get(id),
                appointment.list_for_patient(id, limit=3, order="desc"),
                lab.list_orders_for_patient(id, status="resulted", limit=5),
                rx.list_active_for_patient(id),
                billing.list_outstanding_for_patient(id),
                return_exceptions=True,
            )

        p, appts, labs, rxs, bills = results
        if isinstance(p, BaseException):
            from strawberry import exceptions
            raise Exception("patient-svc unavailable")

        partial = any(isinstance(r, BaseException) for r in (appts, labs, rxs, bills))

        def _safe_list(v):
            return [] if isinstance(v, BaseException) else v

        return PatientSummaryGQL(
            patient=PatientGQL(
                id=p.id, mrn=p.mrn, given_name=p.given_name,
                family_name=p.family_name, birth_date=p.birth_date,
                sex_at_birth=p.sex_at_birth,
            ),
            last_appointments=[
                AppointmentGQL(
                    id=a.id, patient_id=a.patient_id, provider_id=a.provider_id,
                    visit_type_code=a.visit_type_code,
                    scheduled_start=a.scheduled_start,
                    scheduled_end=a.scheduled_end, status=a.status,
                    reason=a.reason,
                )
                for a in _safe_list(appts)
            ],
            active_prescriptions=[
                PrescriptionGQL(
                    id=r.id, patient_id=r.patient_id,
                    prescribing_provider_id=r.prescribing_provider_id,
                    medication_code=r.medication_code, dose_text=r.dose_text,
                    quantity=r.quantity, refills_remaining=r.refills_remaining,
                    status=r.status, start_at=r.start_at, end_at=r.end_at,
                )
                for r in _safe_list(rxs)
            ],
            recent_lab_orders=[
                LabOrderGQL(
                    id=o.id, patient_id=o.patient_id,
                    ordering_provider_id=o.ordering_provider_id,
                    appointment_id=o.appointment_id, panel_code=o.panel_code,
                    status=o.status, ordered_at=o.ordered_at,
                    collected_at=o.collected_at, resulted_at=o.resulted_at,
                )
                for o in _safe_list(labs)
            ],
            outstanding_invoices=[
                InvoiceGQL(
                    id=inv.id, patient_id=inv.patient_id,
                    appointment_id=inv.appointment_id,
                    total_amount_cents=inv.total_amount_cents,
                    currency=inv.currency, status=inv.status,
                    issued_at=inv.issued_at, due_at=inv.due_at,
                )
                for inv in _safe_list(bills)
            ],
            partial=partial,
        )

    @strawberry.field(description="Unified chronological timeline for a patient.")
    async def patient_timeline(
        self, info: Info[BFFGraphQLContext, None], id: UUID
    ) -> list[TimelineEventGQL]:
        ctx = info.context

        async with (
            AppointmentClient(ctx.user_token, ctx.branch) as appointment,
            PrescriptionClient(ctx.user_token, ctx.branch) as rx,
            LabClient(ctx.user_token, ctx.branch) as lab,
            BillingClient(ctx.user_token, ctx.branch) as billing,
        ):
            results = await asyncio.gather(
                appointment.list_for_patient(id, limit=20, order="desc"),
                rx.list_active_for_patient(id),
                lab.list_orders_for_patient(id, limit=20),
                billing.list_outstanding_for_patient(id),
                return_exceptions=True,
            )

        appts, rxs, labs, bills = results
        events: list[TimelineEventGQL] = []

        if not isinstance(appts, BaseException):
            for a in appts:
                events.append(TimelineEventGQL(
                    timestamp=a.scheduled_start,
                    event_type="appointment",
                    title=f"{a.visit_type_code} visit",
                    detail=a.reason,
                    status=a.status,
                ))

        if not isinstance(rxs, BaseException):
            for r in rxs:
                events.append(TimelineEventGQL(
                    timestamp=r.start_at,
                    event_type="prescription",
                    title=f"Rx: {r.medication_code}",
                    detail=r.dose_text,
                    status=r.status,
                ))

        if not isinstance(labs, BaseException):
            for lo in labs:
                events.append(TimelineEventGQL(
                    timestamp=lo.ordered_at,
                    event_type="lab",
                    title=f"Lab: {lo.panel_code}",
                    detail=None,
                    status=lo.status,
                ))

        if not isinstance(bills, BaseException):
            for b in bills:
                events.append(TimelineEventGQL(
                    timestamp=b.issued_at,
                    event_type="billing",
                    title=f"Invoice: ${b.total_amount_cents / 100:.2f}",
                    detail=None,
                    status=b.status,
                ))

        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events

    @strawberry.field(description="Clinical alerts: overdue invoices, stale labs, no follow-up.")
    async def alerts(
        self,
        info: Info[BFFGraphQLContext, None],
        q: str | None = None,
        severity: str | None = None,
        type: str | None = None,
    ) -> AlertsResultGQL:
        ctx = info.context

        async with (
            BillingClient(ctx.user_token, ctx.branch) as billing,
            LabClient(ctx.user_token, ctx.branch) as lab,
            AppointmentClient(ctx.user_token, ctx.branch) as appointment,
            PatientClient(ctx.user_token, ctx.branch) as patient,
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
        labs_items, _ = _unpack(labs_res)
        appts_items, _ = _unpack(appts_res)
        patients_items, _ = _unpack(patients_res)

        patient_map = {str(p.id): f"{p.given_name} {p.family_name}" for p in patients_items}
        now = datetime.now(timezone.utc)
        today = date.today()
        alert_list: list[AlertGQL] = []

        for inv in invoices:
            if inv.status == "outstanding" and inv.due_at and inv.due_at.date() < today:
                alert_list.append(AlertGQL(
                    type="overdue_invoice",
                    severity="warning",
                    title="Overdue invoice",
                    detail=f"${inv.total_amount_cents / 100:.2f} due {inv.due_at.date()}",
                    patient_id=inv.patient_id,
                    patient_name=patient_map.get(str(inv.patient_id)),
                ))

        for lo in labs_items:
            if lo.status in ("ordered", "collected"):
                hours_waiting = (now - lo.ordered_at).total_seconds() / 3600
                if hours_waiting > 48:
                    alert_list.append(AlertGQL(
                        type="stale_lab",
                        severity="info",
                        title="Lab pending > 48h",
                        detail=f"{lo.panel_code} ordered {lo.ordered_at.date()}",
                        patient_id=lo.patient_id,
                        patient_name=patient_map.get(str(lo.patient_id)),
                    ))

        if appts_items and patients_items:
            patients_with_future_appts = {
                str(a.patient_id)
                for a in appts_items
                if a.scheduled_start > now
            }
            for p in patients_items:
                if str(p.id) not in patients_with_future_appts:
                    alert_list.append(AlertGQL(
                        type="no_followup",
                        severity="info",
                        title="No upcoming appointment",
                        detail="Consider scheduling a follow-up",
                        patient_id=p.id,
                        patient_name=f"{p.given_name} {p.family_name}",
                    ))

        if severity:
            alert_list = [a for a in alert_list if a.severity == severity]
        if type:
            alert_list = [a for a in alert_list if a.type == type]
        if q:
            needle = q.lower()
            alert_list = [
                a for a in alert_list
                if needle in a.title.lower()
                or needle in a.detail.lower()
                or (a.patient_name or "").lower().find(needle) >= 0
            ]

        alert_list.sort(key=lambda a: (0 if a.severity == "warning" else 1, a.title))
        return AlertsResultGQL(alerts=alert_list, total=len(alert_list), partial=partial)

    @strawberry.field(description="Paginated billing with aging aggregate tiles.")
    async def billing_overview(
        self,
        info: Info[BFFGraphQLContext, None],
        q: str | None = None,
        status: str | None = None,
        patient_q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> BillingOverviewGQL:
        ctx = info.context
        safe_limit, safe_offset = _clamp(limit, offset)

        async with (
            BillingClient(ctx.user_token, ctx.branch) as billing,
            PatientClient(ctx.user_token, ctx.branch) as patient_client,
        ):
            resolved_patient_id: UUID | None = None
            partial = False
            if patient_q:
                matched = await _resolve_patient_ids(patient_client, patient_q)
                if matched is not None:
                    if not matched:
                        return BillingOverviewGQL(
                            invoices=[], total=0, limit=safe_limit, offset=safe_offset,
                            total_outstanding_cents=0, overdue_count=0, due_soon_count=0,
                            partial=False,
                        )
                    if len(matched) == 1:
                        resolved_patient_id = matched[0]
                else:
                    partial = True

            page_task = billing.list_invoices(
                q=q, status=status, patient_id=resolved_patient_id,
                limit=safe_limit, offset=safe_offset,
            )
            aging_task = _aging_aggregate(billing)
            invoice_page, aging = await asyncio.gather(
                page_task, aging_task, return_exceptions=True
            )

        if isinstance(invoice_page, BaseException):
            raise Exception("billing-svc unavailable")

        if isinstance(aging, BaseException):
            total_outstanding, overdue, due_soon = 0, 0, 0
            partial = True
        else:
            total_outstanding, overdue, due_soon = aging

        return BillingOverviewGQL(
            invoices=[
                InvoiceGQL(
                    id=inv.id, patient_id=inv.patient_id,
                    appointment_id=inv.appointment_id,
                    total_amount_cents=inv.total_amount_cents,
                    currency=inv.currency, status=inv.status,
                    issued_at=inv.issued_at, due_at=inv.due_at,
                )
                for inv in invoice_page.items
            ],
            total=invoice_page.total,
            limit=safe_limit,
            offset=safe_offset,
            total_outstanding_cents=total_outstanding,
            overdue_count=overdue,
            due_soon_count=due_soon,
            partial=partial,
        )
