"""FastAPI entrypoint. Wires shutdown of the per-user pools."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import close_all_pools
from .routers import lab_orders


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_all_pools()


app = FastAPI(
    title="lab-svc",
    version="1.0.0",
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

app.include_router(lab_orders.router, prefix="/api/v1")


@app.get("/api/v1/healthz")
async def healthz():
    return {"ok": True}
