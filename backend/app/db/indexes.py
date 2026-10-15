"""Index definitions for the Week 1 master-data collections (LLD §10)."""

from pymongo import ASCENDING, DESCENDING, IndexModel

FACILITY_INDEXES = [
    IndexModel([("code", ASCENDING)], unique=True, name="uniq_code"),
    IndexModel([("active", ASCENDING), ("group", ASCENDING)], name="active_group"),
]

TARIFF_INDEXES = [
    IndexModel(
        [
            ("facility_id", ASCENDING),
            ("category", ASCENDING),
            ("unit", ASCENDING),
            ("active", ASCENDING),
            ("effective_from", DESCENDING),
        ],
        name="tariff_lookup",
    ),
    # Makes the seed's natural key unique so concurrent/rerun seeds can never duplicate a tariff.
    IndexModel(
        [("facility_id", ASCENDING), ("category", ASCENDING), ("unit", ASCENDING), ("version", ASCENDING)],
        unique=True,
        name="uniq_tariff_version",
    ),
]

SLOT_WINDOW_INDEXES = [
    IndexModel([("facility_id", ASCENDING), ("slot_key", ASCENDING)], unique=True, name="uniq_facility_slot"),
]


async def ensure_indexes(db) -> None:
    await db.facilities.create_indexes(FACILITY_INDEXES)
    await db.tariffs.create_indexes(TARIFF_INDEXES)
    await db.slot_windows.create_indexes(SLOT_WINDOW_INDEXES)
