"""Database access for facilities, tariffs and slot windows."""

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Facility, SlotWindow, Tariff


class FacilityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_facilities(self, active: bool | None = True) -> list[Facility]:
        stmt = select(Facility).order_by(Facility.sort_order, Facility.code)
        if active is not None:
            stmt = stmt.where(Facility.active.is_(active))
        return list(self.session.scalars(stmt))

    def get_by_code(self, code: str) -> Facility | None:
        return self.session.scalars(select(Facility).where(Facility.code == code)).first()

    def effective_tariffs_for(self, facility_ids: list[int], at: datetime) -> list[Tariff]:
        """Active tariffs whose effective window contains ``at``."""
        stmt = select(Tariff).where(
            Tariff.facility_id.in_(facility_ids),
            Tariff.active.is_(True),
            Tariff.effective_from <= at,
            or_(Tariff.effective_to.is_(None), Tariff.effective_to > at),
        )
        return list(self.session.scalars(stmt))

    def active_slot_windows_for(self, facility_ids: list[int]) -> list[SlotWindow]:
        stmt = select(SlotWindow).where(SlotWindow.facility_id.in_(facility_ids), SlotWindow.active.is_(True))
        return list(self.session.scalars(stmt))
