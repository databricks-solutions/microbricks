"""Patient-journey orchestrator.

Drives a single simulated patient through the full clinic flow against the
real backend services. Emits structured events at every step so the UI can
animate the patient's avatar in lockstep with what's actually happening on
the wire.

A "run" is a batch of N journeys orchestrated by `run_simulation`. The whole
run is bounded by a `Semaphore` so a single 10k-patient request can't blow
through service connection pools.
"""
from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Literal
from uuid import UUID

from ..clients import (
    AppointmentClient,
    AppointmentCreatePayload,
    BillingClient,
    InvoiceCreatePayload,
    LabClient,
    LabOrderCreatePayload,
    PatientClient,
    PatientCreatePayload,
    PrescriptionClient,
    PrescriptionCreatePayload,
    ProviderClient,
)


# Clinic floor stages — every patient moves through these in order, except
# `lab` and `pharmacy` which are conditional (~40% and ~50%).
Stage = Literal[
    "entering",
    "reception",
    "waiting",
    "exam",
    "lab",
    "pharmacy",
    "checkout",
    "leaving",
    "done",
    "failed",
]

# Catalog codes — must match what's seeded in each service's seed.py.
# Hard-coded here rather than fetched at runtime: these are tiny fixed sets,
# and reading the catalogs on every flow would mean 3 extra round-trips per
# patient × 10k patients = 30k extra calls.
VISIT_TYPE_CODES = ("NEW_PATIENT", "FOLLOW_UP", "TELEHEALTH", "ANNUAL")
LAB_PANEL_CODES = ("LP-CBC", "LP-LIPID", "LP-A1C", "LP-BMP", "LP-TSH")
MEDICATION_CODES = (
    ("MED-METFORMIN", "1 tablet PO daily"),
    ("MED-ATORVA", "1 tablet PO at bedtime"),
    ("MED-AMOX", "1 capsule PO TID x 7 days"),
    ("MED-LISINOPRIL", "1 tablet PO daily"),
    ("MED-OMEPRAZOLE", "1 capsule PO daily before breakfast"),
)

# Synthetic-but-realistic names for newly-registered patients. Same flavor
# as scripts/seeds/_common.py — hand-curated to avoid Mimesis pulling in
# anything resembling a public figure.
GIVEN_NAMES = (
    "Maya", "Hiroshi", "Aaliyah", "Mateo", "Riley", "Priya", "Jamal",
    "Saoirse", "Wei", "Layla", "Tomás", "Ngozi", "Anders", "Yui", "Diego",
    "Aisha", "Kofi", "Sanne", "Joaquín", "Mei", "Eitan", "Aroha", "Idris",
    "Linnea", "Rashid", "Camila", "Bjorn", "Zara", "Hassan", "Fiona",
)
FAMILY_NAMES = (
    "Okafor", "Tanaka", "Greene", "Vargas", "Kim", "Patel", "Boateng",
    "O'Connor", "Chen", "Hassan", "Costa", "Adeyemi", "Lindqvist", "Sato",
    "Morales", "Mahmood", "Mensah", "de Vries", "Reyes", "Yamamoto",
)


@dataclass(frozen=True, slots=True)
class SimEvent:
    """A single event emitted by a running journey.

    The UI subscribes to a stream of these via SSE and uses each event to
    drive the matching avatar's animation. Times are in milliseconds since
    the run started (not since the epoch) so the UI can sync animations to
    a single monotonic clock.
    """

    journey_id: int
    stage: Stage
    elapsed_ms: int
    patient_name: str
    patient_id: str | None = None
    detail: str | None = None
    service: str | None = None
    op: str | None = None
    status_code: int | None = None
    latency_ms: int | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "journey_id": self.journey_id,
            "stage": self.stage,
            "elapsed_ms": self.elapsed_ms,
            "patient_name": self.patient_name,
            "patient_id": self.patient_id,
            "detail": self.detail,
            "service": self.service,
            "op": self.op,
            "status_code": self.status_code,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@dataclass(slots=True)
class _CallResult:
    ok: bool
    status_code: int | None
    latency_ms: int
    error: str | None = None


async def _timed_call(coro):
    """Run an awaitable and return its result + latency, never raising."""
    start = time.perf_counter()
    try:
        result = await coro
        latency_ms = int((time.perf_counter() - start) * 1000)
        return result, _CallResult(ok=True, status_code=200, latency_ms=latency_ms)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        status = None
        # httpx.HTTPStatusError carries .response — extract status without
        # importing httpx here just for the type check.
        resp = getattr(exc, "response", None)
        if resp is not None and hasattr(resp, "status_code"):
            status = resp.status_code
        return None, _CallResult(
            ok=False,
            status_code=status,
            latency_ms=latency_ms,
            error=f"{type(exc).__name__}: {exc}",
        )


