"""Draft booking requests: create, edit, add/edit/remove facility lines, and tariff preview.

Business rules live here (not in the routes or the browser):
- only the owner can see or change a request (others get 404);
- only DRAFT requests can be edited;
- each line's facility, slot and date are checked, and a tariff must exist for the
  user's rate category on that date;
- lines in the same request can't overlap (same facility, same date, overlapping times).
"""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import start_of_day_ist, today_ist
from app.db.models import BookingRequest, RequestLine, SlotWindow, User
from app.repositories.facilities import FacilityRepository
from app.repositories.requests import RequestRepository
from app.schemas.request import (
    ChargesPreviewOut,
    EventDetailsIn,
    EventDetailsOut,
    EventDetailsPatch,
    LineIn,
    LinePatch,
    RatePreviewOut,
    RequestLineOut,
    RequestOut,
    RequestSummaryOut,
)
from app.services.slots import slots_overlap

EDITABLE_STATUSES = {"DRAFT"}
MAX_LINES_PER_REQUEST = 20
MAX_DAYS_AHEAD = 365  # Assumption: bookings up to a year ahead; confirm with Facilities.
PREVIEW_NOTE = (
    "Indicative booking charges only. GST, cleaning, security deposit and electricity are "
    "added when Facilities costs the request."
)


def _hhmm(value) -> str | None:
    return value.strftime("%H:%M") if value else None


class RequestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.requests = RequestRepository(db)
        self.facilities = FacilityRepository(db)

    # ----- queries -----

    def list_for_user(self, user: User) -> list[RequestSummaryOut]:
        return [self._summary(r) for r in self.requests.list_for_user(user.id)]

    def get(self, user: User, request_id: int) -> BookingRequest:
        request = self.requests.get_for_user(request_id, user.id)
        if request is None:
            raise AppError("REQUEST_NOT_FOUND", "Request not found.", 404)
        return request

    def detail(self, user: User, request_id: int) -> RequestOut:
        return self._detail(user, self.get(user, request_id))

    # ----- event details -----

    def create(self, user: User, data: EventDetailsIn) -> RequestOut:
        if user.rate_category is None:
            raise AppError(
                "PROFILE_INCOMPLETE", "Choose your organisation category before creating a request.", 409
            )
        request = BookingRequest(user_id=user.id, status="DRAFT", contact_email=user.email, **data.model_dump())
        self.requests.add(request)
        self.db.commit()
        return self._reload(user, request.id)

    def update_event(self, user: User, request_id: int, data: EventDetailsPatch) -> RequestOut:
        request = self._editable(user, request_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(request, field, value)
        self.db.commit()
        return self._reload(user, request.id)

    def delete(self, user: User, request_id: int) -> None:
        request = self._editable(user, request_id)
        self.requests.delete(request)
        self.db.commit()

    # ----- lines -----

    def add_line(self, user: User, request_id: int, data: LineIn) -> RequestOut:
        request = self._editable(user, request_id)
        if len(request.lines) >= MAX_LINES_PER_REQUEST:
            raise AppError("TOO_MANY_LINES", f"A request can have at most {MAX_LINES_PER_REQUEST} facilities.", 422)
        self._validate_line(user, request, data.facility_id, data.booking_date, data.slot_key, exclude_line_id=None)
        request.lines.append(
            RequestLine(facility_id=data.facility_id, booking_date=data.booking_date, slot_key=data.slot_key)
        )
        self.db.commit()
        return self._reload(user, request.id)

    def update_line(self, user: User, request_id: int, line_id: int, data: LinePatch) -> RequestOut:
        request = self._editable(user, request_id)
        line = self._line(request, line_id)
        facility_id = data.facility_id or line.facility_id
        booking_date = data.booking_date or line.booking_date
        slot_key = data.slot_key or line.slot_key
        self._validate_line(user, request, facility_id, booking_date, slot_key, exclude_line_id=line.id)
        line.facility_id, line.booking_date, line.slot_key = facility_id, booking_date, slot_key
        self.db.commit()
        return self._reload(user, request.id)

    def delete_line(self, user: User, request_id: int, line_id: int) -> RequestOut:
        request = self._editable(user, request_id)
        request.lines.remove(self._line(request, line_id))
        self.db.commit()
        return self._reload(user, request.id)

    # ----- helpers -----

    def _editable(self, user: User, request_id: int) -> BookingRequest:
        request = self.get(user, request_id)
        if request.status not in EDITABLE_STATUSES:
            raise AppError(
                "REQUEST_NOT_EDITABLE", f"This request is {request.status} and can no longer be edited.", 409
            )
        return request

    def _line(self, request: BookingRequest, line_id: int) -> RequestLine:
        line = self.requests.get_line(request, line_id)
        if line is None:
            raise AppError("LINE_NOT_FOUND", "Facility line not found in this request.", 404)
        return line

    def _reload(self, user: User, request_id: int) -> RequestOut:
        self.db.expire_all()  # pick up changed facility/slot relationships after edits
        return self.detail(user, request_id)

    def _validate_line(self, user, request, facility_id, booking_date, slot_key, exclude_line_id) -> SlotWindow:
        facility = self.facilities.get(facility_id)
        if facility is None or not facility.active:
            raise AppError("INVALID_FACILITY", "That facility is not available for booking.", 422)

        slot = self.facilities.get_slot(facility_id, slot_key)
        if slot is None or not slot.active:
            raise AppError(
                "INVALID_SLOT", f"'{slot_key}' is not a bookable slot for {facility.name}.", 422,
                {"field": "slot_key"},
            )

        today = today_ist()
        if booking_date < today:
            raise AppError("DATE_IN_PAST", "The booking date can't be in the past.", 422, {"field": "booking_date"})
        if booking_date > today + timedelta(days=MAX_DAYS_AHEAD):
            raise AppError(
                "DATE_TOO_FAR", f"Bookings can be made up to {MAX_DAYS_AHEAD} days ahead.", 422,
                {"field": "booking_date"},
            )

        tariff = self.facilities.effective_tariff(
            facility_id, user.rate_category, slot.slot_type, start_of_day_ist(booking_date)
        )
        if tariff is None:
            raise AppError(
                "TARIFF_NOT_AVAILABLE", f"No tariff is set for {facility.name} on {booking_date:%d %b %Y}.", 422
            )

        for other in request.lines:
            if other.id == exclude_line_id or other.facility_id != facility_id or other.booking_date != booking_date:
                continue
            if slots_overlap(slot, other.slot):
                raise AppError(
                    "LINE_CONFLICT",
                    f"{facility.name} on {booking_date:%d %b %Y} overlaps another line in this request "
                    f"({other.slot.label}).",
                    409,
                    {"conflicting_line_id": other.id},
                )
        return slot

    def _detail(self, user: User, request: BookingRequest) -> RequestOut:
        lines: list[RequestLineOut] = []
        subtotal = 0
        missing = 0
        for line in request.lines:
            rate = None
            if user.rate_category is not None:
                tariff = self.facilities.effective_tariff(
                    line.facility_id, user.rate_category, line.slot.slot_type, start_of_day_ist(line.booking_date)
                )
                if tariff is not None:
                    rate = RatePreviewOut(
                        category=tariff.category, unit=tariff.unit, amount=tariff.amount,
                        display_label=tariff.display_label,
                    )
                    subtotal += tariff.amount
            if rate is None:
                missing += 1
            lines.append(
                RequestLineOut(
                    id=line.id,
                    facility_id=line.facility_id,
                    facility_code=line.facility.code,
                    facility_name=line.facility.name,
                    section=line.facility.section,
                    booking_date=line.booking_date,
                    slot_key=line.slot_key,
                    slot_label=line.slot.label,
                    slot_type=line.slot.slot_type,
                    start=_hhmm(line.slot.start_time),
                    end=_hhmm(line.slot.end_time),
                    rate=rate,
                )
            )
        return RequestOut(
            id=request.id,
            ref_no=request.ref_no,
            status=request.status,
            editable=request.status in EDITABLE_STATUSES,
            event=EventDetailsOut(
                organisation_name_address=request.organisation_name_address,
                applicant_name=request.applicant_name,
                contact_email=request.contact_email,
                office_contact=request.office_contact,
                mobile=request.mobile,
                purpose=request.purpose,
                participants=request.participants,
            ),
            lines=lines,
            charges_preview=ChargesPreviewOut(
                category=user.rate_category, booking_subtotal=subtotal, lines_without_rate=missing, note=PREVIEW_NOTE
            ),
            created_at=request.created_at,
            updated_at=request.updated_at,
            submitted_at=request.submitted_at,
        )

    @staticmethod
    def _summary(request: BookingRequest) -> RequestSummaryOut:
        names: list[str] = []
        for line in request.lines:
            if line.facility.name not in names:
                names.append(line.facility.name)
        summary = ", ".join(names[:2]) + (f" +{len(names) - 2} more" if len(names) > 2 else "")
        return RequestSummaryOut(
            id=request.id,
            ref_no=request.ref_no,
            status=request.status,
            purpose=request.purpose,
            facility_summary=summary or "No facilities added yet",
            line_count=len(request.lines),
            first_date=min((line.booking_date for line in request.lines), default=None),
            created_at=request.created_at,
            updated_at=request.updated_at,
        )
