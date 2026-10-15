from fastapi import APIRouter, Depends, Query

from app.db.mongo import get_db
from app.repositories.facilities import FacilityRepository
from app.schemas.facility import FacilityListOut, FacilityOut
from app.services.facility_service import FacilityService

router = APIRouter(prefix="/facilities", tags=["facilities"])


def get_facility_service(db=Depends(get_db)) -> FacilityService:
    return FacilityService(FacilityRepository(db))


@router.get("", response_model=FacilityListOut)
async def list_facilities(
    active: bool = Query(True, description="Return active (true) or inactive (false) facilities."),
    service: FacilityService = Depends(get_facility_service),
) -> FacilityListOut:
    items = await service.list_catalogue(active=active)
    return FacilityListOut(items=items, total=len(items))


@router.get("/{code}", response_model=FacilityOut)
async def get_facility(code: str, service: FacilityService = Depends(get_facility_service)) -> FacilityOut:
    return await service.get_by_code(code)