def _random_patient_payload() -> PatientCreatePayload:
    given = random.choice(GIVEN_NAMES)
    family = random.choice(FAMILY_NAMES)
    age_years = random.randint(1, 89)
    birth = (datetime.now(timezone.utc).date()
             - timedelta(days=age_years * 365 + random.randint(0, 364)))
    return PatientCreatePayload(
        given_name=given,
        family_name=family,
        birth_date=birth,
        sex_at_birth=random.choice(["female", "male", "other", "unknown"]),
        preferred_language=random.choice(
            ["en-US", "es-MX", "ja-JP", "zh-CN", "ar-SA", "fr-CA", "pt-BR", "hi-IN"]
        ),
        email=f"{given.lower()}.{family.lower().replace(chr(39), '')}@sim.example.org",
        phone=f"+1415555{random.randint(0, 9999):04d}",
    )


@dataclass(slots=True)
class _SimContext:
    """Per-run shared state: clients, existing patient/provider pools, queue."""

    patient_client: PatientClient
    provider_client: ProviderClient
    appointment_client: AppointmentClient
    lab_client: LabClient
    rx_client: PrescriptionClient
    billing_client: BillingClient

    existing_patient_ids: list[UUID]
    existing_patient_labels: dict[UUID, str]
    provider_ids: list[UUID]

    queue: asyncio.Queue[SimEvent]
    start_monotonic: float
    semaphore: asyncio.Semaphore
    cancel_event: asyncio.Event

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.start_monotonic) * 1000)

    async def emit(self, event: SimEvent) -> None:
        await self.queue.put(event)


async def _emit_call(
    ctx: _SimContext,
    journey_id: int,
    stage: Stage,
    patient_name: str,
    patient_id: str | None,
    service: str,
    op: str,
    call_coro,
):
    """Run a downstream call, time it, and emit a structured event."""
    result, info = await _timed_call(call_coro)
    await ctx.emit(
        SimEvent(
            journey_id=journey_id,
            stage=stage,
            elapsed_ms=ctx.elapsed_ms(),
            patient_name=patient_name,
            patient_id=patient_id,
            service=service,
            op=op,
            status_code=info.status_code,
            latency_ms=info.latency_ms,
            error=info.error,
        )
    )
    return result, info


