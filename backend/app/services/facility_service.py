"""Facility catalogue assembly: facilities + currently effective tariffs + slot options."""

from collections import defaultdict
from datetime import UTC, datetime

from app.core.errors import AppError
from app.repositories.facilities import FacilityRepository
from app.schemas.facility import FacilityOut, SlotOptionOut, TariffOut

CATEGORY_ORDER = {"PRIVATE": 0, "GOVT": 1, "IIT": 2}
UNIT_ORDER = {"FULL_DAY": 0, "HALF_DAY": 1, "PER_DAY": 2, "THREE_HOUR": 3}


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _is_effective(tariff: dict, at: datetime) -> bool:
    start = _as_utc(tariff.get("effective_from"))
    end = _as_utc(tariff.get("effective_to"))
    if start is None or start > at:
        return False
    return end is None or end > at


def select_effective_tariffs(tariffs: list[dict], at: datetime) -> list[dict]:
    """Keep the latest effective tariff per (facility, category, unit)."""
    latest: dict[tuple, dict] = {}
    for tariff in tariffs:
        if not _is_effective(tariff, at):
            continue
        key = (tariff["facility_id"], tariff["category"], tariff["unit"])
        current = latest.get(key)
        if current is None or _as_utc(tariff["effective_from"]) > _as_utc(current["effective_from"]):
            latest[key] = tariff
    return list(latest.values())


class FacilityService:
    def __init__(self, repo: FacilityRepository) -> None:
        self.repo = repo

    async def list_catalogue(self, active: bool | None = True, at: datetime | None = None) -> list[FacilityOut]:
        facilities = await self.repo.list_facilities(active=active)
        return await self._assemble(facilities, at or datetime.now(UTC))

    async def get_by_code(self, code: str, at: datetime | None = None) -> FacilityOut:
        facility = await self.repo.get_by_code(code)
        if facility is None:
            raise AppError("FACILITY_NOT_FOUND", f"No facility with code '{code}'.", status_code=404)
        return (await self._assemble([facility], at or datetime.now(UTC)))[0]

    async def _assemble(self, facilities: list[dict], at: datetime) -> list[FacilityOut]:
        ids = [f["_id"] for f in facilities]
        if not ids:
            return []

        tariffs_by_facility: dict = defaultdict(list)
        for tariff in select_effective_tariffs(await self.repo.active_tariffs_for(ids), at):
            tariffs_by_facility[tariff["facility_id"]].append(tariff)

        slots_by_facility: dict = defaultdict(list)
        for window in await self.repo.active_slot_windows_for(ids):
            slots_by_facility[window["facility_id"]].append(window)

        result = []
        for facility in facilities:
            slot_types = facility.get("slot_types", [])
            tariffs = sorted(
                tariffs_by_facility[facility["_id"]],
                key=lambda t: (UNIT_ORDER.get(t["unit"], 99), CATEGORY_ORDER.get(t["category"], 99)),
            )
            slots = sorted(
                (w for w in slots_by_facility[facility["_id"]] if w.get("slot_type") in slot_types),
                key=lambda w: (UNIT_ORDER.get(w["slot_type"], 99), w.get("start") or "", w["slot_key"]),
            )
            result.append(
                FacilityOut(
                    id=str(facility["_id"]),
                    code=facility["code"],
                    name=facility["name"],
                    group=facility["group"],
                    section=facility["section"],
                    capacity=facility.get("capacity"),
                    slot_types=slot_types,
                    slot_options=[
                        SlotOptionOut(
                            slot_key=w["slot_key"],
                            label=w["label"],
                            slot_type=w["slot_type"],
                            start=w.get("start"),
                            end=w.get("end"),
                        )
                        for w in slots
                    ],
                    tariffs=[
                        TariffOut(
                            category=t["category"],
                            unit=t["unit"],
                            # Normalise null ("No charges") to zero, LLD §5.2.
                            amount=int(t.get("amount") or 0),
                            display_label=t.get("display_label") or "",
                        )
                        for t in tariffs
                    ],
                    notes=facility.get("notes"),
                    active=bool(facility.get("active", False)),
                )
            )
        return result
