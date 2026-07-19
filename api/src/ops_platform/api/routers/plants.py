from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_plant_repository,
    get_project_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import AreaStatus, Plant, User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.plant_repository import PlantRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.machines import PhaseUpdateRequest, PlantCreateRequest, PlantResponse
from ops_platform.schemas.projects import AreaStatusResponse

router = APIRouter(tags=["plants"])


def _phase_status_response(phase_status: AreaStatus | None) -> AreaStatusResponse | None:
    if phase_status is None:
        return None
    return AreaStatusResponse(
        id=phase_status.id,
        area_type_id=phase_status.area_type_id,
        name=phase_status.name,
        sort_order=phase_status.sort_order,
    )


def _plant_response(plant: Plant) -> PlantResponse:
    return PlantResponse(
        id=plant.id,
        project_id=plant.project_id,
        name=plant.name,
        location=plant.location,
        created_at=plant.created_at,
        phase_status=_phase_status_response(plant.phase_status),
    )


async def get_plant_or_404(plant_repo: PlantRepository, plant_id: UUID) -> Plant:
    plant = await plant_repo.get(plant_id)
    if plant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found")
    return plant


@router.post(
    "/projects/{project_id}/plants",
    response_model=PlantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_plant(
    project_id: UUID,
    payload: PlantCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    plant_repo: Annotated[PlantRepository, Depends(get_plant_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlantResponse:
    if await project_repo.get(project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    plant = await plant_repo.create(
        project_id=project_id, name=payload.name, location=payload.location
    )
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="plant",
        entity_id=plant.id,
        action="plant.created",
        diff={"name": plant.name},
    )
    await session.commit()
    return _plant_response(plant)


@router.get("/projects/{project_id}/plants", response_model=list[PlantResponse])
async def list_project_plants(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    plant_repo: Annotated[PlantRepository, Depends(get_plant_repository)],
) -> list[PlantResponse]:
    if await project_repo.get(project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    plants = await plant_repo.list_for_project(project_id)
    return [_plant_response(plant) for plant in plants]


@router.get("/plants/{plant_id}", response_model=PlantResponse)
async def get_plant(
    plant_id: UUID,
    plant_repo: Annotated[PlantRepository, Depends(get_plant_repository)],
) -> PlantResponse:
    plant = await get_plant_or_404(plant_repo, plant_id)
    return _plant_response(plant)


@router.patch("/plants/{plant_id}/phase", response_model=PlantResponse)
async def update_plant_phase(
    plant_id: UUID,
    payload: PhaseUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    plant_repo: Annotated[PlantRepository, Depends(get_plant_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlantResponse:
    plant = await get_plant_or_404(plant_repo, plant_id)
    updated = await plant_repo.update_phase(plant_id, payload.status_id)
    await audit.record(
        project_id=plant.project_id,
        actor_id=current_user.id,
        entity_type="plant",
        entity_id=plant_id,
        action="plant.phase_changed",
        diff={
            "from": plant.phase_status.name if plant.phase_status else None,
            "to": updated.phase_status.name if updated.phase_status else None,
        },
    )
    await session.commit()
    return _plant_response(updated)
