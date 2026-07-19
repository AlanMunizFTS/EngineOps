from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_implementation_repository,
    get_machine_repository,
    get_plant_repository,
)
from ops_platform.api.routers.plants import get_plant_or_404
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import Implementation, Machine, User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.implementation_repository import ImplementationRepository
from ops_platform.domain.ports.machine_repository import MachineRepository
from ops_platform.domain.ports.plant_repository import PlantRepository
from ops_platform.schemas.machines import (
    ImplementationCreateRequest,
    ImplementationResponse,
    MachineCreateRequest,
    MachineResponse,
)

router = APIRouter(tags=["machines"])


def _machine_response(machine: Machine) -> MachineResponse:
    return MachineResponse(
        id=machine.id,
        plant_id=machine.plant_id,
        name=machine.name,
        machine_type=machine.machine_type,
        location=machine.location,
        created_at=machine.created_at,
    )


def _implementation_response(implementation: Implementation) -> ImplementationResponse:
    return ImplementationResponse(
        id=implementation.id,
        machine_id=implementation.machine_id,
        label=implementation.label,
        status=implementation.status,
        superseded_by=implementation.superseded_by,
        created_at=implementation.created_at,
    )


async def _get_machine_or_404(machine_repo: MachineRepository, machine_id: UUID) -> Machine:
    machine = await machine_repo.get(machine_id)
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    return machine


@router.post(
    "/plants/{plant_id}/machines",
    response_model=MachineResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_machine(
    plant_id: UUID,
    payload: MachineCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    plant_repo: Annotated[PlantRepository, Depends(get_plant_repository)],
    machine_repo: Annotated[MachineRepository, Depends(get_machine_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MachineResponse:
    plant = await get_plant_or_404(plant_repo, plant_id)

    machine = await machine_repo.create(
        plant_id=plant_id,
        name=payload.name,
        machine_type=payload.machine_type,
        location=payload.location,
    )
    await audit.record(
        project_id=plant.project_id,
        actor_id=current_user.id,
        entity_type="machine",
        entity_id=machine.id,
        action="machine.created",
        diff={"name": machine.name},
    )
    await session.commit()
    return _machine_response(machine)


@router.get("/plants/{plant_id}/machines", response_model=list[MachineResponse])
async def list_plant_machines(
    plant_id: UUID,
    plant_repo: Annotated[PlantRepository, Depends(get_plant_repository)],
    machine_repo: Annotated[MachineRepository, Depends(get_machine_repository)],
) -> list[MachineResponse]:
    await get_plant_or_404(plant_repo, plant_id)
    machines = await machine_repo.list_for_plant(plant_id)
    return [_machine_response(machine) for machine in machines]


@router.get("/machines/{machine_id}", response_model=MachineResponse)
async def get_machine(
    machine_id: UUID,
    machine_repo: Annotated[MachineRepository, Depends(get_machine_repository)],
) -> MachineResponse:
    machine = await _get_machine_or_404(machine_repo, machine_id)
    return _machine_response(machine)


@router.post(
    "/machines/{machine_id}/implementations",
    response_model=ImplementationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_implementation(
    machine_id: UUID,
    payload: ImplementationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    machine_repo: Annotated[MachineRepository, Depends(get_machine_repository)],
    plant_repo: Annotated[PlantRepository, Depends(get_plant_repository)],
    implementation_repo: Annotated[
        ImplementationRepository, Depends(get_implementation_repository)
    ],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ImplementationResponse:
    machine = await _get_machine_or_404(machine_repo, machine_id)
    plant = await get_plant_or_404(plant_repo, machine.plant_id)

    implementation = await implementation_repo.create(
        machine_id=machine_id, label=payload.label, status=payload.status
    )
    await audit.record(
        project_id=plant.project_id,
        actor_id=current_user.id,
        entity_type="implementation",
        entity_id=implementation.id,
        action="implementation.created",
        diff={"label": implementation.label, "status": implementation.status.value},
    )
    await session.commit()
    return _implementation_response(implementation)


@router.get("/machines/{machine_id}/implementations", response_model=list[ImplementationResponse])
async def list_machine_implementations(
    machine_id: UUID,
    machine_repo: Annotated[MachineRepository, Depends(get_machine_repository)],
    implementation_repo: Annotated[
        ImplementationRepository, Depends(get_implementation_repository)
    ],
) -> list[ImplementationResponse]:
    await _get_machine_or_404(machine_repo, machine_id)
    implementations = await implementation_repo.list_for_machine(machine_id)
    return [_implementation_response(implementation) for implementation in implementations]


@router.post(
    "/implementations/{implementation_id}/supersede", response_model=ImplementationResponse
)
async def supersede_implementation(
    implementation_id: UUID,
    superseded_by: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    machine_repo: Annotated[MachineRepository, Depends(get_machine_repository)],
    plant_repo: Annotated[PlantRepository, Depends(get_plant_repository)],
    implementation_repo: Annotated[
        ImplementationRepository, Depends(get_implementation_repository)
    ],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ImplementationResponse:
    implementation = await implementation_repo.get(implementation_id)
    if implementation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Implementation not found"
        )
    machine = await _get_machine_or_404(machine_repo, implementation.machine_id)
    plant = await get_plant_or_404(plant_repo, machine.plant_id)

    updated = await implementation_repo.supersede(implementation_id, superseded_by)
    await audit.record(
        project_id=plant.project_id,
        actor_id=current_user.id,
        entity_type="implementation",
        entity_id=implementation_id,
        action="implementation.superseded",
        diff={"superseded_by": str(superseded_by)},
    )
    await session.commit()
    return _implementation_response(updated)
