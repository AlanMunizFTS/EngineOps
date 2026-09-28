from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from ops_platform.domain.entities import PieceStatus


class PartNumberCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class PartNumberResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str


class PieceConditionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class PieceConditionResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str


class PieceLocationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class PieceLocationResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str


class MeasurementTypeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=20)
    condition_id: UUID | None = None
    part_number_id: UUID | None = None
    status: PieceStatus | None = None


class MeasurementTypeUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=20)
    condition_id: UUID | None = None
    part_number_id: UUID | None = None
    status: PieceStatus | None = None


class MeasurementTypeResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    unit: str
    condition_id: UUID | None
    part_number_id: UUID | None
    status: PieceStatus | None


class MeasurementResponse(BaseModel):
    id: UUID
    piece_id: UUID
    measurement_type_id: UUID
    name: str
    unit: str
    value: Decimal


class PieceCreateRequest(BaseModel):
    part_number_id: UUID
    status: PieceStatus
    condition_ids: list[UUID] = Field(default_factory=list)
    location_id: UUID | None = None
    notes: str | None = None
    quantity: int = Field(default=1, ge=1, le=1000)


class PieceUpdateRequest(BaseModel):
    status: PieceStatus
    location_id: UUID | None = None
    notes: str | None = None
    condition_ids: list[UUID] = Field(default_factory=list)


class MeasurementSetRequest(BaseModel):
    value: Decimal


class PieceResponse(BaseModel):
    id: UUID
    project_id: UUID
    tracking_number: str
    part_number_id: UUID
    overall_status: PieceStatus
    location_id: UUID | None
    notes: str | None
    created_by: UUID | None
    created_at: datetime
    conditions: list[PieceConditionResponse]
    measurements: list[MeasurementResponse]