async def _run_one_journey(
    ctx: _SimContext,
    journey_id: int,
    register_probability: float,
    lab_probability: float,
    rx_probability: float,
) -> None:
    """Drive one patient through the full clinic flow.

    Any failure short-circuits to the `failed` stage with the error attached;
    we don't try to recover because the whole point is to surface real
    service behavior to the UI.
    """
    async with ctx.semaphore:
        if ctx.cancel_event.is_set():
            return

        # Stage 1: patient enters the clinic (UI-only event, no API call).
        await ctx.emit(SimEvent(
            journey_id=journey_id,
            stage="entering",
            elapsed_ms=ctx.elapsed_ms(),
            patient_name="...",
        ))

        # Stage 2: reception — either register a new patient or pick an
        # existing one from the seeded pool.
        register_new = random.random() < register_probability or not ctx.existing_patient_ids

        patient_name: str
        patient_id: UUID

        if register_new:
            payload = _random_patient_payload()
            patient_name = f"{payload.given_name} {payload.family_name}"
            result, info = await _emit_call(
                ctx, journey_id, "reception", patient_name, None,
                "patient", "mutation createPatient",
                ctx.patient_client.create(payload),
            )
            if not info.ok or result is None:
                await ctx.emit(SimEvent(
                    journey_id=journey_id, stage="failed",
                    elapsed_ms=ctx.elapsed_ms(),
                    patient_name=patient_name,
                    detail="Patient registration failed",
                    error=info.error,
                ))
                return
            patient_id = result.id
            # Remember this patient so later journeys in the same run can
            # reuse them (matches the "patients can be the same" requirement).
            ctx.existing_patient_ids.append(patient_id)
            ctx.existing_patient_labels[patient_id] = patient_name
        else:
            patient_id = random.choice(ctx.existing_patient_ids)
            patient_name = ctx.existing_patient_labels.get(
                patient_id, "Returning patient"
            )
            # Existing-patient flows still emit a reception event so the UI
            # can animate the avatar appearing at the front desk. Note: no
            # `service`/`op`/`latency_ms` here — there's no HTTP call to
            # account for, the patient came from the prefetched pool.
            await ctx.emit(SimEvent(
                journey_id=journey_id, stage="reception",
                elapsed_ms=ctx.elapsed_ms(),
                patient_name=patient_name,
                patient_id=str(patient_id),
                detail="Returning patient (from pool)",
            ))

        # Stage 3: book the appointment.
        provider_id = random.choice(ctx.provider_ids)
        visit_type = random.choice(VISIT_TYPE_CODES)
        start = datetime.now(timezone.utc) + timedelta(minutes=random.randint(0, 60))
        end = start + timedelta(minutes=30)

        appt, info = await _emit_call(
            ctx, journey_id, "waiting", patient_name, str(patient_id),
            "appointment", "mutation createAppointment",
            ctx.appointment_client.create(AppointmentCreatePayload(
                patient_id=patient_id,
                provider_id=provider_id,
                visit_type_code=visit_type,
                scheduled_start=start,
                scheduled_end=end,
                reason=f"sim journey #{journey_id}",
            )),
        )
        if not info.ok or appt is None:
            await ctx.emit(SimEvent(
                journey_id=journey_id, stage="failed",
                elapsed_ms=ctx.elapsed_ms(),
                patient_name=patient_name, patient_id=str(patient_id),
                detail="Appointment booking failed",
                error=info.error,
            ))
            return

        # Stage 4: arrived.
        _, info = await _emit_call(
            ctx, journey_id, "waiting", patient_name, str(patient_id),
            "appointment", "mutation updateAppointmentStatus(arrived)",
            ctx.appointment_client.update_status(appt.id, "arrived"),
        )
        if not info.ok:
            await ctx.emit(SimEvent(
                journey_id=journey_id, stage="failed",
                elapsed_ms=ctx.elapsed_ms(),
                patient_name=patient_name, patient_id=str(patient_id),
                detail="Could not mark arrived", error=info.error,
            ))
            return

        # Stage 5: in progress (in exam room).
        _, info = await _emit_call(
            ctx, journey_id, "exam", patient_name, str(patient_id),
            "appointment", "mutation updateAppointmentStatus(in_progress)",
            ctx.appointment_client.update_status(appt.id, "in_progress"),
        )
        if not info.ok:
            await ctx.emit(SimEvent(
                journey_id=journey_id, stage="failed",
                elapsed_ms=ctx.elapsed_ms(),
                patient_name=patient_name, patient_id=str(patient_id),
                detail="Could not start exam", error=info.error,
            ))
            return

        # Stage 6 (optional): order a lab.
        if random.random() < lab_probability:
            panel = random.choice(LAB_PANEL_CODES)
            lab_order, info = await _emit_call(
                ctx, journey_id, "lab", patient_name, str(patient_id),
                "lab", f"mutation createLabOrder({panel})",
                ctx.lab_client.create_order(LabOrderCreatePayload(
                    patient_id=patient_id,
                    ordering_provider_id=provider_id,
                    appointment_id=appt.id,
                    panel_code=panel,
                )),
            )
            if info.ok and lab_order is not None:
                # Mark collected and resulted in quick succession.
                await _emit_call(
                    ctx, journey_id, "lab", patient_name, str(patient_id),
                    "lab", "mutation updateLabOrderStatus(collected)",
                    ctx.lab_client.update_order_status(lab_order.id, "collected"),
                )
                await _emit_call(
                    ctx, journey_id, "lab", patient_name, str(patient_id),
                    "lab", "mutation updateLabOrderStatus(resulted)",
                    ctx.lab_client.update_order_status(lab_order.id, "resulted"),
                )

        # Stage 7 (optional): prescribe a medication.
        if random.random() < rx_probability:
            med_code, dose = random.choice(MEDICATION_CODES)
            await _emit_call(
                ctx, journey_id, "pharmacy", patient_name, str(patient_id),
                "prescription", f"mutation createPrescription({med_code})",
                ctx.rx_client.create(PrescriptionCreatePayload(
                    patient_id=patient_id,
                    prescribing_provider_id=provider_id,
                    medication_code=med_code,
                    dose_text=dose,
                    quantity=30,
                    refills_remaining=random.randint(0, 3),
                )),
            )

        # Stage 8: complete the appointment.
        await _emit_call(
            ctx, journey_id, "checkout", patient_name, str(patient_id),
            "appointment", "mutation updateAppointmentStatus(completed)",
            ctx.appointment_client.update_status(appt.id, "completed"),
        )

        # Stage 9: invoice → sent → paid.
        amount = random.randint(75_00, 450_00)
        invoice, info = await _emit_call(
            ctx, journey_id, "checkout", patient_name, str(patient_id),
            "billing", f"mutation createInvoice(${amount/100:.2f})",
            ctx.billing_client.create_invoice(InvoiceCreatePayload(
                patient_id=patient_id,
                appointment_id=appt.id,
                total_amount_cents=amount,
                status="draft",
            )),
        )
        if info.ok and invoice is not None:
            await _emit_call(
                ctx, journey_id, "checkout", patient_name, str(patient_id),
                "billing", "mutation updateInvoiceStatus(sent)",
                ctx.billing_client.update_invoice_status(invoice.id, "sent"),
            )
            await _emit_call(
                ctx, journey_id, "checkout", patient_name, str(patient_id),
                "billing", "mutation updateInvoiceStatus(paid)",
                ctx.billing_client.update_invoice_status(invoice.id, "paid"),
            )

        # Stage 10: leaving — UI-only event.
        await ctx.emit(SimEvent(
            journey_id=journey_id, stage="leaving",
            elapsed_ms=ctx.elapsed_ms(),
            patient_name=patient_name, patient_id=str(patient_id),
        ))
        await ctx.emit(SimEvent(
            journey_id=journey_id, stage="done",
            elapsed_ms=ctx.elapsed_ms(),
            patient_name=patient_name, patient_id=str(patient_id),
        ))


