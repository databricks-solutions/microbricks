"""Strawberry types mirroring the Pydantic models in routers/patients.py."""
from __future__ import annotations

from datetime import date
from uuid import UUID

import strawberry


@strawberry.type
class PatientType:
    id: UUID
    mrn: str
    given_name: str
    family_name: str
    birth_date: date
    sex_at_birth: str


@strawberry.type
class PatientPage:
    items: list[PatientType]
    total: int
    limit: int
    offset: int


@strawberry.input
class PatientCreateInput:
    given_name: str
    family_name: str
    birth_date: date
    sex_at_birth: str
    mrn: str | None = None
    gender_identity: str | None = None
    preferred_language: str | None = None
    email: str | None = None
    phone: str | None = None
