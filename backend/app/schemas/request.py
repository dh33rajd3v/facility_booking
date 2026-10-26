"""Request/response models for booking requests (drafts in Week 2).

Input models use ``extra="forbid"``: a browser that sends fields such as user_id,
rate_category, status or amounts gets a 422 instead of having them silently ignored.
Those values are always decided by the server.
"""

import re
from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.schemas.facility import Category, Section, Unit

PHONE_CHARS = re.compile(r"^\+?[0-9 ()\-]{6,20}$")


def _phone(value: str) -> str:
    # Accept common Indian and international formats; just make sure it looks like a number.
    if not PHONE_CHARS.match(value) or sum(ch.isdigit() for ch in value) < 6:
        raise ValueError("Enter a valid phone number (digits, spaces, +, - and brackets).")
    return value


Phone = Annotated[str, Field(min_length=6, max_length=20), AfterValidator(_phone)]
Text500 = Annotated[str, Field(min_length=1, max_length=500)]
Name = Annotated[str, Field(min_length=1, max_length=200)]
Purpose = Annotated[str, Field(min_length=1, max_length=2000)]
Participants = Annotated[int, Field(gt=0, le=100_000)]

_INPUT = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EventDetailsIn(BaseModel):
    model_config = _INPUT

    organisation_name_address: Text500
    applicant_name: Name
    office_contact: Phone
    mobile: Phone
    purpose: Purpose
    participants: Participants


class EventDetailsPatch(BaseModel):
    model_config = _INPUT

    organisation_name_address: Text500 | None = None
    applicant_name: Name | None = None
    office_contact: Phone | None = None
    mobile: Phone | None = None
    purpose: Purpose | None = None
    participants: Participants | None = None

    @model_validator(mode="after")
    def _not_empty(self):
        if not self.model_dump(exclude_none=True):
            raise ValueError("Provide at least one field to update.")
        return self


class LineIn(BaseModel):
    model_config = _INPUT

    facility_id: int = Field(gt=0)
    booking_date: date
    slot_key: str = Field(min_length=1, max_length=32)


class LinePatch(BaseModel):
    model_config = _INPUT

    facility_id: int | None = Field(default=None, gt=0)
    booking_date: date | None = None
    slot_key: str | None = Field(default=None, min_length=1, max_length=32)

    @model_validator(mode="after")
    def _not_empty(self):
        if not self.model_dump(exclude_none=True):
            raise ValueError("Provide at least one field to update.")
        return self


class EventDetailsOut(BaseModel):
    organisation_name_address: str
    applicant_name: str
    contact_email: str
    office_contact: str
    mobile: str
    purpose: str
    participants: int


class RatePreviewOut(BaseModel):
    category: Category
    unit: Unit
    amount: int
    display_label: str


class RequestLineOut(BaseModel):
    id: int
    facility_id: int
    facility_code: str
    facility_name: str
    section: Section
    booking_date: date
    slot_key: str
    slot_label: str
    slot_type: Unit
    start: str | None
    end: str | None
    # Rate for the signed-in user's category today. None if no tariff applies on that date.
    rate: RatePreviewOut | None


class ChargesPreviewOut(BaseModel):
    category: Category | None
    booking_subtotal: int
    lines_without_rate: int
    # Always False in Week 2: final costs (GST, cleaning, deposit, electricity) come later.
    is_final: bool = False
    note: str


class RequestOut(BaseModel):
    id: int
    ref_no: str | None
    status: str
    editable: bool
    event: EventDetailsOut
    lines: list[RequestLineOut]
    charges_preview: ChargesPreviewOut
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None


class RequestSummaryOut(BaseModel):
    id: int
    ref_no: str | None
    status: str
    purpose: str
    facility_summary: str
    line_count: int
    first_date: date | None
    created_at: datetime
    updated_at: datetime


class RequestListOut(BaseModel):
    items: list[RequestSummaryOut]
    total: int
