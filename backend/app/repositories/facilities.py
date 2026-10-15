"""Database access for facilities, tariffs and slot windows."""

from bson import ObjectId


class FacilityRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def list_facilities(self, active: bool | None = True) -> list[dict]:
        query = {} if active is None else {"active": active}
        cursor = self.db.facilities.find(query).sort([("sort_order", 1), ("code", 1)])
        return await cursor.to_list(length=None)

    async def get_by_code(self, code: str) -> dict | None:
        return await self.db.facilities.find_one({"code": code})

    async def active_tariffs_for(self, facility_ids: list[ObjectId]) -> list[dict]:
        cursor = self.db.tariffs.find({"facility_id": {"$in": facility_ids}, "active": True})
        return await cursor.to_list(length=None)

    async def active_slot_windows_for(self, facility_ids: list[ObjectId]) -> list[dict]:
        cursor = self.db.slot_windows.find({"facility_id": {"$in": facility_ids}, "active": True})
        return await cursor.to_list(length=None)
