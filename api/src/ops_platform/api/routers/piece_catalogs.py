"""CRUD for the Material module's four project-scoped catalogs (part
numbers, piece conditions, piece locations, measurement types) - split out
from routers/pieces.py to keep that module focused on pieces themselves and
under the ~400-line limit (CLAUDE.md §3)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_piece_repository,
    get_project_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.piece_repository import PieceRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.pieces import (
    MeasurementTypeCreateRequest,
    MeasurementTypeResponse,
    MeasurementTypeUpdateRequest,
    PartNumberCreateRequest,
    PartNumberResponse,
    PieceConditionCreateRequest,
    PieceConditionResponse,
    PieceLocationCreateRequest,
    PieceLocationResponse,
)
from ops_platform.domain.entities import MeasurementType

router = APIRouter(tags=["piece-catalogs"])


async def _get_project_or_404(project_repo: ProjectRepository, project_id: UUID) -> None:
    if await project_repo.get(project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


async def _get_measurement_type_or_404(
    piece_repo: PieceRepository, measurement_type_id: UUID
) -> MeasurementType:
    measurement_type = await piece_repo.get_measurement_type(measurement_type_id)
    if measurement_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Measurement type not found"
        )
    return measurement_type


def _measurement_type_response(measurement_type: MeasurementType) -> MeasurementTypeResponse:
    return MeasurementTypeResponse(
        id=measurement_type.id,
        project_id=measurement_type.project_id,
        name=measurement_type.name,
        unit=measurement_type.unit,
        condition_id=measurement_type.condition_id,
        part_number_id=measurement_type.part_number_id,
        status=measurement_type.status,
    )


@router.post(
    "/projects/{project_id}/part-numbers",
    response_model=PartNumberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_part_number(
    project_id: UUID,
    payload: PartNumberCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PartNumberResponse:
    await _get_project_or_404(project_repo, project_id)
    part_number = await piece_repo.create_part_number(project_id, payload.name)
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="part_number",
        entity_id=part_number.id,
        action="part_number.created",
        diff={"name": part_number.name},
    )
    await session.commit()
    return PartNumberResponse(
        id=part_number.id, project_id=part_number.project_id, name=part_number.name
    )


@router.get("/projects/{project_id}/part-numbers", response_model=list[PartNumberResponse])
async def list_part_numbers(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
) -> list[PartNumberResponse]:
    await _get_project_or_404(project_repo, project_id)
    part_numbers = await piece_repo.list_part_numbers(project_id)
    return [
        PartNumberResponse(id=p.id, project_id=p.project_id, name=p.name) for p in part_numbers
    ]


@router.post(
    "/projects/{project_id}/piece-conditions",
    response_model=PieceConditionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_piece_condition(
    project_id: UUID,
    payload: PieceConditionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PieceConditionResponse:
    await _get_project_or_404(project_repo, project_id)
    condition = await piece_repo.create_piece_condition(project_id, payload.name)
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="piece_condition",
        entity_id=condition.id,
        action="piece_condition.created",
        diff={"name": condition.name},
    )
    await session.commit()
    return PieceConditionResponse(
        id=condition.id, project_id=condition.project_id, name=condition.name
    )


@router.get(
    "/projects/{project_id}/piece-conditions", response_model=list[PieceConditionResponse]
)
async def list_piece_conditions(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
) -> list[PieceConditionResponse]:
    await _get_project_or_404(project_repo, project_id)
    conditions = await piece_repo.list_piece_conditions(project_id)
    return [
        PieceConditionResponse(id=c.id, project_id=c.project_id, name=c.name) for c in conditions
    ]


@router.post(
    "/projects/{project_id}/piece-locations",
    response_model=PieceLocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_piece_location(
    project_id: UUID,
    payload: PieceLocationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PieceLocationResponse:
    await _get_project_or_404(project_repo, project_id)
    location = await piece_repo.create_piece_location(project_id, payload.name)
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="piece_location",
        entity_id=location.id,
        action="piece_location.created",
        diff={"name": location.name},
    )
    await session.commit()
    return PieceLocationResponse(
        id=location.id, project_id=location.project_id, name=location.name
    )


@router.get("/projects/{project_id}/piece-locations", response_model=list[PieceLocationResponse])
async def list_piece_locations(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
) -> list[PieceLocationResponse]:
    await _get_project_or_404(project_repo, project_id)
    locations = await piece_repo.list_piece_locations(project_id)
    return [
        PieceLocationResponse(id=loc.id, project_id=loc.project_id, name=loc.name)
        for loc in locations
    ]


@router.post(
    "/projects/{project_id}/measurement-types",
    response_model=MeasurementTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_measurement_type(
    project_id: UUID,
    payload: MeasurementTypeCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MeasurementTypeResponse:
    await _get_project_or_404(project_repo, project_id)
    measurement_type = await piece_repo.create_measurement_type(
        project_id,
        payload.name,
        payload.unit,
        payload.condition_id,
        payload.part_number_id,
        payload.status,
    )
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="measurement_type",
        entity_id=measurement_type.id,
        action="measurement_type.created",
        diff={"name": measurement_type.name, "unit": measurement_type.unit},
    )
    await session.commit()
    return _measurement_type_response(measurement_type)


@router.get(
    "/projects/{project_id}/measurement-types", response_model=list[MeasurementTypeResponse]
)
async def list_measurement_types(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
) -> list[MeasurementTypeResponse]:
    await _get_project_or_404(project_repo, project_id)
    types = await piece_repo.list_measurement_types(project_id)
    return [_measurement_type_response(t) for t in types]


@router.patch("/measurement-types/{measurement_type_id}", response_model=MeasurementTypeResponse)
async def update_measurement_type(
    measurement_type_id: UUID,
    payload: MeasurementTypeUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MeasurementTypeResponse:
    existing = await _get_measurement_type_or_404(piece_repo, measurement_type_id)
    updated = await piece_repo.update_measurement_type(
        measurement_type_id,
        name=payload.name,
        unit=payload.unit,
        condition_id=payload.condition_id,
        part_number_id=payload.part_number_id,
        status=payload.status,
    )
    await audit.record(
        project_id=existing.project_id,
        actor_id=current_user.id,
        entity_type="measurement_type",
        entity_id=measurement_type_id,
        action="measurement_type.updated",
        diff={"name": updated.name, "unit": updated.unit},
    )
    await session.commit()
    return _measurement_type_response(updated)


@router.delete("/measurement-types/{measurement_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_measurement_type(
    measurement_type_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    existing = await _get_measurement_type_or_404(piece_repo, measurement_type_id)
    await piece_repo.delete_measurement_type(measurement_type_id)
    await audit.record(
        project_id=existing.project_id,
        actor_id=current_user.id,
        entity_type="measurement_type",
        entity_id=measurement_type_id,
        action="measurement_type.deleted",
        diff={"name": existing.name},
    )
    await session.commit()
