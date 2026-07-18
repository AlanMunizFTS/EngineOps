from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from ops_platform.api.deps import get_area_repository
from ops_platform.domain.ports.area_repository import AreaRepository
from ops_platform.schemas.projects import AreaStatusResponse, AreaTypeResponse

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/area-types", response_model=list[AreaTypeResponse])
async def list_area_types(
    area_repo: Annotated[AreaRepository, Depends(get_area_repository)],
) -> list[AreaTypeResponse]:
    area_types = await area_repo.list_area_types()
    return [
        AreaTypeResponse(id=area_type.id, name=area_type.name, description=area_type.description)
        for area_type in area_types
    ]


@router.get("/area-types/{area_type_id}/statuses", response_model=list[AreaStatusResponse])
async def list_area_statuses(
    area_type_id: UUID,
    area_repo: Annotated[AreaRepository, Depends(get_area_repository)],
) -> list[AreaStatusResponse]:
    statuses = await area_repo.list_statuses_for_type(area_type_id)
    return [
        AreaStatusResponse(
            id=status.id,
            area_type_id=status.area_type_id,
            name=status.name,
            sort_order=status.sort_order,
        )
        for status in statuses
    ]
