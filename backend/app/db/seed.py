"""Idempotent seed for facilities, tariffs and slot windows.

Run with:  python -m app.db.seed

Every write is an upsert keyed on the record's natural key using ``$setOnInsert``,
so rerunning the seed never creates duplicates and never overwrites values an
admin has since changed in the database.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.db.indexes import ensure_indexes
from app.db.seed_data import (
    FACILITIES,
    SEED_TARIFF_EFFECTIVE_FROM,
    SEED_TARIFF_VERSION,
    SLOT_WINDOWS_BY_TYPE,
    TARIFFS,
    tariff_display_label,
)


@dataclass
class SeedReport:
    inserted: dict[str, int] = field(default_factory=lambda: {"facilities": 0, "tariffs": 0, "slot_windows": 0})
    existing: dict[str, int] = field(default_factory=lambda: {"facilities": 0, "tariffs": 0, "slot_windows": 0})

    def count(self, collection: str, was_inserted: bool) -> None:
        bucket = self.inserted if was_inserted else self.existing
        bucket[collection] += 1


async def _upsert(db, collection: str, key: dict, doc: dict, report: SeedReport) -> None:
    result = await db[collection].update_one(key, {"$setOnInsert": doc}, upsert=True)
    report.count(collection, result.upserted_id is not None)


async def seed_all(db, now: datetime | None = None) -> SeedReport:
    now = now or datetime.now(UTC)
    report = SeedReport()

    # Facilities
    for facility in FACILITIES:
        doc = {k: v for k, v in facility.items() if k != "code"}
        doc.setdefault("notes", None)
        doc.update({"active": True, "created_at": now, "updated_at": now})
        await _upsert(db, "facilities", {"code": facility["code"]}, doc, report)

    facility_ids = {f["code"]: f["_id"] async for f in db.facilities.find({}, {"code": 1})}

    # Tariffs
    for (code, unit), amounts in TARIFFS.items():
        for category, amount in amounts.items():
            key = {
                "facility_id": facility_ids[code],
                "category": category,
                "unit": unit,
                "version": SEED_TARIFF_VERSION,
            }
            doc = {
                "amount": amount,
                "effective_from": SEED_TARIFF_EFFECTIVE_FROM,
                "display_label": tariff_display_label(amount, unit),
                "effective_to": None,
                "active": True,
                "created_at": now,
                "updated_at": now,
            }
            await _upsert(db, "tariffs", key, doc, report)

    # Slot windows
    for facility in FACILITIES:
        for slot_type in facility["slot_types"]:
            for window in SLOT_WINDOWS_BY_TYPE[slot_type]:
                key = {"facility_id": facility_ids[facility["code"]], "slot_key": window["slot_key"]}
                doc = {k: v for k, v in window.items() if k != "slot_key"}
                doc.update({"slot_type": slot_type, "active": True})
                await _upsert(db, "slot_windows", key, doc, report)

    return report


async def _main() -> None:
    from app.core.config import get_settings
    from app.db.mongo import create_client

    settings = get_settings()
    client = create_client(settings)
    try:
        db = client[settings.mongodb_database]
        await ensure_indexes(db)
        report = await seed_all(db)
    finally:
        client.close()

    print(f"Seeded database '{settings.mongodb_database}'.")
    for name in ("facilities", "tariffs", "slot_windows"):
        print(f"  {name:<13} inserted={report.inserted[name]:<3} already present={report.existing[name]}")


if __name__ == "__main__":
    asyncio.run(_main())
