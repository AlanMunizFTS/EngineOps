from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_piece_repository,
    get_project_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import MeasurementType, Piece, PieceStatus, User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.piece_repository import PieceRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.pieces import (
    MeasurementResponse,
    MeasurementSetRequest,
    PieceConditionResponse,
    PieceCreateRequest,
    PieceResponse,
    PieceUpdateRequest,
)

router = APIRouter(tags=["pieces"])


async def _get_project_or_404(project_repo: ProjectRepository, project_id: UUID) -> None:
    if await project_repo.get(project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


async def _get_piece_or_404(piece_repo: PieceRepository, piece_id: UUID) -> Piece:
    piece = await piece_repo.get(piece_id)
    if piece is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Piece not found")
    return piece


async def _measurement_types_by_id(
    piece_repo: PieceRepository, project_id: UUID
) -> dict[UUID, MeasurementType]:
    types = await piece_repo.list_measurement_types(project_id)
    return {t.id: t for t in types}


def _piece_response(
    piece: Piece, measurement_types_by_id: dict[UUID, MeasurementType]
) -> PieceResponse:
    return PieceResponse(
        id=piece.id,
        project_id=piece.project_id,
        tracking_number=piece.tracking_number,
        part_number_id=piece.part_number_id,
        overall_status=piece.overall_status,
        location_id=piece.location_id,
        notes=piece.notes,
        created_by=piece.created_by,
        created_at=piece.created_at,
        conditions=[
            PieceConditionResponse(id=c.id, project_id=c.project_id, name=c.name)
            for c in piece.conditions
        ],
        measurements=[
            MeasurementResponse(
                id=m.id,
                piece_id=m.piece_id,
                measurement_type_id=m.measurement_type_id,
                name=measurement_types_by_id[m.measurement_type_id].name,
                unit=measurement_types_by_id[m.measurement_type_id].unit,
                value=m.value,
            )
            for m in piece.measurements
        ],
    )


@router.post(
    "/projects/{project_id}/pieces",
    response_model=list[PieceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_pieces(
    project_id: UUID,
    payload: PieceCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[PieceResponse]:
    await _get_project_or_404(project_repo, project_id)
    pieces = await piece_repo.create_pieces(
        project_id=project_id,
        part_number_id=payload.part_number_id,
        overall_status=payload.status,
        condition_ids=payload.condition_ids,
        location_id=payload.location_id,
        notes=payload.notes,
        created_by=current_user.id,
        quantity=payload.quantity,
    )
    for piece in pieces:
        await audit.record(
            project_id=project_id,
            actor_id=current_user.id,
            entity_type="piece",
            entity_id=piece.id,
            action="piece.created",
            diff={"tracking_number": piece.tracking_number, "status": piece.overall_status.value},
        )
    await session.commit()
    measurement_types_by_id = await _measurement_types_by_id(piece_repo, project_id)
    return [_piece_response(piece, measurement_types_by_id) for piece in pieces]


@router.get("/projects/{project_id}/pieces", response_model=list[PieceResponse])
async def list_project_pieces(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
    part_number_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[PieceStatus | None, Query(alias="status")] = None,
    condition_id: Annotated[list[UUID] | None, Query()] = None,
    location_id: Annotated[UUID | None, Query()] = None,
    measurement_type_id: Annotated[UUID | None, Query()] = None,
    measurement_min: Annotated[Decimal | None, Query()] = None,
    measurement_max: Annotated[Decimal | None, Query()] = None,
) -> list[PieceResponse]:
    await _get_project_or_404(project_repo, project_id)
    pieces = await piece_repo.list_for_project(
        project_id,
        part_number_id=part_number_id,
        status=status_filter,
        condition_ids=condition_id,
        location_id=location_id,
        measurement_type_id=measurement_type_id,
        measurement_min=measurement_min,
        measurement_max=measurement_max,
    )
    measurement_types_by_id = await _measurement_types_by_id(piece_repo, project_id)
    return [_piece_response(piece, measurement_types_by_id) for piece in pieces]


@router.patch("/pieces/{piece_id}", response_model=PieceResponse)
async def update_piece(
    piece_id: UUID,
    payload: PieceUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PieceResponse:
    piece = await _get_piece_or_404(piece_repo, piece_id)
    updated = await piece_repo.update(
        piece_id,
        overall_status=payload.status,
        location_id=payload.location_id,
        notes=payload.notes,
        condition_ids=payload.condition_ids,
    )
    await audit.record(
        project_id=piece.project_id,
        actor_id=current_user.id,
        entity_type="piece",
        entity_id=piece_id,
        action="piece.updated",
        diff={
            "status": {"from": piece.overall_status.value, "to": updated.overall_status.value},
            "location_id": str(payload.location_id) if payload.location_id else None,
        },
    )
    await session.commit()
    measurement_types_by_id = await _measurement_types_by_id(piece_repo, updated.project_id)
    return _piece_response(updated, measurement_types_by_id)


@router.put("/pieces/{piece_id}/measurements/{measurement_type_id}", response_model=PieceResponse)
async def set_piece_measurement(
    piece_id: UUID,
    measurement_type_id: UUID,
    payload: MeasurementSetRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    piece_repo: Annotated[PieceRepository, Depends(get_piece_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PieceResponse:
    piece = await _get_piece_or_404(piece_repo, piece_id)
    updated = await piece_repo.set_measurement(piece_id, measurement_type_id, payload.value)
    await audit.record(
        project_id=piece.project_id,
        actor_id=current_user.id,
        entity_type="piece",
        entity_id=piece_id,
        action="piece.measurement_set",
        diff={"measurement_type_id": str(measurement_type_id), "value": str(payload.value)},
    )
    await session.commit()
    measurement_types_by_id = await _measurement_types_by_id(piece_repo, updated.project_id)
    return _piece_response(updated, measurement_types_by_id)
