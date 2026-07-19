from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ops_platform.domain.entities import ImplementationStatus
from ops_platform.schemas.projects import AreaStatusResponse


class PhaseUpdateRequest(BaseModel):
    """status_id: null clears the override and reverts to inheriting the
    parent's effective phase - see docs/architecture/adr/0003-phase-inheritance.md."""

    status_id: UUID | None


class PlantCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    location: str | None = None


class PlantResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    location: str | None
    created_at: datetime
    phase_status: AreaStatusResponse | None = None


class MachineCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    machine_type: str | None = None
    location: str | None = None


class MachineResponse(BaseModel):
    id: UUID
    plant_id: UUID
    name: str
    machine_type: str | None
    location: str | None
    created_at: datetime
    phase_status: AreaStatusResponse | None = None


class ImplementationCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=255)
    status: ImplementationStatus = ImplementationStatus.PLANNED


class ImplementationResponse(BaseModel):
    id: UUID
    machine_id: UUID
    label: str
    status: ImplementationStatus
    superseded_by: UUID | None
    created_at: datetime
    phase_status: AreaStatusResponse | None = None
