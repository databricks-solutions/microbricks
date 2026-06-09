"""Simulator HTTP routes.

Two endpoints:
  - GET /api/sim/stream  — Server-Sent Events. Driver endpoint; the React UI
    opens an EventSource and animates avatars from the stream of `SimEvent`s.
  - GET /api/sim/healthz — liveness probe that doesn't touch downstream
    services. Same shape as hc-portal's BFF healthz.
"""
from __future__ import annotations

import json
import os
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from ...auth import user_token
from ..simulator import run_simulation

router = APIRouter(prefix="/sim", tags=["simulator"])


def _default_max_concurrency() -> int:
    try:
        return max(1, int(os.environ.get("SIM_MAX_CONCURRENCY", "16")))
    except ValueError:
        return 16


@router.get("/stream", operation_id="streamSimulation")
async def stream_simulation(
    token: Annotated[str, Depends(user_token)],
    count: int = Query(1, ge=1, le=10_000),
    register_probability: float = Query(0.3, ge=0.0, le=1.0),
    lab_probability: float = Query(0.4, ge=0.0, le=1.0),
    rx_probability: float = Query(0.5, ge=0.0, le=1.0),
    max_concurrency: int | None = Query(default=None, ge=1, le=128),
    journey_spacing_ms: int = Query(80, ge=0, le=5000),
) -> StreamingResponse:
    """Stream simulation events as SSE.

    Each event line is `data: {json}\\n\\n`. The browser's EventSource parses
    these one at a time. Cancelling the EventSource from the client side will
    close the connection here, which cancels the producer task in
    `run_simulation` and stops all in-flight journeys.
    """
    if count < 1:
        raise HTTPException(422, "count must be >= 1")

    concurrency = max_concurrency if max_concurrency is not None else _default_max_concurrency()

    async def event_stream() -> AsyncIterator[bytes]:
        # Opening comment so flushing buffers (proxies, browser, etc.) doesn't
        # delay the first event. `: <text>\n\n` is a valid SSE comment.
        yield b": stream opened\n\n"
        try:
            async for evt in run_simulation(
                token,
                count=count,
                register_probability=register_probability,
                lab_probability=lab_probability,
                rx_probability=rx_probability,
                max_concurrency=concurrency,
                journey_spacing_ms=journey_spacing_ms,
            ):
                payload = json.dumps(evt.to_dict(), default=str)
                yield f"data: {payload}\n\n".encode()
            yield b"event: complete\ndata: {}\n\n"
        except Exception as exc:
            err = json.dumps({"error": f"{type(exc).__name__}: {exc}"})
            yield f"event: error\ndata: {err}\n\n".encode()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/healthz", operation_id="simHealthz")
async def healthz() -> dict[str, bool]:
    """Simulator liveness probe; does not touch downstream services."""
    return {"ok": True}
