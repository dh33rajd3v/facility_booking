"""Response models for the facility catalogue."""

from typing import Literal

from pydantic import BaseModel

Category = Literal["IIT", "GOVT", "PRIVATE"]
Unit = Literal["FULL_DAY", "HALF_DAY", "PER_DAY", "THREE_HOUR"]
Group = Literal["LHC", "AUDITORIUM", "SPORTS"]
Section = Literal["ACADEMIC", "SPORTS"]


class TariffOut(BaseModel):
    category: Category
    unit: Unit
    amount: int
    display_label: str


class SlotOptionOut(BaseModel):
    slot_key: str
    label: str
    slot_type: Unit
    start: str | None = None
    end: str | None = None


class FacilityOut(BaseModel):
    id: str
    code: str
    name: str
    group: Group
    section: Section
    capacity: int | None = None
    slot_types: list[Unit]
    slot_options: list[SlotOptionOut]
    tariffs: list[TariffOut]
    notes: str | None = None
    active: bool


class FacilityListOut(BaseModel):
    items: list[FacilityOut]
    total: int


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unreachable"]
    environment: str