async def run_simulation(
    user_token: str,
    *,
    count: int,
    branch: str | None = None,
    register_probability: float = 0.3,
    lab_probability: float = 0.4,
    rx_probability: float = 0.5,
    max_concurrency: int = 16,
    journey_spacing_ms: int = 80,
) -> AsyncIterator[SimEvent]:
    """Run `count` patient journeys and yield events as they happen.

    Implementation notes:
      - All six per-service clients are opened ONCE for the duration of the
        whole run (not per-journey) so HTTPX can reuse the connection pool.
      - A bounded `Semaphore` caps simultaneous in-flight journeys.
      - Journey launches are spaced by `journey_spacing_ms` so the UI gets
        a steady stream of "new patient entering" events instead of all 10k
        appearing in the first 100ms.
      - Initial fetch of existing patients + providers is a single round-trip
        each. Newly-registered patients are added back into the pool so
        later journeys may reuse them.
    """
    queue: asyncio.Queue[SimEvent] = asyncio.Queue(maxsize=4096)
    cancel_event = asyncio.Event()
    sem = asyncio.Semaphore(max_concurrency)

    async with (
        PatientClient(user_token, branch) as patient_client,
        ProviderClient(user_token, branch) as provider_client,
        AppointmentClient(user_token, branch) as appointment_client,
        LabClient(user_token, branch) as lab_client,
        PrescriptionClient(user_token, branch) as rx_client,
        BillingClient(user_token, branch) as billing_client,
    ):
        # One-shot prefetch of patient + provider pools. If the patient list
        # is empty we'll just always register-new; if the provider list is
        # empty we can't proceed at all.
        existing_patients, providers = await asyncio.gather(
            patient_client.list(),
            provider_client.list(),
            return_exceptions=True,
        )

        if isinstance(providers, BaseException) or not providers:
            yield SimEvent(
                journey_id=-1,
                stage="failed",
                elapsed_ms=0,
                patient_name="—",
                detail="No providers available; cannot simulate visits",
                error=str(providers) if isinstance(providers, BaseException) else "empty provider list",
            )
            return

        existing_ids: list[UUID] = []
        existing_labels: dict[UUID, str] = {}
        if not isinstance(existing_patients, BaseException):
            for p in existing_patients:
                existing_ids.append(p.id)
                existing_labels[p.id] = f"{p.given_name} {p.family_name}"

        ctx = _SimContext(
            patient_client=patient_client,
            provider_client=provider_client,
            appointment_client=appointment_client,
            lab_client=lab_client,
            rx_client=rx_client,
            billing_client=billing_client,
            existing_patient_ids=existing_ids,
            existing_patient_labels=existing_labels,
            provider_ids=[pv.id for pv in providers],
            queue=queue,
            start_monotonic=time.monotonic(),
            semaphore=sem,
            cancel_event=cancel_event,
        )

        async def _launch_all() -> None:
            tasks: list[asyncio.Task] = []
            for i in range(count):
                if cancel_event.is_set():
                    break
                tasks.append(asyncio.create_task(_run_one_journey(
                    ctx, i,
                    register_probability=register_probability,
                    lab_probability=lab_probability,
                    rx_probability=rx_probability,
                )))
                if journey_spacing_ms > 0 and i < count - 1:
                    await asyncio.sleep(journey_spacing_ms / 1000)
            for t in tasks:
                try:
                    await t
                except Exception:
                    pass
            # Sentinel to unblock the consumer.
            await queue.put(SimEvent(
                journey_id=-1, stage="done", elapsed_ms=ctx.elapsed_ms(),
                patient_name="__END__",
            ))

        producer = asyncio.create_task(_launch_all())
        try:
            while True:
                event = await queue.get()
                if event.patient_name == "__END__":
                    return
                yield event
        finally:
            cancel_event.set()
            producer.cancel()
            try:
                await producer
            except (asyncio.CancelledError, Exception):
                pass
