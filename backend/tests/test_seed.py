from app.db.seed import seed_all
from app.db.seed_data import FACILITIES, TARIFFS

EXPECTED_TARIFFS = sum(len(amounts) for amounts in TARIFFS.values())  # 11 facility/unit rows x 3 categories


async def test_first_seed_inserts_everything(db):
    report = await seed_all(db)
    assert report.inserted["facilities"] == len(FACILITIES)
    assert report.inserted["tariffs"] == EXPECTED_TARIFFS == 33
    assert report.existing == {"facilities": 0, "tariffs": 0, "slot_windows": 0}
    assert await db.facilities.count_documents({}) == 10
    assert await db.tariffs.count_documents({}) == 33


async def test_seed_is_idempotent(db):
    await seed_all(db)
    counts_before = {name: await db[name].count_documents({}) for name in ("facilities", "tariffs", "slot_windows")}

    report = await seed_all(db)

    counts_after = {name: await db[name].count_documents({}) for name in ("facilities", "tariffs", "slot_windows")}
    assert counts_after == counts_before
    assert report.inserted == {"facilities": 0, "tariffs": 0, "slot_windows": 0}
    assert report.existing["facilities"] == len(FACILITIES)


async def test_rerunning_seed_does_not_overwrite_admin_changes(db):
    await seed_all(db)
    m5 = await db.facilities.find_one({"code": "M5"})
    await db.tariffs.update_one(
        {"facility_id": m5["_id"], "category": "PRIVATE", "unit": "FULL_DAY"}, {"$set": {"amount": 16000}}
    )

    await seed_all(db)

    tariff = await db.tariffs.find_one({"facility_id": m5["_id"], "category": "PRIVATE", "unit": "FULL_DAY"})
    assert tariff["amount"] == 16000


async def test_no_charge_tariffs_are_stored_as_zero_not_null(db):
    await seed_all(db)
    assert await db.tariffs.count_documents({"amount": None}) == 0
    assert await db.tariffs.count_documents({"amount": 0}) == 3  # IIT rate for cricket, football, hockey
